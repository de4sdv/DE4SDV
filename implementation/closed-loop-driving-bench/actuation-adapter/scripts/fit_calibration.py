#!/usr/bin/env python3
"""Fit the actuation adapter's longitudinal lookup table from world.jsonl.

The adapter realises a commanded acceleration with a feedforward lookup
(acceleration -> throttle or brake) plus a PI correction on the speed error.
The lookup is what this script fits: the steady-state pedal that holds each
acceleration on the pinned simulator and vehicle.

Input: the pacer's ``<run_dir>/simulator/world.jsonl`` (ICD section 7), one
JSON object per world tick. The ICD does not fix the field names yet, so the
extractor accepts the shapes below (top level, or under a ``data`` object):

  time (simulation seconds):  t_sim | sim_time | capture_time | time | t
                              or sim_ms (/ 1000) or frame | frame_index (x 0.1 s)
  ego speed:                  speed_mps | speed | speed_kmh | velocity
                              (velocity is [x, y, z], {x, y, z} or, as the world
                              side writes it, {speed_mps, heading_rad}; m/s)
  applied control:            control.throttle / control.brake,
                              control_applied.throttle / .brake,
                              throttle / brake

Records missing any of the three are skipped and counted. The script needs the
*applied* pedal of each tick, not the commanded acceleration.

Method
------
1. Acceleration is the central difference of speed over time.
2. Only quasi-steady samples count: the pedals are constant over the
   neighbouring ticks (``--steady-pedal``), the speed is above ``--min-speed``.
3. For each target acceleration, take the samples within ``--window`` m/s^2
   on the matching pedal side (throttle >= 0, brake < 0) and use the median
   pedal. If the window is empty, widen once and then interpolate the fitted
   (acceleration, pedal) curve of that side.
4. Refuse a side the log cannot support. A side's rows are its targets
   (throttle side >= 0 m/s^2, brake side < 0 m/s^2). A row is measured when at
   least ``--min-row-samples`` samples (default 3) lie within ``--window`` of
   its target, and a side is fitted only when at least ``--min-rows`` of its
   rows (default 3) are measured and the pedal of its measured rows is
   monotonic: more deceleration never needs less brake, more acceleration
   never needs less throttle.
   Otherwise the script names the side, how many of its rows hold samples and
   how many, and the limits, writes no table and exits with status 5.
   Why these limits: a row's pedal is the median of the samples in its window,
   and with fewer than three samples it is one tick or the mean of two, which a
   single transient tick sets. A row without samples of its own takes its
   pedal from the widened window or from the side's interpolated curve, which
   repeats its end values beyond the samples: one steady brake tick of a
   recorded closed-loop drive set all sixteen brake rows to 0.103. Three
   measured rows are the fewest that give the side a shape the monotonic check
   can test; two only give a straight line between them. Only the row's own
   window counts: with the default window and targets one tick lies in the own
   windows of up to two neighbouring rows and in the widened windows of two
   more, so counting those would let one tick pass for several rows. Both
   limits can be raised, not lowered: no option writes an unsupported side.
   A row that is not measured is no evidence of the side's shape, so it is not
   part of the monotonic check, and it is held between the measured rows
   around it: the widened window reaches further into the covered range than
   beyond it, so the first row past the end of what the log covers would
   otherwise sit below its measured neighbour (0.5975 at +3 m/s^2 under 0.5996
   at +2.5 m/s^2 on that recorded drive). The written side is then monotonic,
   and ``fit.sides`` counts the rows held.
5. Write a table block for the run configuration, in the ICD v2 section 5
   form: each row is ``[acceleration_mps2, throttle, brake]``:

     {"longitudinal_controller": {"table": [[-8.0, 0.0, 1.0], ...]},
      "fit": {...provenance, limits, residuals...}}

   The gains are not touched; merge the table into the run's vehicle limits
   configuration (ICD section 5).

One side only: a run that drives one side only (a braking run, for example) is
fitted with ``--side brake`` or ``--side throttle``, and then
``--other-side-from <configuration or table JSON>`` must name the table whose
rows of the other side are copied unchanged into the output (the rows at or
above 0 m/s^2 for the throttle side, below it for the brake side), so the
output stays a whole table that the merge below can use. ``fit.sides`` records
which side was fitted and which was copied from where. Without ``--side`` both
sides are fitted and both must be supported.

Typical use:
  python3 scripts/fit_calibration.py --world run/simulator/world.jsonl \
      --out run/calibration_table.json
  python3 scripts/fit_calibration.py --world run/simulator/world.jsonl \
      --side brake --other-side-from config/vehicle_limits.json \
      --out run/calibration_table.json
  jq -s '.[0] * {longitudinal_controller:
           (.[0].longitudinal_controller + {table: .[1].longitudinal_controller.table})}' \
      config/vehicle_limits.json run/calibration_table.json > run/vehicle_limits.json
"""

