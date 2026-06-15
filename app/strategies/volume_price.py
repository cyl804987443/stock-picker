"""量价关系类策略: 底部爆量, 量窒息, 放量突破"""

import pandas as pd
import numpy as np
from .base import BaseStrategy, ScreeningResult


class DiBuBaoLiangStrategy(BaseStrategy):
    """底部爆量: 底部长期横盘后突然放巨量阳线"""

    @property
    def name(self): return "底部爆量"

    @property
    def category(self): return "量价关系类"

    @property
    def description(self): return "股价处于近60日低位的30%分位，成交量>20日均量×2.5，涨幅>2%"

    def screen(self, df, code, name, **kwargs):
        if df.empty or len(df) < 20:
            return []
        last = df.iloc[-1]

        price_pos = last.get("price_position", 50)
        if price_pos is None or pd.isna(price_pos) or price_pos > 30:
            return []

        vol_ratio = last.get("vol_ratio", 0)
        if vol_ratio is None or pd.isna(vol_ratio) or vol_ratio < 2.5:
            return []

        # Check 20-day high volume
        recent_vol = df.tail(20)["volume"].values
        if len(recent_vol) < 20 or last["volume"] < recent_vol.max():
            return []

        change_pct = (last["close"] - last["open"]) / last["open"] * 100
        if change_pct < 2:
            return []

        return [ScreeningResult(
            stock_code=code, stock_name=name,
            strategy_name=self.name, price=float(last["close"]),
            change_pct=float((last["close"] - df.iloc[-2]["close"]) / df.iloc[-2]["close"] * 100),
            volume_ratio=float(vol_ratio),
            reason=f"底部爆量：量比{vol_ratio:.1f}倍，涨幅{change_pct:.1f}%，价格位于底部{price_pos:.0f}%分位，成交量创20日新高",
            indicators={
                "vol_ratio": float(vol_ratio),
                "price_position": float(price_pos),
                "change_pct": float(change_pct),
                "volume_20d_high": float(last["volume"]),
            }
        )]


class LiangZhiXiStrategy(BaseStrategy):
    """量窒息(地量): 成交量萎缩到极致"""

    @property
    def name(self): return "量窒息"

    @property
    def category(self): return "量价关系类"

    @property
    def description(self): return "成交量<20日均量×0.4，创近20日新低，价格处低位"

    def screen(self, df, code, name, **kwargs):
        if df.empty or len(df) < 20:
            return []
        last = df.iloc[-1]

        vol_ratio = last.get("vol_ratio", 0)
        if vol_ratio is None or pd.isna(vol_ratio) or vol_ratio > 0.4:
            return []

        recent_vol = df.tail(20)["volume"].values
        if len(recent_vol) < 20:
            return []
        if not (last["volume"] == recent_vol.min() and last["volume"] > 0):
            return []

        price_range = last.get("price_range", 0)
        if price_range is None or pd.isna(price_range) or price_range > 4:
            return []

        return [ScreeningResult(
            stock_code=code, stock_name=name,
            strategy_name=self.name, price=float(last["close"]),
            change_pct=float((last["close"] - df.iloc[-2]["close"]) / df.iloc[-2]["close"] * 100),
            volume_ratio=float(vol_ratio),
            reason=f"量窒息：量比{vol_ratio:.2f}（地量），近20日最低量，振幅{price_range:.1f}%",
            indicators={
                "vol_ratio": float(vol_ratio),
                "price_range": float(price_range),
                "volume_20d_min": float(last["volume"]),
            }
        )]


class FangLiangTuPoStrategy(BaseStrategy):
    """放量突破: 突破关键均线或前高"""

    @property
    def name(self): return "放量突破"

    @property
    def category(self): return "量价关系类"

    @property
    def description(self): return "股价突破MA20/MA60或前高，成交量>1.5倍均量，涨幅>3%"

    def screen(self, df, code, name, **kwargs):
        if df.empty or len(df) < 20:
            return []
        last = df.iloc[-1]

        change_pct = (last["close"] - df.iloc[-2]["close"]) / df.iloc[-2]["close"] * 100
        if change_pct < 3:
            return []

        vol_ratio = last.get("vol_ratio", 0)
        if vol_ratio is None or pd.isna(vol_ratio) or vol_ratio < 1.5:
            return []

        # Check if breaking MA20 or MA60
        breaking_ma = False
        target = ""
        prev = df.iloc[-2]

        ma20 = last.get("ma20", 0)
        ma60 = last.get("ma60", 0)

        if ma20 and ma20 > 0 and prev["close"] <= ma20 < last["close"]:
            breaking_ma = True
            target = f"MA20({ma20:.2f})"
        elif ma60 and ma60 > 0 and prev["close"] <= ma60 < last["close"]:
            breaking_ma = True
            target = f"MA60({ma60:.2f})"

        if not breaking_ma:
            # Check if breaking recent high
            prev_high = df.tail(10).iloc[:-1]["high"].max() if len(df) > 10 else 0
            if prev_high > 0 and last["close"] > prev_high:
                breaking_ma = True
                target = f"前高({prev_high:.2f})"

        if breaking_ma:
            return [ScreeningResult(
                stock_code=code, stock_name=name,
                strategy_name=self.name, price=float(last["close"]),
                change_pct=float(change_pct),
                volume_ratio=float(vol_ratio),
                reason=f"放量突破{target}，涨幅{change_pct:.1f}%，量比{vol_ratio:.1f}",
                indicators={
                    "change_pct": float(change_pct),
                    "vol_ratio": float(vol_ratio),
                    "target": target,
                    "close": float(last["close"]),
                }
            )]
        return []
