# geospatial-data-mainlayer

Geospatial and mapping data sold per query to AI location agents via [Mainlayer](https://mainlayer.fr).

## Overview

Production geospatial API: geocoding, routing, map tiles, elevation, and administrative boundaries. Each query is micropaid through Mainlayer.

**API Docs:** https://geo-api.example.com/docs

## Pricing

| Endpoint | Cost | Use Case |
|----------|------|----------|
| `/geocode` | $0.001 | Address → lat/lon |
| `/reverse-geocode` | $0.001 | Lat/lon → address |
| `/places/nearby` | $0.003 | Find restaurants, hotels, etc. near coordinate |
| `/routes` | $0.005 | Route + turn-by-turn directions |
| `/tiles/{z}/{x}/{y}` | $0.0005 | Vector map tile (roads, buildings, land use) |
| `/boundaries/{region}` | $0.002 | Administrative boundary polygon (GeoJSON) |
| `/elevation` | $0.001 | Terrain elevation + surface type |
| `/health` | FREE | Health check |

## Agent Example: Location-Based Queries

```python
from mainlayer import MainlayerClient
import httpx

client = MainlayerClient(api_key="sk_test_...")
token = client.get_access_token("geospatial-data-mainlayer")
headers = {"Authorization": f"Bearer {token}"}

# Geocode ($0.001)
result = httpx.get(
    "https://geo-api.example.com/geocode",
    params={"address": "1600 Pennsylvania Ave, Washington DC"},
    headers=headers
).json()

# Find nearby restaurants ($0.003)
places = httpx.get(
    "https://geo-api.example.com/places/nearby",
    params={"lat": result['lat'], "lon": result['lon'], "type": "restaurant"},
    headers=headers
).json()
print(f"Found {len(places['results'])} restaurants")
```

## Supported Place Types

restaurant, cafe, hotel, hospital, school, park, gym, pharmacy, bank, supermarket, museum, library, gas_station, airport

## Install & Run

```bash
pip install -e ".[dev]"
uvicorn src.main:app --reload
MAINLAYER_BYPASS_AUTH=true pytest tests/ -v  # local dev
```

## Environment Variables

```
MAINLAYER_API_KEY      # Your Mainlayer API key
MAINLAYER_BYPASS_AUTH  # Set true for local dev (skips payment checks)
MAINLAYER_BASE_URL     # Mainlayer API endpoint (default: https://api.mainlayer.fr)
```

📚 [Mainlayer Docs](https://docs.mainlayer.fr) | [mainlayer.fr](https://mainlayer.fr)