import argparse
import json
import math
import statistics
import sys


def _number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def _first(record, names):
    for name in names:
        if name in record:
            value = _number(record[name])
            if value is not None:
                return value
    return None


def _velocity_speed(value):
    if isinstance(value, dict) and "speed_mps" in value:
        return _number(value.get("speed_mps"))   # the world side's velocity {speed_mps, heading_rad}
    if isinstance(value, dict):
        components = [value.get("x"), value.get("y"), value.get("z", 0.0)]
    elif isinstance(value, (list, tuple)) and len(value) >= 2:
        components = list(value) + [0.0]
    else:
        return None
    numbers = []
    for component in components[:3]:
        number = _number(component)
        if number is None:
            return None
        numbers.append(number)
    return math.sqrt(sum(component * component for component in numbers))


def extract(record):
    """Returns (time_s, speed_mps, throttle, brake) or None."""
    containers = [record]
    if isinstance(record.get("data"), dict):
        containers.append(record["data"])
    for container in containers:
        if not isinstance(container, dict):
            continue
        time_s = _first(container, ("t_sim", "sim_time", "capture_time", "time", "t"))
        if time_s is None:
            sim_ms = _first(container, ("sim_ms",))
            if sim_ms is not None:
                time_s = sim_ms / 1000.0
        if time_s is None:
            frame = _first(container, ("frame", "frame_index", "frame_number"))
            if frame is not None:
                time_s = frame * 0.1
        speed = _first(container, ("speed_mps", "speed"))
        if speed is None:
            speed_kmh = _first(container, ("speed_kmh",))
            if speed_kmh is not None:
                speed = speed_kmh / 3.6
        if speed is None and "velocity" in container:
            speed = _velocity_speed(container["velocity"])
        control = None
        for key in ("control", "control_applied", "applied_control"):
            if isinstance(container.get(key), dict):
                control = container[key]
                break
        throttle = brake = None
        if control is not None:
            throttle = _number(control.get("throttle"))
            brake = _number(control.get("brake"))
        if throttle is None:
            throttle = _first(container, ("throttle", "applied_throttle"))
        if brake is None:
            brake = _first(container, ("brake", "applied_brake"))
        if None not in (time_s, speed, throttle, brake):
            return time_s, speed, throttle, brake
    return None


def load_samples(path):
    samples = []
    skipped = 0
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            parsed = extract(record)
            if parsed is None:
                skipped += 1
                continue
            samples.append(parsed)
    samples.sort(key=lambda item: item[0])
    return samples, skipped


def steady_accelerations(samples, min_speed, steady_pedal):
    """Yields (acceleration, throttle, brake, speed) of quasi-steady ticks."""
    out = []
    for index in range(1, len(samples) - 1):
        t0, v0, throttle0, brake0 = samples[index - 1]
        t1, v1, throttle1, brake1 = samples[index]
        t2, v2, throttle2, brake2 = samples[index + 1]
        if t1 <= t0 or t2 <= t1:
            continue
        if v1 < min_speed:
            continue
        if max(throttle0, throttle1, throttle2) - min(throttle0, throttle1, throttle2) > steady_pedal:
            continue
        if max(brake0, brake1, brake2) - min(brake0, brake1, brake2) > steady_pedal:
            continue
        if (throttle1 > 0.0) and (brake1 > 0.0):
            continue
        acceleration = (v2 - v0) / (t2 - t0)
        out.append((acceleration, throttle1, brake1, v1))
    return out


def collapse(pairs):
    """Sorts (x, y), averages duplicate x, returns two lists."""
    pairs = sorted(pairs, key=lambda item: item[0])
    xs, ys = [], []
    index = 0
    while index < len(pairs):
        x = pairs[index][0]
        group = []
        while index < len(pairs) and abs(pairs[index][0] - x) <= 1e-9:
            group.append(pairs[index][1])
            index += 1
        xs.append(x)
        ys.append(statistics.fmean(group))
    return xs, ys


def interpolate(xs, ys, x):
    if not xs:
        return None
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    low, high = 0, len(xs) - 1
    while high - low > 1:
        middle = (low + high) // 2
        if xs[middle] <= x:
            low = middle
        else:
            high = middle
    span = xs[high] - xs[low]
    weight = 0.0 if span <= 0.0 else (x - xs[low]) / span
    return ys[low] + weight * (ys[high] - ys[low])


