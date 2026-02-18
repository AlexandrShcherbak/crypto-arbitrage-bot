from __future__ import annotations

from parsers.p2p_parser import P2PParser


async def get_binance_p2p(asset: str, fiat: str) -> list[dict]:
    parser = P2PParser()
    return [x for x in await parser.fetch_all(asset=asset, fiats=[fiat]) if x["exchange"] == "binance_p2p"]
