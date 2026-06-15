"""Persistent background screening jobs."""

import asyncio
import datetime
import uuid

from sqlalchemy import select

from app.data_fetcher import refresh_stock_universe, sync_market_data
from app.database import async_session
from app.models import ScreeningJob

_background_tasks: set[asyncio.Task] = set()


def calculate_progress(processed: int, total: int) -> int:
    if total <= 0:
        return 0
    return max(0, min(100, round(processed / total * 100)))


async def _update_job(job_id: str, **values) -> None:
    async with async_session() as session:
        job = await session.get(ScreeningJob, job_id)
        if job is None:
            return
        for key, value in values.items():
            setattr(job, key, value)
        await session.commit()


async def execute_screening_job(job_id: str, run_type: str) -> None:
    from app.screener import run_screening

    await _update_job(
        job_id, status="running", stage="refreshing_universe",
        progress=0, started_at=datetime.datetime.now(),
    )
    try:
        stocks = await refresh_stock_universe()
        await _update_job(job_id, stage="syncing_market_data", total_stocks=len(stocks))

        async def on_progress(processed, total, success, failed):
            await _update_job(
                job_id,
                processed_stocks=processed,
                total_stocks=total,
                success_count=success,
                failed_count=failed,
                progress=min(90, round(calculate_progress(processed, total) * 0.9)),
            )

        sync_result = await sync_market_data(stocks, on_progress)
        await _update_job(job_id, stage="screening", progress=92)
        result = await run_screening(run_type, sync_data=False)
        await _update_job(
            job_id,
            status="completed",
            stage="completed",
            progress=100,
            success_count=sync_result["success"],
            failed_count=sync_result["failed"],
            screened_stocks=result["screened_stocks"],
            selected_stocks=result["total_stocks"],
            total_hits=result["total_hits"],
            finished_at=datetime.datetime.now(),
        )
    except Exception as exc:
        await _update_job(
            job_id, status="failed", stage="failed",
            error_message=str(exc), finished_at=datetime.datetime.now(),
        )


async def start_screening_job(run_type: str) -> ScreeningJob:
    async with async_session() as session:
        running = await session.scalar(
            select(ScreeningJob)
            .where(ScreeningJob.status.in_(["pending", "running"]))
            .order_by(ScreeningJob.created_at.desc())
        )
        if running:
            return running
        job = ScreeningJob(id=str(uuid.uuid4()), run_type=run_type)
        session.add(job)
        await session.commit()
        await session.refresh(job)

    task = asyncio.create_task(execute_screening_job(job.id, run_type))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return job