def median_pedal(window, target, candidates):
    """Median pedal of the samples within `window` of `target`."""
    close = [pedal for acceleration, pedal, _speed in candidates if abs(acceleration - target) <= window]
    if not close:
        return None, 0
    return statistics.median(close), len(close)


def fit(steady, targets, window):
    positive = [(a, throttle) for a, throttle, _brake, _speed in steady if throttle > 0.0]
    negative = [(a, brake) for a, _throttle, brake, _speed in steady if brake > 0.0]
    positive_curve = collapse(positive)
    negative_curve = collapse(negative)

    rows = []
    residuals = []
    for target in targets:
        throttle = 0.0
        brake = 0.0
        count = 0
        if target >= 0.0:
            candidates = [(a, pedal, speed) for a, pedal, _brake, speed in steady if pedal > 0.0]
            value, count = median_pedal(window, target, candidates)
            own = count
            if value is None:
                value, count = median_pedal(window * 3.0, target, candidates)
            if value is None:
                value = interpolate(positive_curve[0], positive_curve[1], target)
            if value is None:
                continue
            throttle = min(1.0, max(0.0, value))
        else:
            candidates = [(a, pedal, speed) for a, _throttle, pedal, speed in steady if pedal > 0.0]
            value, count = median_pedal(window, target, candidates)
            own = count
            if value is None:
                value, count = median_pedal(window * 3.0, target, candidates)
            if value is None:
                value = interpolate(negative_curve[0], negative_curve[1], target)
            if value is None:
                continue
            brake = min(1.0, max(0.0, value))

        close = [a for a, _t, _b, _s in steady if abs(a - target) <= window]
        residual = None
        if close:
            residual = statistics.fmean(close) - target
            residuals.append(residual)
        rows.append(
            {
                "acceleration_mps2": round(target, 6),
                "throttle": round(throttle, 6),
                "brake": round(brake, 6),
                "_samples": count,
                "_own": own,
                "_residual": residual,
            }
        )
    return rows, residuals


SIDES = ("throttle", "brake")
# Step 4 of the method: the defaults of --min-rows and --min-row-samples, which are also their floors.
MIN_ROWS = 3
MIN_ROW_SAMPLES = 3


def side_of(acceleration):
    """The pedal side of a target: throttle at or above 0 m/s^2, brake below."""
    return "throttle" if acceleration >= 0.0 else "brake"


def _plural(count, word):
    return "%d %s%s" % (count, word, "" if count == 1 else "s")


def side_refusals(side, rows, side_targets, steady, window, min_rows, min_row_samples):
    """The reasons the log cannot support `side`; empty when it can."""
    reasons = []
    side_rows = [row for row in rows if side_of(row["acceleration_mps2"]) == side]
    own_counts = [row["_own"] for row in side_rows]
    measured = sum(1 for count in own_counts if count >= min_row_samples)
    if measured < min_rows:
        holding = [count for count in own_counts if count > 0]
        steady_on_side = sum(1 for _a, throttle, brake, _s in steady
                             if (throttle if side == "throttle" else brake) > 0.0)
        reasons.append(
            "%s side not fitted: %d of its %d rows hold at least %d samples within %.2f m/s^2 of their target; "
            "%s %s any, %s in all, from %s in the log. Limits: at least %d such rows (--min-rows %d) "
            "of at least %d samples (--min-row-samples %d)."
            % (side, measured, len(side_targets), min_row_samples, window,
               _plural(len(holding), "row"), "holds" if len(holding) == 1 else "hold",
               _plural(sum(holding), "sample"), _plural(steady_on_side, "steady %s sample" % side),
               min_rows, min_rows, min_row_samples, min_row_samples))
    falls = []
    measured_rows = [row for row in side_rows if row["_own"] >= min_row_samples]
    for lower, upper in zip(measured_rows, measured_rows[1:]):
        if side == "throttle" and upper["throttle"] < lower["throttle"]:
            falls.append("%.4f at %+.2f m/s^2 is less than %.4f at %+.2f m/s^2"
                         % (upper["throttle"], upper["acceleration_mps2"],
                            lower["throttle"], lower["acceleration_mps2"]))
        if side == "brake" and lower["brake"] < upper["brake"]:
            falls.append("%.4f at %+.2f m/s^2 is less than %.4f at %+.2f m/s^2"
                         % (lower["brake"], lower["acceleration_mps2"],
                            upper["brake"], upper["acceleration_mps2"]))
    if falls:
        reasons.append("%s side not fitted: the pedal of its measured rows is not monotonic in the acceleration "
                       "(more %s never needs less %s): %s."
                       % (side, "acceleration" if side == "throttle" else "deceleration", side, "; ".join(falls)))
    return reasons


