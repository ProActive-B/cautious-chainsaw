"""Quick local check of the community ADS-B feed."""

import asyncio

from app.feeds import adsb


async def main() -> None:
    ac = await adsb.fetch_aircraft(32.6, -97.2, 33.1, -96.5, use_cache=False)
    print("status:", adsb.last_status)
    print("count:", len(ac))
    if ac:
        print("sample:", ac[0])


if __name__ == "__main__":
    asyncio.run(main())
