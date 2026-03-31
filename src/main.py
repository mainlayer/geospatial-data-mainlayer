"""
Geospatial Data Mainlayer — FastAPI application.

Endpoints:
  GET /geocode                  — address → coordinates          ($0.001)
  GET /reverse-geocode          — coordinates → address          ($0.001)
  GET /places/nearby            — nearby places search           ($0.003)
  GET /routes                   — route calculation              ($0.005)
  GET /tiles/{z}/{x}/{y}        — vector map tile data           ($0.0005)
  GET /boundaries/{region}      — administrative boundaries      ($0.002)
  GET /elevation                — terrain elevation data         ($0.001)

Auth: Authorization: Bearer <api_key>
"""
import os
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Path, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from geo_db import GeoDatabase
from mainlayer import get_usage_summary, require_payment
from models import (
    BoundaryResponse,
    ElevationResponse,
    ErrorResponse,
    GeocodeResponse,
    HealthResponse,
    PlacesResponse,
    ReverseGeocodeResponse,
    RouteResponse,
    TileResponse,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

VERSION = "1.0.0"

app = FastAPI(
    title="Geospatial Data Mainlayer",
    description=(
        "Geospatial data API for AI mapping and location agents. "
        "Pay per query — geocoding, routing, places, elevation, tiles, and boundaries. "
        "Powered by Mainlayer (https://api.mainlayer.xyz)."
    ),
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Authorization", "Content-Type"],
)

db = GeoDatabase()

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": detail.get("error", "request_error"), **detail, "status_code": exc.status_code},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "An unexpected error occurred.", "status_code": 500},
    )


# ---------------------------------------------------------------------------
# Health / meta
# ---------------------------------------------------------------------------

@app.get("/", response_model=HealthResponse, tags=["Meta"])
async def root() -> HealthResponse:
    """Service health check and metadata."""
    return HealthResponse(
        status="ok",
        service="geospatial-data-mainlayer",
        version=VERSION,
        base_url=os.getenv("MAINLAYER_BASE_URL", "https://api.mainlayer.xyz"),
    )


@app.get("/health", response_model=HealthResponse, tags=["Meta"])
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="geospatial-data-mainlayer",
        version=VERSION,
        base_url=os.getenv("MAINLAYER_BASE_URL", "https://api.mainlayer.xyz"),
    )


# ---------------------------------------------------------------------------
# Geocoding  — $0.001
# ---------------------------------------------------------------------------

@app.get(
    "/geocode",
    response_model=GeocodeResponse,
    tags=["Geocoding"],
    summary="Convert an address to coordinates",
    responses={
        200: {"description": "Geocoding results with lat/lon coordinates"},
        400: {"model": ErrorResponse, "description": "Invalid or empty address"},
        401: {"model": ErrorResponse, "description": "Missing or invalid API key"},
    },
)
async def geocode(
    request: Request,
    address: str = Query(..., min_length=3, max_length=512, description="Free-text address to geocode"),
) -> GeocodeResponse:
    """
    Convert a free-text address string to one or more candidate coordinate pairs.

    Returns results sorted by confidence score (highest first). Cost: **$0.001** per request.
    """
    await require_payment(request, cost_usd=0.001, endpoint="/geocode")
    results = db.geocode(address)
    if not results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "not_found", "message": f"No results found for address: {address}"})
    return GeocodeResponse(query=address, results=results, cost_usd=0.001)


# ---------------------------------------------------------------------------
# Reverse geocoding  — $0.001
# ---------------------------------------------------------------------------

@app.get(
    "/reverse-geocode",
    response_model=ReverseGeocodeResponse,
    tags=["Geocoding"],
    summary="Convert coordinates to an address",
    responses={
        200: {"description": "Nearest address for the given coordinates"},
        400: {"model": ErrorResponse, "description": "Coordinates out of range"},
        401: {"model": ErrorResponse, "description": "Missing or invalid API key"},
    },
)
async def reverse_geocode(
    request: Request,
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees"),
) -> ReverseGeocodeResponse:
    """
    Convert a latitude/longitude pair to a human-readable address.

    Cost: **$0.001** per request.
    """
    await require_payment(request, cost_usd=0.001, endpoint="/reverse-geocode")
    data = db.reverse_geocode(lat, lon)
    return ReverseGeocodeResponse(**data)


# ---------------------------------------------------------------------------
# Nearby places  — $0.003
# ---------------------------------------------------------------------------

VALID_PLACE_TYPES = {
    "restaurant", "cafe", "hotel", "hospital", "school", "park",
    "gym", "pharmacy", "bank", "supermarket", "museum", "library",
    "gas_station", "airport",
}


@app.get(
    "/places/nearby",
    response_model=PlacesResponse,
    tags=["Places"],
    summary="Find nearby places of interest",
    responses={
        200: {"description": "List of nearby places sorted by distance"},
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        401: {"model": ErrorResponse, "description": "Missing or invalid API key"},
    },
)
async def places_nearby(
    request: Request,
    lat: float = Query(..., ge=-90.0, le=90.0, description="Center latitude"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Center longitude"),
    type: str = Query(..., description=f"Place type. One of: {', '.join(sorted(VALID_PLACE_TYPES))}"),
    radius: float = Query(1000.0, ge=50.0, le=50000.0, description="Search radius in metres (50–50,000)"),
) -> PlacesResponse:
    """
    Search for places of a specific type near a coordinate.

    Cost: **$0.003** per request.
    """
    if type not in VALID_PLACE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_place_type",
                "message": f"Unknown place type '{type}'. Valid types: {sorted(VALID_PLACE_TYPES)}",
            },
        )
    await require_payment(request, cost_usd=0.003, endpoint="/places/nearby")
    results = db.nearby_places(lat, lon, type, radius)
    return PlacesResponse(
        lat=lat, lon=lon, type=type,
        radius_meters=radius, results=results,
        total_found=len(results), cost_usd=0.003,
    )


