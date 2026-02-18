from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class FeeModel:
    exchange_fee_percent: float = 0.1
    network_fee_abs: float = 0.0
    withdrawal_fee_abs: float = 0.0
    gas_fee_abs: float = 0.0

    @property
    def total_abs(self) -> float:
        return self.network_fee_abs + self.withdrawal_fee_abs + self.gas_fee_abs


def calculate_spread_percent(price_buy: float, price_sell: float, fees_abs: float = 0.0) -> float:
    if price_buy <= 0:
        return 0.0
    return ((price_sell - price_buy - fees_abs) / price_buy) * 100


def calculate_p2p_profit(rub_spent: float, usdt_received: float, rub_sell_price: float, fees_abs: float = 0.0) -> float:
    return (usdt_received * rub_sell_price) - (rub_spent + fees_abs)


def calculate_international_profit(initial_rub: float, final_rub: float, all_fees_abs: float) -> float:
    return final_rub - initial_rub - all_fees_abs
