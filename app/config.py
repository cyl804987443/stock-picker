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
    market_data_concurrency: int = 4
    minimum_sync_ratio: float = 0.95
    initial_history_days: int = 120

    model_config = {"env_file": ".env"}

settings = Settings()
