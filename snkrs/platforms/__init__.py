"""
Marketplace Platform Connectors.
"""

from .base import BaseMarketplace
from .stockx import StockXMarketplace
from .goat import GoatMarketplace
from .ebay import EbayMarketplace
from .vinted import VintedMarketplace
from .aggregator import MarketplaceAggregator

__all__ = [
    "BaseMarketplace",
    "StockXMarketplace",
    "GoatMarketplace",
    "EbayMarketplace",
    "VintedMarketplace",
    "MarketplaceAggregator",
]
