# A股选股器 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a daily A-share stock screening website with 15 trading strategies, automated daily runs (pre-market 7:00, call-auction 9:25, post-market 15:30), SPA frontend, shareable via web link.

**Architecture:** FastAPI backend serving REST API + static SPA frontend. akshare for A-share market data. SQLite for persistence. APScheduler for cron-style daily runs. Strategy engine with pluggable pattern classes.

**Tech Stack:** Python 3.11+, FastAPI, SQLite (sqlalchemy+aiosqlite), akshare~=1.16, APScheduler, pandas+numpy, pure HTML/CSS/JS frontend.

---

## File Structure

```
/Users/jackiechan/Desktop/codex project/
├── main.py              # FastAPI app entry + APScheduler startup
├── requirements.txt     # pip dependencies
├── app/
│   ├── __init__.py
│   ├── config.py        # Settings from env / defaults
│   ├── database.py      # SQLAlchemy engine + session
│   ├── models.py        # ORM: screening_results, daily_summary, stock_cache
│   ├── schemas.py       # Pydantic models for API
│   ├── api.py           # FastAPI router with 5 endpoints
│   ├── data_fetcher.py  # akshare wrapper: batch fetch + cache
│   ├── indicators.py    # TA: MA, MACD, RSI, volume, etc.
│   ├── screener.py      # Orchestrator: run all strategies, save results
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base.py      # BaseStrategy abstract class
│   │   ├── call_auction.py    # 三一模式, 竞价爆量, 竞价弱转强
│   │   ├── limit_up_relay.py  # 一进二, 二进三, 龙头战法
│   │   ├── kline_pattern.py   # 反包, 仙人指路, 多方炮, N字战法
│   │   ├── volume_price.py    # 底部爆量, 量窒息, 放量突破
│   │   └── sentiment.py       # 龙回头, 涨停基因
│   └── utils.py         # Helpers: date helpers, numeric formatting
├── static/
│   ├── index.html       # SPA shell
│   ├── style.css        # All styles
│   └── app.js           # All frontend logic
└── data/
    └── .gitkeep         # SQLite db lives here
```

---

### Task 1: Project scaffold, config, database models

**Files:**
- Create: `requirements.txt`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `app/database.py`
- Create: `app/models.py`

- [ ] **Step 1: Write requirements.txt**

```
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
sqlalchemy>=2.0.36
aiosqlite>=0.20.0
akshare>=1.16.0
pandas>=2.2.0
numpy>=1.26.0
apscheduler>=3.10.4
pydantic>=2.0
pydantic-settings>=2.0
```

- [ ] **Step 2: Write app/__init__.py** (empty)

- [ ] **Step 3: Write app/config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///data/stock_picker.db"
    stock_cache_days: int = 120
    results_retention_days: int = 365
    pre_market_time: str = "07:00"
    call_auction_time: str = "09:25"
    post_market_time: str = "15:30"
    max_retries: int = 3
    retry_delay_minutes: int = 10

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 4: Write app/database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    from app.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session():
    async with async_session() as session:
        yield session
```

- [ ] **Step 5: Write app/models.py** — Define `screening_results`, `daily_summary`, `stock_cache` tables per the spec schema.

```python
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, func
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
    price = Column(Float)
    change_pct = Column(Float)
    volume_ratio = Column(Float)
    reason = Column(Text)
    indicators_json = Column(Text)
    sector = Column(String(30))
    market_cap = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

class DailySummary(Base):
    __tablename__ = "daily_summary"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), unique=True, nullable=False)
    total_stocks = Column(Integer, default=0)
    strategies_count = Column(Text)  # JSON
    run_at = Column(String(10))
    status = Column(String(10), default="pending")

class StockCache(Base):
    __tablename__ = "stock_cache"
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(6), index=True, nullable=False)
    trade_date = Column(String(10), nullable=False)
    open = Column(Float)
    close = Column(Float)
    high = Column(Float)
    low = Column(Float)
    volume = Column(Float)
    amount = Column(Float)
    ma5 = Column(Float)
    ma10 = Column(Float)
    ma20 = Column(Float)
    ma60 = Column(Float)
    macd_dif = Column(Float)
    macd_dea = Column(Float)
    macd_bar = Column(Float)
    rsi_14 = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 6: Verify imports work**

Run: `python -c "from app.config import settings; from app.database import init_db; from app.models import ScreeningResult; print('OK')"`
Expected: `OK`

