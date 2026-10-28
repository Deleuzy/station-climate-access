"""Access: how many residential buildings lie within walking distance of each station."""

from __future__ import annotations

import numpy as np

from .config import ACCESS_RADII_M


def count_within(
    station_xy: tuple[float, float],
    building_xy: np.ndarray,
    radii_m: tuple[int, ...] = ACCESS_RADII_M,
) -> dict[int, int]:
    """Count building points within each radius (straight-line, metric CRS).

    building_xy is an (n, 2) array in the same metric CRS as station_xy.
    """
    if building_xy.size == 0:
        return {r: 0 for r in radii_m}
    dist = np.hypot(building_xy[:, 0] - station_xy[0], building_xy[:, 1] - station_xy[1])
    return {r: int(np.count_nonzero(dist <= r)) for r in radii_m}
