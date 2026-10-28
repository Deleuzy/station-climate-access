"""Study areas, data sources and fixed thresholds.

Thresholds are set before the first run and are not tuned to the output.
"""

from dataclasses import dataclass

# Denmark: ETRS89 / UTM zone 32N. Metric distances are computed in this CRS.
METRIC_CRS = "EPSG:25832"

DEM_BASE_URL = "https://copernicus-dem-30m.s3.amazonaws.com"
DEM_RESOLUTION_M = 30

OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
USER_AGENT = "station-climate-access/0.1 (portfolio demo; github.com/Deleuzy/station-climate-access)"

# Residential building types in OSM (building=yes is excluded on purpose: it is ambiguous).
RESIDENTIAL_BUILDINGS = (
    "apartments|residential|house|detached|terrace|semidetached_house|dormitory|bungalow|houseboat"
)

EXPOSURE_RADIUS_M = 250
ACCESS_RADII_M = (400, 800)
# Stations at or above this index are "high exposure".
HIGH_EXPOSURE_INDEX = 0.6
# Depression (metres below the surrounding ring mean) that counts as a full depression term.
FULL_DEPRESSION_M = 5.0
# Margin added around the station extent for buildings and DEM reads (degrees, about 2 km).
MARGIN_DEG = 0.02


@dataclass(frozen=True)
class City:
    key: str
    label: str
    network: str
    # Bounding box for the Overpass station query: (south, west, north, east).
    station_search_bbox: tuple
    # Overpass tag filter that selects the network's stations.
    station_filter: str


CITIES = {
    "aarhus": City(
        key="aarhus",
        label="Aarhus",
        network="Aarhus Letbane",
        station_search_bbox=(56.0, 10.0, 56.5, 10.5),
        station_filter='["railway"~"^(station|halt)$"]["light_rail"="yes"]',
    ),
    "copenhagen": City(
        key="copenhagen",
        label="Copenhagen",
        network="Copenhagen Metro",
        station_search_bbox=(55.55, 12.40, 55.75, 12.70),
        station_filter='["railway"~"^(station|halt)$"]["station"="subway"]',
    ),
}
