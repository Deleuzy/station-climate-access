import numpy as np
import pytest
from rasterio.transform import from_origin

from sca.config import METRIC_CRS

# A 30 m grid, 1 km x 1 km, origin at a round UTM coordinate (no network needed).
ORIGIN_X, ORIGIN_Y, RES = 600_000.0, 6_200_000.0, 30.0


@pytest.fixture
def grid_transform():
    return from_origin(ORIGIN_X, ORIGIN_Y, RES, RES)


@pytest.fixture
def flat_dem():
    return np.full((100, 100), 20.0, dtype="float32")


def cell_centre(col: int, row: int) -> tuple[float, float]:
    return ORIGIN_X + (col + 0.5) * RES, ORIGIN_Y - (row + 0.5) * RES