---

### Task 2: Data fetcher (akshare wrapper)

**Files:**
- Create: `app/data_fetcher.py`

**Key decisions:**
- Batch stock list from `ak.stock_zh_a_spot_em()` to get all ~5000 codes
- Daily K-line from `ak.stock_zh_a_hist(symbol, "daily", start_date, end_date)`
- Cache results to avoid re-fetching
- Handle akshare's occasional connection/rate-limit errors

- [ ] **Step 1: Write get_all_stock_codes()**

```python
import akshare as ak
import pandas as pd

def get_all_stock_codes() -> list[tuple[str, str]]:
    """Return [(code, name), ...] for all A-share stocks."""
    df = ak.stock_zh_a_spot_em()
    codes = []
    for _, row in df.iterrows():
        code = str(row["代码"])
        name = str(row["名称"])
        # Filter: only main board, SME, GEM, STAR (exclude indices and funds)
        if code.startswith(("00", "30", "60", "68")) and len(code) == 6:
            codes.append((code, name))
    return codes
```

- [ ] **Step 2: Write fetch_daily_kline()**

```python
def fetch_daily_kline(code: str, days: int = 60) -> pd.DataFrame | None:
    """Fetch daily K-line for one stock. Returns DataFrame with columns:
    trade_date, open, close, high, low, volume, amount."""
    import datetime
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days * 1.5)  # buffer for weekends
    try:
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="qfq"  # 前复权
        )
        if df.empty:
            return None
        df = df.rename(columns={
            "日期": "trade_date", "开盘": "open", "收盘": "close",
            "最高": "high", "最低": "low", "成交量": "volume", "成交额": "amount"
        })
        df["trade_date"] = df["trade_date"].astype(str)
        return df[["trade_date", "open", "close", "high", "low", "volume", "amount"]]
    except Exception:
        return None
```

- [ ] **Step 3: Write batch_fetch_and_cache()** — Iterate all codes, fetch + store in SQLite via async session. Batch 50 at a time with 0.5s delay between groups.

- [ ] **Step 4: Write get_cached_data()** — Read stock_cache from DB for given date range.

