from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, text
from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    from app.models import AppMetadata, Base, DailySummary, ScreeningResult, StockCache
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Lightweight migrations for the pre-migration SQLite project.
        columns = {
            row[1] for row in (
                await conn.execute(text("PRAGMA table_info(daily_summary)"))
            ).fetchall()
        }
        if "total_hits" not in columns:
            await conn.execute(text(
                "ALTER TABLE daily_summary ADD COLUMN total_hits INTEGER DEFAULT 0"
            ))
        if "screened_stocks" not in columns:
            await conn.execute(text(
                "ALTER TABLE daily_summary ADD COLUMN screened_stocks INTEGER DEFAULT 0"
            ))
        # Migration for concepts column in screening_results
        sr_columns = {
            row[1] for row in (
                await conn.execute(text("PRAGMA table_info(screening_results)"))
            ).fetchall()
        }
        if "concepts" not in sr_columns:
            await conn.execute(text(
                "ALTER TABLE screening_results ADD COLUMN concepts TEXT DEFAULT ''"
            ))
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_stock_cache_code_date "
            "ON stock_cache(stock_code, trade_date)"
        ))

    async with async_session() as session:
        marker = await session.get(AppMetadata, "real_market_data_v1")
        if marker is None:
            # The existing database contains the explicitly deprecated demo pool.
            await session.execute(StockCache.__table__.delete())
            await session.execute(ScreeningResult.__table__.delete())
            await session.execute(DailySummary.__table__.delete())
            session.add(AppMetadata(key="real_market_data_v1", value="initialized"))
            await session.commit()

async def get_session():
    async with async_session() as session:
        yield session

async def cleanup_old_data(retain_days: int | None = None):
    """Remove old cached data beyond retention period."""
    from app.models import StockCache, ScreeningResult
    from app.config import settings as cfg
    from datetime import datetime, timedelta
    import json

    retain = retain_days or cfg.results_retention_days
    cutoff = (datetime.now() - timedelta(days=retain)).strftime("%Y-%m-%d")
    cache_cutoff = (datetime.now() - timedelta(days=cfg.stock_cache_days)).strftime("%Y-%m-%d")

    async with async_session() as session:
        async with session.begin():
            r1 = await session.execute(
                ScreeningResult.__table__.delete().where(ScreeningResult.date < cutoff)
            )
            r2 = await session.execute(
                StockCache.__table__.delete().where(StockCache.trade_date < cache_cutoff)
            )
        return {"results_deleted": r1.rowcount, "cache_deleted": r2.rowcount}
