"""
Base abstract platform provider.
"""

from abc import ABC, abstractmethod
from typing import Optional
from ..models import PlatformSummary, ConditionGrade, BoxCondition


class BaseMarketplace(ABC):
    """Abstract interface for all sneaker marketplaces."""

    name: str
    platform_id: str
    seller_fee_percent: float = 0.0
    seller_fixed_fee: float = 0.0

    @abstractmethod
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
        """
        Fetches market listings and summarizes key price metrics for a given sneaker & condition.
        """
        pass

    def calculate_net_payout(self, gross_price: float) -> float:
        """Calculates expected take-home cash after platform seller fees."""
        if gross_price <= 0:
            return 0.0
        fee = (gross_price * (self.seller_fee_percent / 100.0)) + self.seller_fixed_fee
        return max(0.0, round(gross_price - fee, 2))
