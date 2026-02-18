from __future__ import annotations

from typing import Any


def welcome(username: str | None) -> str:
    user = username or "трейдер"
    return (
        f"Привет, {user}!\n"
        "Я бот для поиска крипто-арбитража между CEX/DEX/P2P.\n"
        "Нажмите '🔎 Сканировать' для запуска поиска возможностей."
    )


def format_opportunity(op: dict[str, Any]) -> str:
    return (
        f"📌 <b>{op.get('type')}</b>\n"
        f"Маршрут: <code>{op.get('route')}</code>\n"
        f"Покупка: {op.get('buy_price'):.4f}\n"
        f"Продажа: {op.get('sell_price'):.4f}\n"
        f"Спред: <b>{op.get('spread_percent'):.2f}%</b>\n"
        f"Комиссии: {op.get('fees'):.4f}\n"
        f"Ликвидность: {op.get('liquidity'):.2f}"
    )
