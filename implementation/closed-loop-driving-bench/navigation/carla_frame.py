"""CARLA's world frame to the map frame the ICD and AutoE2E navigation use.

CARLA's world is left-handed: ``x`` forward, ``y`` to the **right**, ``z`` up,
and ``rotation.yaw`` grows clockwise seen from above (from ``+x`` towards
``+y``).  AutoE2E's navigation contract wants a right-handed metric frame with
the heading counter-clockwise from ``+x`` (its rasterizer rotates map points
into the ego frame with the usual ``R(-yaw)``).

The ICD (section 9) fixes the conversion: **x stays, y is negated**.  With
``y_map = -y_carla`` a heading of ``yaw_carla`` (clockwise, so direction
``(cos y, sin y)`` in CARLA) becomes ``(cos y, -sin y)`` in the map frame,
which is exactly ``yaw_map = -yaw_carla``.  So::

    x_map  =  x_carla
    y_map  = -y_carla
    yaw_map = -yaw_carla          (radians, either representation)

Everything downstream (map JSON, route file, ego pose, rasterizer) is in this
map frame.  A yaw taken from CARLA in degrees is converted as
``radians(-yaw_deg)``.

Consequences, deliberate and documented:

* The conversion is a mirror, so it flips handedness: a point that is on the
  driver's left in CARLA is on the driver's right in the map frame.  The
  exporter therefore keeps the CARLA-side labels in primitive ids
  (``:left``/``:right``) as provenance only; the rasterizer draws both sides
  into the same ``lane_boundary`` channel and closes drivable polygons by the
  even-odd rule, so neither label nor polygon winding affects a raster.
* Distances, lane widths and angles keep their magnitude; only the sign of
  lateral offsets and headings changes.
"""

from __future__ import annotations

import math


def carla_to_map_xy(x: float, y: float) -> tuple[float, float]:
    """CARLA world metres to map-frame metres."""
    return float(x), -float(y)


def carla_to_map_heading(yaw_rad: float) -> float:
    """CARLA yaw (clockwise, radians) to map-frame heading (CCW, radians)."""
    return -float(yaw_rad)


def carla_to_map_heading_deg(yaw_deg: float) -> float:
    """CARLA yaw in degrees to map-frame heading in radians."""
    return -math.radians(float(yaw_deg))


def carla_to_map_point(location) -> tuple[float, float]:
    """CARLA ``Location`` (or any object with .x/.y) to map-frame metres."""
    return carla_to_map_xy(location.x, location.y)


def right_vector(yaw_rad: float) -> tuple[float, float]:
    """Unit vector to the driver's right in the CARLA frame.

    CARLA yaw grows towards ``+y`` and ``+y`` is the driver's right, so the
    right vector is ``(cos(yaw + pi/2), sin(yaw + pi/2)) = (-sin, cos)``.
    """
    return -math.sin(yaw_rad), math.cos(yaw_rad)


def lane_boundary_points(
    centerline: list[tuple[float, float]],
    yaws_rad: list[float],
    half_widths: list[float],
    *,
    side: str,
) -> list[list[float]]:
    """Offset a CARLA lane centreline to one of its boundaries.

    ``side="left"`` moves to the driver's left, ``side="right"`` to the right,
    both in the CARLA frame; the result is returned in the map frame as
    ``[x, y, 0.0]`` triplets, the shape upstream's primitives take.
    """
    if side not in ("left", "right"):
        raise ValueError("side must be left or right")
    sign = -1.0 if side == "left" else 1.0
    points: list[list[float]] = []
    for (x, y), yaw, half_width in zip(centerline, yaws_rad, half_widths):
        rx, ry = right_vector(yaw)
        offset_x = x + sign * half_width * rx
        offset_y = y + sign * half_width * ry
        map_x, map_y = carla_to_map_xy(offset_x, offset_y)
        points.append([map_x, map_y, 0.0])
    return points
