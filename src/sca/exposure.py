"""Topographic exposure of each station: is it lower than its surroundings?

This is a screening index for surface water collecting during cloudbursts. It is
not a hydraulic model. It uses only the DEM surface (buildings and trees included)
and no drainage network or rainfall.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .config import EXPOSURE_RADIUS_M, FULL_DEPRESSION_M, HIGH_EXPOSURE_INDEX


@dataclass(frozen=True)
class Exposure:
    station_elev_m: float
    ring_mean_m: float
    depression_m: float
    low_point_pct: float
    index: float

    @property
    def is_high(self) -> bool:
        return self.index >= HIGH_EXPOSURE_INDEX


def station_exposure(
    dem: np.ndarray,
    transform,
    x: float,
    y: float,
    radius_m: float = EXPOSURE_RADIUS_M,
) -> Exposure | None:
    """Exposure of the station at metric coordinates (x, y).

    depression_m: mean elevation of the ring within radius_m minus the station cell
        (positive means the station sits below its surroundings).
    low_point_pct: share of ring cells higher than the station (100 = a pit).
    index: 0.5 * low_point share + 0.5 * min(depression / FULL_DEPRESSION_M, 1).
    Returns None when the station falls outside the DEM or on a nodata cell.
    """
    col_f, row_f = ~transform @ (x, y)
    row, col = math.floor(row_f), math.floor(col_f)
    height, width = dem.shape
    if not (0 <= row < height and 0 <= col < width):
        return None
    station_elev = float(dem[row, col])
    if np.isnan(station_elev):
        return None

    res = abs(transform.a)
    reach = math.ceil(radius_m / res)
    r0, r1 = max(row - reach, 0), min(row + reach + 1, height)
    c0, c1 = max(col - reach, 0), min(col + reach + 1, width)
    window = dem[r0:r1, c0:c1]
    rows, cols = np.mgrid[r0:r1, c0:c1]
    dist = np.hypot(rows - row, cols - col) * res
    ring_mask = (dist <= radius_m) & (dist > 0) & ~np.isnan(window)
    ring = window[ring_mask]
    if ring.size == 0:
        return None

    ring_mean = float(ring.mean())
    depression = ring_mean - station_elev
    low_share = float((ring > station_elev).mean())
    index = 0.5 * low_share + 0.5 * min(max(depression / FULL_DEPRESSION_M, 0.0), 1.0)
    return Exposure(
        station_elev_m=round(station_elev, 2),
        ring_mean_m=round(ring_mean, 2),
        depression_m=round(depression, 2),
        low_point_pct=round(100 * low_share, 1),
        index=round(index, 3),
    )
