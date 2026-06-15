"""集合竞价类策略: 三一模式, 竞价爆量, 竞价弱转强"""

import pandas as pd
import numpy as np
from .base import BaseStrategy, ScreeningResult


class SanYiMoShiStrategy(BaseStrategy):
    """三一模式: 集合竞价期间成交额、换手率、涨幅排市场/板块前列"""

    @property
    def name(self): return "三一模式"

    @property
    def category(self): return "集合竞价类"

    @property
    def description(self): return "集合竞价期间成交额、换手率、涨幅三项指标排全市场前5%或板块前三"

    @property
    def run_time(self): return "call_auction"

    def screen(self, df, code, name, **kwargs):
        results = []
        ca_data = kwargs.get("call_auction_data", {})
        if not ca_data:
            return results

        price = ca_data.get("price", 0)
        change_pct = ca_data.get("change_pct", 0)
        amount = ca_data.get("amount", 0)
        volume = ca_data.get("volume", 0)

        # Rank calculation requires cross-market data in screener
        # Here we flag candidates; screener does cross-market ranking
        rankings = kwargs.get("rankings", {})
        amt_rank = rankings.get("amount_rank", 999)
        vol_rank = rankings.get("volume_rank", 999)
        chg_rank = rankings.get("change_rank", 999)
        total = rankings.get("total_stocks", 1)

        top_5pct = int(total * 0.05)
        if amt_rank <= top_5pct and vol_rank <= top_5pct and chg_rank <= top_5pct:
            results.append(ScreeningResult(
                stock_code=code, stock_name=name,
                strategy_name=self.name, price=price,
                change_pct=change_pct, volume_ratio=0,
                reason=f"竞价三一：成交额排名{amt_rank}/{total}，换手排名{vol_rank}/{total}，涨幅排名{chg_rank}/{total}",
                indicators={
                    "amount_rank": amt_rank, "volume_rank": vol_rank,
                    "change_rank": chg_rank, "total_stocks": total,
                    "ca_price": price, "ca_change_pct": change_pct,
                }
            ))
        return results


class JingJiaBaoLiangStrategy(BaseStrategy):
    """竞价爆量: 集合竞价成交量异常放大，跳空高开"""

    @property
    def name(self): return "竞价爆量"

    @property
    def category(self): return "集合竞价类"

    @property
    def description(self): return "集合竞价量比>3且跳空高开>2%，资金抢筹信号"

    @property
    def run_time(self): return "call_auction"

    def screen(self, df, code, name, **kwargs):
        ca_data = kwargs.get("call_auction_data", {})
        if not ca_data:
            return []

        price = ca_data.get("price", 0)
        change_pct = ca_data.get("change_pct", 0)
        volume = ca_data.get("volume", 0)
        ca_volume_ratio = ca_data.get("volume_ratio", 0)

        if ca_volume_ratio > 3.0 and change_pct > 2.0:
            return [ScreeningResult(
                stock_code=code, stock_name=name,
                strategy_name=self.name, price=price,
                change_pct=change_pct, volume_ratio=ca_volume_ratio,
                reason=f"竞价爆量：量比{ca_volume_ratio:.1f}，竞价涨幅{change_pct:.2f}%",
                indicators={"ca_volume_ratio": ca_volume_ratio, "ca_change_pct": change_pct}
            )]
        return []


class JingJiaRuoZhuanQiangStrategy(BaseStrategy):
    """竞价弱转强: 昨日走弱，今日竞价从水下转红"""

    @property
    def name(self): return "竞价弱转强"

    @property
    def category(self): return "集合竞价类"

    @property
    def description(self): return "昨日炸板/走弱，今日竞价从水下(-2%)拉升至红盘(+2%)以上，强弱逆转"

    @property
    def run_time(self): return "call_auction"

    def screen(self, df, code, name, **kwargs):
        ca_data = kwargs.get("call_auction_data", {})
        yesterday_close = kwargs.get("yesterday_close", 0)
        if not ca_data or df.empty or len(df) < 2:
            return []

        ca_data.get("price", 0)
        prev = df.iloc[-2]
        prev_change = (prev["close"] - prev["open"]) / prev["open"] * 100
        ca_low_pct = ca_data.get("low_change_pct", 0)
        ca_final_pct = ca_data.get("change_pct", 0)
        ca_volume_ratio = ca_data.get("volume_ratio", 0)

        # Yesterday was weak: close < open (negative) or low gain
        yesterday_weak = prev_change < 1.0 or prev["close"] < prev["open"]

        if yesterday_weak and ca_low_pct < -2 and ca_final_pct > 2 and ca_volume_ratio > 2:
            return [ScreeningResult(
                stock_code=code, stock_name=name,
                strategy_name=self.name, price=ca_data.get("price", 0),
                change_pct=ca_final_pct, volume_ratio=ca_volume_ratio,
                reason=f"竞价弱转强：从{ca_low_pct:.1f}%拉升至{ca_final_pct:.1f}%，量比{ca_volume_ratio:.1f}",
                indicators={"ca_low_pct": ca_low_pct, "ca_final_pct": ca_final_pct, "ca_vr": ca_volume_ratio}
            )]
        return []