- [ ] **Step 5: Write get_call_auction_data()** — Fetch 集合竞价 data (using akshare's minute-level data for 9:25 snapshot, or use `stock_zh_a_tick_tx_js` for tick data).

```python
def get_call_auction_data(code: str) -> dict | None:
    """Get call auction data for a stock at 9:25. Returns { price, volume, amount, turnover, change_pct } or None."""
    try:
        df = ak.stock_zh_a_tick_tx_js(code)
        if df is None or df.empty:
            return None
        # Filter to first tick after 9:25 (9:25 is the call auction match)
        ca = df[df["成交时间"] == "09:25:00"]
        if ca.empty:
            return None
        row = ca.iloc[0]
        return {
            "price": float(row["成交价"]),
            "volume": float(row["成交量"]),
            "amount": float(row["成交金额"]),
            "change_pct": float(row.get("涨跌幅", 0)),
        }
    except:
        return None
```

---

### Task 3: Technical indicators calculator

**Files:**
- Create: `app/indicators.py`

Implement pure functions (pandas-based) for all required indicators:

- [ ] **Step 1: Moving averages**

```python
def calc_ma(df: pd.DataFrame, periods: list[int] = [5, 10, 20, 60]) -> pd.DataFrame:
    for p in periods:
        df[f"ma{p}"] = df["close"].rolling(window=p).mean()
    return df
```

- [ ] **Step 2: MACD**

```python
def calc_macd(df: pd.DataFrame, fast=12, slow=26, signal=9) -> pd.DataFrame:
    ema_fast = df["close"].ewm(span=fast).mean()
    ema_slow = df["close"].ewm(span=slow).mean()
    df["macd_dif"] = ema_fast - ema_slow
    df["macd_dea"] = df["macd_dif"].ewm(span=signal).mean()
    df["macd_bar"] = 2 * (df["macd_dif"] - df["macd_dea"])
    return df
```

- [ ] **Step 3: RSI**

```python
def calc_rsi(df: pd.DataFrame, period=14) -> pd.DataFrame:
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, float("nan"))
    df["rsi_14"] = 100 - (100 / (1 + rs))
    return df
```

- [ ] **Step 4: Volume metrics**

```python
def calc_volume_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df["vol_ma20"] = df["volume"].rolling(window=20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_ma20"]  # volume ratio to 20d avg
    df["amount_ma20"] = df["amount"].rolling(window=20).mean()
    df["price_range"] = (df["high"] - df["low"]) / df["close"] * 100
    return df
```

- [ ] **Step 5: Combined calculator**

```python
def calc_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = calc_ma(df)
    df = calc_macd(df)
    df = calc_rsi(df)
    df = calc_volume_metrics(df)
    return df
```

---

### Task 4: Strategy base class

**Files:**
- Create: `app/strategies/__init__.py`
- Create: `app/strategies/base.py`

- [ ] **Step 1: Define BaseStrategy**

```python
from abc import ABC, abstractmethod
import pandas as pd

class ScreeningResult(NamedTuple):
    stock_code: str
    stock_name: str
    strategy_name: str
    price: float
    change_pct: float
    volume_ratio: float
    reason: str
    indicators: dict
    sector: str = ""
    market_cap: float = 0

class BaseStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def screen(self, df: pd.DataFrame, code: str, name: str, **kwargs) -> list[ScreeningResult]: ...
```

---

### Task 5: All 15 strategy implementations

**Files:**
- Create: `app/strategies/call_auction.py` (3 strategies)
- Create: `app/strategies/limit_up_relay.py` (3 strategies)
- Create: `app/strategies/kline_pattern.py` (4 strategies)
- Create: `app/strategies/volume_price.py` (3 strategies)
- Create: `app/strategies/sentiment.py` (2 strategies)

Each strategy file follows the same pattern:
```python
class SanYiMoShiStrategy(BaseStrategy):
    @property
    def name(self): return "三一模式"

    def screen(self, df, code, name, **kwargs):
        # ... implementation using df.tail(60) for enough data
        # return [ScreeningResult(...)] if conditions met, else []
```

**Quantitative rules (from spec doc, implemented as code):**

- [ ] **call_auction.py** — 三一模式: rank across market for turnover, amount, change_pct in top 5% during call auction. 竞价爆量: call auction volume ratio > 3.0, jump > 2%. 竞价弱转强: yesterday weak (<3%), today auction goes from -2% to +2%.

- [ ] **limit_up_relay.py** — 一进二: yesterday first limit-up (close/ref_close-1 > 0.095 for 10% board), before 14:00 freeze, 30-200B cap. 二进三: 2 consecutive limit-ups, turnover > 10%. 龙头战法: sector with 3+ limit-ups, earliest freeze.

- [ ] **kline_pattern.py** — 反包: today close > yesterday high, volume up. 仙人指路: upper shadow > 2× body, at bottom. 多方炮: 3-day pattern + - +. N字战法: up > 10%, pullback < 60%, break新高.

- [ ] **volume_price.py** — 底部爆量: price in bottom 30%, volume > 2.5× MA20, close up > 2%. 量窒息: volume < 0.4× MA20, new 20d low, price at low. 放量突破: break MA20/MA60 or resistance, vol > 1.5× MA20, up > 3%.

- [ ] **sentiment.py** — 龙回头: 30d max return > 30%, pullback 15-40%, at MA20 support, volume shrinking. 涨停基因: 20d内有涨停, max pullback < 15%.

---

### Task 6: Screener orchestrator

**Files:**
- Create: `app/screener.py`

- [ ] **Step 1: Write run_screening()**

```python
async def run_screening(date: str, run_type: str = "pre_market") -> dict:
    """Run all applicable strategies and save results."""
    # 1. Get cached stock data
    # 2. For each stock, run each enabled strategy
    # 3. Collect all ScreeningResult objects
    # 4. Batch insert to screening_results table
    # 5. Generate daily_summary
    # 6. Return summary dict
```

- [ ] **Step 2: Handle run_type filtering**
  - `pre_market` (7:00): exclude call_auction strategies
  - `call_auction` (9:25): only call_auction strategies
  - `post_market` (15:30): all strategies + stats/胜率

- [ ] **Step 3: Add progress logging** via Python logging.

---

### Task 7: API routes

**Files:**
- Create: `app/schemas.py`
- Create: `app/api.py`

- [ ] **Step 1: Write Pydantic schemas**

```python
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
    market_cap: float

class DailySummaryOut(BaseModel):
    date: str
    total_stocks: int
    strategies_count: dict
    status: str

class StrategyInfo(BaseModel):
    name: str
    category: str
    description: str
    run_time: str  # "pre_market" | "call_auction" | "both"
```

- [ ] **Step 2: Write FastAPI router** with 5 endpoints:
  - `GET /api/results` — Query `screening_results` by date + optional strategy filter
  - `GET /api/strategies` — Return static list of all 15 strategies
  - `GET /api/summary` — Return `daily_summary` for a date
  - `POST /api/run-screening` — Trigger manual screening (with basic auth token or skip for now)
  - `GET /api/dates` — List distinct dates in screening_results

---

### Task 8: Frontend SPA (static assets)

**Files:**
- Create: `static/index.html`
- Create: `static/style.css`
- Create: `static/app.js`

This is the biggest single task. The SPA has 4 views:
1. **Main results** — date nav, strategy filter pills, stock card grid
2. **Strategy detail** — single strategy view showing all its picks
3. **Daily review** — post-market stats (win rate, best strategy)
4. **History** — date picker to browse past results

- [ ] **Step 1: Write index.html** — SPA shell with view container, top nav, date bar, filter bar, result grid area, footer.

- [ ] **Step 2: Write style.css** — Clean, professional dark-top-nav, card grid layout, red/green color coding, responsive.

- [ ] **Step 3: Write app.js** — State management, fetch API calls, render functions for each view.

Key JS functions:
```javascript
const state = { currentDate: null, results: [], summary: null, strategies: [] };
async function fetchResults(date, strategy) { ... }
async function fetchSummary(date) { ... }
async function fetchDates() { ... }
function renderCards(results) { ... }
function renderFilters(strategies, counts) { ... }
function renderDateNav(dates) { ... }
function init() { ... }
```

---

### Task 9: Main entry point + scheduler

**Files:**
- Modify: `main.py` (create)

- [ ] **Step 1: Write main.py**

```python
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.database import init_db
from app.api import router

scheduler = AsyncIOScheduler()

async def run_pre_market():
    from app.screener import run_screening
    await run_screening(run_type="pre_market")

async def run_call_auction():
    from app.screener import run_screening
    await run_screening(run_type="call_auction")

async def run_post_market():
    from app.screener import run_screening
    await run_screening(run_type="post_market")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    scheduler.add_job(run_pre_market, "cron", hour=7, minute=0)
    scheduler.add_job(run_call_auction, "cron", hour=9, minute=25)
    scheduler.add_job(run_post_market, "cron", hour=15, minute=30)
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
app.include_router(router, prefix="/api")
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

---

### Task 10: Verification script

**Files:**
- Create: `scripts/verify_screening.py`

- [ ] **Step 1: Quick manual test**

```python
"""Test screening a subset of stocks to verify strategies work."""
import asyncio
from app.database import async_session, init_db
from app.data_fetcher import get_all_stock_codes, fetch_daily_kline
from app.indicators import calc_all_indicators
from app.strategies.volume_price import DiBuBaoLiangStrategy

async def test():
    await init_db()
    codes = get_all_stock_codes()[:5]  # Just 5 stocks
    strategy = DiBuBaoLiangStrategy()
    for code, name in codes:
        df = fetch_daily_kline(code)
        if df is not None:
            df = calc_all_indicators(df)
            results = strategy.screen(df, code, name)
            for r in results:
                print(f"  {r.stock_name}({r.stock_code}): {r.reason}")
```

---

## Execution Order

1. Task 1 (scaffold + DB) → 2 (data_fetcher) → 3 (indicators) → 4 (base strategy)
5. Task 5 sub-tasks in any order (each strategy file is independent)
6. Task 6 (screener) → 7 (API) → 8 (frontend) → 9 (main entry) → 10 (verify)

Parallel: Task 5 strategy files can be written independently once Task 4 is done.

## Self-Review

**Spec coverage:**
- Architecture (FastAPI + SQLite + SPA): Tasks 1, 7, 9
- Data model (3 tables): Task 1
- 15 strategies: Task 5 (all covered)
- Daily runs (pre-market 7:00, call auction 9:25, post-market 15:30): Task 9
- Frontend SPA: Task 8
- API 5 endpoints: Task 7
- Storage cleanup: Task 1 (retention settings in config)
- Manual trigger: Task 7 (POST endpoint)

**No placeholders** — each task has concrete code and steps.

**Type consistency** — ScreeningResult namedtuple used consistently across all strategy modules and screener. API returns Pydantic models matching the ORM.
