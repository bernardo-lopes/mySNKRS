"""
Sneaker Valuation Engine & Profit Optimizer.
Calculates fair market values, condition depreciation, fee-deducted net profits, and actionable selling strategies.
"""

from typing import Dict, List, Optional, Tuple
import statistics
from .models import (
    ConditionGrade,
    BoxCondition,
    PlatformSummary,
    ValuationReport,
)
from .size_converter import SizeConverter
from .platforms.stockx import CATALOG_BENCHMARKS


class SneakerValuationEngine:
    """Core valuation algorithm and seller recommendation engine."""

    CONDITION_MULTIPLIERS = {
        ConditionGrade.DEADSTOCK: 1.00,
        ConditionGrade.VNDS: 0.91,
        ConditionGrade.USED_LIKE_NEW: 0.82,
        ConditionGrade.USED_GOOD: 0.70,
        ConditionGrade.USED_FAIR: 0.52,
        ConditionGrade.USED_BEAT: 0.35,
    }

    BOX_MULTIPLIERS = {
        BoxCondition.ORIGINAL_GOOD: 1.00,
        BoxCondition.ORIGINAL_DAMAGED: 0.94,
        BoxCondition.REPLACEMENT: 0.88,
        BoxCondition.NO_BOX: 0.80,
    }

    @classmethod
    def evaluate(
        cls,
        sku: str,
        size_input: str,
        condition: ConditionGrade,
        box_condition: BoxCondition,
        platforms_data: Dict[str, PlatformSummary],
        model_name: Optional[str] = None,
        currency: str = "USD",
    ) -> ValuationReport:
        clean_sku = sku.strip().upper()
        norm_size = SizeConverter.normalize(size_input)
        size_us = norm_size["us_m"]
        size_eu = norm_size["eu"]

        # 1. Establish StockX Deadstock reference
        stockx = platforms_data.get("stockx")
        stockx_ref_price: Optional[float] = None
        brand = "Sneakers"
        resolved_name = model_name or f"Sneaker {clean_sku}"
        retail_price = 130.0
        image_url = None

        if stockx and (stockx.lowest_ask or stockx.last_sale_price):
            stockx_ref_price = stockx.lowest_ask or stockx.last_sale_price
        elif clean_sku in CATALOG_BENCHMARKS:
            stockx_ref_price = CATALOG_BENCHMARKS[clean_sku]["base_stockx_ds"]
            resolved_name = CATALOG_BENCHMARKS[clean_sku]["title"]
            brand = CATALOG_BENCHMARKS[clean_sku]["brand"]
            retail_price = CATALOG_BENCHMARKS[clean_sku]["retail_price"]
            image_url = CATALOG_BENCHMARKS[clean_sku].get("image_url")
        else:
            stockx_ref_price = 140.0

        # Check metadata from benchmark if available
        if clean_sku in CATALOG_BENCHMARKS:
            resolved_name = CATALOG_BENCHMARKS[clean_sku]["title"]
            brand = CATALOG_BENCHMARKS[clean_sku]["brand"]
            retail_price = CATALOG_BENCHMARKS[clean_sku]["retail_price"]
            image_url = CATALOG_BENCHMARKS[clean_sku].get("image_url")
        elif "LANEY" in clean_sku or ("LANEY" in (model_name or "").upper()):
            item = CATALOG_BENCHMARKS["FD2596-700"]
            resolved_name = item["title"]
            brand = item["brand"]
            retail_price = item["retail_price"]
            image_url = item.get("image_url")

        # Synced StockX data has the exact product name and photo
        if stockx and stockx.product_title:
            resolved_name = stockx.product_title
        if stockx and stockx.image_url:
            image_url = stockx.image_url

        # 2. Multipliers
        cond_mult = cls.CONDITION_MULTIPLIERS.get(condition, 1.00)
        box_mult = cls.BOX_MULTIPLIERS.get(box_condition, 1.00)

        # Baseline adjusted for condition and box
        adjusted_base = stockx_ref_price * cond_mult * box_mult

        # 3. Market Consensus: collect all platform prices
        active_prices = []
        sold_prices = []
        for pid, pdata in platforms_data.items():
            if not pdata:
                continue
            for l in pdata.listings:
                if l.price > 0:
                    if l.listing_type == "sold":
                        sold_prices.append(l.price)
                    else:
                        active_prices.append(l.price)

        all_market_prices = sold_prices if sold_prices else active_prices
        if not all_market_prices:
            all_market_prices = [adjusted_base]

        # Calculate median market price
        median_market = statistics.median(all_market_prices)

        # Blend baseline with market observations: 60% condition-adjusted baseline + 40% real listings
        fair_market_price = round(0.55 * adjusted_base + 0.45 * median_market, 2)
        quick_sale_price = round(fair_market_price * 0.90, 2)
        patient_sale_price = round(fair_market_price * 1.12, 2)

        est_min = round(fair_market_price * 0.88, 2)
        est_max = round(fair_market_price * 1.15, 2)

        # 4. Confidence Score based on data density
        total_samples = sum(p.sample_count for p in platforms_data.values() if p)
        has_stockx = stockx_ref_price is not None
        confidence = min(98, 45 + (total_samples * 5) + (20 if has_stockx else 0))

        # 5. Net Profit Analysis per platform
        # Calculate take-home payout for each platform at fair market price
        # StockX computes its own payout from the highest bid
        for pid, pdata in platforms_data.items():
            if pdata and pid != "stockx":
                gross = pdata.lowest_ask or fair_market_price
                fee = (gross * (pdata.seller_fee_percentage / 100.0)) + pdata.seller_fixed_fee
                pdata.estimated_net_payout = max(0.0, round(gross - fee, 2))

        # Determine Best Platform to Sell
        best_platform, best_reason = cls._determine_best_platform(
            condition=condition,
            box_condition=box_condition,
            platforms=platforms_data,
            fair_market=fair_market_price
        )

        # 6. Generate Actionable Insights
        insights = cls._generate_insights(
            condition=condition,
            box_condition=box_condition,
            stockx_ref=stockx_ref_price,
            fair_market=fair_market_price,
            platforms=platforms_data,
            best_platform=best_platform
        )

        return ValuationReport(
            sku=clean_sku,
            model_name=resolved_name,
            brand=brand,
            size_input=size_input,
            normalized_size_us=size_us,
            normalized_size_eu=size_eu,
            condition=condition,
            box_condition=box_condition,
            currency=currency,
            image_url=image_url,
            retail_price=retail_price,
            stockx_reference_price=stockx_ref_price,
            condition_multiplier=round(cond_mult, 2),
            box_multiplier=round(box_mult, 2),
            quick_sale_price=quick_sale_price,
            fair_market_price=fair_market_price,
            patient_sale_price=patient_sale_price,
            estimated_range_min=est_min,
            estimated_range_max=est_max,
            confidence_score=confidence,
            platforms=platforms_data,
            best_platform_to_sell=best_platform,
            best_platform_reason=best_reason,
            insights=insights,
        )

    @staticmethod
    def _determine_best_platform(
        condition: ConditionGrade,
        box_condition: BoxCondition,
        platforms: Dict[str, PlatformSummary],
        fair_market: float
    ) -> Tuple[str, str]:
        """Chooses the most advantageous platform for the seller's specific condition and fees."""
        # Safe extractor for platform estimated net payout
        def get_payout(pid: str, default_val: float) -> float:
            p = platforms.get(pid)
            if p and p.estimated_net_payout is not None:
                return p.estimated_net_payout
            return default_val

        # Condition check:
        # StockX strictly requires Deadstock (DS) and original good box.
        if condition != ConditionGrade.DEADSTOCK or box_condition != BoxCondition.ORIGINAL_GOOD:
            # Cannot sell on StockX!
            vinted_payout = get_payout("vinted", fair_market)
            ebay_payout = get_payout("ebay", fair_market * 0.90)
            goat_payout = get_payout("goat", fair_market * 0.86)

            if vinted_payout >= ebay_payout and vinted_payout >= goat_payout:
                return (
                    "Vinted (US)",
                    "StockX does not accept used or damaged-box sneakers. Vinted US gives you 100% of your selling price with 0% seller fees, maximizing your cash payout."
                )
            elif goat_payout >= ebay_payout:
                return (
                    "GOAT (US)",
                    "StockX rejects pre-owned sneakers. GOAT has the highest-trust dedicated Used sneaker market with verified buyers."
                )
            else:
                return (
                    "eBay (US)",
                    "StockX rejects pre-owned sneakers. eBay gives you massive US reach and sneaker Authenticity Guarantee for peace of mind."
                )

        # For Deadstock sneakers:
        stockx_obj = platforms.get("stockx")
        stockx_bid = stockx_obj.highest_bid if stockx_obj else None
        vinted_net = get_payout("vinted", fair_market)
        stockx_net = get_payout("stockx", fair_market * 0.88)

        if vinted_net > stockx_net + 15:
            return (
                "Vinted (US)",
                f"Although StockX is popular, Vinted US charges 0% seller commission compared to StockX's ~12% fee, earning you ~${round(vinted_net - stockx_net, 2)} more net profit!"
            )
        elif stockx_bid and stockx_bid >= fair_market * 0.92:
            return (
                "StockX (US)",
                f"High instant bid available (${stockx_bid})! You can sell immediately with zero messaging or negotiation hassle."
            )
        else:
            return (
                "StockX (US)",
                "Deadstock condition commands the highest price floor and fastest turnover on StockX US."
            )

    @staticmethod
    def _generate_insights(
        condition: ConditionGrade,
        box_condition: BoxCondition,
        stockx_ref: Optional[float],
        fair_market: float,
        platforms: Dict[str, PlatformSummary],
        best_platform: str
    ) -> List[str]:
        insights = []

        # Fee comparison insight
        vinted_summary = platforms.get("vinted")
        stockx_summary = platforms.get("stockx")
        if vinted_summary and stockx_summary:
            v_net = vinted_summary.estimated_net_payout or 0
            s_net = stockx_summary.estimated_net_payout or 0
            if v_net > s_net:
                diff = round(v_net - s_net, 2)
                insights.append(f"💰 **Fee Advantage**: Selling on Vinted US pockets ~${diff} more than StockX due to Vinted's 0% seller fee structure.")

        # Box penalty insight
        if box_condition == BoxCondition.NO_BOX:
            insights.append("📦 **No Box Impact**: Missing the original box reduces sneaker resale value by ~20%. Be sure to disclose this clearly with high-quality photos of inner tags and insole logos.")
        elif box_condition == BoxCondition.ORIGINAL_DAMAGED:
            insights.append("📦 **Box Flaw**: Minor box lid tears or dings reduce value by ~6%. On GOAT you must list this under 'Damaged Box'.")

        # Condition insight
        if condition in [ConditionGrade.USED_GOOD, ConditionGrade.USED_FAIR]:
            insights.append("🧼 **Sneakerhead Tip**: A 15-minute deep clean (cleaning midsoles with Magic Eraser / Jason Markk and un-creasing the toebox with a warm damp cloth & iron) can bump this pair from 'Fair' to 'Good', adding 15-25% to your sale price.")
        elif condition == ConditionGrade.VNDS:
            insights.append("✨ **Near Mint Pair**: Worn once or twice indoors with stars intact can easily sell for 90%+ of Deadstock on eBay and Vinted.")

        # Fast cash option
        if stockx_summary and stockx_summary.highest_bid:
            insights.append(f"⚡ **Instant Cash Out**: StockX currently has active buyer bids ready to buy immediately at ${stockx_summary.highest_bid}.")

        return insights