# ---------------------------------------------------------------------------
# Routes  — $0.005
# ---------------------------------------------------------------------------

@app.get(
    "/routes",
    response_model=RouteResponse,
    tags=["Routing"],
    summary="Calculate a route between two locations",
    responses={
        200: {"description": "Calculated route with step-by-step directions"},
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        401: {"model": ErrorResponse, "description": "Missing or invalid API key"},
    },
)
async def routes(
    request: Request,
    from_: str = Query(..., alias="from", min_length=3, description="Origin address or place name"),
    to: str = Query(..., min_length=3, description="Destination address or place name"),
    mode: Literal["driving", "walking"] = Query("driving", description="Travel mode"),
) -> RouteResponse:
    """
    Calculate a route between two addresses including turn-by-turn directions.

    Cost: **$0.005** per request.
    """
    await require_payment(request, cost_usd=0.005, endpoint="/routes")
    data = db.calculate_route(from_, to, mode)
    return RouteResponse(**data)


# ---------------------------------------------------------------------------
# Map tiles  — $0.0005
# ---------------------------------------------------------------------------

@app.get(
    "/tiles/{z}/{x}/{y}",
    response_model=TileResponse,
    tags=["Tiles"],
    summary="Fetch vector map tile data",
    responses={
        200: {"description": "Vector tile data in GeoJSON-compatible format"},
        400: {"model": ErrorResponse, "description": "Invalid tile coordinates"},
        401: {"model": ErrorResponse, "description": "Missing or invalid API key"},
    },
)
async def map_tile(
    request: Request,
    z: int = Path(..., ge=0, le=22, description="Zoom level (0–22)"),
    x: int = Path(..., ge=0, description="Tile X coordinate"),
    y: int = Path(..., ge=0, description="Tile Y coordinate"),
) -> TileResponse:
    """
    Fetch vector map tile data for a given TMS tile coordinate (z/x/y).

    Includes layers for roads, buildings (zoom ≥ 14), and land use.
    Cost: **$0.0005** per tile.
    """
    # Validate x/y against zoom level
    max_coord = 2 ** z
    if x >= max_coord or y >= max_coord:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_tile_coords",
                "message": f"At zoom {z}, tile coords must be in [0, {max_coord - 1}]. Got x={x}, y={y}.",
            },
        )
    await require_payment(request, cost_usd=0.0005, endpoint="/tiles/{z}/{x}/{y}")
    data = db.get_tile(z, x, y)
    return TileResponse(**data, attribution="Mainlayer Geospatial", cost_usd=0.0005)


# ---------------------------------------------------------------------------
# Administrative boundaries  — $0.002
# ---------------------------------------------------------------------------

@app.get(
    "/boundaries/{region}",
    response_model=BoundaryResponse,
    tags=["Boundaries"],
    summary="Fetch administrative boundary polygon for a region",
    responses={
        200: {"description": "GeoJSON polygon for the administrative boundary"},
        400: {"model": ErrorResponse, "description": "Region name too short"},
        401: {"model": ErrorResponse, "description": "Missing or invalid API key"},
        404: {"model": ErrorResponse, "description": "Region not found"},
    },
)
async def boundaries(
    request: Request,
    region: str = Path(..., min_length=2, max_length=128, description="City, state, or country name"),
) -> BoundaryResponse:
    """
    Return the GeoJSON polygon for an administrative boundary.

    Supports cities, states, and countries by name. Cost: **$0.002** per request.
    """
    await require_payment(request, cost_usd=0.002, endpoint="/boundaries/{region}")
    data = db.get_boundary(region)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "region_not_found", "message": f"No boundary data found for region: {region}"},
        )
    return BoundaryResponse(**data)


# ---------------------------------------------------------------------------
# Elevation  — $0.001
# ---------------------------------------------------------------------------

@app.get(
    "/elevation",
    response_model=ElevationResponse,
    tags=["Elevation"],
    summary="Get terrain elevation for a coordinate",
    responses={
        200: {"description": "Elevation in metres above sea level with terrain classification"},
        400: {"model": ErrorResponse, "description": "Coordinates out of range"},
        401: {"model": ErrorResponse, "description": "Missing or invalid API key"},
    },
)
async def elevation(
    request: Request,
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees"),
) -> ElevationResponse:
    """
    Look up terrain elevation and surface type for a coordinate.

    Returns elevation in metres (EGM96 datum) and terrain classification.
    Cost: **$0.001** per request.
    """
    await require_payment(request, cost_usd=0.001, endpoint="/elevation")
    data = db.get_elevation(lat, lon)
    return ElevationResponse(**data, cost_usd=0.001)


# ---------------------------------------------------------------------------
# Internal usage debug endpoint
# ---------------------------------------------------------------------------

@app.get("/debug/usage", tags=["Meta"], include_in_schema=False)
async def debug_usage(request: Request, api_key: Optional[str] = Query(None)):
    """Return aggregated usage stats for the current session (debug only)."""
    bypass = os.getenv("MAINLAYER_BYPASS_AUTH", "false").lower() == "true"
    if not bypass:
        raise HTTPException(status_code=403, detail="Debug endpoint requires MAINLAYER_BYPASS_AUTH=true")
    return get_usage_summary(api_key)
