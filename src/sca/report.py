"""Write the ranking CSV, a GeoJSON of stations, a folium map and a PNG map."""

from __future__ import annotations

from pathlib import Path

import folium
import geopandas as gpd
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from rasterio.transform import xy as transform_xy  # noqa: E402

from .config import HIGH_EXPOSURE_INDEX  # noqa: E402

CLASS_COLOURS = {
    "high exposure and access": "#b2182b",
    "high exposure": "#ef8a62",
    "high access": "#2166ac",
    "other": "#7f7f7f",
}


def station_class(row: pd.Series) -> str:
    if row["high_exposure_and_access"]:
        return "high exposure and access"
    if row["high_exposure"]:
        return "high exposure"
    if row["high_access"]:
        return "high access"
    return "other"


def write_outputs(table: pd.DataFrame, inputs, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    table = table.copy()
    table["class"] = table.apply(station_class, axis=1)
    table.to_csv(out_dir / "ranking.csv", index=False)

    geo = inputs.stations.merge(
        table.drop(columns=["lat", "lon", "network"]), left_on="name", right_on="station"
    )
    geo.drop(columns=["station"]).to_file(out_dir / "stations.geojson", driver="GeoJSON")

    write_folium(table, out_dir / "map.html")
    write_png(table, inputs.dem, inputs.transform, out_dir / "map.png")


def write_folium(table: pd.DataFrame, path: Path) -> None:
    centre = [table["lat"].mean(), table["lon"].mean()]
    fmap = folium.Map(location=centre, zoom_start=12, tiles="OpenStreetMap")
    for _, row in table.iterrows():
        colour = CLASS_COLOURS[row["class"]]
        popup = (
            f"<b>{row['station']}</b> (rank {row['rank']})<br>"
            f"Class: {row['class']}<br>"
            f"Elevation: {row['station_elev_m']} m, ring mean {row['ring_mean_m']} m<br>"
            f"Depression: {row['depression_m']} m, lower than {row['low_point_pct']}% of ring<br>"
            f"Exposure index: {row['exposure_index']}<br>"
            f"Residential buildings within 400 m: {row['residential_400m']}<br>"
            f"Residential buildings within 800 m: {row['residential_800m']}"
        )
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=4 + min(row["residential_800m"], 6000) / 600,
            color=colour,
            fill=True,
            fill_color=colour,
            fill_opacity=0.8,
            popup=folium.Popup(popup, max_width=320),
            tooltip=row["station"],
        ).add_to(fmap)
    legend = "".join(
        f'<div><span style="background:{c};display:inline-block;width:12px;height:12px"></span> {k}</div>'
        for k, c in CLASS_COLOURS.items()
    )
    fmap.get_root().html.add_child(
        folium.Element(
            '<div style="position:fixed;bottom:20px;left:20px;z-index:999;background:white;'
            'padding:8px;border:1px solid #999;font:12px sans-serif">'
            "<b>Station class</b><br>"
            f"{legend}"
            "<i>Circle size: residential buildings within 800 m</i></div>"
        )
    )
    fmap.save(str(path))


def write_png(table: pd.DataFrame, dem: np.ndarray, transform, path: Path) -> None:
    """Hillshade of the DEM with stations coloured by exposure and sized by access."""
    filled = np.where(np.isnan(dem), np.nanmin(dem), dem)
    dz_dy, dz_dx = np.gradient(filled, transform.e, transform.a)
    slope = np.arctan(np.hypot(dz_dx, dz_dy))
    aspect = np.arctan2(-dz_dy, dz_dx)
    azimuth, altitude = np.radians(315), np.radians(45)
    shade = np.sin(altitude) * np.cos(slope) + np.cos(altitude) * np.sin(slope) * np.cos(azimuth - aspect)
    shade = np.clip(shade, 0, 1)

    height, width = dem.shape
    x0, y0 = transform @ (0, 0)
    x1, y1 = transform @ (width, height)
    extent = [x0 / 1000, x1 / 1000, y1 / 1000, y0 / 1000]  # km, UTM 32N

    xs, ys = [], []
    from pyproj import Transformer

    to_metric = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True)
    for lon, lat in zip(table["lon"], table["lat"]):
        x, y = to_metric.transform(lon, lat)
        xs.append(x / 1000)
        ys.append(y / 1000)

    fig, ax = plt.subplots(figsize=(8, 8), dpi=150)
    ax.imshow(shade, cmap="Greys", extent=extent, alpha=0.6)
    colours = [CLASS_COLOURS[c] for c in table["class"]]
    sizes = 12 + table["residential_800m"].clip(upper=6000) / 40
    ax.scatter(xs, ys, s=sizes, c=colours, edgecolors="black", linewidths=0.4, zorder=3)
    for (_, row), x, y in zip(table.iterrows(), xs, ys):
        if row["high_exposure_and_access"]:
            ax.annotate(row["station"], (x, y), xytext=(4, 4), textcoords="offset points", fontsize=7)
    ax.set_title(f"Station exposure and access: {len(table)} stations")
    ax.set_xlabel("km (UTM 32N)")
    ax.set_ylabel("km (UTM 32N)")
    handles = [
        plt.Line2D([], [], marker="o", linestyle="", color=c, label=k) for k, c in CLASS_COLOURS.items()
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=7, framealpha=0.9)
    ax.text(
        0.99, 0.01,
        f"Exposure: high if index >= {HIGH_EXPOSURE_INDEX}\nDEM 30 m, Copernicus GLO-30",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=6,
    )
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
