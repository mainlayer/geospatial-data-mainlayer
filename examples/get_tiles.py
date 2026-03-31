"""
Example: Fetch map tiles and nearby places via the Geospatial Data API.

Usage:
    export MAINLAYER_API_KEY=your_key_here
    python examples/get_tiles.py
"""

import os
import math
import httpx

BASE_URL = os.getenv("GEO_API_URL", "http://localhost:8000")
API_KEY = os.getenv("MAINLAYER_API_KEY", "your_api_key_here")

headers = {"Authorization": f"Bearer {API_KEY}"}


def lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """Convert lat/lon to tile x/y for a given zoom level (TMS/XYZ convention)."""
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def get_tile(z: int, x: int, y: int) -> dict:
    """Fetch a vector tile."""
    resp = httpx.get(f"{BASE_URL}/tiles/{z}/{x}/{y}", headers=headers)
    resp.raise_for_status()
    return resp.json()


def get_nearby_places(lat: float, lon: float, place_type: str = "restaurant", radius: int = 500) -> dict:
    """Search for nearby places."""
    resp = httpx.get(
        f"{BASE_URL}/places/nearby",
        params={"lat": lat, "lon": lon, "type": place_type, "radius": radius},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


def get_boundary(region: str) -> dict:
    """Fetch administrative boundary polygon."""
    resp = httpx.get(f"{BASE_URL}/boundaries/{region}", headers=headers)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    # 1. Fetch tiles around Paris at zoom level 12
    paris_lat, paris_lon = 48.8566, 2.3522
    zoom = 12
    x, y = lat_lon_to_tile(paris_lat, paris_lon, zoom)

    print(f"=== Map Tiles Around Paris (zoom={zoom}) ===\n")
    tile_costs = 0.0
    for dx, dy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        tx, ty = x + dx, y + dy
        tile = get_tile(zoom, tx, ty)
        features = tile.get("features", tile.get("feature_count", "?"))
        print(f"  Tile ({zoom}/{tx}/{ty}): {features} features")
        tile_costs += 0.0005

    print(f"  Tile fetch cost: ${tile_costs:.4f}")
    print()

    # 2. Nearby places search
    print("=== Nearby Places: Eiffel Tower area ===\n")
    for place_type in ["restaurant", "museum", "hotel"]:
        result = get_nearby_places(48.8584, 2.2945, place_type=place_type, radius=300)
        places = result.get("places", [])
        print(f"  {place_type.capitalize()}s within 300m: {len(places)}")
        for p in places[:2]:
            name = p.get("name", "Unknown")
            dist = p.get("distance_m", "?")
            print(f"    - {name} ({dist}m)")

    print(f"\nNearby places cost: ${3 * 0.003:.4f} (3 searches)")
    print()

    # 3. Administrative boundaries
    print("=== Administrative Boundaries ===\n")
    regions = ["Paris", "California", "Bavaria"]
    for region in regions:
        try:
            boundary = get_boundary(region)
            bbox = boundary.get("bbox", boundary.get("bounding_box", {}))
            area = boundary.get("area_km2", "N/A")
            print(f"  {region}: area={area} km², bbox={bbox}")
        except httpx.HTTPStatusError as e:
            print(f"  {region}: {e.response.status_code} — {e.response.text[:60]}")

    print(f"\nBoundary cost: ${len(regions) * 0.002:.4f}")


if __name__ == "__main__":
    main()
