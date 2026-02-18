from __future__ import annotations

from analyzers.arbitrage_analyzer import ArbitrageAnalyzer
from analyzers.opportunity_finder import filter_opportunities
from analyzers.spread_calculator import calculate_international_profit, calculate_p2p_profit, calculate_spread_percent
from parsers.excel_parser import ExcelStrategyParser
from utils.validators import validate_profit_threshold


def test_spread_formula() -> None:
    spread = calculate_spread_percent(90.5, 92.3, fees_abs=1.0)
    assert round(spread, 4) == round(((92.3 - 90.5 - 1.0) / 90.5) * 100, 4)


def test_p2p_profit_formula() -> None:
    profit = calculate_p2p_profit(rub_spent=9050, usdt_received=100, rub_sell_price=92.3, fees_abs=90.5)
    assert profit == (100 * 92.3) - (9050 + 90.5)


def test_international_profit_formula() -> None:
    assert calculate_international_profit(100000, 104000, 1500) == 2500


def test_excel_strategy_detection() -> None:
    parser = ExcelStrategyParser()
    assert parser._detect_type("Покупка на Binance P2P через Тинькофф") == "p2p"
    assert parser._detect_type("ETH Uniswap -> PancakeSwap") == "dex"


def test_validate_profit_threshold() -> None:
    assert validate_profit_threshold(1.0)
    assert not validate_profit_threshold(-1)
    assert not validate_profit_threshold(101)


def test_filter_by_strategy() -> None:
    data = [
        {"type": "p2p", "spread_percent": 3.2},
        {"type": "cex-cex", "spread_percent": 3.0},
    ]
    result = filter_opportunities(data, min_profit=1.0, strategy="p2p")
    assert len(result) == 1
    assert result[0]["type"] == "p2p"


def test_arbitrage_analyzer_find() -> None:
    analyzer = ArbitrageAnalyzer()
    cex_data = [
        {"exchange": "binance", "symbol": "BTC/USDT", "ask": 100.0, "bid": 100.5, "spot_price": 100.2, "orderbook_depth": 1000, "maker_fee": 0.001, "taker_fee": 0.001},
        {"exchange": "bybit", "symbol": "BTC/USDT", "ask": 101.0, "bid": 101.5, "spot_price": 101.2, "orderbook_depth": 900, "maker_fee": 0.001, "taker_fee": 0.001},
        {"exchange": "binance", "symbol": "ETH/BTC", "ask": 0.05, "bid": 0.051, "spot_price": 0.0505, "orderbook_depth": 1000, "maker_fee": 0.001, "taker_fee": 0.001},
        {"exchange": "binance", "symbol": "ETH/USDT", "ask": 5.1, "bid": 5.2, "spot_price": 5.15, "orderbook_depth": 1000, "maker_fee": 0.001, "taker_fee": 0.001},
    ]
    dex_data = [{"exchange": "ethereum-dex", "symbol": "BTC/USDT", "price": 99.0, "liquidity": 10000}]
    p2p_data = [
        {"exchange": "binance_p2p", "asset": "USDT", "fiat": "RUB", "price": 90.5, "max_limit": 100000},
        {"exchange": "garantex_p2p", "asset": "USDT", "fiat": "RUB", "price": 92.3, "max_limit": 120000},
    ]

    result = analyzer.find(cex_data, dex_data, p2p_data, min_profit_percent=0.1)
    assert result
    assert any(x["type"] == "p2p" for x in result)
