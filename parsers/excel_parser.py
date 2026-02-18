from __future__ import annotations

import re
from pathlib import Path
from typing import Any

STRATEGY_PATTERNS = {
    "p2p": re.compile(r"p2p|банк|тинькофф|сбер|merchan", re.IGNORECASE),
    "dex": re.compile(r"uniswap|pancakeswap|dex|swap", re.IGNORECASE),
    "cex": re.compile(r"binance|bybit|okx|huobi|cex", re.IGNORECASE),
    "international": re.compile(r"swift|золотая\s*корона|uzs|kzt|uah", re.IGNORECASE),
}


class ExcelStrategyParser:
    def parse(self, filepath: str) -> list[dict[str, Any]]:
        if not Path(filepath).exists():
            return []

        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError("Для чтения Excel установите pandas/openpyxl") from exc

        xls = pd.ExcelFile(filepath)
        strategies: list[dict[str, Any]] = []
        for sheet in xls.sheet_names:
            df = pd.read_excel(filepath, sheet_name=sheet)
            df = df.fillna("")
            for _, row in df.iterrows():
                row_text = " | ".join(str(v) for v in row.values)
                strategy_type = self._detect_type(row_text)
                spread_values = self._extract_spreads(row_text)
                steps = [x.strip() for x in re.split(r"->|→|\n", row_text) if x.strip()]
                strategies.append(
                    {
                        "sheet": sheet,
                        "strategy_type": strategy_type,
                        "raw": row.to_dict(),
                        "steps": steps,
                        "spread_hints": spread_values,
                        "requirements": self._extract_requirements(row_text),
                    }
                )
        return strategies

    def _detect_type(self, text: str) -> str:
        for strategy, pattern in STRATEGY_PATTERNS.items():
            if pattern.search(text):
                return strategy
        return "unknown"

    def _extract_spreads(self, text: str) -> list[float]:
        found = re.findall(r"(\d+(?:[\.,]\d+)?)\s*%", text)
        return [float(x.replace(",", ".")) for x in found]

    def _extract_requirements(self, text: str) -> list[str]:
        req: list[str] = []
        for keyword in ["KYC", "TRC20", "BEP20", "ERC20", "лимит", "банк", "мерчант"]:
            if keyword.lower() in text.lower():
                req.append(keyword)
        return req
