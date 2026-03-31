"""
Realistic geospatial data generator.

Produces deterministic, plausible geo data for any coordinate or address
without requiring a live third-party mapping service. Intended for
development, testing, and demo environments. Swap out the methods here
to wire up a real provider (e.g. Google Maps, HERE, OpenStreetMap Nominatim).
"""
import hashlib
import math
import random
import re
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_from_str(*parts: Any) -> int:
    """Deterministic seed derived from arbitrary values."""
    raw = "|".join(str(p) for p in parts)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return int(digest[:16], 16)


def _rng(*seed_parts: Any) -> random.Random:
    return random.Random(_seed_from_str(*seed_parts))


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in metres between two WGS-84 points."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# Address corpus
# ---------------------------------------------------------------------------

_STREET_NAMES = [
    "Main Street", "Oak Avenue", "Maple Drive", "Park Boulevard",
    "Cedar Lane", "Elm Street", "Washington Road", "Lincoln Avenue",
    "Highland Drive", "Sunset Boulevard", "River Road", "Lake View Drive",
    "Forest Hill Road", "Valley Way", "Mountain View Avenue",
    "Commerce Street", "Market Street", "Harbor Drive", "Bay Street",
    "Colonial Road", "University Boulevard", "Tech Parkway", "Innovation Drive",
]

_CITY_DATA: List[Dict[str, Any]] = [
    {"city": "New York",         "state": "New York",       "country": "US", "lat":  40.7128, "lon": -74.0060, "tz": "America/New_York",      "pop": 8_336_817},
    {"city": "Los Angeles",      "state": "California",     "country": "US", "lat":  34.0522, "lon": -118.2437, "tz": "America/Los_Angeles",   "pop": 3_979_576},
    {"city": "Chicago",          "state": "Illinois",       "country": "US", "lat":  41.8781, "lon": -87.6298, "tz": "America/Chicago",        "pop": 2_693_976},
    {"city": "Houston",          "state": "Texas",          "country": "US", "lat":  29.7604, "lon": -95.3698, "tz": "America/Chicago",        "pop": 2_304_580},
    {"city": "London",           "state": "England",        "country": "GB", "lat":  51.5074, "lon":  -0.1278, "tz": "Europe/London",         "pop": 8_982_000},
    {"city": "Paris",            "state": "Île-de-France",  "country": "FR", "lat":  48.8566, "lon":   2.3522, "tz": "Europe/Paris",          "pop": 2_161_000},
    {"city": "Tokyo",            "state": "Tokyo",          "country": "JP", "lat":  35.6762, "lon": 139.6503, "tz": "Asia/Tokyo",            "pop": 13_960_000},
    {"city": "Sydney",           "state": "New South Wales","country": "AU", "lat": -33.8688, "lon": 151.2093, "tz": "Australia/Sydney",      "pop": 5_312_000},
    {"city": "Berlin",           "state": "Berlin",         "country": "DE", "lat":  52.5200, "lon":  13.4050, "tz": "Europe/Berlin",         "pop": 3_669_000},
    {"city": "Toronto",          "state": "Ontario",        "country": "CA", "lat":  43.6532, "lon": -79.3832, "tz": "America/Toronto",       "pop": 2_930_000},
    {"city": "Singapore",        "state": "Singapore",      "country": "SG", "lat":   1.3521, "lon": 103.8198, "tz": "Asia/Singapore",        "pop": 5_804_000},
    {"city": "Dubai",            "state": "Dubai",          "country": "AE", "lat":  25.2048, "lon":  55.2708, "tz": "Asia/Dubai",            "pop": 3_331_000},
    {"city": "São Paulo",        "state": "São Paulo",      "country": "BR", "lat": -23.5505, "lon": -46.6333, "tz": "America/Sao_Paulo",     "pop": 12_325_000},
    {"city": "Mumbai",           "state": "Maharashtra",    "country": "IN", "lat":  19.0760, "lon":  72.8777, "tz": "Asia/Kolkata",          "pop": 20_667_000},
    {"city": "Cape Town",        "state": "Western Cape",   "country": "ZA", "lat": -33.9249, "lon":  18.4241, "tz": "Africa/Johannesburg",   "pop": 4_618_000},
]

