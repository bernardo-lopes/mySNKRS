"""
Vinted Platform Connector.
Vinted is a major peer-to-peer marketplace with a GAME-CHANGING advantage:
0% SELLER FEES (The buyer pays the Buyer Protection fee and shipping!).
"""

from typing import Optional, List, Dict, Any
import httpx
import re
import logging
from .base import BaseMarketplace
from ..models import PlatformSummary, MarketListing, ConditionGrade, BoxCondition

logger = logging.getLogger(__name__)


class VintedMarketplace(BaseMarketplace):
    """
    Vinted Marketplace Provider.
    Zero seller fees — the buyer pays the Buyer Protection fee!
    """

    name = "Vinted (US)"
    platform_id = "vinted"
    seller_fee_percent = 0.0  # ZERO seller fee!
    seller_fixed_fee = 0.0

    # Vinted condition status codes:
    # 6: New with tags / box
    # 1: New without tags
    # 2: Very good condition
    # 3: Good condition
    # 4: Fair / Satisfactory
    CONDITION_MAPPING = {
        ConditionGrade.DEADSTOCK: 6,
        ConditionGrade.VNDS: 1,
        ConditionGrade.USED_LIKE_NEW: 2,
        ConditionGrade.USED_GOOD: 3,
        ConditionGrade.USED_FAIR: 4,
        ConditionGrade.USED_BEAT: 4,
    }

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
        search_term = f"{clean_sku} {int(size_eu)}" if clean_sku else f"{model_name} {int(size_eu)}"
        
        listings = await self._attempt_vinted_scrape(search_term, condition, currency)

        # Only what Vinted returned: no results means no prices
        prices = [l.price for l in listings]
        lowest_ask = min(prices) if prices else None

        return PlatformSummary(
            platform_name="Vinted",
            platform_id=self.platform_id,
            is_live=bool(listings),
            data_source="live" if listings else "none",
            currency=currency,
            lowest_ask=lowest_ask,
            highest_bid=None,  # Vinted uses direct offers / chat
            last_sale_price=None,  # Vinted doesn't publish sold prices
            sample_count=len(listings),
            listings=listings,
            seller_fee_percentage=0.0,
            seller_fixed_fee=0.0,
            estimated_net_payout=self.calculate_net_payout(lowest_ask) if lowest_ask else None,
            notes="0% seller fees: you keep your full selling price (the buyer pays protection and shipping).",
        )

    async def _attempt_vinted_scrape(
        self,
        search_text: str,
        condition: ConditionGrade,
        currency: str
    ) -> List[MarketListing]:
        """Attempts to search Vinted catalog API."""
        results: List[MarketListing] = []
        try:
            status_id = self.CONDITION_MAPPING.get(condition, 2)
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
            }
            # Vinted search items
            url = f"https://www.vinted.com/api/v2/catalog/items?search_text={search_text}&status_ids={status_id}&order=price_low_to_high&per_page=6"
            
            async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
                # First visit homepage to initialize session cookie if needed
                await client.get("https://www.vinted.com", headers=headers)
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    items = data.get("items", [])
                    for it in items:
                        price_val = float(it.get("price", {}).get("amount") or it.get("price", 0.0))
                        title = it.get("title") or it.get("brand_title") or search_text
                        item_id = it.get("id")
                        photo = it.get("photo", {}).get("url")
                        results.append(
                            MarketListing(
                                platform="vinted",
                                title=title,
                                price=price_val,
                                currency=currency,
                                size=str(it.get("size_title", "EU")),
                                condition=condition.value,
                                listing_type="active",
                                url=f"https://www.vinted.com/items/{item_id}",
                                thumbnail_url=photo
                            )
                        )
        except Exception as e:
            logger.debug(f"Vinted API query: {e}")
        return results[:4]
