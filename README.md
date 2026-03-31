# Geospatial Data Mainlayer

Geospatial and mapping data sold per query to AI agents via [Mainlayer](https://mainlayer.fr) payment infrastructure.

## Endpoints

| Method | Path | Price | Description |
|--------|------|-------|-------------|
| GET | `/geocode?address=` | $0.001 | Address → coordinates |
| GET | `/reverse-geocode?lat=&lon=` | $0.001 | Coordinates → address |
| GET | `/places/nearby?lat=&lon=&type=` | $0.003 | Nearby places search |
| GET | `/routes?from=&to=` | $0.005 | Route calculation |
| GET | `/tiles/{z}/{x}/{y}` | $0.0005 | Vector map tile data |
| GET | `/boundaries/{region}` | $0.002 | Administrative boundaries |
| GET | `/elevation?lat=&lon=` | $0.001 | Terrain elevation data |
| GET | `/health` | free | Health check |

## Authentication

All paid endpoints require a Mainlayer API key:

```
Authorization: Bearer <your_mainlayer_api_key>
```

Get your API key at [mainlayer.fr](https://mainlayer.fr).

## Quick Start

```python
import httpx

headers = {"Authorization": "Bearer YOUR_API_KEY"}

# Geocode an address
result = httpx.get(
    "https://geo-api.example.com/geocode",
    params={"address": "10 Downing Street, London"},
    headers=headers,
).json()

print(f"Lat: {result['lat']}, Lon: {result['lon']}")
```

## Running Locally

```bash
pip install -e ".[dev]"
MAINLAYER_BYPASS_AUTH=true uvicorn src.main:app --reload
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive API docs.

## Development Mode

Set `MAINLAYER_BYPASS_AUTH=true` to bypass payment validation during local development.

## Running Tests

```bash
pytest tests/ -v
```

## Examples

- [`examples/geocode_addresses.py`](examples/geocode_addresses.py) — Geocode addresses and reverse-geocode coordinates
- [`examples/get_tiles.py`](examples/get_tiles.py) — Fetch map tiles and nearby places
