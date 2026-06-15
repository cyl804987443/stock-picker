"""Screening orchestrator: run all strategies and save results."""

import asyncio
import json
import datetime
import pandas as pd
from typing import Any
from sqlalchemy import select, func
from app.database import async_session
from app.models import ScreeningResult as ResultModel, DailySummary, StockCache, StockUniverse
from app.data_fetcher import build_sector_concept_maps, get_cached_data, get_stock_universe, refresh_stock_universe, sync_market_data
from app.indicators import calc_all_indicators
from app.strategies import get_strategies_for_run
from app.strategies.base import ScreeningResult
from app.utils import get_today_str, to_json

RUN_TYPES = {
    "pre_market": "盘前预选",
    "call_auction": "竞价选股",
    "post_market": "收盘复盘",
}


async def fetch_and_prepare_data() -> dict[str, pd.DataFrame]:
    """Fetch cached stock data and calculate indicators for all stocks."""
    print("[screener] Loading cached data...")
    today = get_today_str()

    data = await get_cached_data(end_date=today)
    if not data:
        return {}

    print(f"[screener] Calculating indicators for {len(data)} stocks...")

    result: dict[str, pd.DataFrame] = {}
    for code, df in data.items():
        if df.empty:
            continue
        # Add prev_close column
        close_shifted = df["close"].shift(1)
        df["prev_close"] = close_shifted
        df = calc_all_indicators(df)
        if not df.empty:
            result[code] = df

    return result


def summarize_results(results: list[ScreeningResult]) -> dict[str, Any]:
    strategy_counts: dict[str, int] = {}
    for result in results:
        strategy_counts[result.strategy_name] = (
            strategy_counts.get(result.strategy_name, 0) + 1
        )
    return {
        "total_stocks": len({result.stock_code for result in results}),
        "total_hits": len(results),
        "strategy_counts": strategy_counts,
    }


async def run_screening(
    run_type: str = "pre_market",
    sync_data: bool = False,
) -> dict[str, Any]:
    """Run screening for given run type. Returns summary."""
    today = get_today_str()
    print(f"\n{'='*50}")
    print(f"[screener] Running {RUN_TYPES.get(run_type, run_type)} ({today})")
    print(f"{'='*50}")

    data = await fetch_and_prepare_data()
    if not data:
        return {"status": "error", "message": "No data available"}

    strategies = get_strategies_for_run(run_type)
    print(f"[screener] Loaded {len(strategies)} strategies")

    # Build code->name mapping from stock list
    all_codes = await get_stock_universe()
    code_name_map = {item["code"]: item["name"] for item in all_codes}

    # Build comprehensive sector/concept maps from real-time market data
    sector_map, concept_map = await asyncio.to_thread(build_sector_concept_maps)
    print(f"[screener] Built sector map with {len(sector_map)} stocks, concept map with {len(concept_map)} stocks")

    all_results: list[ScreeningResult] = []
    total = len(data)

    for idx, (code, df) in enumerate(data.items()):
        if df.empty or len(df) < 5:
            continue

        name = code_name_map.get(code, code)
        sector = sector_map.get(code, "")
        concepts = concept_map.get(code, "")

        for strategy in strategies:
            try:
                kwargs = {}
                results = strategy.screen(df, code, name, **kwargs)
                # Apply sector/concepts to each result
                for result in results:
                    result.sector = sector
                    result.concepts = concepts
                all_results.extend(results)
            except Exception as e:
                print(f"  [screener] Error {strategy.name}/{code}: {e}")
                continue

        if (idx + 1) % 200 == 0:
            print(f"  [screener] Processed {idx + 1}/{total}")

    print(f"[screener] Total results: {len(all_results)}")

    result_summary = summarize_results(all_results)
    await save_results(all_results, today, run_type, screened_stocks=total)

    summary = {
        "status": "success",
        "date": today,
        "run_type": run_type,
        "screened_stocks": total,
        **result_summary,
    }
    print(f"[screener] Summary: {json.dumps(summary, ensure_ascii=False)}")
    return summary


async def save_results(
    results: list[ScreeningResult],
    date: str,
    run_type: str,
    screened_stocks: int,
):
    """Save screening results to database."""
    summary = summarize_results(results)
    async with async_session() as session:
        async with session.begin():
            # Remove old results for same date + run type
            await session.execute(
                ResultModel.__table__.delete().where(
                    ResultModel.date == date
                )
            )

            for r in results:
                record = ResultModel(
                    date=date,
                    stock_code=r.stock_code,
                    stock_name=r.stock_name,
                    strategy_name=r.strategy_name,
                    price=r.price,
                    change_pct=r.change_pct,
                    volume_ratio=r.volume_ratio,
                    reason=r.reason,
                    indicators_json=to_json(r.indicators),
                    sector=r.sector,
                    concepts=r.concepts,
                    market_cap=r.market_cap,
                )
                session.add(record)
            existing = await session.scalar(
                select(DailySummary).where(DailySummary.date == date)
            )
            if existing:
                existing.total_stocks = summary["total_stocks"]
                existing.total_hits = summary["total_hits"]
                existing.screened_stocks = screened_stocks
                existing.strategies_count = to_json(summary["strategy_counts"])
                existing.run_at = run_type
                existing.status = "success"
            else:
                session.add(DailySummary(
                    date=date,
                    total_stocks=summary["total_stocks"],
                    total_hits=summary["total_hits"],
                    screened_stocks=screened_stocks,
                    strategies_count=to_json(summary["strategy_counts"]),
                    run_at=run_type,
                    status="success",
                ))

    print(
        f"[screener] Saved {summary['total_hits']} hits / "
        f"{summary['total_stocks']} stocks for {date}"
    )
