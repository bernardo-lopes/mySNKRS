"""
Inventory valuation: each pair you own, priced from your synced StockX data.
"""

from typing import Any, Dict, List

from .models import BoxCondition, ConditionGrade
from .platforms.stockx import StockXMarketplace
from .size_converter import SizeConverter
from .marketplace_links import stockx_product_link
from .stockx_history import summarize_sales
from .storage import SneakerStorage


def stockx_eligible(item: Dict[str, Any]) -> bool:
    """StockX only accepts deadstock pairs in their original, undamaged box."""
    return item["condition"] == ConditionGrade.DEADSTOCK.value and item["box_condition"] == BoxCondition.ORIGINAL_GOOD.value


def value_item(item: Dict[str, Any], storage: SneakerStorage, stockx: StockXMarketplace) -> Dict[str, Any]:
    key = stockx.resolve_size_key(item["sku"], SizeConverter.normalize(item["size"] or "")["us_m"])
    market = storage.get_stockx_market(item["sku"], key) if key else None
    sales = storage.get_stockx_sales(item["sku"], key) if key else []
    product = storage.get_stockx_product(item["sku"]) or {}

    bid = market["highest_bid"] if market else None
    eligible = stockx_eligible(item)
    net_now = stockx.calculate_net_payout(bid) if (bid and eligible) else None
    ask = market["lowest_ask"] if market else None
    paid = item["purchase_price"]
    six_months = summarize_sales(sales, "6m")

    return {
        **item,
        "favorite": bool(item.get("favorite")),
        "title": product.get("title") or item["model_name"],
        "image_url": product.get("image_url"),
        "stockx_url": stockx_product_link(product.get("url"), key, item["size"]) or f"https://stockx.com/search?s={item['sku']}",
        "retail_price": product.get("retail_price"),
        "synced": bool(market or sales),
        "synced_at": market["synced_at"] if market else None,
        "stockx_eligible": eligible,
        "highest_bid": bid,
        "lowest_ask": ask,
        "lowest_ask_net_payout": stockx.calculate_net_payout(ask) if (ask and eligible) else None,
        "avg_sale_6m": six_months["avg_price"],
        "units_sold_6m": six_months["units_sold"],
        "last_sale": sales[0]["price"] if sales else None,
        "last_sale_date": sales[0]["date"] if sales else None,
        "net_payout_now": net_now,
        "profit_now": round(net_now - paid, 2) if (net_now is not None and paid) else None,
    }


def value_inventory(
    storage: SneakerStorage, stockx: StockXMarketplace, status: str = "for_sale", favorites_only: bool = False,
) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = [value_item(i, storage, stockx) for i in storage.get_inventory(status)]
    if favorites_only:
        items = [i for i in items if i["favorite"]]
    priced = [i for i in items if i["net_payout_now"] is not None]
    paid = [i["purchase_price"] for i in items if i["purchase_price"] is not None]
    profits = [i["profit_now"] for i in priced if i["profit_now"] is not None]
    return {
        "items": items,
        "totals": {
            "pairs": len(items),
            "synced": sum(1 for i in items if i["synced"]),
            "stockx_eligible": sum(1 for i in items if i["stockx_eligible"]),
            "priced": len(priced),
            "net_payout_now": round(sum(i["net_payout_now"] for i in priced), 2),
            "paid": round(sum(paid), 2) if paid else None,
            "profit_now": round(sum(profits), 2) if profits else None,
        },
    }
