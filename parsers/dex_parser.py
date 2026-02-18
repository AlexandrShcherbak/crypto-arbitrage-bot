from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
from web3 import AsyncWeb3
from web3.providers.async_rpc import AsyncHTTPProvider

from config import get_settings
from utils import AsyncTTLCache, retry_async


class DEXParser:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.cache: AsyncTTLCache[list[dict[str, Any]]] = AsyncTTLCache(self.settings.cache_ttl_sec)
        self.graph_endpoints = {
            "ethereum": "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3",
            "bsc": "https://api.thegraph.com/subgraphs/name/pancakeswap/exchange-v3-bsc",
            "polygon": "https://api.thegraph.com/subgraphs/name/ianlapham/uniswap-v3-polygon",
        }

    @retry_async(retries=2, delay=1)
    async def fetch_coincap_prices(self, assets: list[str]) -> list[dict[str, Any]]:
        cache_key = f"coincap:{','.join(sorted(assets))}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            tasks = [self._fetch_asset(session, asset) for asset in assets]
            prices = [x for x in await asyncio.gather(*tasks, return_exceptions=False) if x]
            await self.cache.set(cache_key, prices)
            return prices

    async def _fetch_asset(self, session: aiohttp.ClientSession, asset: str) -> dict[str, Any] | None:
        async with session.get(f"{self.settings.coincap_base_url}/assets/{asset.lower()}") as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            asset_data = data.get("data", {})
            return {
                "source": "CoinCap",
                "exchange": "dex-aggregated",
                "symbol": asset_data.get("symbol", asset.upper()) + "/USDT",
                "price": float(asset_data.get("priceUsd", 0)),
                "liquidity": float(asset_data.get("volumeUsd24Hr", 0)),
                "network": "ethereum",
            }

    async def fetch_graph_pool_price(self, network: str, token0: str, token1: str) -> dict[str, Any] | None:
        endpoint = self.graph_endpoints.get(network)
        if not endpoint:
            return None
        query = {
            "query": """
            { pools(first: 1, orderBy: totalValueLockedUSD, orderDirection: desc,
              where: {token0_: {symbol: \"%s\"}, token1_: {symbol: \"%s\"}}) {
                token0Price
                totalValueLockedUSD
              }
            }
            """
            % (token0, token1)
        }
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.post(endpoint, json=query) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                pools = data.get("data", {}).get("pools", [])
                if not pools:
                    return None
                p = pools[0]
                return {
                    "source": "TheGraph",
                    "exchange": f"{network}-dex",
                    "symbol": f"{token0}/{token1}",
                    "price": float(p.get("token0Price", 0)),
                    "liquidity": float(p.get("totalValueLockedUSD", 0)),
                    "network": network,
                }

    async def fetch_gas_price_gwei(self, rpc_url: str) -> float:
        w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))
        gas_wei = await w3.eth.gas_price
        return float(w3.from_wei(gas_wei, "gwei"))
