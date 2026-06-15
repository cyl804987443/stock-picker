"""FastAPI router for stock picker API."""

import json
import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, Response, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_session
from app.models import (
    ScreeningResult as ResultModel,
    DailySummary,
    ScreeningJob,
    StockCache,
    StockUniverse,
)
from app.schemas import (
    ScreeningResultOut,
    DailySummaryOut,
    ScreeningJobOut,
    StrategyInfo,
)
from app.strategies import ALL_STRATEGIES, STRATEGY_CATEGORIES
from app.data_fetcher import build_sector_concept_maps
from app.jobs import start_screening_job

router = APIRouter()


@router.get("/results")
async def get_results(
    date: Optional[str] = Query(None),
    strategy: Optional[str] = Query(None),
    limit: int = Query(500, le=10000),
    session: AsyncSession = Depends(get_session),
):
    """Get screening results for a date, optionally filtered by strategy."""
    if date is None:
        date = datetime.date.today().strftime("%Y-%m-%d")

    query = select(ResultModel).where(ResultModel.date == date)
    if strategy:
        query = query.where(ResultModel.strategy_name == strategy)
    query = query.order_by(ResultModel.change_pct.desc()).limit(limit)

    result = await session.execute(query)
    rows = result.scalars().all()

    return [
        ScreeningResultOut(
            id=r.id, date=r.date, stock_code=r.stock_code,
            stock_name=r.stock_name, strategy_name=r.strategy_name,
            price=r.price or 0, change_pct=r.change_pct or 0,
            volume_ratio=r.volume_ratio or 0, reason=r.reason or "",
            sector=r.sector or "", concepts=r.concepts or "",
            market_cap=r.market_cap or 0,
        )
        for r in rows
    ]


@router.get("/strategies")
async def get_strategies():
    """Get all available strategies."""
    return [
        StrategyInfo(
            name=s.name,
            category=s.category,
            description=s.description,
            run_time=s.run_time,
        )
        for s in ALL_STRATEGIES
    ]


