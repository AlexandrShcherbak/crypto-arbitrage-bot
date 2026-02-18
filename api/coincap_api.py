from __future__ import annotations

from parsers.dex_parser import DEXParser


async def get_assets_prices(assets: list[str]) -> list[dict]:
    parser = DEXParser()
    return await parser.fetch_coincap_prices(assets)