def hold_unmeasured_rows(rows, side, min_row_samples):
    """Keep each row of `side` without enough samples of its own between the measured rows around it.

    The rows are walked from the least demand to the most (throttle: rising acceleration, brake: rising
    deceleration). A measured row keeps its pedal. A row that is not measured keeps the pedal the widened window
    or the interpolated curve gave it, unless that is below the row before it or above the next measured row;
    then it takes that row's pedal. With monotonic measured rows the side is monotonic afterwards. Returns the
    number of rows whose pedal it changed.
    """
    side_rows = [row for row in rows if side_of(row["acceleration_mps2"]) == side]
    ordered = side_rows if side == "throttle" else side_rows[::-1]
    measured = [index for index, row in enumerate(ordered) if row["_own"] >= min_row_samples]
    held = 0
    floor = 0.0
    for index, row in enumerate(ordered):
        if row["_own"] < min_row_samples:
            later = [m for m in measured if m > index]
            ceiling = ordered[later[0]][side] if later else 1.0
            pedal = min(max(row[side], floor), ceiling)
            if pedal != row[side]:
                row["_held_from"] = row[side]
                row[side] = pedal
                held += 1
        floor = row[side]
    return held


def load_table_rows(path):
    """The rows of the longitudinal table in a configuration or table JSON, as [a, throttle, brake]."""
    with open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    controller = document.get("longitudinal_controller") if isinstance(document, dict) else None
    table = controller.get("table") if isinstance(controller, dict) else None
    if not isinstance(table, list):
        raise ValueError("%s has no longitudinal_controller.table" % path)
    rows = []
    for row in table:
        if isinstance(row, dict):
            row = [row.get("acceleration_mps2"), row.get("throttle"), row.get("brake")]
        values = [_number(value) for value in row] if isinstance(row, list) and len(row) == 3 else []
        numbers = [value for value in values if value is not None]
        if len(numbers) != 3 or not all(0.0 <= pedal <= 1.0 for pedal in numbers[1:]):
            raise ValueError("%s: table row %r is not [acceleration_mps2, throttle, brake] with pedals in [0, 1]"
                             % (path, row))
        if rows and not numbers[0] > rows[-1][0]:
            raise ValueError("%s: the table is not sorted by strictly increasing acceleration" % path)
        rows.append(numbers)
    return rows


