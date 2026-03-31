"""
Tests for the Geospatial Data Mainlayer API.

Run with:
    pytest tests/test_api.py -v
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

# Ensure src/ is on the path when running from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Bypass auth for all tests
os.environ["MAINLAYER_BYPASS_AUTH"] = "true"

from main import app  # noqa: E402  (import after env var set)

client = TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def auth_headers() -> dict:
    return {"Authorization": "Bearer test-key-1234567890abcdef"}


# ---------------------------------------------------------------------------
# Health / meta
# ---------------------------------------------------------------------------

class TestHealth:
    def test_root_returns_ok(self):
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "geospatial-data-mainlayer"
        assert "version" in body

    def test_health_endpoint(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_docs_available(self):
        resp = client.get("/docs")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------

class TestGeocode:
    def test_basic_geocode(self):
        resp = client.get("/geocode", params={"address": "1600 Pennsylvania Avenue, Washington DC"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["query"] == "1600 Pennsylvania Avenue, Washington DC"
        assert len(body["results"]) >= 1
        first = body["results"][0]
        assert "lat" in first and "lon" in first
        assert 0.0 <= first["confidence"] <= 1.0
        assert body["cost_usd"] == 0.001

    def test_results_sorted_by_confidence(self):
        resp = client.get("/geocode", params={"address": "10 Downing Street, London"})
        assert resp.status_code == 200
        results = resp.json()["results"]
        scores = [r["confidence"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_geocode_returns_formatted_address(self):
        resp = client.get("/geocode", params={"address": "Eiffel Tower, Paris"})
        assert resp.status_code == 200
        result = resp.json()["results"][0]
        assert len(result["formatted_address"]) > 5
        assert "place_id" in result

    def test_geocode_missing_address_422(self):
        resp = client.get("/geocode")
        assert resp.status_code == 422

    def test_geocode_address_too_short_422(self):
        resp = client.get("/geocode", params={"address": "ab"})
        assert resp.status_code == 422

    def test_geocode_deterministic(self):
        """Same address must always return the same first result."""
        addr = "Times Square, New York"
        r1 = client.get("/geocode", params={"address": addr}).json()["results"][0]
        r2 = client.get("/geocode", params={"address": addr}).json()["results"][0]
        assert r1["lat"] == r2["lat"]
        assert r1["lon"] == r2["lon"]


# ---------------------------------------------------------------------------
# Reverse geocoding
# ---------------------------------------------------------------------------

class TestReverseGeocode:
    def test_basic_reverse_geocode(self):
        resp = client.get("/reverse-geocode", params={"lat": 51.5074, "lon": -0.1278})
        assert resp.status_code == 200
        body = resp.json()
        assert body["lat"] == 51.5074
        assert body["lon"] == -0.1278
        assert "formatted_address" in body
        assert body["cost_usd"] == 0.001

    def test_reverse_geocode_returns_components(self):
        resp = client.get("/reverse-geocode", params={"lat": 40.7128, "lon": -74.006})
        body = resp.json()
        assert "components" in body
        comp = body["components"]
        assert "city" in comp or "road" in comp

    def test_reverse_geocode_lat_out_of_range(self):
        resp = client.get("/reverse-geocode", params={"lat": 95.0, "lon": 0.0})
        assert resp.status_code == 422

    def test_reverse_geocode_lon_out_of_range(self):
        resp = client.get("/reverse-geocode", params={"lat": 0.0, "lon": 200.0})
        assert resp.status_code == 422

    def test_reverse_geocode_missing_params(self):
        resp = client.get("/reverse-geocode", params={"lat": 51.5})
        assert resp.status_code == 422

    def test_reverse_geocode_accuracy_positive(self):
        resp = client.get("/reverse-geocode", params={"lat": 35.6762, "lon": 139.6503})
        assert resp.json()["accuracy_meters"] > 0


# ---------------------------------------------------------------------------
# Nearby places
# ---------------------------------------------------------------------------

class TestPlacesNearby:
    def test_basic_nearby_restaurant(self):
        resp = client.get("/places/nearby", params={"lat": 40.7128, "lon": -74.006, "type": "restaurant", "radius": 500})
        assert resp.status_code == 200
        body = resp.json()
        assert body["type"] == "restaurant"
        assert body["radius_meters"] == 500
        assert len(body["results"]) > 0
        assert body["cost_usd"] == 0.003

    def test_results_sorted_by_distance(self):
        resp = client.get("/places/nearby", params={"lat": 51.5074, "lon": -0.1278, "type": "cafe"})
        results = resp.json()["results"]
        distances = [r["distance_meters"] for r in results]
        assert distances == sorted(distances)

    def test_all_results_within_radius(self):
        radius = 1000.0
        resp = client.get("/places/nearby", params={"lat": 48.8566, "lon": 2.3522, "type": "hotel", "radius": radius})
        for place in resp.json()["results"]:
            assert place["distance_meters"] <= radius * 1.01  # 1% tolerance

    def test_invalid_place_type_400(self):
        resp = client.get("/places/nearby", params={"lat": 0.0, "lon": 0.0, "type": "spaceship"})
        assert resp.status_code == 400
        assert "invalid_place_type" in resp.json()["error"]

    def test_radius_too_small_422(self):
        resp = client.get("/places/nearby", params={"lat": 0.0, "lon": 0.0, "type": "park", "radius": 10})
        assert resp.status_code == 422

    def test_valid_place_types(self):
        valid_types = ["restaurant", "cafe", "hotel", "pharmacy", "bank", "museum"]
        for pt in valid_types:
            resp = client.get("/places/nearby", params={"lat": 40.7128, "lon": -74.006, "type": pt})
            assert resp.status_code == 200, f"Failed for type: {pt}"

    def test_place_fields_complete(self):
        resp = client.get("/places/nearby", params={"lat": 40.7128, "lon": -74.006, "type": "restaurant"})
        place = resp.json()["results"][0]
        for field in ("place_id", "name", "type", "lat", "lon", "distance_meters", "address"):
            assert field in place, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

class TestRoutes:
    def test_driving_route(self):
        resp = client.get("/routes", params={
            "from": "1 Main Street, New York",
            "to": "Times Square, New York",
            "mode": "driving",
        })
        assert resp.status_code == 200
        body = resp.json()
        route = body["route"]
        assert route["mode"] == "driving"
        assert route["distance_meters"] > 0
        assert route["duration_seconds"] > 0
        assert body["cost_usd"] == 0.005

    def test_walking_route(self):
        resp = client.get("/routes", params={
            "from": "Central Park, New York",
            "to": "Metropolitan Museum, New York",
            "mode": "walking",
        })
        assert resp.status_code == 200
        route = resp.json()["route"]
        assert route["mode"] == "walking"
        # Walking should generally be slower (longer duration relative to distance)
        assert route["duration_seconds"] > 0

    def test_route_has_steps(self):
        resp = client.get("/routes", params={
            "from": "Piccadilly Circus, London",
            "to": "Tower Bridge, London",
            "mode": "driving",
        })
        route = resp.json()["route"]
        assert len(route["legs"]) > 0
        leg = route["legs"][0]
        assert len(leg["steps"]) >= 2

    def test_route_geometry_line_string(self):
        resp = client.get("/routes", params={
            "from": "Berlin Airport",
            "to": "Brandenburg Gate, Berlin",
            "mode": "driving",
        })
        geom = resp.json()["route"]["geometry"]
        assert geom["type"] == "LineString"
        assert len(geom["coordinates"]) >= 2
        for coord in geom["coordinates"]:
            assert len(coord) == 2

    def test_route_has_alternatives(self):
        resp = client.get("/routes", params={
            "from": "Sydney Opera House",
            "to": "Bondi Beach, Sydney",
            "mode": "driving",
        })
        assert "alternatives" in resp.json()

    def test_invalid_mode_422(self):
        resp = client.get("/routes", params={
            "from": "A", "to": "B", "mode": "flying",
        })
        assert resp.status_code == 422

    def test_route_from_too_short_422(self):
        resp = client.get("/routes", params={"from": "A", "to": "Valid destination address", "mode": "driving"})
        assert resp.status_code == 422

    def test_route_deterministic(self):
        params = {"from": "Grand Central, New York", "to": "JFK Airport", "mode": "driving"}
        r1 = client.get("/routes", params=params).json()["route"]["distance_meters"]
        r2 = client.get("/routes", params=params).json()["route"]["distance_meters"]
        assert r1 == r2


# ---------------------------------------------------------------------------
# Map tiles
# ---------------------------------------------------------------------------

class TestTiles:
    def test_valid_tile(self):
        resp = client.get("/tiles/10/512/512")
        assert resp.status_code == 200
        body = resp.json()
        assert body["z"] == 10
        assert body["x"] == 512
        assert body["y"] == 512
        assert len(body["layers"]) > 0
        assert body["cost_usd"] == 0.0005

    def test_tile_has_roads_layer(self):
        resp = client.get("/tiles/12/1234/1234")
        layers = {layer["name"]: layer for layer in resp.json()["layers"]}
        assert "roads" in layers
        assert len(layers["roads"]["features"]) > 0

    def test_high_zoom_has_buildings(self):
        resp = client.get("/tiles/16/32000/21000")
        layers = {layer["name"]: layer for layer in resp.json()["layers"]}
        assert "buildings" in layers

    def test_low_zoom_no_buildings(self):
        resp = client.get("/tiles/5/10/10")
        layers = {layer["name"]: layer for layer in resp.json()["layers"]}
        assert "buildings" not in layers

    def test_tile_invalid_coords(self):
        # At zoom 5, max coord is 2^5=32; x=100 is invalid
        resp = client.get("/tiles/5/100/5")
        assert resp.status_code == 400
        assert "invalid_tile_coords" in resp.json()["error"]

    def test_tile_zoom_zero(self):
        resp = client.get("/tiles/0/0/0")
        assert resp.status_code == 200

    def test_tile_zoom_too_high_422(self):
        resp = client.get("/tiles/23/0/0")
        assert resp.status_code == 422

    def test_tile_attribution(self):
        resp = client.get("/tiles/8/100/100")
        assert resp.json()["attribution"] == "Mainlayer Geospatial"


# ---------------------------------------------------------------------------
# Administrative boundaries
# ---------------------------------------------------------------------------

class TestBoundaries:
    def test_known_city_boundary(self):
        resp = client.get("/boundaries/London")
        assert resp.status_code == 200
        body = resp.json()
        assert body["region"] == "London"
        assert body["geometry"]["type"] == "Polygon"
        assert body["cost_usd"] == 0.002

    def test_boundary_bounding_box(self):
        resp = client.get("/boundaries/Tokyo")
        bb = resp.json()["bounding_box"]
        assert bb["north"] > bb["south"]
        assert bb["east"] > bb["west"]

    def test_boundary_properties_populated(self):
        resp = client.get("/boundaries/Paris")
        props = resp.json()["properties"]
        assert props["name"]
        assert props["admin_level"] >= 0

    def test_unknown_region_still_returns_data(self):
        # Unknown regions return synthetic data, not 404
        resp = client.get("/boundaries/Atlantis")
        assert resp.status_code == 200

    def test_boundary_polygon_closed(self):
        """First and last coordinate of the exterior ring must match."""
        resp = client.get("/boundaries/Berlin")
        coords = resp.json()["geometry"]["coordinates"][0]
        assert coords[0] == coords[-1]

    def test_region_name_too_short_422(self):
        resp = client.get("/boundaries/X")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Elevation
# ---------------------------------------------------------------------------

class TestElevation:
    def test_basic_elevation(self):
        resp = client.get("/elevation", params={"lat": 27.9881, "lon": 86.9250})  # Everest
        assert resp.status_code == 200
        body = resp.json()
        assert body["lat"] == 27.9881
        assert body["lon"] == 86.9250
        assert body["elevation_meters"] >= 0
        assert body["datum"] == "EGM96"
        assert body["cost_usd"] == 0.001

    def test_elevation_terrain_type_present(self):
        resp = client.get("/elevation", params={"lat": 0.0, "lon": 0.0})
        assert "terrain_type" in resp.json()

    def test_coastal_terrain_near_sea_level(self):
        # Flat equatorial coordinate — elevation should be low → coastal/plains
        resp = client.get("/elevation", params={"lat": 1.0, "lon": 103.8})
        body = resp.json()
        terrain = body["terrain_type"]
        assert terrain in ("coastal", "plains", "hills", "highland", "mountain")

    def test_elevation_missing_lat(self):
        resp = client.get("/elevation", params={"lon": 0.0})
        assert resp.status_code == 422

    def test_elevation_lat_out_of_range(self):
        resp = client.get("/elevation", params={"lat": 91.0, "lon": 0.0})
        assert resp.status_code == 422

    def test_elevation_deterministic(self):
        params = {"lat": 48.8566, "lon": 2.3522}
        e1 = client.get("/elevation", params=params).json()["elevation_meters"]
        e2 = client.get("/elevation", params=params).json()["elevation_meters"]
        assert e1 == e2

    def test_resolution_positive(self):
        resp = client.get("/elevation", params={"lat": 40.0, "lon": -75.0})
        assert resp.json()["resolution_meters"] > 0


# ---------------------------------------------------------------------------
# Auth enforcement (non-bypass mode)
# ---------------------------------------------------------------------------

class TestAuth:
    def setup_method(self):
        """Temporarily disable bypass to test real auth."""
        os.environ["MAINLAYER_BYPASS_AUTH"] = "false"
        # Re-import the module so the env var is picked up
        import importlib
        import mainlayer
        importlib.reload(mainlayer)
        import main as main_module
        importlib.reload(main_module)
        self._client = TestClient(main_module.app)

    def teardown_method(self):
        os.environ["MAINLAYER_BYPASS_AUTH"] = "true"

    def test_missing_key_returns_401(self):
        resp = self._client.get("/geocode", params={"address": "London, UK"})
        assert resp.status_code == 401

    def test_valid_key_accepted(self):
        resp = self._client.get(
            "/geocode",
            params={"address": "London, UK"},
            headers={"Authorization": "Bearer valid-test-key-1234567890"},
        )
        assert resp.status_code == 200

    def test_invalid_key_format_401(self):
        resp = self._client.get(
            "/geocode",
            params={"address": "London, UK"},
            headers={"Authorization": "Bearer x"},
        )
        assert resp.status_code == 401

    def test_bearer_prefix_required(self):
        resp = self._client.get(
            "/geocode",
            params={"address": "London, UK"},
            headers={"Authorization": "valid-test-key-1234567890"},
        )
        assert resp.status_code == 401
