from __future__ import annotations

import asyncio
import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from bot import callbacks, history, scan, settings_handler, start
from config import get_settings
from data import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


async def periodic_scan(application: Application) -> None:
    from bot.handlers import _collect_data, analyzer, db  # локальный import, чтобы не создавать циклы

    settings = get_settings()
    while True:
        await asyncio.sleep(settings.scan_interval_sec)
        users = await _get_users(db)
        if not users:
            continue

        cex_data, dex_data, p2p_data = await _collect_data(["BTC/USDT", "ETH/USDT", "SOL/USDT", "ETH/BTC"])
        for user in users:
            if not bool(user["notifications_enabled"]):
                continue
            opportunities = analyzer.find(
                cex_data,
                dex_data,
                p2p_data,
                min_profit_percent=float(user["min_profit_percent"]),
                strategy=str(user["selected_strategy"]),
            )
            for op in opportunities[:3]:
                await db.save_opportunity(user["user_id"], op)
                try:
                    await application.bot.send_message(
                        chat_id=user["user_id"],
                        text=(f"🚨 {op['route']}\nДоходность: {op['spread_percent']:.2f}%"),
                    )
                except Exception:  # noqa: BLE001
                    logging.exception("Failed sending notification")


async def _get_users(db: Database) -> list[dict]:
    import aiosqlite

    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM users") as cur:
            return [dict(r) for r in await cur.fetchall()]


def build_application() -> Application:
    settings = get_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not configured")

    app = Application.builder().token(settings.bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    app.add_handler(CommandHandler("settings", settings_handler))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CallbackQueryHandler(callbacks))

    app.add_handler(MessageHandler(filters.Regex("^🔎 Сканировать$"), scan))
    app.add_handler(MessageHandler(filters.Regex("^⚙️ Настройки$"), settings_handler))
    app.add_handler(MessageHandler(filters.Regex("^📜 История$"), history))
    return app


async def main() -> None:
    settings = get_settings()
    db = Database(settings.database_path)
    await db.init()

    app = build_application()
    app.create_task(periodic_scan(app))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
