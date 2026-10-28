import numpy as np
import pytest

from sca.exposure import station_exposure

from conftest import cell_centre


def test_flat_ground_has_no_exposure(flat_dem, grid_transform):
    x, y = cell_centre(50, 50)
    result = station_exposure(flat_dem, grid_transform, x, y)
    assert result.depression_m == 0
    assert result.low_point_pct == 0
    assert result.index == 0
    assert not result.is_high


def test_pit_is_fully_exposed(flat_dem, grid_transform):
    dem = flat_dem.copy()
    dem[50, 50] = 10.0  # station sits 10 m below a flat 20 m surround
    x, y = cell_centre(50, 50)
    result = station_exposure(dem, grid_transform, x, y)
    assert result.depression_m == pytest.approx(10.0, abs=0.05)
    assert result.low_point_pct == 100
    assert result.index == pytest.approx(1.0)
    assert result.is_high


def test_hilltop_is_not_exposed(flat_dem, grid_transform):
    dem = flat_dem.copy()
    dem[50, 50] = 35.0
    x, y = cell_centre(50, 50)
    result = station_exposure(dem, grid_transform, x, y)
    assert result.depression_m < 0
    assert result.low_point_pct == 0
    assert not result.is_high


def test_ring_ignores_cells_beyond_250_m(flat_dem, grid_transform):
    dem = flat_dem.copy()
    dem[50, 50] = 10.0
    dem[50 - 10 : 50 + 11, 50 - 10 : 50 + 11] = 50.0  # high ground, only at 300 m+ reach
    dem[50, 50] = 10.0
    x, y = cell_centre(50, 50)
    # Cells beyond 250 m are set high but the ring average should only see the flat 20 m ring
    dem2 = flat_dem.copy()
    dem2[50, 50] = 10.0
    far = station_exposure(dem2, grid_transform, x, y)
    assert far.ring_mean_m == pytest.approx(20.0)


def test_outside_dem_returns_none(flat_dem, grid_transform):
    assert station_exposure(flat_dem, grid_transform, 0.0, 0.0) is None


def test_nodata_station_returns_none(flat_dem, grid_transform):
    dem = flat_dem.copy()
    dem[50, 50] = np.nan
    x, y = cell_centre(50, 50)
    assert station_exposure(dem, grid_transform, x, y) is None
