from __future__ import annotations

from typing import Any


def classify_opportunity(spread_percent: float) -> str:
    if spread_percent >= 5:
        return "high"
    if spread_percent >= 2:
        return "medium"
    if spread_percent >= 1:
        return "low"
    return "ignore"


def filter_opportunities(opportunities: list[dict[str, Any]], min_profit: float, strategy: str = "all") -> list[dict[str, Any]]:
    out = [o for o in opportunities if float(o.get("spread_percent", 0)) >= min_profit]
    if strategy != "all":
        out = [o for o in out if o.get("type") == strategy]
    return sorted(out, key=lambda x: x.get("spread_percent", 0), reverse=True)
