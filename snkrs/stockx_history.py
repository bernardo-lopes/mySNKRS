"""
StockX sales history summaries (avg sale price and units sold per period).
"""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

RANGE_DAYS = {"1m": 30, "3m": 91, "6m": 182, "3y": 365 * 3}


def summarize_sales(
    sales: List[Dict[str, Any]],
    range_key: str,
    today: Optional[date] = None,
) -> Dict[str, Any]:
    """Filters sales ({"date": "YYYY-MM-DD...", "price": float}) to a period and aggregates them."""
    if range_key not in RANGE_DAYS:
        raise ValueError(f"Unknown range '{range_key}', expected one of {list(RANGE_DAYS)}")
    today = today or date.today()
    start = today - timedelta(days=RANGE_DAYS[range_key])

    points = sorted(
        (s for s in sales if start <= date.fromisoformat(s["date"][:10]) <= today),
        key=lambda s: s["date"],
    )
    prices = [float(s["price"]) for s in points]
    return {
        "range": range_key,
        "points": points,
        "units_sold": len(prices),
        "avg_price": round(sum(prices) / len(prices), 2) if prices else None,
        "high": max(prices) if prices else None,
        "low": min(prices) if prices else None,
    }