_PLACE_TYPES: Dict[str, List[str]] = {
    "restaurant": ["The Golden Fork", "Café Milano", "Sakura Garden", "Burger Barn", "La Maison", "Spice Route", "The Local Bistro", "Harbor Grill"],
    "cafe":       ["Blue Bottle Coffee", "Sunrise Brew", "The Daily Grind", "Perk Up", "Corner Café", "Bean & Gone", "Drip Lab"],
    "hotel":      ["Grand Meridian Hotel", "City Suites", "The Plaza Inn", "Harbor View Hotel", "Comfort Stay", "Urban Lodge"],
    "hospital":   ["City General Hospital", "St. Mary Medical Center", "Regional Health Clinic", "Community Hospital"],
    "school":     ["Lincoln Elementary", "Westside High School", "Lakefront Academy", "Central Middle School"],
    "park":       ["Riverside Park", "Central Green", "Heritage Gardens", "Lakeside Park", "Sunset Trail"],
    "gym":        ["FitLife Gym", "Iron Works", "CrossFit Central", "Zen Wellness Studio", "PowerZone Fitness"],
    "pharmacy":   ["HealthPlus Pharmacy", "City Drug Store", "QuickMed Pharmacy", "Wellness Center"],
    "bank":       ["First National Bank", "City Credit Union", "Commerce Bank", "Metro Financial"],
    "supermarket":["FreshMart", "City Grocers", "Whole Foods Market", "Daily Provisions", "Green Valley Market"],
    "museum":     ["City History Museum", "Modern Art Gallery", "Science Discovery Center", "Natural History Museum"],
    "library":    ["Public Library – Main Branch", "Community Reading Center", "Downtown Library"],
    "gas_station":["FastFuel", "City Gas & Go", "Metro Fuel Stop", "QuickFill Station"],
    "airport":    ["International Airport", "Regional Airport", "Municipal Airfield"],
}

_TERRAIN_TYPES = ["plains", "hills", "mountain", "coastal", "valley", "plateau", "wetland", "urban"]


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

