from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import aiosqlite


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def init(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as conn:
            schema = Path("data/schema.sql").read_text(encoding="utf-8")
            await conn.executescript(schema)
            await conn.commit()

    async def upsert_user(self, user_id: int, username: str | None) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT INTO users(user_id, username)
                VALUES(?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                  username=excluded.username,
                  updated_at=CURRENT_TIMESTAMP
                """,
                (user_id, username),
            )
            await conn.commit()

    async def update_user_settings(self, user_id: int, min_profit_percent: float, selected_strategy: str, notifications_enabled: bool) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                UPDATE users
                SET min_profit_percent=?, selected_strategy=?, notifications_enabled=?, updated_at=CURRENT_TIMESTAMP
                WHERE user_id=?
                """,
                (min_profit_percent, selected_strategy, int(notifications_enabled), user_id),
            )
            await conn.commit()

    async def get_user(self, user_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def save_opportunity(self, user_id: int | None, opportunity: dict[str, Any]) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT INTO opportunities(user_id, opportunity_type, route, buy_price, sell_price, fees, spread_percent, liquidity, metadata_json)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    opportunity.get("type", "unknown"),
                    opportunity.get("route", ""),
                    opportunity.get("buy_price"),
                    opportunity.get("sell_price"),
                    opportunity.get("fees", 0),
                    opportunity.get("spread_percent"),
                    opportunity.get("liquidity"),
                    json.dumps(opportunity, ensure_ascii=False),
                ),
            )
            await conn.commit()

    async def get_recent_opportunities(self, user_id: int, limit: int = 10) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                """
                SELECT * FROM opportunities
                WHERE user_id=?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ) as cur:
                rows = await cur.fetchall()
                return [dict(row) for row in rows]

    async def set_cache(self, key: str, payload: dict[str, Any], ttl_sec: int) -> None:
        expires_at = int(time.time()) + ttl_sec
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT INTO scan_cache(cache_key, payload_json, expires_at)
                VALUES(?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET payload_json=excluded.payload_json, expires_at=excluded.expires_at
                """,
                (key, json.dumps(payload, ensure_ascii=False), expires_at),
            )
            await conn.commit()

    async def get_cache(self, key: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute(
                "SELECT payload_json, expires_at FROM scan_cache WHERE cache_key=?",
                (key,),
            ) as cur:
                row = await cur.fetchone()
                if not row:
                    return None
                payload_json, expires_at = row
                if expires_at < int(time.time()):
                    return None
                return json.loads(payload_json)
