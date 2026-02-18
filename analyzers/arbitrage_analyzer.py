from __future__ import annotations

from collections import defaultdict
from typing import Any

from analyzers.opportunity_finder import classify_opportunity, filter_opportunities
from analyzers.spread_calculator import calculate_spread_percent


class ArbitrageAnalyzer:
    def find(
        self,
        cex_data: list[dict[str, Any]],
        dex_data: list[dict[str, Any]],
        p2p_data: list[dict[str, Any]],
        min_profit_percent: float,
        strategy: str = "all",
    ) -> list[dict[str, Any]]:
        opportunities: list[dict[str, Any]] = []
        opportunities.extend(self._cex_to_cex(cex_data))
        opportunities.extend(self._dex_to_cex(dex_data, cex_data))
        opportunities.extend(self._p2p_pairs(p2p_data))
        opportunities.extend(self._triangular(cex_data))

        for opp in opportunities:
            opp["grade"] = classify_opportunity(float(opp.get("spread_percent", 0)))

        return filter_opportunities(opportunities, min_profit=min_profit_percent, strategy=strategy)

    def _cex_to_cex(self, cex_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in cex_data:
            by_symbol[item.get("symbol", "")].append(item)

        out: list[dict[str, Any]] = []
        for symbol, markets in by_symbol.items():
            for buy in markets:
                for sell in markets:
                    if buy["exchange"] == sell["exchange"]:
                        continue
                    buy_price = float(buy.get("ask") or buy.get("spot_price") or 0)
                    sell_price = float(sell.get("bid") or sell.get("spot_price") or 0)
                    if buy_price <= 0 or sell_price <= 0:
                        continue
                    fee = float(buy.get("taker_fee", 0)) * buy_price + float(sell.get("maker_fee", 0)) * sell_price
                    spread = calculate_spread_percent(buy_price, sell_price, fee)
                    out.append(
                        {
                            "type": "cex-cex",
                            "route": f"{buy['exchange']} -> {sell['exchange']} ({symbol})",
                            "buy_price": buy_price,
                            "sell_price": sell_price,
                            "fees": fee,
                            "spread_percent": spread,
                            "liquidity": min(float(buy.get("orderbook_depth", 0)), float(sell.get("orderbook_depth", 0))),
                        }
                    )
        return out

    def _dex_to_cex(self, dex_data: list[dict[str, Any]], cex_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for dex in dex_data:
            symbol = dex.get("symbol")
            for cex in cex_data:
                if cex.get("symbol") != symbol:
                    continue
                buy_price = float(dex.get("price") or 0)
                sell_price = float(cex.get("bid") or cex.get("spot_price") or 0)
                if buy_price <= 0 or sell_price <= 0:
                    continue
                fees = 1.5
                spread = calculate_spread_percent(buy_price, sell_price, fees)
                out.append(
                    {
                        "type": "dex-cex",
                        "route": f"{dex['exchange']} -> {cex['exchange']} ({symbol})",
                        "buy_price": buy_price,
                        "sell_price": sell_price,
                        "fees": fees,
                        "spread_percent": spread,
                        "liquidity": min(float(dex.get("liquidity", 0)), float(cex.get("orderbook_depth", 0))),
                    }
                )
        return out

    def _p2p_pairs(self, p2p_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for buy in p2p_data:
            for sell in p2p_data:
                if buy["exchange"] == sell["exchange"]:
                    continue
                if buy["fiat"] != sell["fiat"]:
                    continue
                buy_price = float(buy.get("price", 0))
                sell_price = float(sell.get("price", 0))
                if sell_price <= buy_price:
                    continue
                fees = 1.0
                spread = calculate_spread_percent(buy_price, sell_price, fees)
                out.append(
                    {
                        "type": "p2p",
                        "route": f"{buy['exchange']} -> {sell['exchange']} ({buy['asset']}/{buy['fiat']})",
                        "buy_price": buy_price,
                        "sell_price": sell_price,
                        "fees": fees,
                        "spread_percent": spread,
                        "liquidity": min(float(buy.get("max_limit", 0)), float(sell.get("max_limit", 0))),
                    }
                )
        return out

    def _triangular(self, cex_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Упрощенный поиск: ищем символы BTC/USDT, ETH/BTC, ETH/USDT в одной бирже
        by_exchange: dict[str, dict[str, float]] = defaultdict(dict)
        for row in cex_data:
            exchange = row.get("exchange", "")
            symbol = row.get("symbol", "")
            price = float(row.get("spot_price") or 0)
            if symbol and price > 0:
                by_exchange[exchange][symbol] = price

        out: list[dict[str, Any]] = []
        for exchange, prices in by_exchange.items():
            if not {"BTC/USDT", "ETH/BTC", "ETH/USDT"}.issubset(set(prices.keys())):
                continue
            theoretical = prices["BTC/USDT"] * prices["ETH/BTC"]
            actual = prices["ETH/USDT"]
            spread = calculate_spread_percent(theoretical, actual, fees_abs=theoretical * 0.002)
            out.append(
                {
                    "type": "triangle",
                    "route": f"{exchange}: USDT -> BTC -> ETH -> USDT",
                    "buy_price": theoretical,
                    "sell_price": actual,
                    "fees": theoretical * 0.002,
                    "spread_percent": spread,
                    "liquidity": 0,
                }
            )
        return out
