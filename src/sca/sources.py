"""Fetch and parse OpenStreetMap data from the Overpass API.

Raw responses are cached as JSON. Parsing is kept apart from the network call so
the tests can run on small fixtures without any network access.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

from .config import OVERPASS_URLS, RESIDENTIAL_BUILDINGS, USER_AGENT, City


class OverpassError(RuntimeError):
    pass


def run_query(query: str, timeout: int = 180, rounds: int = 3) -> dict:
    """POST an Overpass QL query, trying each public endpoint in turn.

    Public Overpass servers often answer with HTTP 504 or an HTML busy page, so
    the whole list is retried with a growing pause between rounds.
    """
    last_error = None
    for attempt in range(rounds):
        for url in OVERPASS_URLS:
            try:
                response = requests.post(
                    url,
                    data={"data": query},
                    headers={"User-Agent": USER_AGENT},
                    timeout=timeout,
                )
            except requests.RequestException as exc:
                last_error = exc
                continue
            # Overpass returns HTML error pages with HTTP 200 when the server is busy.
            if response.status_code == 200 and response.text.lstrip().startswith("{"):
                return response.json()
            last_error = OverpassError(f"{url} returned HTTP {response.status_code}")
        time.sleep(30 * (attempt + 1))
    raise OverpassError(f"all Overpass endpoints failed: {last_error}")


def station_query(city: City) -> str:
    south, west, north, east = city.station_search_bbox
    return (
        "[out:json][timeout:90];"
        f"nwr{city.station_filter}({south},{west},{north},{east});"
        "out tags center;"
    )


def buildings_query(south: float, west: float, north: float, east: float) -> str:
    return (
        "[out:json][timeout:180];"
        f'way["building"~"^({RESIDENTIAL_BUILDINGS})$"]({south},{west},{north},{east});'
        "out center;"
    )


def parse_stations(payload: dict) -> list[dict]:
    """Return one dict per station with name, network, lat and lon."""
    stations = []
    seen = set()
    for element in payload.get("elements", []):
        key = (element["type"], element["id"])
        if key in seen:
            continue
        seen.add(key)
        lat, lon = _position(element)
        if lat is None:
            continue
        tags = element.get("tags", {})
        stations.append(
            {
                "osm_id": f'{element["type"]}/{element["id"]}',
                "name": tags.get("name", "(unnamed)"),
                "network": tags.get("network", ""),
                "lat": lat,
                "lon": lon,
            }
        )
    return sorted(stations, key=lambda s: s["name"])


def parse_buildings(payload: dict) -> list[tuple[float, float]]:
    """Return (lat, lon) centroids of residential building ways."""
    points = []
    for element in payload.get("elements", []):
        lat, lon = _position(element)
        if lat is not None:
            points.append((lat, lon))
    return points


def _position(element: dict) -> tuple[float | None, float | None]:
    if "lat" in element and "lon" in element:
        return element["lat"], element["lon"]
    center = element.get("center")
    if center:
        return center["lat"], center["lon"]
    return None, None


def load_or_fetch(cache_path: Path, query: str, offline: bool = False) -> dict:
    """Return the cached Overpass JSON, fetching and caching it when missing."""
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    if offline:
        raise FileNotFoundError(f"{cache_path} missing and --offline was given")
    payload = run_query(query)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload
