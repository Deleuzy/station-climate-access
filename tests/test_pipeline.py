import geopandas as gpd
import numpy as np

from sca.config import METRIC_CRS
from sca.pipeline import compute_ranking
from sca.report import write_outputs

from conftest import cell_centre, ORIGIN_X, ORIGIN_Y, RES


def _lonlat(col, row, transform_crs=METRIC_CRS):
    # Convert a grid cell centre back to WGS84 so the table looks like real input.
    point = gpd.GeoSeries(gpd.points_from_xy([cell_centre(col, row)[0]], [cell_centre(col, row)[1]]), crs=METRIC_CRS)
    p = point.to_crs("EPSG:4326").iloc[0]
    return p.y, p.x


def _stations(cells):
    records = []
    for name, (col, row) in cells.items():
        lat, lon = _lonlat(col, row)
        records.append({"name": name, "network": "Test", "lat": lat, "lon": lon})
    return gpd.GeoDataFrame(records, geometry=gpd.points_from_xy([r["lon"] for r in records], [r["lat"] for r in records]), crs="EPSG:4326")


def test_ranking_puts_pit_next_to_dense_area_first(grid_transform, flat_dem):
    dem = flat_dem.copy()
    dem[50, 50] = 10.0  # pit station
    stations = _stations({"Pit": (50, 50), "Hill": (20, 20)})
    dem[20, 20] = 30.0  # hill station on high ground
    # 40 buildings close to the pit, 3 near the hill
    buildings = np.array([cell_centre(50 + i % 5, 50 + i // 5) for i in range(40)]
                         + [cell_centre(20, 20 + i) for i in range(3)])
    table = compute_ranking(stations, buildings, dem, grid_transform)
    assert table.loc[0, "station"] == "Pit"
    assert bool(table.loc[0, "high_exposure_and_access"])
    assert table.loc[0, "residential_800m"] == 40  # hill buildings are about 900 m away
    assert table.loc[1, "station"] == "Hill"
    assert not table.loc[1, "high_exposure"]


def test_outside_dem_station_has_nan_but_is_kept(grid_transform, flat_dem):
    stations = _stations({"Inside": (50, 50)})
    far = gpd.GeoDataFrame(
        [{"name": "Far", "network": "Test", "lat": 60.0, "lon": 20.0}],
        geometry=gpd.points_from_xy([20.0], [60.0]),
        crs="EPSG:4326",
    )
    stations = gpd.GeoDataFrame(
        list(stations.drop(columns="geometry").to_dict("records")) + list(far.drop(columns="geometry").to_dict("records")),
        geometry=list(stations.geometry) + list(far.geometry),
        crs="EPSG:4326",
    )
    table = compute_ranking(stations, np.empty((0, 2)), flat_dem, grid_transform)
    row = table.set_index("station").loc["Far"]
    assert np.isnan(row["exposure_index"]) and row["high_exposure"] == False  # noqa: E712


def test_write_outputs_creates_all_files(tmp_path, grid_transform, flat_dem):
    dem = flat_dem.copy()
    dem[50, 50] = 10.0
    stations = _stations({"Pit": (50, 50), "Flat": (30, 30)})
    buildings = np.array([cell_centre(50, 50)] * 10)
    table = compute_ranking(stations, buildings, dem, grid_transform)

    class Inputs:
        pass

    inputs = Inputs()
    inputs.stations = stations
    inputs.dem = dem
    inputs.transform = grid_transform
    write_outputs(table, inputs, tmp_path)
    for name in ["ranking.csv", "stations.geojson", "map.html", "map.png"]:
        assert (tmp_path / name).stat().st_size > 0
    csv = (tmp_path / "ranking.csv").read_text()
    assert "exposure_index" in csv and "Pit" in csv
