from sqlalchemy import Boolean, Column, Integer, String, Float, Text, DateTime, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class ScreeningResult(Base):
    __tablename__ = "screening_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), index=True, nullable=False)
    stock_code = Column(String(6), nullable=False)
    stock_name = Column(String(20), nullable=False)
    strategy_name = Column(String(30), nullable=False)
    price = Column(Float, default=0)
    change_pct = Column(Float, default=0)
    volume_ratio = Column(Float, default=0)
    reason = Column(Text, default="")
    indicators_json = Column(Text, default="{}")
    sector = Column(String(30), default="")
    concepts = Column(Text, default="")
    market_cap = Column(Float, default=0)
    created_at = Column(DateTime, server_default=func.now())

class DailySummary(Base):
    __tablename__ = "daily_summary"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), unique=True, nullable=False)
    total_stocks = Column(Integer, default=0)
    strategies_count = Column(Text, default="{}")
    run_at = Column(String(10), default="")
    status = Column(String(10), default="pending")
    total_hits = Column(Integer, default=0)
    screened_stocks = Column(Integer, default=0)

class StockCache(Base):
    __tablename__ = "stock_cache"
    __table_args__ = (
        UniqueConstraint("stock_code", "trade_date", name="uq_stock_cache_code_date"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(6), index=True, nullable=False)
    trade_date = Column(String(10), nullable=False)
    open = Column(Float, default=0)
    close = Column(Float, default=0)
    high = Column(Float, default=0)
    low = Column(Float, default=0)
    volume = Column(Float, default=0)
    amount = Column(Float, default=0)
    ma5 = Column(Float, default=0)
    ma10 = Column(Float, default=0)
    ma20 = Column(Float, default=0)
    ma60 = Column(Float, default=0)
    macd_dif = Column(Float, default=0)
    macd_dea = Column(Float, default=0)
    macd_bar = Column(Float, default=0)
    rsi_14 = Column(Float, default=0)
    created_at = Column(DateTime, server_default=func.now())


class StockUniverse(Base):
    __tablename__ = "stock_universe"
    stock_code = Column(String(6), primary_key=True)
    stock_name = Column(String(30), nullable=False)
    market = Column(String(2), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    latest_price = Column(Float, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ScreeningJob(Base):
    __tablename__ = "screening_jobs"
    id = Column(String(36), primary_key=True)
    run_type = Column(String(20), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    stage = Column(String(30), default="queued", nullable=False)
    progress = Column(Integer, default=0)
    total_stocks = Column(Integer, default=0)
    processed_stocks = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    screened_stocks = Column(Integer, default=0)
    selected_stocks = Column(Integer, default=0)
    total_hits = Column(Integer, default=0)
    error_message = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime)
    finished_at = Column(DateTime)


class AppMetadata(Base):
    __tablename__ = "app_metadata"
    key = Column(String(60), primary_key=True)
    value = Column(Text, default="")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
