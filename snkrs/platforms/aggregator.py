"""
Platform Aggregator.
Queries StockX, GOAT, eBay, and Vinted concurrently.
"""

import asyncio
from typing import Dict, Optional, List
import logging

from .base import BaseMarketplace
from .stockx import StockXMarketplace
from .goat import GoatMarketplace
from .ebay import EbayMarketplace
from .vinted import VintedMarketplace
from ..models import PlatformSummary, ConditionGrade, BoxCondition

logger = logging.getLogger(__name__)


class MarketplaceAggregator:
    """Coordinates data retrieval across all 4 platforms."""

    def __init__(self):
        self.platforms: Dict[str, BaseMarketplace] = {
            "stockx": StockXMarketplace(),
            "goat": GoatMarketplace(),
            "ebay": EbayMarketplace(),
            "vinted": VintedMarketplace(),
        }

    async def aggregate(
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
    ) -> Dict[str, PlatformSummary]:
        """Runs concurrent queries against all marketplaces."""
        tasks = []
        platform_ids = list(self.platforms.keys())

        for pid in platform_ids:
            p = self.platforms[pid]
            tasks.append(
                p.fetch_summary(
                    sku=sku,
                    model_name=model_name,
                    size_us=size_us,
                    size_eu=size_eu,
                    condition=condition,
                    box_condition=box_condition,
                    currency=currency,
                    stockx_override=stockx_override,
                    stockx_last_20_avg=stockx_last_20_avg,
                    stockx_year_avg=stockx_year_avg
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        summaries: Dict[str, PlatformSummary] = {}
        for pid, result in zip(platform_ids, results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching from {pid}: {result}")
                summaries[pid] = PlatformSummary(
                    platform_name=self.platforms[pid].name,
                    platform_id=pid,
                    is_live=False,
                    error_message=str(result),
                    currency=currency
                )
            else:
                summaries[pid] = result

        return summaries
