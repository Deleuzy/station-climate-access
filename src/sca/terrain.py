"""Copernicus DEM GLO-30 access: tile naming and reading a study area in metric CRS."""

from __future__ import annotations

import math

import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject, transform_bounds

from .config import DEM_BASE_URL, DEM_RESOLUTION_M, METRIC_CRS


def tile_name(lat_floor: int, lon_floor: int) -> str:
    """Copernicus tile id, e.g. N56_00_E010_00 for the tile covering 56-57 N, 10-11 E."""
    ns = "N" if lat_floor >= 0 else "S"
    ew = "E" if lon_floor >= 0 else "W"
    return f"{ns}{abs(lat_floor):02d}_00_{ew}{abs(lon_floor):03d}_00"


def tile_urls_for_bbox(south: float, west: float, north: float, east: float) -> list[str]:
    """GDAL /vsicurl/ paths of every 1-degree tile touching the bounding box."""
    urls = []
    for lat in range(math.floor(south), math.ceil(north)):
        for lon in range(math.floor(west), math.ceil(east)):
            name = tile_name(lat, lon)
            base = f"Copernicus_DSM_COG_10_{name}_DEM"
            urls.append(f"/vsicurl/{DEM_BASE_URL}/{base}/{base}.tif")
    return urls


def read_dem_metric(south: float, west: float, north: float, east: float):
    """Read the DEM over a WGS84 box and resample it to 30 m in the metric CRS.

    Returns (array, transform) with NaN for missing cells. Reads only the needed
    windows over HTTP (COG range requests), not whole 1-degree tiles.
    """
    sources = [rasterio.open(url) for url in tile_urls_for_bbox(south, west, north, east)]
    try:
        mosaic, mosaic_transform = merge(sources, bounds=(west, south, east, north))
    finally:
        for src in sources:
            src.close()
    src_array = mosaic[0].astype("float32")
    src_nodata = src_array <= -9999  # defensive, the GLO-30 product has no nodata in Denmark
    src_array[src_nodata] = np.nan

    min_x, min_y, max_x, max_y = transform_bounds("EPSG:4326", METRIC_CRS, west, south, east, north)
    width = math.ceil((max_x - min_x) / DEM_RESOLUTION_M)
    height = math.ceil((max_y - min_y) / DEM_RESOLUTION_M)
    dst_transform = from_origin(min_x, max_y, DEM_RESOLUTION_M, DEM_RESOLUTION_M)
    dst = np.full((height, width), np.nan, dtype="float32")
    reproject(
        source=src_array,
        destination=dst,
        src_transform=mosaic_transform,
        src_crs="EPSG:4326",
        dst_transform=dst_transform,
        dst_crs=METRIC_CRS,
        src_nodata=np.nan,
        dst_nodata=np.nan,
        resampling=Resampling.bilinear,
    )
    return dst, dst_transform
