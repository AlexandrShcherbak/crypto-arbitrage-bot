from __future__ import annotations

import logging
from typing import Any

import aiohttp

from config import get_settings
from utils import AsyncRateLimiter, AsyncTTLCache

logger = logging.getLogger(__name__)


class P2PParser:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.cache: AsyncTTLCache[list[dict[str, Any]]] = AsyncTTLCache(self.settings.cache_ttl_sec)
        self.last_success: dict[str, list[dict[str, Any]]] = {}
        self.rate_limiter = AsyncRateLimiter(self.settings.max_api_calls_per_sec, 1.0)

    async def fetch_all(
        self,
        asset: str = "USDT",
        fiats: list[str] | None = None,
        banks: list[str] | None = None,
        min_limit: float = 0,
        max_limit: float = 1_000_000,
    ) -> list[dict[str, Any]]:
        fiats = fiats or self.settings.p2p_fiats
        banks = banks or self.settings.p2p_banks
        cache_key = f"p2p:{asset}:{','.join(fiats)}:{','.join(banks)}:{min_limit}:{max_limit}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        opportunities: list[dict[str, Any]] = []
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
                for fiat in fiats:
                    opportunities.extend(await self._binance(session, asset, fiat, banks, min_limit, max_limit))
                    opportunities.extend(await self._bybit(session, asset, fiat, banks, min_limit, max_limit))
                    opportunities.extend(await self._garantex(session, asset, fiat, min_limit, max_limit))
            await self.cache.set(cache_key, opportunities)
            self.last_success[cache_key] = opportunities
            return opportunities
        except Exception as exc:  # noqa: BLE001
            logger.warning("P2P fetch failed, fallback to stale cache: %s", exc)
            return self.last_success.get(cache_key, [])

    async def _binance(self, session: aiohttp.ClientSession, asset: str, fiat: str, banks: list[str], min_limit: float, max_limit: float) -> list[dict[str, Any]]:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        payload = {
            "asset": asset,
            "fiat": fiat,
            "page": 1,
            "rows": 10,
            "tradeType": "BUY",
            "payTypes": banks,
        }
        try:
            await self.rate_limiter.wait()
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                out = []
                for adv in data.get("data", []):
                    price = float(adv["adv"].get("price", 0))
                    min_amt = float(adv["adv"].get("minSingleTransAmount", 0))
                    max_amt = float(adv["adv"].get("dynamicMaxSingleTransAmount", 0))
                    merchant = adv.get("advertiser", {}).get("userType") == "merchant"
                    if min_amt <= max_limit and max_amt >= min_limit:
                        out.append(
                            {
                                "exchange": "binance_p2p",
                                "asset": asset,
                                "fiat": fiat,
                                "price": price,
                                "min_limit": min_amt,
                                "max_limit": max_amt,
                                "merchant": merchant,
                                "payments": adv["adv"].get("tradeMethods", []),
                            }
                        )
                return out
        except Exception as exc:  # noqa: BLE001
            logger.warning("Binance P2P error: %s", exc)
            return []

    async def _bybit(self, session: aiohttp.ClientSession, asset: str, fiat: str, banks: list[str], min_limit: float, max_limit: float) -> list[dict[str, Any]]:
        url = "https://api2.bybit.com/fiat/otc/item/online"
        payload = {"tokenId": asset, "currencyId": fiat, "side": "1", "size": "10", "page": "1", "payment": banks}
        try:
            await self.rate_limiter.wait()
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                result: list[dict[str, Any]] = []
                for item in data.get("result", {}).get("items", []):
                    price = float(item.get("price", 0))
                    min_amt = float(item.get("minAmount", 0))
                    max_amt = float(item.get("maxAmount", 0))
                    if min_amt <= max_limit and max_amt >= min_limit:
                        result.append(
                            {
                                "exchange": "bybit_p2p",
                                "asset": asset,
                                "fiat": fiat,
                                "price": price,
                                "min_limit": min_amt,
                                "max_limit": max_amt,
                                "merchant": bool(item.get("authTag")),
                                "payments": item.get("payments", []),
                            }
                        )
                return result
        except Exception:
            return []

    async def _garantex(self, session: aiohttp.ClientSession, asset: str, fiat: str, min_limit: float, max_limit: float) -> list[dict[str, Any]]:
        if fiat != "RUB":
            return []
        try:
            await self.rate_limiter.wait()
            async with session.get("https://garantex.org/api/v2/depth?market=usdtrub") as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                asks = data.get("asks", [])[:5]
                out = []
                for ask in asks:
                    price = float(ask[0])
                    amount = float(ask[1])
                    rub_volume = price * amount
                    if min_limit <= rub_volume <= max_limit:
                        out.append(
                            {
                                "exchange": "garantex_p2p",
                                "asset": asset,
                                "fiat": fiat,
                                "price": price,
                                "min_limit": min_limit,
                                "max_limit": rub_volume,
                                "merchant": True,
                                "payments": ["bank_transfer"],
                            }
                        )
                return out
        except Exception:
            return []
