"""K线形态类策略: 反包, 仙人指路, 多方炮, N字战法"""

import pandas as pd
import numpy as np
from .base import BaseStrategy, ScreeningResult


class FanBaoStrategy(BaseStrategy):
    """反包战法: 前日收阴/炸板，今日阳线反包前日高点"""

    @property
    def name(self): return "反包"

    @property
    def category(self): return "K线形态类"

    @property
    def description(self): return "前日收阴/炸板，今日阳线收盘价高于前日最高价，情绪修复"

    def screen(self, df, code, name, **kwargs):
        if df.empty or len(df) < 3:
            return []
        last = df.iloc[-1]
        prev = df.iloc[-2]

        prev_negative = prev["close"] < prev["open"]
        today_up = last["close"] > last["open"]

        if not (prev_negative and today_up):
            return []

        today_covers = last["close"] > prev["high"]
        volume_up = last["volume"] > prev["volume"]
        change_pct = (last["close"] - prev["close"]) / prev["close"] * 100

        if today_covers and volume_up and change_pct > 3:
            return [ScreeningResult(
                stock_code=code, stock_name=name,
                strategy_name=self.name, price=float(last["close"]),
                change_pct=float(change_pct),
                volume_ratio=float(last.get("vol_ratio", 0)),
                reason=f"反包：今日涨幅{change_pct:.1f}%，收盘{last['close']:.2f}覆盖前日最高{prev['high']:.2f}",
                indicators={
                    "prev_close": float(prev["close"]),
                    "prev_high": float(prev["high"]),
                    "today_close": float(last["close"]),
                    "change_pct": float(change_pct),
                }
            )]
        return []



class SuoLiangFanBaoStrategy(BaseStrategy):
    """缩量反包战法: 反包形态下，今日成交量小于前一日，说明抛压减轻"""

    @property
    def name(self): return "缩量反包"

    @property
    def category(self): return "K线形态类"

    @property
    def description(self): return "反包形态中，今日反包阳线成交量低于前一日阴线量，抛压减轻"

    def screen(self, df, code, name, **kwargs):
        if df.empty or len(df) < 3:
            return []
        last = df.iloc[-1]
        prev = df.iloc[-2]

        prev_negative = prev["close"] < prev["open"]
        today_up = last["close"] > last["open"]

        if not (prev_negative and today_up):
            return []

        today_covers = last["close"] > prev["high"]
        volume_shrink = last["volume"] < prev["volume"]
        change_pct = (last["close"] - prev["close"]) / prev["close"] * 100

        if today_covers and volume_shrink and change_pct > 0:
            return [ScreeningResult(
                stock_code=code, stock_name=name,
                strategy_name=self.name, price=float(last["close"]),
                change_pct=float(change_pct),
                volume_ratio=float(last.get("vol_ratio", 0)),
                reason=f"缩量反包：涨幅{change_pct:.1f}%，收盘{last['close']:.2f}覆盖前日最高{prev['high']:.2f}，量缩{prev['volume']-last['volume']:.0f}手",
                indicators={
                    "prev_close": float(prev["close"]),
                    "prev_high": float(prev["high"]),
                    "today_close": float(last["close"]),
                    "change_pct": float(change_pct),
                    "volume_shrink": float((prev["volume"] - last["volume"]) / prev["volume"] * 100),
                }
            )]
        return []


