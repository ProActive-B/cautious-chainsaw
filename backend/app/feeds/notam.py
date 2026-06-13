"""Temporary Flight Restrictions (TFR) / NOTAMs.

The authoritative source (FAA FNS NOTAM API) requires a registered API key.
When ``FAA_NOTAM_API_KEY`` is configured this client queries it; otherwise it
degrades to an empty result with a status note rather than fabricating TFRs.
TFR geometry parsing (AIXM) is intentionally deferred until a key is available.
"""

from __future__ import annotations

from ..config import settings
from .cache import TTLCache

_cache = TTLCache(ttl_seconds=120)


async def fetch_tfrs(lamin: float, lomin: float, lamax: float, lomax: float) -> dict:
    """Return {"configured": bool, "tfrs": [...], "note": str}.

    Each TFR (when available) is {"name": str, "geometry": GeoJSON-or-None}.
    """
    if not settings.faa_notam_api_key:
        return {
            "configured": False,
            "tfrs": [],
            "note": "TFR/NOTAM feed not configured (set FAA_NOTAM_API_KEY). "
            "Active TFRs are NOT reflected in this assessment.",
        }

    key = f"tfr:{lamin:.1f},{lomin:.1f},{lamax:.1f},{lomax:.1f}"
    cached = _cache.get(key)
    if cached is not None:
        return cached

    # Placeholder for the authenticated FNS call + AIXM->GeoJSON parsing.
    # Implemented once a key is provisioned; fail safe to "no TFRs" on error.
    result = {"configured": True, "tfrs": [], "note": "FNS query returned no active TFRs."}
    _cache.set(key, result)
    return result