def parse_targets(spec):
    parts = spec.split(":")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("--targets needs start:stop:step, e.g. --targets=-8:3:0.5")
    start, stop, step = (float(part) for part in parts)
    if step <= 0.0 or stop < start:
        raise argparse.ArgumentTypeError("--targets needs stop >= start and step > 0")
    count = int(round((stop - start) / step))
    return [round(start + index * step, 6) for index in range(count + 1)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--world", required=True, help="world.jsonl of the run")
    parser.add_argument("--out", required=True, help="table block to write (JSON)")
    parser.add_argument("--targets", default="-8:3:0.5", help="target accelerations start:stop:step (m/s^2); a range that starts below zero needs the = form, --targets=-8:3:0.5, or argparse reads it as an option")
    parser.add_argument("--window", type=float, default=0.3, help="acceleration window of the median (m/s^2)")
    parser.add_argument("--min-speed", type=float, default=1.0, help="ignore ticks below this speed (m/s)")
    parser.add_argument("--steady-pedal", type=float, default=0.02,
                        help="max pedal variation over three ticks to count as steady")
    parser.add_argument("--min-rows", type=int, default=MIN_ROWS,
                        help="rows of a side that must be measured for the side to be fitted (default %d, "
                             "at least %d)" % (MIN_ROWS, MIN_ROWS))
    parser.add_argument("--min-row-samples", type=int, default=MIN_ROW_SAMPLES,
                        help="samples within --window of its target that make a row measured (default %d, "
                             "at least %d)" % (MIN_ROW_SAMPLES, MIN_ROW_SAMPLES))
    parser.add_argument("--side", choices=("both",) + SIDES, default="both",
                        help="fit both sides (default) or one; one side needs --other-side-from")
    parser.add_argument("--other-side-from", metavar="JSON",
                        help="with --side: configuration or table whose rows of the other side are copied unchanged")
    args = parser.parse_args(argv)
    if args.min_rows < MIN_ROWS:
        parser.error("--min-rows must be at least %d: fewer measured rows cannot show the side's shape" % MIN_ROWS)
    if args.min_row_samples < MIN_ROW_SAMPLES:
        parser.error("--min-row-samples must be at least %d: below that a row is one or two ticks"
                     % MIN_ROW_SAMPLES)
    if args.side != "both" and not args.other_side_from:
        parser.error("--side %s fits one side only: name the table its other side is copied from with "
                     "--other-side-from" % args.side)
    if args.side == "both" and args.other_side_from:
        parser.error("--other-side-from copies the side --side does not fit: give --side throttle or --side brake")

    targets = parse_targets(args.targets)
    fitted_sides = SIDES if args.side == "both" else (args.side,)
    copied_rows = []
    if args.side != "both":
        try:
            copied_rows = [row for row in load_table_rows(args.other_side_from)
                           if side_of(row[0]) != args.side]
        except (OSError, ValueError) as error:
            print("fit_calibration: cannot copy the other side: %s" % error, file=sys.stderr)
            return 2
        if not copied_rows:
            print("fit_calibration: %s has no rows of the side --side %s does not fit"
                  % (args.other_side_from, args.side), file=sys.stderr)
            return 2

    samples, skipped = load_samples(args.world)
    if len(samples) < 10:
        print("fit_calibration: fewer than 10 usable world records in %s" % args.world, file=sys.stderr)
        return 2
    steady = steady_accelerations(samples, args.min_speed, args.steady_pedal)
    if len(steady) < 10:
        print("fit_calibration: no quasi-steady samples (need step responses with constant pedals)",
              file=sys.stderr)
        return 3

    rows, _residuals = fit(steady, targets, args.window)
    rows = [row for row in rows if side_of(row["acceleration_mps2"]) in fitted_sides]
    refusals = []
    for side in fitted_sides:
        refusals += side_refusals(side, rows, [target for target in targets if side_of(target) == side],
                                  steady, args.window, args.min_rows, args.min_row_samples)
    if refusals:
        for reason in refusals:
            print("fit_calibration: " + reason, file=sys.stderr)
        print("fit_calibration: no table written to %s (the README lists the manoeuvres each side needs)"
              % args.out, file=sys.stderr)
        return 5
    held_rows = {side: hold_unmeasured_rows(rows, side, args.min_row_samples) for side in fitted_sides}

    table = sorted([[row["acceleration_mps2"], row["throttle"], row["brake"]] for row in rows] + copied_rows)
    if len(table) < 3:
        print("fit_calibration: too few table rows fitted", file=sys.stderr)
        return 4

    residuals = [row["_residual"] for row in rows if row["_residual"] is not None]
    rms = math.sqrt(statistics.fmean([value * value for value in residuals])) if residuals else None
    sides = {}
    for side in SIDES:
        side_rows = [row for row in rows if side_of(row["acceleration_mps2"]) == side]
        if side in fitted_sides:
            sides[side] = {"source": "fitted", "rows": len(side_rows),
                           "measured_rows": sum(1 for row in side_rows if row["_own"] >= args.min_row_samples),
                           "samples_in_own_windows": sum(row["_own"] for row in side_rows),
                           "held_rows": held_rows[side]}
        else:
            sides[side] = {"source": "copied", "from": args.other_side_from, "rows": len(copied_rows)}
    document = {
        "longitudinal_controller": {"table": table},
        "fit": {
            "source": args.world,
            "records": len(samples),
            "skipped_records": skipped,
            "steady_samples": len(steady),
            "targets": args.targets,
            "window_mps2": args.window,
            "min_rows": args.min_rows,
            "min_row_samples": args.min_row_samples,
            "sides": sides,
            "residual_rms_mps2": None if rms is None else round(rms, 6),
            "median_samples_per_row": statistics.median([row["_samples"] for row in rows]),
        },
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2)
        handle.write("\n")

    print("fit_calibration: %d records, %d steady, %d rows, residual RMS %s m/s^2 -> %s"
          % (len(samples), len(steady), len(table),
             "n/a" if rms is None else "%.3f" % rms, args.out))
    for row in rows:
        held = "  held at its neighbour (the fill gave %.4f)" % row["_held_from"] if "_held_from" in row else ""
        print("  a=%+6.2f  throttle=%.3f  brake=%.3f  samples=%d%s"
              % (row["acceleration_mps2"], row["throttle"], row["brake"], row["_samples"], held))
    for row in copied_rows:
        print("  a=%+6.2f  throttle=%.3f  brake=%.3f  copied from %s"
              % (row[0], row[1], row[2], args.other_side_from))
    return 0


if __name__ == "__main__":
    sys.exit(main())
