import datetime
import json
from decimal import Decimal
from typing import Any

def get_today_str() -> str:
    return datetime.date.today().strftime("%Y-%m-%d")

def get_yesterday_str() -> str:
    return (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

def is_trading_day(date_str: str | None = None) -> bool:
    """Simple check: skip weekends. A proper check would use holiday calendar."""
    if date_str is None:
        d = datetime.date.today()
    else:
        d = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    return d.weekday() < 5

def get_previous_trading_day(date_str: str | None = None) -> str:
    if date_str is None:
        d = datetime.date.today()
    else:
        d = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    d -= datetime.timedelta(days=1)
    while d.weekday() >= 5:
        d -= datetime.timedelta(days=1)
    return d.strftime("%Y-%m-%d")

def fmt_change(pct: float) -> str:
    if pct > 0:
        return f"+{pct:.2f}%"
    return f"{pct:.2f}%"

def to_json(obj: Any) -> str:
    return json.dumps(obj, default=str, ensure_ascii=False)

def safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default
