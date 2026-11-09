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
                              or frame | frame_index (x 0.1 s)
  ego speed:                  speed_mps | speed | speed_kmh | velocity
                              (velocity is [x, y, z] or {x, y, z}, m/s)
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
4. Write a table block for the run configuration, in the ICD v2 section 5
   form: each row is ``[acceleration_mps2, throttle, brake]``:

     {"longitudinal_controller": {"table": [[-8.0, 0.0, 1.0], ...]},
      "fit": {...provenance and residuals...}}

   The gains are not touched; merge the table into the run's vehicle limits
   configuration (ICD section 5).

Typical use:
  python3 scripts/fit_calibration.py --world run/simulator/world.jsonl \
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
            if value is None:
                value, count = median_pedal(window * 3.0, target, candidates)
            if value is None:
                value = interpolate(negative_curve[0], negative_curve[1], target)
            if value is None:
                continue
            brake = min(1.0, max(0.0, value))

        close = [a for a, _t, _b, _s in steady if abs(a - target) <= window]
        if close:
            residual = statistics.fmean(close) - target
            residuals.append(residual)
        rows.append(
            {
                "acceleration_mps2": round(target, 6),
                "throttle": round(throttle, 6),
                "brake": round(brake, 6),
                "_samples": count,
            }
        )
    return rows, residuals


def parse_targets(spec):
    parts = spec.split(":")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("--targets needs start:stop:step, e.g. -8:3:0.5")
    start, stop, step = (float(part) for part in parts)
    if step <= 0.0 or stop < start:
        raise argparse.ArgumentTypeError("--targets needs stop >= start and step > 0")
    count = int(round((stop - start) / step))
    return [round(start + index * step, 6) for index in range(count + 1)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--world", required=True, help="world.jsonl of the run")
    parser.add_argument("--out", required=True, help="table block to write (JSON)")
    parser.add_argument("--targets", default="-8:3:0.5", help="target accelerations start:stop:step (m/s^2)")
    parser.add_argument("--window", type=float, default=0.3, help="acceleration window of the median (m/s^2)")
    parser.add_argument("--min-speed", type=float, default=1.0, help="ignore ticks below this speed (m/s)")
    parser.add_argument("--steady-pedal", type=float, default=0.02,
                        help="max pedal variation over three ticks to count as steady")
    args = parser.parse_args(argv)

    targets = parse_targets(args.targets)
    samples, skipped = load_samples(args.world)
    if len(samples) < 10:
        print("fit_calibration: fewer than 10 usable world records in %s" % args.world, file=sys.stderr)
        return 2
    steady = steady_accelerations(samples, args.min_speed, args.steady_pedal)
    if len(steady) < 10:
        print("fit_calibration: no quasi-steady samples (need step responses with constant pedals)",
              file=sys.stderr)
        return 3

    rows, residuals = fit(steady, targets, args.window)
    if len(rows) < 3:
        print("fit_calibration: too few table rows fitted", file=sys.stderr)
        return 4

    rms = math.sqrt(statistics.fmean([value * value for value in residuals])) if residuals else None
    table = [
        [row["acceleration_mps2"], row["throttle"], row["brake"]]
        for row in rows
    ]
    document = {
        "longitudinal_controller": {"table": table},
        "fit": {
            "source": args.world,
            "records": len(samples),
            "skipped_records": skipped,
            "steady_samples": len(steady),
            "targets": args.targets,
            "window_mps2": args.window,
            "residual_rms_mps2": None if rms is None else round(rms, 6),
            "median_samples_per_row": statistics.median([row["_samples"] for row in rows]),
        },
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2)
        handle.write("\n")

    print("fit_calibration: %d records, %d steady, %d rows, residual RMS %s m/s^2 -> %s"
          % (len(samples), len(steady), len(rows),
             "n/a" if rms is None else "%.3f" % rms, args.out))
    for row in rows:
        print("  a=%+6.2f  throttle=%.3f  brake=%.3f  samples=%d"
              % (row["acceleration_mps2"], row["throttle"], row["brake"], row["_samples"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
