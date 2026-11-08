"""
GOAT Platform Connector.
Recommended 4th platform: GOAT is the premier global sneaker marketplace alongside StockX,
with the distinct advantage of natively supporting both Deadstock and USED sneaker sales with box grading!
"""

from typing import Optional, List, Dict, Any
import httpx
import logging
from .base import BaseMarketplace
from ..models import PlatformSummary, MarketListing, ConditionGrade, BoxCondition

logger = logging.getLogger(__name__)


class GoatMarketplace(BaseMarketplace):
    """
    GOAT Marketplace Provider.
    Supports Deadstock, New with defects/damaged box, and Pre-owned (Used).
    Fee Structure:
    - 9.5% commission fee (tier 1 standard)
    - $5.00 cash out fee
    - 2.9% cash out processing
    Total average seller fee is ~13-14%.
    """

    name = "GOAT (US)"
    platform_id = "goat"
    seller_fee_percent = 12.4  # 9.5% commission + 2.9% cash out
    seller_fixed_fee = 5.00    # $5.00 cash out fee in US

    async def fetch_summary(
        self,
        sku: str,
        model_name: Optional[str],
        size_us: float,
        size_eu: float,
        condition: ConditionGrade,
        box_condition: BoxCondition,
        currency: str = "USD",
        stockx_override: Optional[float] = None,
        stockx_last_20_avg: Optional[float] = None,
        stockx_year_avg: Optional[float] = None
    ) -> PlatformSummary:
        clean_sku = sku.strip().upper()
        query = clean_sku or model_name or ""

        # GOAT's search only gives the cheapest pair across all sizes, so no price is shown here.
        # The lookup is kept for the product page, which lets the app link straight to your size.
        live_result = await self._attempt_live_goat_search(query, size_us)

        return PlatformSummary(
            platform_name="GOAT",
            platform_id=self.platform_id,
            is_live=False,
            data_source="none",
            currency=currency,
            product_url=live_result.get("url") if live_result else None,
            seller_fee_percentage=self.seller_fee_percent,
            seller_fixed_fee=self.seller_fixed_fee,
            notes="No size-specific GOAT prices available; open GOAT to see them.",
        )

    async def _attempt_live_goat_search(self, query: str, size_us: float) -> Optional[Dict[str, Any]]:
        """Queries GOAT's public Algolia search endpoint."""
        if not query:
            return None
        try:
            url = "https://2fwvbgjaiv-dsn.algolia.net/1/indexes/product_variants_v2/query"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "x-algolia-application-id": "2FWVBGJAIV",
                "x-algolia-api-key": "ac96de6fcc0e02b0d02333e1349692da",
            }
            payload = {
                "params": f"query={query}&hitsPerPage=1"
            }
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    hits = data.get("hits", [])
                    if hits:
                        hit = hits[0]
                        lowest_price = hit.get("lowest_price_cents", 0)
                        if lowest_price == 0:
                            lowest_price = hit.get("retail_price_cents", 15000)
                        return {
                            "title": hit.get("name"),
                            "lowest_price_cents": lowest_price,
                            "image_url": hit.get("original_image_url") or hit.get("grid_picture_url"),
                            "slug": hit.get("slug"),
                            "url": f"https://www.goat.com/sneakers/{hit.get('slug')}" if hit.get("slug") else None
                        }
        except Exception as e:
            logger.debug(f"GOAT live query: {e}")
        return None
