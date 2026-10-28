from sca.config import CITIES
from sca.sources import buildings_query, parse_buildings, parse_stations, station_query

STATIONS = {
    "elements": [
        {"type": "node", "id": 1, "lat": 56.17, "lon": 10.20, "tags": {"name": "Aarhus H", "network": "Aarhus Letbane"}},
        {"type": "node", "id": 1, "lat": 56.17, "lon": 10.20, "tags": {"name": "Aarhus H"}},  # duplicate id
        {"type": "node", "id": 2, "lat": 56.20, "lon": 10.10, "tags": {"name": "Lystrup"}},
        {"type": "way", "id": 3, "center": {"lat": 56.25, "lon": 10.30}, "tags": {"name": "Mårslet"}},
        {"type": "node", "id": 4, "tags": {"name": "no position"}},  # no coordinates: dropped
    ]
}

BUILDINGS = {
    "elements": [
        {"type": "way", "id": 10, "center": {"lat": 56.1, "lon": 10.1}, "tags": {"building": "apartments"}},
        {"type": "way", "id": 11, "center": {"lat": 56.2, "lon": 10.2}, "tags": {"building": "house"}},
        {"type": "way", "id": 12, "tags": {"building": "yes"}},  # no centre: dropped
    ]
}


def test_parse_stations_dedupes_and_sorts():
    stations = parse_stations(STATIONS)
    assert [s["name"] for s in stations] == ["Aarhus H", "Lystrup", "Mårslet"]
    assert stations[2]["lat"] == 56.25 and stations[2]["lon"] == 10.30
    assert stations[1]["network"] == ""


def test_parse_buildings_uses_centres():
    assert parse_buildings(BUILDINGS) == [(56.1, 10.1), (56.2, 10.2)]


def test_queries_select_the_network_and_bbox():
    aarhus = station_query(CITIES["aarhus"])
    assert '"light_rail"="yes"' in aarhus and "(56.0,10.0,56.5,10.5)" in aarhus
    copenhagen = station_query(CITIES["copenhagen"])
    assert '"station"="subway"' in copenhagen
    q = buildings_query(56.1, 10.1, 56.2, 10.2)
    assert '"building"~"^(apartments|residential|house' in q and "(56.1,10.1,56.2,10.2)" in q
