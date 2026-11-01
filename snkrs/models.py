"""
Data models for Sneaker Valuation and Multi-Platform Marketplaces.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ConditionGrade(str, Enum):
    DEADSTOCK = "deadstock"            # Brand New in Box (DS) - 10/10
    VNDS = "vnds"                      # Very Near Deadstock / Pass as DS - 9.5/10 (Tried on / Worn once)
    USED_LIKE_NEW = "used_like_new"    # Gently Used - 9/10 (No creases, zero sole wear)
    USED_GOOD = "used_good"            # Used / Good Condition - 7.5 - 8.5/10 (Minor creases, slight heel wear)
    USED_FAIR = "used_fair"            # Used / Fair - 5 - 7/10 (Visible creasing, star loss, midsole scuffs)
    USED_BEAT = "used_beat"            # Beat / Project - <5/10 (Heavy wear, separation, heel drag)


class BoxCondition(str, Enum):
    ORIGINAL_GOOD = "original_good"       # Original box in good condition with tissue/accessories
    ORIGINAL_DAMAGED = "original_damaged" # Original box damaged or missing lid
    REPLACEMENT = "replacement"           # Replacement / generic shoe box
    NO_BOX = "no_box"                     # No box (shoes only)


class SizeSystem(str, Enum):
    US_MEN = "US_M"
    US_WOMEN = "US_W"
    EU = "EU"
    UK = "UK"
    CM = "CM"


class MarketListing(BaseModel):
    """An individual listing or recent sale found on a marketplace."""
    platform: str                        # stockx, goat, ebay, vinted
    title: str
    price: float                         # Price in currency
    currency: str = "EUR"
    size: str
    condition: str
    listing_type: str = "active"         # "active" (for sale) or "sold" (transaction)
    url: Optional[str] = None
    seller_rating: Optional[str] = None
    shipping_estimate: Optional[float] = 0.0
    date_sold: Optional[str] = None
    thumbnail_url: Optional[str] = None


class PlatformSummary(BaseModel):
    """Summary of market data from a specific platform."""
    platform_name: str
    platform_id: str                     # stockx, goat, ebay, vinted
    is_live: bool = True
    error_message: Optional[str] = None
    
    # Pricing metrics
    currency: str = "EUR"
    lowest_ask: Optional[float] = None   # Current cheapest available
    highest_bid: Optional[float] = None  # Instant payout if sold now
    last_sale_price: Optional[float] = None
    average_price: Optional[float] = None
    sample_count: int = 0
    
    # Listings
    listings: List[MarketListing] = Field(default_factory=list)
    
    # Platform seller fee calculation
    seller_fee_percentage: float = 0.0
    seller_fixed_fee: float = 0.0
    estimated_net_payout: Optional[float] = None
    notes: Optional[str] = None


class ValuationReport(BaseModel):
    """Consolidated market price estimation and reselling strategy."""
    sku: str
    model_name: str
    brand: str
    size_input: str
    normalized_size_us: float
    normalized_size_eu: float
    condition: ConditionGrade
    box_condition: BoxCondition
    currency: str = "EUR"
    image_url: Optional[str] = None
    retail_price: Optional[float] = None

    # Reference baseline (StockX Deadstock)
    stockx_reference_price: Optional[float] = None
    condition_multiplier: float = 1.0
    box_multiplier: float = 1.0

    # Pricing recommendations
    quick_sale_price: float = Field(..., description="Undercut to sell within 24-48 hours")
    fair_market_price: float = Field(..., description="Realistic target selling price within 1-2 weeks")
    patient_sale_price: float = Field(..., description="Top dollar target for patient sellers")

    # Range
    estimated_range_min: float
    estimated_range_max: float
    confidence_score: int = Field(..., ge=0, le=100, description="Confidence percentage based on data density")

    # Platform breakdown & net payout analysis
    platforms: Dict[str, PlatformSummary] = Field(default_factory=dict)
    best_platform_to_sell: str
    best_platform_reason: str

    # Resell tips & insights
    insights: List[str] = Field(default_factory=list)
