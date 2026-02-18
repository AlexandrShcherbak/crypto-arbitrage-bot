from __future__ import annotations

from typing import Iterable


def validate_profit_threshold(value: float) -> bool:
    return 0 <= value <= 100


def validate_symbol(symbol: str) -> bool:
    return "/" in symbol and 3 <= len(symbol) <= 20


def normalize_banks(banks: Iterable[str]) -> list[str]:
    return [b.strip() for b in banks if b and b.strip()]