@router.get("/summary")
async def get_summary(
    date: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """Get daily summary for a date."""
    if date is None:
        date = datetime.date.today().strftime("%Y-%m-%d")

    result = await session.execute(
        select(DailySummary).where(DailySummary.date == date)
    )
    summary = result.scalar_one_or_none()
    if summary is None:
        return DailySummaryOut(
            date=date, total_stocks=0,
            strategies_count={}, status="no_data",
            total_hits=0, screened_stocks=0,
        )

    sc = {}
    try:
        sc = json.loads(summary.strategies_count) if summary.strategies_count else {}
    except (json.JSONDecodeError, TypeError):
        sc = {}

    return DailySummaryOut(
        date=summary.date,
        total_stocks=summary.total_stocks,
        strategies_count=sc,
        status=summary.status,
        total_hits=summary.total_hits or 0,
        screened_stocks=summary.screened_stocks or 0,
    )


@router.post("/run-screening")
async def trigger_screening(
    response: Response,
    run_type: str = Query("pre_market", description="pre_market, call_auction, or post_market"),
):
    """Create a persistent background synchronization and screening job."""
    if run_type not in {"pre_market", "call_auction", "post_market"}:
        raise HTTPException(status_code=400, detail="Invalid run_type")
    job = await start_screening_job(run_type)
    response.status_code = status.HTTP_202_ACCEPTED
    return {"job_id": job.id, "status": job.status}


@router.get("/jobs/{job_id}", response_model=ScreeningJobOut)
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)):
    job = await session.get(ScreeningJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/data-status")
async def get_data_status(session: AsyncSession = Depends(get_session)):
    universe_count = await session.scalar(
        select(func.count(StockUniverse.stock_code))
        .where(StockUniverse.is_active.is_(True))
    )
    cached_count = await session.scalar(
        select(func.count(func.distinct(StockCache.stock_code)))
    )
    latest_trade_date = await session.scalar(select(func.max(StockCache.trade_date)))
    latest_job = await session.scalar(
        select(ScreeningJob)
        .where(ScreeningJob.status == "completed")
        .order_by(ScreeningJob.finished_at.desc())
    )
    return {
        "universe_stocks": universe_count or 0,
        "cached_stocks": cached_count or 0,
        "latest_trade_date": latest_trade_date,
        "last_successful_sync": (
            latest_job.finished_at.isoformat() if latest_job and latest_job.finished_at else None
        ),
    }


@router.get("/dates")
async def get_dates(
    session: AsyncSession = Depends(get_session),
):
    """Get list of dates with screening results."""
    result = await session.execute(
        select(ResultModel.date)
        .distinct()
        .order_by(ResultModel.date.desc())
    )
    dates = [row[0] for row in result.all()]
    return dates


@router.get("/results/by-strategy")
async def get_results_by_strategy(
    date: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """Get results grouped by strategy."""
    if date is None:
        date = datetime.date.today().strftime("%Y-%m-%d")

    query = select(ResultModel).where(ResultModel.date == date)
    result = await session.execute(query)
    rows = result.scalars().all()

    grouped: dict[str, list] = {}
    for r in rows:
        sname = r.strategy_name
        if sname not in grouped:
            grouped[sname] = []
        grouped[sname].append(ScreeningResultOut(
            id=r.id, date=r.date, stock_code=r.stock_code,
            stock_name=r.stock_name, strategy_name=r.strategy_name,
            price=r.price or 0, change_pct=r.change_pct or 0,
            volume_ratio=r.volume_ratio or 0, reason=r.reason or "",
            sector=r.sector or "", market_cap=r.market_cap or 0,
        ).model_dump())

    # Convert to list for easier frontend rendering
    result_list = [
        {"strategy": sname, "count": len(items), "results": items}
        for sname, items in grouped.items()
    ]
    result_list.sort(key=lambda x: x["count"], reverse=True)
    return result_list


@router.get("/stock/{code}/kline")
async def get_stock_kline(
    code: str,
    days: int = Query(60, le=120),
    session: AsyncSession = Depends(get_session),
):
    """Get K-line data for a specific stock."""
    from app.models import StockCache
    from app.indicators import calc_kdj, calc_ma
    import pandas as pd
    query = (
        select(StockCache)
        .where(StockCache.stock_code == code)
        .order_by(StockCache.trade_date.desc())
        .limit(days)
    )
    result = await session.execute(query)
    rows = result.scalars().all()

    if not rows:
        raise HTTPException(status_code=404, detail="No data found")

    # Build results with KDJ calculated on-the-fly
    records = []
    for r in rows:
        records.append({
            "trade_date": r.trade_date,
            "open": float(r.open) if r.open else 0,
            "close": float(r.close) if r.close else 0,
            "high": float(r.high) if r.high else 0,
            "low": float(r.low) if r.low else 0,
            "volume": int(r.volume) if r.volume else 0,
            "ma5": float(r.ma5) if r.ma5 else 0,
            "ma10": float(r.ma10) if r.ma10 else 0,
            "ma20": float(r.ma20) if r.ma20 else 0,
        })
    records = records[::-1]  # Chronological order

    # Calculate MA and KDJ
    if len(records) >= 9:
        df = pd.DataFrame(records)
        df = calc_ma(df)
        df = calc_kdj(df)
        for i, rec in enumerate(records):
            rec["ma5"] = round(float(df.iloc[i]["ma5"]), 2) if not pd.isna(df.iloc[i].get("ma5", float('nan'))) else 0
            rec["ma10"] = round(float(df.iloc[i]["ma10"]), 2) if not pd.isna(df.iloc[i].get("ma10", float('nan'))) else 0
            rec["ma20"] = round(float(df.iloc[i]["ma20"]), 2) if not pd.isna(df.iloc[i].get("ma20", float('nan'))) else 0
            rec["kdj_k"] = round(float(df.iloc[i]["kdj_k"]), 2) if not pd.isna(df.iloc[i].get("kdj_k", float('nan'))) else 0
            rec["kdj_d"] = round(float(df.iloc[i]["kdj_d"]), 2) if not pd.isna(df.iloc[i].get("kdj_d", float('nan'))) else 0
            rec["kdj_j"] = round(float(df.iloc[i]["kdj_j"]), 2) if not pd.isna(df.iloc[i].get("kdj_j", float('nan'))) else 0
    else:
        for rec in records:
            rec["ma5"] = 0; rec["ma10"] = 0; rec["ma20"] = 0
            rec["kdj_k"] = 0; rec["kdj_d"] = 0; rec["kdj_j"] = 0

    return records
@router.post("/backfill-sectors")
async def backfill_sectors(session: AsyncSession = Depends(get_session)):
    """Backfill empty sector fields for existing screening results."""
    import asyncio
    
    # Build sector/concept mapping from real-time data
    sector_map, concept_map = await asyncio.to_thread(build_sector_concept_maps)
    updated = 0
    
    # Update all results with empty sector
    rows = (
        await session.execute(
            select(ResultModel).where(ResultModel.sector == "")
        )
    ).scalars().all()
    
    for row in rows:
        sector = sector_map.get(row.stock_code, "")
        if sector:
            row.sector = sector
            updated += 1
        concepts = concept_map.get(row.stock_code, "")
        if concepts:
            row.concepts = concepts
            updated += 1
    
    await session.commit()
    
    return {"updated": updated, "total_empty": len(rows), "map_size": len(sector_map), "concept_map_size": len(concept_map)}

