"""
FastAPI Web Application for Sneaker Valuation and Multi-Platform Reselling Intelligence.
"""

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
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


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Renders the main sneaker evaluation page."""
    recent_history = storage.get_recent_evaluations(limit=6)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "popular_catalog": CATALOG_BENCHMARKS,
            "conditions": [c.value for c in ConditionGrade],
            "box_conditions": [b.value for b in BoxCondition],
            "recent_history": recent_history,
        }
    )


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
    stockx_price: Optional[float] = Form(None)
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
        stockx_override=stockx_price
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
