"""
FastAPI Web Application for Sneaker Valuation and Multi-Platform Reselling Intelligence.
"""

from fastapi import FastAPI, Request, Form, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional

from ..models import ConditionGrade, BoxCondition
from ..size_converter import SizeConverter
from ..platforms.aggregator import MarketplaceAggregator
from ..platforms.stockx import CATALOG_BENCHMARKS
from ..valuation import SneakerValuationEngine
from ..storage import SneakerStorage
from ..stockx_sync import parse_stockx_page, size_key
from ..stockx_history import RANGE_DAYS, summarize_sales

app = FastAPI(title="SNKRS - Sneaker Market Price Valuation")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

aggregator = MarketplaceAggregator()
storage = SneakerStorage()
aggregator.platforms["stockx"].storage = storage


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Renders the main sneaker evaluation page."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"popular_catalog": CATALOG_BENCHMARKS},
    )


@app.get("/sync", response_class=HTMLResponse)
async def sync_page(request: Request):
    """Receives StockX page data from the sync bookmark (via postMessage) and stores it."""
    return templates.TemplateResponse(request=request, name="sync.html", context={})


@app.get("/api/popular")
async def get_popular():
    """Returns curated list of popular sneakers."""
    return CATALOG_BENCHMARKS


@app.post("/api/evaluate")
async def evaluate_sneaker(
    sku: str = Form(...),
    size: str = Form(...),
    condition: str = Form(ConditionGrade.DEADSTOCK.value),
    box_condition: str = Form(BoxCondition.ORIGINAL_GOOD.value),
    model_name: Optional[str] = Form(None),
    currency: str = Form("USD"),
):
    """Processes sneaker estimation across StockX, GOAT, eBay, and Vinted."""
    try:
        cond_enum = ConditionGrade(condition)
        box_enum = BoxCondition(box_condition)
    except ValueError:
        cond_enum = ConditionGrade.DEADSTOCK
        box_enum = BoxCondition.ORIGINAL_GOOD

    norm_size = SizeConverter.normalize(size)

    platforms_data = await aggregator.aggregate(
        sku=sku,
        model_name=model_name,
        size_us=norm_size["us_m"],
        size_eu=norm_size["eu"],
        condition=cond_enum,
        box_condition=box_enum,
        currency=currency,
    )

    report = SneakerValuationEngine.evaluate(
        sku=sku,
        size_input=size,
        condition=cond_enum,
        box_condition=box_enum,
        platforms_data=platforms_data,
        model_name=model_name,
        currency=currency
    )

    # Save to history
    storage.save_evaluation(report)

    return JSONResponse(content=report.model_dump())


@app.get("/api/history")
async def get_history():
    """Fetches recent valuations."""
    return storage.get_recent_evaluations(limit=20)


class StockXSyncPayload(BaseModel):
    text: str
    title: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    sku: Optional[str] = None


@app.post("/api/stockx/sync")
async def stockx_sync(payload: StockXSyncPayload):
    """Stores bid, ask and sales parsed from a StockX page (sync bookmark or pasted text)."""
    parsed = parse_stockx_page(payload.text, payload.title)
    sku = (payload.sku or parsed["sku"] or "").strip().upper()
    if not sku:
        raise HTTPException(400, "Could not find the style code (SKU) on this page.")

    sales = [dict(s, size_key=size_key(s["size"])) for s in parsed["sales"]]
    sales = [s for s in sales if s["size_key"]]
    market = None
    page_key = size_key(parsed["size"]) if parsed["size"] else None
    if page_key and (parsed["highest_bid"] or parsed["lowest_ask"]):
        market = {
            "size_key": page_key,
            "size_label": parsed["size"],
            "highest_bid": parsed["highest_bid"],
            "lowest_ask": parsed["lowest_ask"],
        }
    if not market and not sales:
        raise HTTPException(400, "No bid, ask or sales found. Pick your size and open Market Data > Sales first.")

    added = storage.save_stockx_sync(sku, parsed["title"], payload.url, payload.image_url, market, sales)
    return {
        "sku": sku,
        "title": parsed["title"],
        "size": parsed["size"],
        "highest_bid": parsed["highest_bid"],
        "lowest_ask": parsed["lowest_ask"],
        "sales_found": len(sales),
        "sales_added": added,
    }


@app.get("/api/stockx/history")
async def stockx_history(
    sku: str,
    size: str,
    range: str = Query("6m", pattern="^(" + "|".join(RANGE_DAYS) + ")$"),
):
    """Sales in a period (1m, 3m, 6m, 3y) with average price and units sold."""
    stockx = aggregator.platforms["stockx"]
    key = stockx.resolve_size_key(sku, SizeConverter.normalize(size)["us_m"])
    sales = storage.get_stockx_sales(sku, key) if key else []
    result = summarize_sales(sales, range)
    result["oldest_sale"] = sales[-1]["date"] if sales else None
    result["sales_on_file"] = len(sales)
    return result
