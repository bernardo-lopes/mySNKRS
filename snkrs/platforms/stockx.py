"""
StockX Platform Connector.
StockX is the primary industry reference for Deadstock market value.

StockX blocks automated access, so prices come only from data you sync from your own browser
(see stockx_sync.py). Nothing is estimated: without a sync, the summary has no prices.
"""

from typing import Optional, Dict, Any, List
from .base import BaseMarketplace
from ..models import PlatformSummary, ConditionGrade, BoxCondition
from ..size_converter import NIKE_MENS_CHART
from ..storage import SneakerStorage

# Popular drops for quick presets and the non-StockX valuation baseline (not used for StockX prices)
CATALOG_BENCHMARKS: Dict[str, Dict[str, Any]] = {
    "DD1391-100": {
        "title": "Nike Dunk Low Retro White Black Panda",
        "brand": "Nike",
        "retail_price": 115.0,
        "base_stockx_ds": 125.0,
        "lowest_ask": 130.0,
        "highest_bid": 118.0,
        "last_sale": 122.0,
        "image_url": "https://images.stockx.com/images/Nike-Dunk-Low-Retro-White-Black-2021-Product.jpg",
        "url": "https://stockx.com/nike-dunk-low-retro-white-black-2021",
    },
    "DZ5485-612": {
        "title": "Air Jordan 1 Retro High OG Chicago Lost and Found",
        "brand": "Jordan",
        "retail_price": 180.0,
        "base_stockx_ds": 235.0,
        "lowest_ask": 245.0,
        "highest_bid": 220.0,
        "last_sale": 230.0,
        "image_url": "https://images.stockx.com/images/Air-Jordan-1-Retro-High-OG-Chicago-Reimagined-Lost-and-Found-Product.jpg",
        "url": "https://stockx.com/air-jordan-1-retro-high-og-chicago-reimagined-lost-and-found",
    },
    "DH6927-111": {
        "title": "Air Jordan 4 Retro Military Black",
        "brand": "Jordan",
        "retail_price": 210.0,
        "base_stockx_ds": 440.0,
        "lowest_ask": 455.0,
        "highest_bid": 425.0,
        "last_sale": 435.0,
        "image_url": "https://images.stockx.com/images/Air-Jordan-4-Retro-Military-Black-Product.jpg",
        "url": "https://stockx.com/air-jordan-4-retro-military-black",
    },
    "DM7866-162": {
        "title": "Air Jordan 1 Retro Low OG SP Travis Scott Reverse Mocha",
        "brand": "Jordan",
        "retail_price": 150.0,
        "base_stockx_ds": 1150.0,
        "lowest_ask": 1190.0,
        "highest_bid": 1080.0,
        "last_sale": 1120.0,
        "image_url": "https://images.stockx.com/images/Air-Jordan-1-Low-OG-SP-Travis-Scott-Reverse-Mocha-Product.jpg",
        "url": "https://stockx.com/air-jordan-1-low-og-sp-travis-scott-reverse-mocha",
    },
    "B75806": {
        "title": "adidas Samba OG Cloud White Core Black",
        "brand": "adidas",
        "retail_price": 100.0,
        "base_stockx_ds": 110.0,
        "lowest_ask": 115.0,
        "highest_bid": 102.0,
        "last_sale": 108.0,
        "image_url": "https://images.stockx.com/images/adidas-Samba-OG-Cloud-White-Core-Black-Product.jpg",
        "url": "https://stockx.com/adidas-samba-og-cloud-white-core-black",
    },
    "BB550PB1": {
        "title": "New Balance 550 White Grey",
        "brand": "New Balance",
        "retail_price": 110.0,
        "base_stockx_ds": 115.0,
        "lowest_ask": 120.0,
        "highest_bid": 105.0,
        "last_sale": 112.0,
        "image_url": "https://images.stockx.com/images/New-Balance-550-White-Grey-Product.jpg",
        "url": "https://stockx.com/new-balance-550-white-grey",
    },
    "DN3707-100": {
        "title": "Air Jordan 3 Retro White Cement Reimagined",
        "brand": "Jordan",
        "retail_price": 210.0,
        "base_stockx_ds": 240.0,
        "lowest_ask": 250.0,
        "highest_bid": 228.0,
        "last_sale": 235.0,
        "image_url": "https://images.stockx.com/images/Air-Jordan-3-Retro-White-Cement-Reimagined-Product.jpg",
        "url": "https://stockx.com/air-jordan-3-retro-white-cement-reimagined",
    },
    "FD0860-001": {
        "title": "Nike SB Dunk Low Jarritos",
        "brand": "Nike SB",
        "retail_price": 130.0,
        "base_stockx_ds": 520.0,
        "lowest_ask": 540.0,
        "highest_bid": 490.0,
        "last_sale": 510.0,
        "image_url": "https://images.stockx.com/images/Nike-SB-Dunk-Low-Jarritos-Product.jpg",
        "url": "https://stockx.com/nike-sb-dunk-low-jarritos",
    },
    "HQ4540": {
        "title": "adidas Yeezy Boost 350 V2 Onyx",
        "brand": "adidas",
        "retail_price": 230.0,
        "base_stockx_ds": 260.0,
        "lowest_ask": 275.0,
        "highest_bid": 245.0,
        "last_sale": 255.0,
        "image_url": "https://images.stockx.com/images/adidas-Yeezy-Boost-350-V2-Onyx-Product.jpg",
        "url": "https://stockx.com/adidas-yeezy-boost-350-v2-onyx",
    },
    "FD2596-700": {
        "title": "Air Jordan 1 Retro High OG Reverse Laney (Women's)",
        "brand": "Jordan",
        "retail_price": 180.0,
        "base_stockx_ds": 105.0,  # $105 USD lowest ask
        "lowest_ask": 105.0,
        "highest_bid": 95.0,
        "last_sale": 103.0,     # $103 USD average sale
        "image_url": "https://images.stockx.com/images/Air-Jordan-1-Retro-High-OG-Reverse-Laney-W-Product.jpg",
        "url": "https://stockx.com/air-jordan-1-retro-high-og-reverse-laney-w",
    }
}


