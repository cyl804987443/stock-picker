from pydantic import BaseModel
from typing import Optional


class ScreeningResultOut(BaseModel):
    id: int
    date: str
    stock_code: str
    stock_name: str
    strategy_name: str
    price: float
    change_pct: float
    volume_ratio: float
    reason: str
    sector: str
    concepts: str = ""
    market_cap: float

    class Config:
        from_attributes = True


class DailySummaryOut(BaseModel):
    date: str
    total_stocks: int
    strategies_count: dict
    status: str
    total_hits: int = 0
    screened_stocks: int = 0


class ScreeningJobOut(BaseModel):
    id: str
    run_type: str
    status: str
    stage: str
    progress: int
    total_stocks: int
    processed_stocks: int
    success_count: int
    failed_count: int
    screened_stocks: int
    selected_stocks: int
    total_hits: int
    error_message: str

    class Config:
        from_attributes = True


class StrategyInfo(BaseModel):
    name: str
    category: str
    description: str
    run_time: str
