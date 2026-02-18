from __future__ import annotations

import asyncio
import logging
from typing import Any

import ccxt.async_support as ccxt

from config import get_settings
from utils import AsyncRateLimiter, AsyncTTLCache

logger = logging.getLogger(__name__)


class CEXParser:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.cache: AsyncTTLCache[list[dict[str, Any]]] = AsyncTTLCache(self.settings.cache_ttl_sec)
        self.rate_limiter = AsyncRateLimiter(self.settings.max_api_calls_per_sec, 1.0)

    async def fetch_market_snapshot(self, symbols: list[str]) -> list[dict[str, Any]]:
        cache_key = f"cex:{','.join(sorted(symbols))}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        tasks = [self._fetch_exchange(exchange_id, symbols) for exchange_id in self.settings.enabled_cex]
        results = [x for x in await asyncio.gather(*tasks, return_exceptions=True) if not isinstance(x, Exception)]
        flattened = [item for sub in results for item in sub]
        await self.cache.set(cache_key, flattened)
        return flattened

    async def _fetch_exchange(self, exchange_id: str, symbols: list[str]) -> list[dict[str, Any]]:
        exchange_cls = getattr(ccxt, exchange_id, None)
        if not exchange_cls:
            return []

        exchange = exchange_cls({"enableRateLimit": True, "timeout": 12000})
        try:
            await self.rate_limiter.wait()
            await exchange.load_markets()
            out: list[dict[str, Any]] = []
            for symbol in symbols:
                if symbol not in exchange.markets:
                    continue
                await self.rate_limiter.wait()
                ticker = await exchange.fetch_ticker(symbol)
                await self.rate_limiter.wait()
                order_book = await exchange.fetch_order_book(symbol, limit=10)
                quote_asset = symbol.split("/")[-1]
                network_fees = await self._get_network_fees(exchange, quote_asset)
                out.append(
                    {
                        "source": "CCXT",
                        "exchange": exchange_id,
                        "symbol": symbol,
                        "spot_price": ticker.get("last") or ticker.get("close"),
                        "bid": ticker.get("bid"),
                        "ask": ticker.get("ask"),
                        "futures_price": None,
                        "orderbook_depth": self._depth(order_book),
                        "network_fees": network_fees,
                        "maker_fee": exchange.fees.get("trading", {}).get("maker", 0.001),
                        "taker_fee": exchange.fees.get("trading", {}).get("taker", 0.001),
                    }
                )
            return out
        except Exception as exc:  # noqa: BLE001
            logger.warning("CEX fetch error %s: %s", exchange_id, exc)
            return []
        finally:
            await exchange.close()

    async def _get_network_fees(self, exchange: Any, currency: str) -> dict[str, float]:
        try:
            await self.rate_limiter.wait()
            currencies = await exchange.fetch_currencies()
            c = currencies.get(currency, {})
            networks = c.get("networks", {})
            return {name: float(net.get("fee") or 0) for name, net in networks.items()}
        except Exception:  # noqa: BLE001
            return {"TRC20": 1.0, "BEP20": 0.3, "ERC20": 5.0}

    def _depth(self, order_book: dict[str, Any]) -> float:
        bids = order_book.get("bids", [])[:10]
        asks = order_book.get("asks", [])[:10]
        return float(sum(level[1] for level in bids + asks if len(level) >= 2))
