"""连板接力类策略: 一进二, 二进三, 龙头战法"""

import pandas as pd
import numpy as np
from .base import BaseStrategy, ScreeningResult


class YiJinErStrategy(BaseStrategy):
    """一进二: 昨日首板涨停，今日有望连板"""

    @property
    def name(self): return "一进二"

    @property
    def category(self): return "连板接力类"

    @property
    def description(self): return "昨日首次涨停（非一字），封板早，量能温和，板块效应强"

    def screen(self, df, code, name, **kwargs):
        if df.empty or len(df) < 10:
            return []
        last = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3] if len(df) > 2 else None

        is_limit_up = last["close"] >= last["prev_close"] * 1.095 if "prev_close" in df.columns else False
        if not is_limit_up:
            return []

        is_first_board = True
        if prev2 is not None:
            prev_up = prev["close"] >= prev["prev_close"] * 1.095 if "prev_close" in df.columns else False
            if prev_up:
                is_first_board = False

        # Volume check: not extreme
        vol_ratio = last.get("vol_ratio", 0)
        if vol_ratio > 5:
            return []

        sector_info = kwargs.get("sector_info", {})
        sector_strength = sector_info.get("limit_up_count", 0)

        reasons = []
        reasons.append(f"昨日涨停")
        if is_first_board:
            reasons.append("首板")
        if sector_strength >= 3:
            reasons.append(f"板块内有{sector_strength}只涨停")

        return [ScreeningResult(
            stock_code=code, stock_name=name,
            strategy_name=self.name, price=float(last["close"]),
            change_pct=float(((last["close"] - last["prev_close"]) / last["prev_close"] * 100) if "prev_close" in df.columns else 0),
            volume_ratio=float(vol_ratio),
            reason="，".join(reasons),
            indicators={
                "vol_ratio": float(vol_ratio),
                "sector_limit_ups": sector_strength,
                "is_first_board": is_first_board,
            },
            sector=sector_info.get("name", ""),
            market_cap=kwargs.get("market_cap", 0),
        )]


class ErJinSanStrategy(BaseStrategy):
    """二进三: 二连板后冲击三板"""

    @property
    def name(self): return "二进三"

    @property
    def category(self): return "连板接力类"

    @property
    def description(self): return "连续两个涨停后冲击三板，确认龙头地位的关键转折"

    def screen(self, df, code, name, **kwargs):
        if df.empty or len(df) < 5:
            return []
        last = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3] if len(df) > 2 else None

        is_limit_up = last["close"] >= last["prev_close"] * 1.095 if "prev_close" in df.columns else False
        if not is_limit_up:
            return []

        prev_limit_up = prev["close"] >= prev["prev_close"] * 1.095 if "prev_close" in df.columns else False
        prev2_limit_up = False
        if prev2 is not None:
            prev2_limit_up = prev2["close"] >= prev2["prev_close"] * 1.095 if "prev_close" in df.columns else False

        if not (prev_limit_up and prev2_limit_up):
            return []

        # Turnover check
        turnover = kwargs.get("turnover", 0)
        if turnover < 10:
            return []

        return [ScreeningResult(
            stock_code=code, stock_name=name,
            strategy_name=self.name, price=float(last["close"]),
            change_pct=10.0, volume_ratio=float(last.get("vol_ratio", 0)),
            reason=f"二进三：连续3个涨停，换手率{turnover:.1f}%，龙头确认阶段",
            indicators={"turnover": turnover, "board_count": 3}
        )]


class LongTouStrategy(BaseStrategy):
    """龙头战法: 热点板块中最强的龙头股"""

    @property
    def name(self): return "龙头战法"

    @property
    def category(self): return "连板接力类"

    @property
    def description(self): return "识别热点板块中最强的龙头股，板块内3只以上涨停"

    def screen(self, df, code, name, **kwargs):
        if df.empty:
            return []
        sector_info = kwargs.get("sector_info", {})
        sector_limit_ups = sector_info.get("limit_up_count", 0)

        if sector_limit_ups < 3:
            return []

        last = df.iloc[-1]
        is_limit_up = last["close"] >= last["prev_close"] * 1.095 if "prev_close" in df.columns else False
        if not is_limit_up:
            return []

        return [ScreeningResult(
            stock_code=code, stock_name=name,
            strategy_name=self.name, price=float(last["close"]),
            change_pct=10.0, volume_ratio=float(last.get("vol_ratio", 0)),
            reason=f"龙头战法：所属板块今日{sector_limit_ups}只涨停，板块效应显著",
            indicators={"sector_limit_ups": sector_limit_ups},
            sector=sector_info.get("name", ""),
        )]
