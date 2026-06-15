"""Strategy base class."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
import pandas as pd


@dataclass
class ScreeningResult:
    stock_code: str = ""
    stock_name: str = ""
    strategy_name: str = ""
    price: float = 0.0
    change_pct: float = 0.0
    volume_ratio: float = 0.0
    reason: str = ""
    indicators: dict[str, Any] = field(default_factory=dict)
    sector: str = ""
    concepts: str = ""
    market_cap: float = 0.0


class BaseStrategy(ABC):
    """Base class for all stock screening strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    def category(self) -> str:
        return "其他"

    @property
    def description(self) -> str:
        return ""

    @property
    def run_time(self) -> str:
        """When this strategy should run: 'pre_market', 'call_auction', or 'both'."""
        return "pre_market"

    @abstractmethod
    def screen(self, df: pd.DataFrame, code: str, name: str, **kwargs) -> list[ScreeningResult]:
        ...

    def get_latest(self, df: pd.DataFrame) -> pd.Series | None:
        if df.empty:
            return None
        return df.iloc[-1]
