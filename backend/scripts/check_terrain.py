"""Live check of the USGS 3DEP terrain feed."""

import asyncio

from app.feeds import terrain

POINTS = {
    "downtown Dallas (flat/rolling)": (32.7831, -96.8067),
    "Guadalupe Mtns (rugged)": (31.89, -104.86),
}


async def main() -> None:
    for name, (lat, lon) in POINTS.items():
        t = await terrain.terrain(lat, lon)
        print(f"{name}: {t}")


if __name__ == "__main__":
    asyncio.run(main())
