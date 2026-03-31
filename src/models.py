"""
Pydantic models for the Geospatial Data Mainlayer API.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

class Coordinates(BaseModel):
    lat: float = Field(..., description="Latitude in decimal degrees")
    lon: float = Field(..., description="Longitude in decimal degrees")


class BoundingBox(BaseModel):
    north: float
    south: float
    east: float
    west: float


# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------

class GeocodeResult(BaseModel):
    address: str
    lat: float
    lon: float
    confidence: float = Field(..., ge=0.0, le=1.0)
    components: Dict[str, str] = Field(default_factory=dict)
    place_id: str
    formatted_address: str


class GeocodeResponse(BaseModel):
    query: str
    results: List[GeocodeResult]
    cost_usd: float = 0.001
    cached: bool = False


# ---------------------------------------------------------------------------
# Reverse geocoding
# ---------------------------------------------------------------------------

class AddressComponents(BaseModel):
    house_number: Optional[str] = None
    road: Optional[str] = None
    suburb: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    postcode: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None


class ReverseGeocodeResponse(BaseModel):
    lat: float
    lon: float
    formatted_address: str
    components: AddressComponents
    place_id: str
    accuracy_meters: float
    cost_usd: float = 0.001


# ---------------------------------------------------------------------------
# Places
# ---------------------------------------------------------------------------

class PlaceResult(BaseModel):
    place_id: str
    name: str
    type: str
    lat: float
    lon: float
    distance_meters: float
    address: str
    rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    review_count: Optional[int] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    hours: Optional[Dict[str, str]] = None
    tags: List[str] = Field(default_factory=list)
    open_now: Optional[bool] = None


class PlacesResponse(BaseModel):
    lat: float
    lon: float
    type: str
    radius_meters: float
    results: List[PlaceResult]
    total_found: int
    cost_usd: float = 0.003


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

class RouteStep(BaseModel):
    instruction: str
    distance_meters: float
    duration_seconds: float
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    maneuver: Optional[str] = None
    road_name: Optional[str] = None


class RouteGeometry(BaseModel):
    type: str = "LineString"
    coordinates: List[List[float]]


class RouteLeg(BaseModel):
    distance_meters: float
    duration_seconds: float
    steps: List[RouteStep]


class RouteResult(BaseModel):
    from_address: str
    to_address: str
    mode: str
    distance_meters: float
    duration_seconds: float
    geometry: RouteGeometry
    legs: List[RouteLeg]
    waypoints: List[Coordinates]
    traffic_delay_seconds: Optional[float] = None
    toll_cost_usd: Optional[float] = None


class RouteResponse(BaseModel):
    route: RouteResult
    alternatives: List[RouteResult] = Field(default_factory=list)
    cost_usd: float = 0.005


# ---------------------------------------------------------------------------
# Map tiles
# ---------------------------------------------------------------------------

class TileFeature(BaseModel):
    type: str
    geometry: Dict[str, Any]
    properties: Dict[str, Any] = Field(default_factory=dict)


class TileLayer(BaseModel):
    name: str
    version: int = 2
    extent: int = 4096
    features: List[TileFeature]


class TileResponse(BaseModel):
    z: int = Field(..., ge=0, le=22)
    x: int
    y: int
    layers: List[TileLayer]
    attribution: str = "Mainlayer Geospatial"
    cost_usd: float = 0.0005


# ---------------------------------------------------------------------------
# Administrative boundaries
# ---------------------------------------------------------------------------

class BoundaryGeometry(BaseModel):
    type: str
    coordinates: List[Any]


class BoundaryProperties(BaseModel):
    name: str
    name_local: Optional[str] = None
    admin_level: int
    population: Optional[int] = None
    area_km2: Optional[float] = None
    capital: Optional[str] = None
    timezone: Optional[str] = None
    iso_code: Optional[str] = None
    wikidata_id: Optional[str] = None


class BoundaryResponse(BaseModel):
    region: str
    type: str
    geometry: BoundaryGeometry
    properties: BoundaryProperties
    bounding_box: BoundingBox
    cost_usd: float = 0.002


# ---------------------------------------------------------------------------
# Elevation
# ---------------------------------------------------------------------------

class ElevationResponse(BaseModel):
    lat: float
    lon: float
    elevation_meters: float
    datum: str = "EGM96"
    resolution_meters: float
    terrain_type: str
    cost_usd: float = 0.001


# ---------------------------------------------------------------------------
# Error / health
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    error: str
    message: str
    status_code: int


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    base_url: str
