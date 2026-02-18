from __future__ import annotations

from pathlib import Path
from typing import Any

from telegram import Update
from telegram.ext import CallbackContext

from analyzers import ArbitrageAnalyzer
from bot.keyboards import main_menu, settings_menu
from bot.messages import format_opportunity, welcome
from config import get_settings
from data import Database
from parsers.cex_parser import CEXParser
from parsers.dex_parser import DEXParser
from parsers.p2p_parser import P2PParser
from utils.validators import validate_profit_threshold

settings = get_settings()
db = Database(settings.database_path)
cex_parser = CEXParser()
dex_parser = DEXParser()
p2p_parser = P2PParser()
analyzer = ArbitrageAnalyzer()


async def start(update: Update, context: CallbackContext) -> None:
    if not update.effective_user or not update.message:
        return
    await db.upsert_user(update.effective_user.id, update.effective_user.username)
    await update.message.reply_text(welcome(update.effective_user.username), reply_markup=main_menu())


async def settings_handler(update: Update, context: CallbackContext) -> None:
    if update.message:
        await update.message.reply_text("Выберите порог доходности и тип стратегии:", reply_markup=settings_menu())


async def callbacks(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    if not query or not query.data or not update.effective_user:
        return

    await query.answer()
    user = await db.get_user(update.effective_user.id)
    if not user:
        await db.upsert_user(update.effective_user.id, update.effective_user.username)
        user = await db.get_user(update.effective_user.id)
        assert user is not None

    if query.data.startswith("threshold:"):
        threshold = float(query.data.split(":", 1)[1])
        if not validate_profit_threshold(threshold):
            await query.edit_message_text("❌ Некорректный порог")
            return
        await db.update_user_settings(
            update.effective_user.id,
            min_profit_percent=threshold,
            selected_strategy=user["selected_strategy"],
            notifications_enabled=bool(user["notifications_enabled"]),
        )
        await query.edit_message_text(f"✅ Порог обновлен: {threshold}%")
    elif query.data.startswith("strategy:"):
        strategy = query.data.split(":", 1)[1]
        await db.update_user_settings(
            update.effective_user.id,
            min_profit_percent=float(user["min_profit_percent"]),
            selected_strategy=strategy,
            notifications_enabled=bool(user["notifications_enabled"]),
        )
        await query.edit_message_text(f"✅ Стратегия обновлена: {strategy}")
    elif query.data == "toggle_notifications":
        new_status = not bool(user["notifications_enabled"])
        await db.update_user_settings(
            update.effective_user.id,
            min_profit_percent=float(user["min_profit_percent"]),
            selected_strategy=user["selected_strategy"],
            notifications_enabled=new_status,
        )
        await query.edit_message_text(f"🔔 Уведомления: {'вкл' if new_status else 'выкл'}")


async def scan(update: Update, context: CallbackContext) -> None:
    if not update.effective_user:
        return
    user = await db.get_user(update.effective_user.id)
    min_profit = float(user["min_profit_percent"]) if user else settings.min_profit_percent
    strategy = str(user["selected_strategy"]) if user else "all"

    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ETH/BTC"]
    cex_data, dex_data, p2p_data = await _collect_data(symbols)
    opportunities = analyzer.find(cex_data, dex_data, p2p_data, min_profit, strategy=strategy)

    filtered = [o for o in opportunities if float(o.get("liquidity", 0)) >= settings.min_liquidity_usd]
    if not filtered:
        if update.message:
            await update.message.reply_text("Возможности не найдены.")
        return

    top = filtered[:5]
    for op in top:
        await db.save_opportunity(update.effective_user.id, op)
        if update.message:
            await update.message.reply_html(format_opportunity(op))


async def history(update: Update, context: CallbackContext) -> None:
    if not update.effective_user or not update.message:
        return
    rows = await db.get_recent_opportunities(update.effective_user.id, limit=10)
    if not rows:
        await update.message.reply_text("История пока пустая.")
        return
    for row in rows:
        await update.message.reply_text(
            f"{row['created_at']} | {row['opportunity_type']} | {row['route']} | {row['spread_percent']:.2f}%"
        )


async def export_history(update: Update, context: CallbackContext) -> None:
    if not update.effective_user or not update.message:
        return
    rows = await db.get_recent_opportunities(update.effective_user.id, limit=200)
    if not rows:
        await update.message.reply_text("Нет данных для экспорта.")
        return

    try:
        from openpyxl import Workbook
    except ImportError:
        await update.message.reply_text("openpyxl не установлен, экспорт недоступен")
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "opportunities"
    ws.append(["created_at", "type", "route", "spread_percent", "buy_price", "sell_price", "fees", "liquidity"])
    for r in rows:
        ws.append([
            r.get("created_at"),
            r.get("opportunity_type"),
            r.get("route"),
            r.get("spread_percent"),
            r.get("buy_price"),
            r.get("sell_price"),
            r.get("fees"),
            r.get("liquidity"),
        ])

    out_dir = Path("data/exports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"history_{update.effective_user.id}.xlsx"
    wb.save(out_file)

    with out_file.open("rb") as f:
        await update.message.reply_document(document=f, filename=out_file.name, caption="Экспорт истории")


async def _collect_data(symbols: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    cex_data = await cex_parser.fetch_market_snapshot(symbols)
    dex_data = await dex_parser.fetch_coincap_prices(["bitcoin", "ethereum", "solana"])
    p2p_data = await p2p_parser.fetch_all(asset="USDT")
    return cex_data, dex_data, p2p_data
