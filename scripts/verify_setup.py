"""Verify project setup is correct."""
import sys

def check():
    errors = []
    try:
        from app.config import settings
        print(f"✓ config: DB={settings.database_url}")
    except Exception as e:
        errors.append(f"config: {e}")

    try:
        import akshare as ak
        print(f"✓ akshare: {ak.__version__}")
    except Exception as e:
        errors.append(f"akshare: {e}")

    try:
        import pandas as pd
        import numpy as np
        print(f"✓ pandas: {pd.__version__}, numpy: {np.__version__}")
    except Exception as e:
        errors.append(f"pandas/numpy: {e}")

    try:
        from sqlalchemy import __version__ as sa_v
        print(f"✓ sqlalchemy: {sa_v}")
    except Exception as e:
        errors.append(f"sqlalchemy: {e}")

    try:
        from app.models import Base, ScreeningResult, DailySummary, StockCache
        print("✓ models: ORM tables defined")
    except Exception as e:
        errors.append(f"models: {e}")

    try:
        from app.indicators import calc_all_indicators
        print("✓ indicators: calculator loaded")
    except Exception as e:
        errors.append(f"indicators: {e}")

    try:
        from app.strategies import ALL_STRATEGIES
        print(f"✓ strategies: {len(ALL_STRATEGIES)} loaded")
        for s in ALL_STRATEGIES:
            print(f"  - {s.name} ({s.category})")
    except Exception as e:
        errors.append(f"strategies: {e}")

    try:
        from app.screener import run_screening
        print("✓ screener: orchestrator loaded")
    except Exception as e:
        errors.append(f"screener: {e}")

    try:
        from app.api import router
        print("✓ api: router loaded")
    except Exception as e:
        errors.append(f"api: {e}")

    if errors:
        print(f"\n❌ {len(errors)} errors:")
        for e in errors:
            print(f"  - {e}")
        return False
    else:
        print(f"\n✅ All checks passed!")
        return True

if __name__ == "__main__":
    sys.exit(0 if check() else 1)
