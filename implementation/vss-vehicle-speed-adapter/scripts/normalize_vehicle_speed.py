#!/usr/bin/env python3
"""Run the provider-neutral adapter against one JSON sample."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from de4sdv_vss_vehicle_speed_adapter import (  # noqa: E402
    AdapterConfig,
    SampleValidationError,
    SignalQuality,
    VehicleSpeedSample,
    VssVehicleSpeedAdapter,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sample", help="JSON object containing a VSS Vehicle.Speed sample")
    parser.add_argument("--now-ns", type=int, default=None)
    parser.add_argument("--max-age-ns", type=int, default=None)
    args = parser.parse_args()

    try:
        raw = json.loads(args.sample)
        sample = VehicleSpeedSample(
            value=raw["value"],
            unit=raw["unit"],
            timestamp_ns=raw["timestamp_ns"],
            clock_domain=raw["clock_domain"],
            quality=SignalQuality(raw["quality"]),
            semantic_path=raw.get("semantic_path", "Vehicle.Speed"),
        )
        output = VssVehicleSpeedAdapter(
            AdapterConfig(max_age_ns=args.max_age_ns)
        ).translate(sample, now_ns=args.now_ns)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"invalid sample: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "semantic_path": output.semantic_path,
                "longitudinal_velocity_mps": output.longitudinal_velocity_mps,
                "timestamp_ns": output.timestamp_ns,
                "clock_domain": output.clock_domain,
                "quality": output.quality.value,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
