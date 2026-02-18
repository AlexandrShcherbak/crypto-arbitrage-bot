from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["🔎 Сканировать", "⚙️ Настройки"], ["📜 История", "📤 Экспорт XLSX"]],
        resize_keyboard=True,
    )


def settings_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Порог 1%", callback_data="threshold:1")],
            [InlineKeyboardButton("Порог 3%", callback_data="threshold:3")],
            [InlineKeyboardButton("Порог 5%", callback_data="threshold:5")],
            [InlineKeyboardButton("Стратегия: все", callback_data="strategy:all")],
            [InlineKeyboardButton("Стратегия: P2P", callback_data="strategy:p2p")],
            [InlineKeyboardButton("Стратегия: CEX", callback_data="strategy:cex-cex")],
            [InlineKeyboardButton("Стратегия: DEX", callback_data="strategy:dex-cex")],
            [InlineKeyboardButton("Стратегия: Triangle", callback_data="strategy:triangle")],
            [InlineKeyboardButton("Уведомления ON/OFF", callback_data="toggle_notifications")],
        ]
    )
