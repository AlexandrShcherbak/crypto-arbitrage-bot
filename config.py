from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from typing import List


@dataclass(slots=True)
class Settings:
    bot_token: str
    database_path: str
    scan_interval_sec: int
    min_profit_percent: float
    cache_ttl_sec: int
    coincap_base_url: str
    enabled_cex: List[str]
    p2p_fiats: List[str]
    p2p_banks: List[str]
    min_liquidity_usd: float
    max_api_calls_per_sec: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", ""),
        database_path=os.getenv("DATABASE_PATH", "data/arbitrage.db"),
        scan_interval_sec=int(os.getenv("SCAN_INTERVAL_SEC", "60")),
        min_profit_percent=float(os.getenv("MIN_PROFIT_PERCENT", "1.0")),
        cache_ttl_sec=int(os.getenv("CACHE_TTL_SEC", "45")),
        coincap_base_url=os.getenv("COINCAP_BASE_URL", "https://api.coincap.io/v2"),
        enabled_cex=[x.strip() for x in os.getenv("ENABLED_CEX", "binance,bybit,okx,kucoin,kraken,huobi,bitfinex,mexc,gateio,coinbase").split(",") if x.strip()],
        p2p_fiats=[x.strip().upper() for x in os.getenv("P2P_FIATS", "RUB,USD,EUR,UZS,KZT,UAH").split(",") if x.strip()],
        p2p_banks=[x.strip() for x in os.getenv("P2P_BANKS", "Tinkoff,Sberbank,Raiffeisen,QIWI,YooMoney").split(",") if x.strip()],
        min_liquidity_usd=float(os.getenv("MIN_LIQUIDITY_USD", "1000")),
        max_api_calls_per_sec=int(os.getenv("MAX_API_CALLS_PER_SEC", "5")),
    )