class XianRenZhiLuStrategy(BaseStrategy):
    """仙人指路: 长上影线试盘"""

    @property
    def name(self): return "仙人指路"

    @property
    def category(self): return "K线形态类"

    @property
    def description(self): return "K线带长上影线（上影线>实体2倍），试盘信号"

    def screen(self, df, code, name, **kwargs):
        if df.empty or len(df) < 5:
            return []
        last = df.iloc[-1]

        body = abs(last["close"] - last["open"])
        upper_shadow = last["high"] - max(last["close"], last["open"])
        lower_shadow = min(last["close"], last["open"]) - last["low"]
        total_range = last["high"] - last["low"]

        if total_range == 0:
            return []

        upper_ratio = upper_shadow / body if body > 0 else 0
        upper_to_range = upper_shadow / total_range

        if upper_ratio > 2 and upper_to_range > 0.6:
            # Check at bottom or early rise phase
            price_pos = last.get("price_position", 50)
            pos_ok = 20 <= price_pos <= 60

            vol_ratio = last.get("vol_ratio", 0)
            vol_ok = vol_ratio < 2.0  # not blowout volume

            if pos_ok and vol_ok:
                return [ScreeningResult(
                    stock_code=code, stock_name=name,
                    strategy_name=self.name, price=float(last["close"]),
                    change_pct=float(((last["close"] - last["open"]) / last["open"] * 100) if last["open"] > 0 else 0),
                    volume_ratio=float(vol_ratio),
                    reason=f"仙人指路：上影线{last['high']-max(last['close'],last['open']):.2f}，实体{body:.2f}，试盘信号",
                    indicators={
                        "upper_shadow": float(upper_shadow),
                        "body": float(body),
                        "upper_ratio": float(upper_ratio),
                        "price_position": float(price_pos),
                    }
                )]
        return []


class DuoFangPaoStrategy(BaseStrategy):
    """多方炮: 两阳夹一阴"""

    @property
    def name(self): return "多方炮"

    @property
    def category(self): return "K线形态类"

    @property
    def description(self): return "两根阳线夹一根阴线，上涨中继形态"

    def screen(self, df, code, name, **kwargs):
        if df.empty or len(df) < 4:
            return []
        d1, d2, d3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]

        d1_up = d1["close"] > d1["open"]
        d2_down = d2["close"] < d2["open"]
        d3_up = d3["close"] > d3["open"]

        if not (d1_up and d2_down and d3_up):
            return []

        d1_change = (d1["close"] - d1["open"]) / d1["open"] * 100
        d2_change = (d2["close"] - d2["open"]) / d2["open"] * 100
        d3_above_d1 = d3["close"] > d1["close"]
        d3_vol_up = d3["volume"] > d2["volume"]

        if d1_change > 2 and abs(d2_change) < 3 and d3_above_d1 and d3_vol_up:
            return [ScreeningResult(
                stock_code=code, stock_name=name,
                strategy_name=self.name, price=float(d3["close"]),
                change_pct=float((d3["close"] - d2["close"]) / d2["close"] * 100),
                volume_ratio=float(d3.get("vol_ratio", 0)),
                reason="多方炮：两阳夹一阴，洗盘后继续上攻",
                indicators={
                    "d1_change": float(d1_change),
                    "d2_change": float(d2_change),
                    "d3_close": float(d3["close"]),
                    "d1_close": float(d1["close"]),
                }
            )]
        return []


class NZiStrategy(BaseStrategy):
    """N字战法: 涨→回调→再突破前高"""

    @property
    def name(self): return "N字战法"

    @property
    def category(self): return "K线形态类"

    @property
    def description(self): return "先涨>10%，回调<涨幅60%，再次放量突破前高"

    def screen(self, df, code, name, **kwargs):
        if df.empty or len(df) < 20:
            return []
        # Look back 10 days for first leg up
        recent = df.tail(15)
        if len(recent) < 10:
            return []

        h10 = recent["high"].max()
        l10 = recent["low"].min()
        first_leg_up = (h10 - l10) / l10 * 100

        if first_leg_up < 10:
            return []

        last = recent.iloc[-1]
        prev_high = recent.iloc[:-1]["high"].max()

        if last["close"] > prev_high * 1.01:  # break above prev high
            vol_ratio = last.get("vol_ratio", 0)
            if vol_ratio > 1.5:
                return [ScreeningResult(
                    stock_code=code, stock_name=name,
                    strategy_name=self.name, price=float(last["close"]),
                    change_pct=float((last["close"] - prev_high) / prev_high * 100),
                    volume_ratio=float(vol_ratio),
                    reason=f"N字突破：近10日涨幅{first_leg_up:.1f}%，今日突破前高{prev_high:.2f}",
                    indicators={
                        "first_leg_up": float(first_leg_up),
                        "prev_high": float(prev_high),
                        "vol_ratio": float(vol_ratio),
                    }
                )]
        return []
