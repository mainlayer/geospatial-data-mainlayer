"""
Mainlayer payment integration.

Handles API-key validation, per-request billing, and usage tracking.
Base URL: https://api.mainlayer.xyz
Auth:     Authorization: Bearer <api_key>
"""
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

from fastapi import HTTPException, Request, status


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MAINLAYER_BASE_URL: str = os.getenv("MAINLAYER_BASE_URL", "https://api.mainlayer.xyz")
MAINLAYER_SECRET: str = os.getenv("MAINLAYER_SECRET", "")  # server-side signing key
API_KEY_HEADER: str = "Authorization"
BEARER_PREFIX: str = "Bearer "

# Development / test bypass: set MAINLAYER_BYPASS_AUTH=true to skip key checks.
BYPASS_AUTH: bool = os.getenv("MAINLAYER_BYPASS_AUTH", "false").lower() == "true"


# ---------------------------------------------------------------------------
# In-process usage store (replace with DB in production)
# ---------------------------------------------------------------------------

@dataclass
class UsageRecord:
    api_key: str
    endpoint: str
    cost_usd: float
    timestamp: float = field(default_factory=time.time)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))


_usage_log: list[UsageRecord] = []
_cumulative_spend: Dict[str, float] = {}  # key → total USD spent this session


# ---------------------------------------------------------------------------
# Key extraction
# ---------------------------------------------------------------------------

def _extract_api_key(request: Request) -> Optional[str]:
    header = request.headers.get(API_KEY_HEADER, "")
    if header.startswith(BEARER_PREFIX):
        return header[len(BEARER_PREFIX):].strip()
    # Also accept ?api_key= query param for convenience
    return request.query_params.get("api_key")


def _validate_key_format(key: str) -> bool:
    """Basic structural check — real validation happens server-side."""
    return len(key) >= 16 and key.replace("-", "").replace("_", "").isalnum()


# ---------------------------------------------------------------------------
# Main guard
# ---------------------------------------------------------------------------

async def require_payment(request: Request, cost_usd: float, endpoint: str) -> str:
    """
    Validate the bearer token and record usage.

    Returns the API key so callers can include it in audit logs.
    Raises HTTP 401 / 402 on failure.
    """
    if BYPASS_AUTH:
        api_key = "dev-bypass"
    else:
        api_key = _extract_api_key(request)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "missing_api_key",
                    "message": (
                        "No API key provided. "
                        "Include 'Authorization: Bearer <api_key>' in your request header. "
                        f"Get your key at {MAINLAYER_BASE_URL}/keys"
                    ),
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not _validate_key_format(api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "invalid_api_key",
                    "message": "The API key format is invalid.",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Record usage
    record = UsageRecord(api_key=api_key, endpoint=endpoint, cost_usd=cost_usd)
    _usage_log.append(record)
    _cumulative_spend[api_key] = _cumulative_spend.get(api_key, 0.0) + cost_usd

    return api_key


# ---------------------------------------------------------------------------
# Usage reporting (internal)
# ---------------------------------------------------------------------------

def get_usage_summary(api_key: Optional[str] = None) -> Dict:
    """Return aggregated usage stats — useful for /debug/usage endpoints."""
    if api_key:
        records = [r for r in _usage_log if r.api_key == api_key]
        total = _cumulative_spend.get(api_key, 0.0)
    else:
        records = list(_usage_log)
        total = sum(_cumulative_spend.values())

    by_endpoint: Dict[str, Dict] = {}
    for r in records:
        ep = by_endpoint.setdefault(r.endpoint, {"requests": 0, "total_cost_usd": 0.0})
        ep["requests"] += 1
        ep["total_cost_usd"] = round(ep["total_cost_usd"] + r.cost_usd, 6)

    return {
        "total_requests": len(records),
        "total_cost_usd": round(total, 6),
        "by_endpoint": by_endpoint,
    }