class GeoDatabase:
    """Deterministic geospatial data generator."""

    # -----------------------------------------------------------------------
    # Geocoding
    # -----------------------------------------------------------------------

    def geocode(self, address: str) -> List[Dict[str, Any]]:
        """Return 1–3 result candidates for a free-text address."""
        rng = _rng("geocode", address.lower().strip())
        base = rng.choice(_CITY_DATA)
        results = []
        count = rng.randint(1, 3)

        for i in range(count):
            jitter_lat = rng.uniform(-0.05, 0.05)
            jitter_lon = rng.uniform(-0.05, 0.05)
            lat = round(base["lat"] + jitter_lat, 6)
            lon = round(base["lon"] + jitter_lon, 6)
            street_num = rng.randint(1, 9999)
            street = rng.choice(_STREET_NAMES)
            postcode = f"{rng.randint(10000, 99999)}"
            confidence = round(rng.uniform(0.60, 0.99) if i == 0 else rng.uniform(0.30, 0.65), 3)
            place_id = f"ml_place_{hashlib.md5((address + str(i)).encode()).hexdigest()[:12]}"
            formatted = f"{street_num} {street}, {base['city']}, {base['state']} {postcode}, {base['country']}"
            results.append({
                "address": address,
                "lat": lat,
                "lon": lon,
                "confidence": confidence,
                "components": {
                    "street_number": str(street_num),
                    "route": street,
                    "locality": base["city"],
                    "administrative_area": base["state"],
                    "country": base["country"],
                    "postal_code": postcode,
                },
                "place_id": place_id,
                "formatted_address": formatted,
            })

        results.sort(key=lambda r: r["confidence"], reverse=True)
        return results

    # -----------------------------------------------------------------------
    # Reverse geocoding
    # -----------------------------------------------------------------------

    def reverse_geocode(self, lat: float, lon: float) -> Dict[str, Any]:
        """Return address information for a coordinate pair."""
        city = self._nearest_city(lat, lon)
        rng = _rng("reverse", round(lat, 3), round(lon, 3))
        street_num = rng.randint(1, 9999)
        street = rng.choice(_STREET_NAMES)
        postcode = f"{rng.randint(10000, 99999)}"
        suburb_names = ["Northside", "Westgate", "Eastbrook", "Southpark", "Midtown", "Uptown", "Riverside"]
        suburb = rng.choice(suburb_names)
        accuracy = round(rng.uniform(5.0, 50.0), 1)
        place_id = f"ml_place_{hashlib.md5(f'{lat:.4f}{lon:.4f}'.encode()).hexdigest()[:12]}"
        formatted = f"{street_num} {street}, {suburb}, {city['city']}, {city['state']} {postcode}, {city['country']}"
        return {
            "lat": lat,
            "lon": lon,
            "formatted_address": formatted,
            "components": {
                "house_number": str(street_num),
                "road": street,
                "suburb": suburb,
                "city": city["city"],
                "county": f"{city['city']} County",
                "state": city["state"],
                "postcode": postcode,
                "country": city["country"],
                "country_code": city["country"],
            },
            "place_id": place_id,
            "accuracy_meters": accuracy,
        }

    # -----------------------------------------------------------------------
    # Nearby places
    # -----------------------------------------------------------------------

    def nearby_places(self, lat: float, lon: float, place_type: str, radius_meters: float) -> List[Dict[str, Any]]:
        """Return nearby places of a given type within radius."""
        rng = _rng("places", round(lat, 3), round(lon, 3), place_type)
        names = _PLACE_TYPES.get(place_type, _PLACE_TYPES["restaurant"])
        count = rng.randint(3, min(12, len(names) + 5))
        results: List[Dict[str, Any]] = []

        for i in range(count):
            # Scatter within the requested radius
            bearing = rng.uniform(0, 2 * math.pi)
            dist = rng.uniform(50, radius_meters)
            dlat = (dist / 111_320) * math.cos(bearing)
            dlon = (dist / (111_320 * math.cos(math.radians(lat)))) * math.sin(bearing)
            p_lat = round(lat + dlat, 6)
            p_lon = round(lon + dlon, 6)
            actual_dist = round(_haversine(lat, lon, p_lat, p_lon), 1)

            name_idx = i % len(names)
            name = names[name_idx]
            place_id = f"ml_place_{hashlib.md5(f'{place_type}{i}{lat:.3f}{lon:.3f}'.encode()).hexdigest()[:12]}"
            street_num = rng.randint(1, 999)
            street = rng.choice(_STREET_NAMES)
            city = self._nearest_city(p_lat, p_lon)
            tag_pool = [place_type, "open", "popular", "local", "verified"]

            results.append({
                "place_id": place_id,
                "name": name,
                "type": place_type,
                "lat": p_lat,
                "lon": p_lon,
                "distance_meters": actual_dist,
                "address": f"{street_num} {street}, {city['city']}",
                "rating": round(rng.uniform(3.0, 5.0), 1),
                "review_count": rng.randint(10, 2000),
                "phone": f"+1-{rng.randint(200, 999)}-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}",
                "website": f"https://www.{name.lower().replace(' ', '')}.example.com",
                "hours": {
                    "Monday": "09:00-21:00", "Tuesday": "09:00-21:00",
                    "Wednesday": "09:00-21:00", "Thursday": "09:00-21:00",
                    "Friday": "09:00-22:00", "Saturday": "10:00-22:00",
                    "Sunday": "10:00-20:00",
                },
                "tags": rng.sample(tag_pool, k=rng.randint(2, len(tag_pool))),
                "open_now": rng.choice([True, True, True, False]),
            })

        results.sort(key=lambda p: p["distance_meters"])
        return results

    # -----------------------------------------------------------------------
    # Routing
    # -----------------------------------------------------------------------

    def calculate_route(self, from_address: str, to_address: str, mode: str) -> Dict[str, Any]:
        """Generate a realistic route between two addresses."""
        from_data = self.geocode(from_address)[0]
        to_data = self.geocode(to_address)[0]
        rng = _rng("route", from_address, to_address, mode)

        lat1, lon1 = from_data["lat"], from_data["lon"]
        lat2, lon2 = to_data["lat"], to_data["lon"]
        straight_dist = _haversine(lat1, lon1, lat2, lon2)

        # Route distance is slightly longer than straight-line
        route_distance = straight_dist * rng.uniform(1.15, 1.45)

        # Speed by mode (m/s)
        speeds = {"driving": rng.uniform(8, 14), "walking": rng.uniform(1.2, 1.6)}
        speed = speeds.get(mode, speeds["driving"])
        duration = route_distance / speed
        traffic_delay = rng.uniform(0, duration * 0.15) if mode == "driving" else 0.0

        steps = self._generate_steps(lat1, lon1, lat2, lon2, route_distance, duration, rng)
        geometry_coords = self._generate_geometry(lat1, lon1, lat2, lon2, rng)
        waypoints = [{"lat": lat1, "lon": lon1}, {"lat": lat2, "lon": lon2}]

        route = {
            "from_address": from_data["formatted_address"],
            "to_address": to_data["formatted_address"],
            "mode": mode,
            "distance_meters": round(route_distance, 1),
            "duration_seconds": round(duration, 1),
            "geometry": {"type": "LineString", "coordinates": geometry_coords},
            "legs": [{"distance_meters": round(route_distance, 1), "duration_seconds": round(duration, 1), "steps": steps}],
            "waypoints": waypoints,
            "traffic_delay_seconds": round(traffic_delay, 1) if mode == "driving" else None,
            "toll_cost_usd": round(rng.uniform(0, 8.0), 2) if mode == "driving" and rng.random() > 0.6 else None,
        }

        # One alternative route
        alt_distance = route_distance * rng.uniform(1.05, 1.30)
        alt_duration = alt_distance / speed
        alternative = dict(route)
        alternative["distance_meters"] = round(alt_distance, 1)
        alternative["duration_seconds"] = round(alt_duration, 1)
        alternative["legs"] = [{"distance_meters": round(alt_distance, 1), "duration_seconds": round(alt_duration, 1), "steps": steps}]

        return {"route": route, "alternatives": [alternative]}

    def _generate_steps(
        self, lat1: float, lon1: float, lat2: float, lon2: float,
        total_dist: float, total_dur: float, rng: random.Random
    ) -> List[Dict[str, Any]]:
        num_steps = rng.randint(4, 10)
        maneuvers = ["turn-left", "turn-right", "straight", "slight-left", "slight-right", "u-turn"]
        steps = []
        seg_dist = total_dist / num_steps
        seg_dur = total_dur / num_steps
        for i in range(num_steps):
            frac_start = i / num_steps
            frac_end = (i + 1) / num_steps
            slat = round(lat1 + (lat2 - lat1) * frac_start, 6)
            slon = round(lon1 + (lon2 - lon1) * frac_start, 6)
            elat = round(lat1 + (lat2 - lat1) * frac_end, 6)
            elon = round(lon1 + (lon2 - lon1) * frac_end, 6)
            road = rng.choice(_STREET_NAMES)
            maneuver = rng.choice(maneuvers)
            if i == 0:
                instruction = f"Head {self._cardinal(lat1, lon1, lat2, lon2)} on {road}"
                maneuver = "depart"
            elif i == num_steps - 1:
                instruction = f"Arrive at destination on {road}"
                maneuver = "arrive"
            else:
                instruction = f"{maneuver.replace('-', ' ').title()} onto {road}"
            steps.append({
                "instruction": instruction,
                "distance_meters": round(seg_dist, 1),
                "duration_seconds": round(seg_dur, 1),
                "start_lat": slat, "start_lon": slon,
                "end_lat": elat, "end_lon": elon,
                "maneuver": maneuver,
                "road_name": road,
            })
        return steps

    def _generate_geometry(
        self, lat1: float, lon1: float, lat2: float, lon2: float, rng: random.Random
    ) -> List[List[float]]:
        """Return a GeoJSON LineString coordinate list with slight jitter."""
        points = 12
        coords = []
        for i in range(points):
            frac = i / (points - 1)
            lat = lat1 + (lat2 - lat1) * frac + rng.uniform(-0.003, 0.003)
            lon = lon1 + (lon2 - lon1) * frac + rng.uniform(-0.003, 0.003)
            coords.append([round(lon, 6), round(lat, 6)])
        coords[0] = [round(lon1, 6), round(lat1, 6)]
        coords[-1] = [round(lon2, 6), round(lat2, 6)]
        return coords

    @staticmethod
    def _cardinal(lat1: float, lon1: float, lat2: float, lon2: float) -> str:
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        angle = math.degrees(math.atan2(dlon, dlat)) % 360
        dirs = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
        idx = int((angle + 22.5) / 45) % 8
        return dirs[idx]

    # -----------------------------------------------------------------------
    # Map tiles
    # -----------------------------------------------------------------------

    def get_tile(self, z: int, x: int, y: int) -> Dict[str, Any]:
        """Return vector tile feature data for a given TMS tile coordinate."""
        rng = _rng("tile", z, x, y)

        # Convert tile coords to lat/lon for context
        n = 2 ** z
        lon_deg = x / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat_deg = math.degrees(lat_rad)

        layers = []

        # Roads layer
        road_features = []
        road_count = rng.randint(3, 12) if z >= 10 else rng.randint(1, 4)
        road_types = ["motorway", "primary", "secondary", "residential", "footway", "cycleway"]
        for i in range(road_count):
            road_type = rng.choice(road_types)
            road_features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [round(lon_deg + rng.uniform(-0.01, 0.01), 6), round(lat_deg + rng.uniform(-0.01, 0.01), 6)],
                        [round(lon_deg + rng.uniform(-0.01, 0.01), 6), round(lat_deg + rng.uniform(-0.01, 0.01), 6)],
                    ],
                },
                "properties": {
                    "class": road_type,
                    "name": rng.choice(_STREET_NAMES) if rng.random() > 0.3 else None,
                    "oneway": rng.choice([True, False]),
                    "maxspeed": rng.choice([25, 35, 45, 55, 65]),
                    "lanes": rng.randint(1, 4),
                },
            })
        layers.append({"name": "roads", "version": 2, "extent": 4096, "features": road_features})

        # Buildings layer (only zoom >= 14)
        if z >= 14:
            building_features = []
            for i in range(rng.randint(5, 25)):
                cx = lon_deg + rng.uniform(-0.005, 0.005)
                cy = lat_deg + rng.uniform(-0.005, 0.005)
                size = rng.uniform(0.0002, 0.001)
                building_features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [round(cx - size, 6), round(cy - size, 6)],
                            [round(cx + size, 6), round(cy - size, 6)],
                            [round(cx + size, 6), round(cy + size, 6)],
                            [round(cx - size, 6), round(cy + size, 6)],
                            [round(cx - size, 6), round(cy - size, 6)],
                        ]],
                    },
                    "properties": {
                        "height": rng.randint(3, 200),
                        "type": rng.choice(["residential", "commercial", "industrial", "civic"]),
                    },
                })
            layers.append({"name": "buildings", "version": 2, "extent": 4096, "features": building_features})

        # Land use layer
        land_classes = ["grass", "wood", "water", "industrial", "residential", "commercial"]
        layers.append({
            "name": "landuse",
            "version": 2,
            "extent": 4096,
            "features": [{
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [round(lon_deg - 0.02, 6), round(lat_deg - 0.02, 6)],
                        [round(lon_deg + 0.02, 6), round(lat_deg - 0.02, 6)],
                        [round(lon_deg + 0.02, 6), round(lat_deg + 0.02, 6)],
                        [round(lon_deg - 0.02, 6), round(lat_deg + 0.02, 6)],
                        [round(lon_deg - 0.02, 6), round(lat_deg - 0.02, 6)],
                    ]],
                },
                "properties": {"class": rng.choice(land_classes)},
            }],
        })

        return {"z": z, "x": x, "y": y, "layers": layers}

    # -----------------------------------------------------------------------
    # Administrative boundaries
    # -----------------------------------------------------------------------

    def get_boundary(self, region: str) -> Optional[Dict[str, Any]]:
        """Return administrative boundary data for a named region."""
        # Try to match a known city/country
        region_lower = region.lower().strip()
        matched: Optional[Dict[str, Any]] = None
        for city in _CITY_DATA:
            if city["city"].lower() == region_lower or city["country"].lower() == region_lower:
                matched = city
                break

        rng = _rng("boundary", region_lower)
        if matched is None:
            # Generate plausible synthetic data
            lat = rng.uniform(-60, 70)
            lon = rng.uniform(-180, 180)
            matched = {
                "city": region.title(), "state": f"{region.title()} State",
                "country": "XX", "lat": lat, "lon": lon,
                "tz": "UTC", "pop": rng.randint(50_000, 5_000_000),
            }

        clat, clon = matched["lat"], matched["lon"]
        spread = rng.uniform(0.1, 0.8)
        polygon = self._generate_polygon(clat, clon, spread, rng)
        area = math.pi * (spread * 111) ** 2  # rough km²

        return {
            "region": region,
            "type": "administrative",
            "geometry": {"type": "Polygon", "coordinates": [polygon]},
            "properties": {
                "name": matched["city"],
                "name_local": matched["city"],
                "admin_level": 6,
                "population": matched.get("pop"),
                "area_km2": round(area, 2),
                "capital": matched["city"],
                "timezone": matched["tz"],
                "iso_code": matched["country"],
                "wikidata_id": f"Q{rng.randint(100000, 9999999)}",
            },
            "bounding_box": {
                "north": round(clat + spread, 6),
                "south": round(clat - spread, 6),
                "east": round(clon + spread, 6),
                "west": round(clon - spread, 6),
            },
        }

    def _generate_polygon(
        self, clat: float, clon: float, spread: float, rng: random.Random
    ) -> List[List[float]]:
        """Generate a rough convex polygon around a center point."""
        n = 16
        coords = []
        for i in range(n):
            angle = (2 * math.pi * i / n)
            r = spread * rng.uniform(0.7, 1.0)
            lat = clat + r * math.cos(angle)
            lon = clon + r * math.sin(angle) / max(0.1, math.cos(math.radians(clat)))
            coords.append([round(lon, 6), round(lat, 6)])
        coords.append(coords[0])  # close ring
        return coords

    # -----------------------------------------------------------------------
    # Elevation
    # -----------------------------------------------------------------------

    def get_elevation(self, lat: float, lon: float) -> Dict[str, Any]:
        """Return elevation and terrain data for a coordinate."""
        rng = _rng("elevation", round(lat, 2), round(lon, 2))

        # Rough heuristic: mountainous near poles/high latitudes, coastal near 0
        base_elev = abs(lat) * 20 + rng.uniform(-200, 200)
        # Add noise that's consistent for nearby coordinates
        noise = math.sin(lat * 10) * 50 + math.cos(lon * 10) * 30
        elevation = max(0.0, base_elev + noise + rng.uniform(-50, 50))

        if elevation < 10:
            terrain = "coastal"
        elif elevation < 100:
            terrain = "plains"
        elif elevation < 500:
            terrain = "hills"
        elif elevation < 1500:
            terrain = "highland"
        else:
            terrain = "mountain"

        resolution = 30.0 if rng.random() > 0.3 else 10.0

        return {
            "lat": lat,
            "lon": lon,
            "elevation_meters": round(elevation, 2),
            "datum": "EGM96",
            "resolution_meters": resolution,
            "terrain_type": terrain,
        }

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _nearest_city(self, lat: float, lon: float) -> Dict[str, Any]:
        """Return the city dict nearest to the given coordinates."""
        return min(
            _CITY_DATA,
            key=lambda c: _haversine(lat, lon, c["lat"], c["lon"]),
        )
