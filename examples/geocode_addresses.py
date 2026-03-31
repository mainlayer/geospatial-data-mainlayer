"""
Example: Geocode and reverse-geocode locations via the Geospatial Data API.

Usage:
    export MAINLAYER_API_KEY=your_key_here
    python examples/geocode_addresses.py
"""

import os
import httpx

BASE_URL = os.getenv("GEO_API_URL", "http://localhost:8000")
API_KEY = os.getenv("MAINLAYER_API_KEY", "your_api_key_here")

headers = {"Authorization": f"Bearer {API_KEY}"}


def geocode(address: str) -> dict:
    """Convert an address to coordinates."""
    resp = httpx.get(f"{BASE_URL}/geocode", params={"address": address}, headers=headers)
    resp.raise_for_status()
    return resp.json()


def reverse_geocode(lat: float, lon: float) -> dict:
    """Convert coordinates to a human-readable address."""
    resp = httpx.get(
        f"{BASE_URL}/reverse-geocode",
        params={"lat": lat, "lon": lon},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


def get_elevation(lat: float, lon: float) -> dict:
    """Get terrain elevation at a coordinate."""
    resp = httpx.get(
        f"{BASE_URL}/elevation",
        params={"lat": lat, "lon": lon},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    addresses = [
        "Eiffel Tower, Paris, France",
        "1600 Pennsylvania Avenue NW, Washington DC",
        "Big Ben, London, UK",
        "Sydney Opera House, Australia",
    ]

    # 1. Geocode multiple addresses
    print("=== Geocoding Addresses ===\n")
    geocoded = []
    for addr in addresses:
        result = geocode(addr)
        geocoded.append(result)
        print(f"  {addr}")
        print(f"    → lat={result.get('lat'):.6f}, lon={result.get('lon'):.6f}")
        print(f"    → {result.get('formatted_address', result.get('display_name', ''))}")
        print()

    # 2. Reverse geocode
    print("=== Reverse Geocoding ===\n")
    coords = [
        (48.8584, 2.2945, "Eiffel Tower area"),
        (51.5007, -0.1246, "Westminster area"),
        (35.6762, 139.6503, "Tokyo area"),
    ]
    for lat, lon, label in coords:
        result = reverse_geocode(lat, lon)
        print(f"  ({lat}, {lon}) — {label}")
        print(f"    → {result.get('formatted_address', result.get('display_name', 'N/A'))}")
        print()

    # 3. Elevation data
    print("=== Elevation Data ===\n")
    elevation_points = [
        (27.9881, 86.9250, "Mount Everest base"),
        (36.4557, -118.5918, "Mount Whitney, CA"),
        (51.5074, -0.1278, "London (sea level)"),
    ]
    for lat, lon, label in elevation_points:
        result = get_elevation(lat, lon)
        elev = result.get("elevation_m", result.get("elevation", "N/A"))
        print(f"  {label}: {elev}m")

    total_calls = len(addresses) + len(coords) + len(elevation_points)
    total_cost = len(addresses) * 0.001 + len(coords) * 0.001 + len(elevation_points) * 0.001
    print(f"\nTotal: {total_calls} API calls, estimated cost: ${total_cost:.3f}")


if __name__ == "__main__":
    main()
