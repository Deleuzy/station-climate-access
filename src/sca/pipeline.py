"""Glue: stations + buildings + DEM -> one ranked table per city."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from .access import count_within
from .config import ACCESS_RADII_M, MARGIN_DEG, METRIC_CRS, City
from .exposure import station_exposure
from .sources import buildings_query, load_or_fetch, parse_buildings, parse_stations, station_query
from .terrain import read_dem_metric


@dataclass
class CityInputs:
    stations: gpd.GeoDataFrame  # WGS84 points with name, network, lat, lon
    buildings_xy: np.ndarray  # (n, 2) in METRIC_CRS
    dem: np.ndarray
    transform: object


def compute_ranking(
    stations: gpd.GeoDataFrame,
    buildings_xy: np.ndarray,
    dem: np.ndarray,
    transform,
) -> pd.DataFrame:
    """Exposure and access for every station. Pure function: no network, no files."""
    metric = stations.to_crs(METRIC_CRS)
    rows = []
    for (_, station), point in zip(stations.iterrows(), metric.geometry):
        xy = (point.x, point.y)
        exposure = station_exposure(dem, transform, *xy)
        counts = count_within(xy, buildings_xy)
        rows.append(
            {
                "station": station["name"],
                "network": station["network"],
                "lat": round(station["lat"], 5),
                "lon": round(station["lon"], 5),
                "station_elev_m": exposure.station_elev_m if exposure else np.nan,
                "ring_mean_m": exposure.ring_mean_m if exposure else np.nan,
                "depression_m": exposure.depression_m if exposure else np.nan,
                "low_point_pct": exposure.low_point_pct if exposure else np.nan,
                "exposure_index": exposure.index if exposure else np.nan,
                "high_exposure": bool(exposure and exposure.is_high),
                "residential_400m": counts[ACCESS_RADII_M[0]],
                "residential_800m": counts[ACCESS_RADII_M[1]],
            }
        )
    table = pd.DataFrame(rows)
    median_800 = table["residential_800m"].median()
    table["high_access"] = table["residential_800m"] >= median_800
    table["high_exposure_and_access"] = table["high_exposure"] & table["high_access"]
    table = table.sort_values(
        ["high_exposure_and_access", "exposure_index", "residential_800m"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    table.insert(0, "rank", table.index + 1)
    return table


def load_city_inputs(city: City, data_dir: Path, offline: bool = False) -> CityInputs:
    """Fetch (or read cached) OSM data and read the DEM for one city."""
    raw = data_dir / "raw" / f"{city.key}_stations.json"
    stations_payload = load_or_fetch(raw, station_query(city), offline=offline)
    records = parse_stations(stations_payload)
    if not records:
        raise ValueError(f"no stations found for {city.label}")
    stations = gpd.GeoDataFrame(
        records,
        geometry=gpd.points_from_xy([r["lon"] for r in records], [r["lat"] for r in records]),
        crs="EPSG:4326",
    )

    south, west, north, east = _extent(stations)
    cache = data_dir / "cache" / f"{city.key}_buildings.json"
    buildings_payload = load_or_fetch(
        cache, buildings_query(south, west, north, east), offline=offline
    )
    centroids = parse_buildings(buildings_payload)
    buildings = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy([p[1] for p in centroids], [p[0] for p in centroids]),
        crs="EPSG:4326",
    ).to_crs(METRIC_CRS)
    buildings_xy = np.column_stack([buildings.geometry.x, buildings.geometry.y]) if len(centroids) else np.empty((0, 2))

    dem, transform = read_dem_metric(south, west, north, east)
    return CityInputs(stations=stations, buildings_xy=buildings_xy, dem=dem, transform=transform)


def _extent(stations: gpd.GeoDataFrame) -> tuple[float, float, float, float]:
    """Station extent plus a margin, so the 800 m rings are never clipped."""
    west, south, east, north = stations.total_bounds
    return (
        south - MARGIN_DEG,
        west - MARGIN_DEG,
        north + MARGIN_DEG,
        east + MARGIN_DEG,
    )


def run_city(city: City, data_dir: Path, out_dir: Path, offline: bool = False) -> pd.DataFrame:
    from .report import write_outputs

    inputs = load_city_inputs(city, data_dir, offline=offline)
    table = compute_ranking(inputs.stations, inputs.buildings_xy, inputs.dem, inputs.transform)
    write_outputs(table, inputs, out_dir / city.key)
    return table
