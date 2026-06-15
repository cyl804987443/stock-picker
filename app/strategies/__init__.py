from .call_auction import SanYiMoShiStrategy, JingJiaBaoLiangStrategy, JingJiaRuoZhuanQiangStrategy
from .limit_up_relay import YiJinErStrategy, ErJinSanStrategy, LongTouStrategy
from .kline_pattern import FanBaoStrategy, SuoLiangFanBaoStrategy, XianRenZhiLuStrategy, DuoFangPaoStrategy, NZiStrategy
from .volume_price import DiBuBaoLiangStrategy, LiangZhiXiStrategy, FangLiangTuPoStrategy
from .sentiment import LongHuiTouStrategy

ALL_STRATEGIES = [
    SanYiMoShiStrategy(),
    JingJiaBaoLiangStrategy(),
    JingJiaRuoZhuanQiangStrategy(),
    YiJinErStrategy(),
    ErJinSanStrategy(),
    LongTouStrategy(),
    FanBaoStrategy(),
    SuoLiangFanBaoStrategy(),
    XianRenZhiLuStrategy(),
    DuoFangPaoStrategy(),
    NZiStrategy(),
    DiBuBaoLiangStrategy(),
    LiangZhiXiStrategy(),
    FangLiangTuPoStrategy(),
    LongHuiTouStrategy(),
]

STRATEGY_CATEGORIES = {
    "集合竞价类": ["三一模式", "竞价爆量", "竞价弱转强"],
    "连板接力类": ["一进二", "二进三", "龙头战法"],
    "K线形态类": ["反包", "缩量反包", "仙人指路", "多方炮", "N字战法"],
    "量价关系类": ["底部爆量", "量窒息", "放量突破"],
    "情绪趋势类": ["龙回头"],
}

def get_strategy_by_name(name: str):
    for s in ALL_STRATEGIES:
        if s.name == name:
            return s
    return None

def get_strategies_for_run(run_type: str = "pre_market"):
    """Return strategies applicable for given run time."""
    if run_type == "call_auction":
        return [s for s in ALL_STRATEGIES if s.run_time == "call_auction"]
    elif run_type == "post_market":
        return ALL_STRATEGIES  # all strategies for review
    else:  # pre_market
        return [s for s in ALL_STRATEGIES if s.run_time != "call_auction"]
