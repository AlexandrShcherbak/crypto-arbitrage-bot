from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["🔎 Сканировать", "⚙️ Настройки"], ["📜 История"]],
        resize_keyboard=True,
    )


def settings_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Порог 1%", callback_data="threshold:1")],
            [InlineKeyboardButton("Порог 3%", callback_data="threshold:3")],
            [InlineKeyboardButton("Порог 5%", callback_data="threshold:5")],
            [InlineKeyboardButton("Уведомления ON/OFF", callback_data="toggle_notifications")],
        ]
    )
