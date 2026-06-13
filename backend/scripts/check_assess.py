"""Reproduce the /api/assess chain locally with live ADS-B to surface errors."""

import asyncio
import traceback

from app.feeds import adsb
from app.models import AssessRequest
from app.report import build_report
from app.spatial.attributes import gather


async def main() -> None:
    bbox = (32.8998 - 0.25, -97.0403 - 0.25, 32.8998 + 0.25, -97.0403 + 0.25)
    air = await adsb.fetch_aircraft(*bbox, use_cache=False)
    print("aircraft fetched:", len(air))
    nulls = [a for a in air if not a.get("icao24")]
    print("aircraft with null icao24:", len(nulls))
    try:
        loc = gather(32.8998, -97.0403, aircraft=air)
        report = build_report(AssessRequest(profile="federal_124n", lat=32.8998, lon=-97.0403), loc)
        print("OK: nearby_aircraft =", len(loc.nearby_aircraft), "| conditional =", len(report.conditional))
    except Exception:
        print("EXCEPTION:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
