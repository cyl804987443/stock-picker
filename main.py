"""A股选股器 - Main entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import init_db
from app.api import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_pre_market():
    from app.jobs import start_screening_job
    logger.info("🕐 Starting pre-market screening (7:00)...")
    try:
        job = await start_screening_job("pre_market")
        logger.info(f"Pre-market job queued: {job.id}")
    except Exception as e:
        logger.error(f"❌ Pre-market failed: {e}")


async def run_call_auction():
    from app.jobs import start_screening_job
    logger.info("🕐 Starting call auction screening (9:25)...")
    try:
        job = await start_screening_job("call_auction")
        logger.info(f"Call auction job queued: {job.id}")
    except Exception as e:
        logger.error(f"❌ Call auction failed: {e}")


async def run_post_market():
    from app.jobs import start_screening_job
    logger.info("🕐 Starting post-market review (15:30)...")
    try:
        job = await start_screening_job("post_market")
        logger.info(f"Post-market job queued: {job.id}")
    except Exception as e:
        logger.error(f"❌ Post-market failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting A-Share Stock Picker...")
    await init_db()

    # Schedule daily tasks
    scheduler.add_job(run_pre_market, "cron", hour=7, minute=0, id="pre_market")
    scheduler.add_job(run_call_auction, "cron", hour=9, minute=25, id="call_auction")
    scheduler.add_job(run_post_market, "cron", hour=15, minute=30, id="post_market")

    scheduler.start()
    logger.info("✅ Scheduler started (7:00, 9:25, 15:30 daily)")

    yield

    scheduler.shutdown()
    logger.info("🛑 Scheduler stopped")


app = FastAPI(
    title="A股选股器",
    description="每日盘前/竞价/收盘自动运行15个短线战法选股",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api")

# Mount static files - serve SPA
app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
