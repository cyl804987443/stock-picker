"""情绪趋势类策略: 龙回头, 涨停基因"""

import pandas as pd
import numpy as np
from .base import BaseStrategy, ScreeningResult


class LongHuiTouStrategy(BaseStrategy):
    """龙回头: 前期龙头回调至均线支撑位"""

    @property
    def name(self): return "龙回头"

    @property
    def category(self): return "情绪趋势类"

    @property
    def description(self): return "前期30日内涨幅>30%，回调15-40%至MA20/MA60附近，缩量企稳"

    def screen(self, df, code, name, **kwargs):
        if df.empty or len(df) < 30:
            return []
        df30 = df.tail(30)
        if len(df30) < 20:
            return []

        max_close = df30["close"].max()
        min_close_30 = df30["close"].min()
        current = df30.iloc[-1]["close"]

        max_gain = (max_close - min_close_30) / min_close_30 * 100
        pullback = (max_close - current) / max_close * 100

        if max_gain < 30:
            return []
        if pullback < 15 or pullback > 40:
            return []

        last = df.iloc[-1]
        ma20 = last.get("ma20", 0)
        ma60 = last.get("ma60", 0)

        near_support = False
        support = ""
        if ma20 > 0 and abs(current - ma20) / ma20 < 0.03:
            near_support = True
            support = f"MA20({ma20:.2f})"
        elif ma60 > 0 and abs(current - ma60) / ma60 < 0.03:
            near_support = True
            support = f"MA60({ma60:.2f})"

        if not near_support:
            return []

        # Volume shrinking
        vol_ratio = last.get("vol_ratio", 0)
        if vol_ratio is None or pd.isna(vol_ratio) or vol_ratio > 0.7:
            return []

        # Not making new lows
        recent_lows = df.tail(5)["low"].values
        if len(recent_lows) < 5:
            return []
        if not (recent_lows[-1] >= recent_lows[-2] >= recent_lows[-3]):
            return []

        return [ScreeningResult(
            stock_code=code, stock_name=name,
            strategy_name=self.name, price=float(current),
            change_pct=float((last["close"] - df.iloc[-2]["close"]) / df.iloc[-2]["close"] * 100),
            volume_ratio=float(vol_ratio),
            reason=f"龙回头：前期涨幅{max_gain:.0f}%，回调{pullback:.1f}%至{support}，缩量企稳",
            indicators={
                "max_gain": float(max_gain),
                "pullback": float(pullback),
                "support": support,
                "vol_ratio": float(vol_ratio),
            }
        )]


class TingBanJiYinStrategy(BaseStrategy):
    """涨停基因: 近期有涨停记录，回调后可能再起"""

    @property
    def name(self): return "涨停基因"

    @property
    def category(self): return "情绪趋势类"

    @property
    def description(self): return "近20日内出现涨停，回调<15%，在MA20上方，今日量放大"

    def screen(self, df, code, name, **kwargs):
        if df.empty or len(df) < 20:
            return []
        df20 = df.tail(20)
        last = df20.iloc[-1]

        # Check if any recent limit-up
        has_limit_up = False
        limit_date = ""
        for i in range(len(df20) - 1):
            row = df20.iloc[i]
            prev_close = df20.iloc[i - 1]["close"] if i > 0 else row["close"] * 0.9
            try:
                change = (row["close"] - prev_close) / prev_close * 100
                if change > 9.0:
                    has_limit_up = True
                    limit_date = row["trade_date"] if "trade_date" in df20.columns else ""
                    break
            except:
                continue

        if not has_limit_up:
            return []

        # Pullback check: current price above MA20
        ma20 = last.get("ma20", 0)
        if not ma20 or last["close"] < ma20:
            return []

        # Volume increasing today
        vol_ratio = last.get("vol_ratio", 0)
        if vol_ratio is None or pd.isna(vol_ratio) or vol_ratio < 1.0:
            return []

        return [ScreeningResult(
            stock_code=code, stock_name=name,
            strategy_name=self.name, price=float(last["close"]),
            change_pct=float((last["close"] - df20.iloc[-2]["close"]) / df20.iloc[-2]["close"] * 100),
            volume_ratio=float(vol_ratio),
            reason=f"涨停基因：近20日出现涨停({limit_date})，今日量能放大(量比{vol_ratio:.1f})，站稳MA20上方",
            indicators={
                "limit_date": limit_date,
                "vol_ratio": float(vol_ratio),
                "above_ma20": float(ma20),
            }
        )]