class StockXMarketplace(BaseMarketplace):
    """
    StockX Provider (US Instance).
    Primary reference point for Deadstock prices.
    Fee Structure (US):
    - 9.0% Transaction Fee
    - 3.0% Payment Processing Fee
    - $5.00 Shipping
    Net payout is computed on the highest bid (what you get if you sell now).
    """

    name = "StockX (US)"
    platform_id = "stockx"
    seller_fee_percent = 12.0  # 9% commission + 3% payment processing
    seller_fixed_fee = 5.0  # shipping

    TRANSACTION_FEE_PERCENT = 9.0
    PROCESSING_FEE_PERCENT = 3.0

    def __init__(self, storage: Optional[SneakerStorage] = None):
        self._storage = storage

    @property
    def storage(self) -> SneakerStorage:
        if self._storage is None:
            self._storage = SneakerStorage()
        return self._storage

    @storage.setter
    def storage(self, value: SneakerStorage):
        self._storage = value

    def payout_breakdown(self, price: float) -> Dict[str, float]:
        """Mirrors StockX's Total Payout breakdown: ask, 9% transaction fee, 3% processing, $5 shipping."""
        transaction = round(price * self.TRANSACTION_FEE_PERCENT / 100.0, 2)
        processing = round(price * self.PROCESSING_FEE_PERCENT / 100.0, 2)
        return {
            "price": price,
            "transaction_fee": transaction,
            "processing_fee": processing,
            "shipping": self.seller_fixed_fee,
            "payout": max(0.0, round(price - transaction - processing - self.seller_fixed_fee, 2)),
        }

    def calculate_net_payout(self, gross_price: float) -> float:
        if gross_price is None or gross_price <= 0:
            return 0.0
        return self.payout_breakdown(gross_price)["payout"]

    @staticmethod
    def size_key_candidates(size_us: float) -> List[str]:
        """Men's and women's StockX size keys for a normalized US men's size (a SKU is one or the other)."""
        row = next((r for r in NIKE_MENS_CHART if r["us_m"] == size_us), None)
        fmt = lambda v: f"{v:g}"
        keys = [f"M{fmt(size_us)}"]
        if row:
            keys.append(f"W{fmt(row['us_w'])}")
        return keys

    def resolve_size_key(self, sku: str, size_us: float) -> Optional[str]:
        synced = set(self.storage.get_stockx_size_keys(sku))
        return next((k for k in self.size_key_candidates(size_us) if k in synced), None)

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
        product = self.storage.get_stockx_product(clean_sku) or {}
        key = self.resolve_size_key(clean_sku, size_us)
        market = self.storage.get_stockx_market(clean_sku, key) if key else None
        sales = self.storage.get_stockx_sales(clean_sku, key) if key else []

        summary = PlatformSummary(
            platform_name="StockX",
            platform_id=self.platform_id,
            currency=currency,
            seller_fee_percentage=self.seller_fee_percent,
            seller_fixed_fee=self.seller_fixed_fee,
            product_title=product.get("title"),
            image_url=product.get("image_url"),
            product_url=product.get("url") or f"https://stockx.com/search?s={clean_sku}",
            size_key=key,
        )

        if not market and not sales:
            summary.is_live = False
            summary.data_source = "not_synced"
            summary.notes = "No StockX data for this size yet. Open it on StockX and click the SNKRS sync bookmark."
            return summary

        summary.is_live = True
        summary.data_source = "browser_sync"
        summary.recent_sales = sales
        summary.sample_count = len(sales)
        summary.last_sale_price = sales[0]["price"] if sales else None
        if market:
            summary.highest_bid = market["highest_bid"]
            summary.lowest_ask = market["lowest_ask"]
            summary.size_label = market["size_label"]
            summary.synced_at = market["synced_at"]
        elif sales:
            summary.size_label = sales[0]["size"]

        # Selling now means accepting the highest bid
        if summary.highest_bid:
            summary.payout_breakdown = self.payout_breakdown(summary.highest_bid)
            summary.estimated_net_payout = summary.payout_breakdown["payout"]
        if summary.lowest_ask:
            summary.lowest_ask_net_payout = self.calculate_net_payout(summary.lowest_ask)
        return summary
