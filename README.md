# Crypto Arbitrage Telegram Bot

Асинхронный Telegram-бот для поиска арбитражных возможностей между CEX/DEX/P2P.

## Возможности
- Мониторинг CEX (через CCXT)
- Мониторинг DEX (CoinCap + The Graph + Web3 gas)
- P2P сканирование Binance / Bybit / Garantex
- Расчёт спреда, учёт комиссий и ликвидности
- Поиск треугольного арбитража
- Хранение пользователей/настроек/истории в SQLite
- Уведомления по порогу доходности

## Структура
- `parsers/` — сбор рыночных данных и Excel-стратегий
- `analyzers/` — математика и поиск возможностей
- `data/` — схема и CRUD
- `bot/` — Telegram handlers + UI

## Быстрый старт
1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
2. Создайте `.env` на основе `.env.example` и укажите `BOT_TOKEN`.
3. Запустите:
   ```bash
   python main.py
   ```

## Docker
```bash
docker compose up --build -d
```

## Excel стратегии
Парсер `parsers/excel_parser.py` читает `База связок.xlsx` (или любой xlsx), выделяет:
- тип стратегии (p2p/dex/cex/international),
- шаги связки,
- подсказки по спредам,
- требования (KYC, сети TRC20/BEP20/ERC20, лимиты, банки).

## Тесты
```bash
pytest -q
```
