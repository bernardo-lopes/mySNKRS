import pytest
from snkrs.models import ConditionGrade, BoxCondition, PlatformSummary
from snkrs.valuation import SneakerValuationEngine


def test_deadstock_valuation():
    platforms = {
        "stockx": PlatformSummary(
            platform_name="StockX",
            platform_id="stockx",
            lowest_ask=130.0,
            highest_bid=115.0,
            last_sale_price=125.0,
            seller_fee_percentage=12.0
        ),
        "vinted": PlatformSummary(
            platform_name="Vinted",
            platform_id="vinted",
            lowest_ask=120.0,
            seller_fee_percentage=0.0
        )
    }

    report = SneakerValuationEngine.evaluate(
        sku="DD1391-100",
        size_input="EU 44",
        condition=ConditionGrade.DEADSTOCK,
        box_condition=BoxCondition.ORIGINAL_GOOD,
        platforms_data=platforms,
        currency="USD"
    )

    assert report.stockx_reference_price == 130.0
    assert report.condition_multiplier == 1.00
    assert report.box_multiplier == 1.00
    assert report.currency == "USD"
    assert report.fair_market_price > 0
    assert report.quick_sale_price < report.fair_market_price
    assert report.patient_sale_price > report.fair_market_price


def test_used_sneaker_depreciation_and_best_platform():
    platforms = {
        "stockx": PlatformSummary(
            platform_name="StockX",
            platform_id="stockx",
            lowest_ask=200.0,
            last_sale_price=200.0,
            seller_fee_percentage=12.0
        ),
        "vinted": PlatformSummary(
            platform_name="Vinted",
            platform_id="vinted",
            lowest_ask=130.0,
            seller_fee_percentage=0.0
        ),
        "goat": PlatformSummary(
            platform_name="GOAT",
            platform_id="goat",
            lowest_ask=135.0,
            seller_fee_percentage=12.4,
            seller_fixed_fee=4.5
        )
    }

    # Used sneaker with no box
    report = SneakerValuationEngine.evaluate(
        sku="DZ5485-612",
        size_input="US 10",
        condition=ConditionGrade.USED_GOOD,
        box_condition=BoxCondition.NO_BOX,
        platforms_data=platforms,
        currency="USD"
    )

    # Condition multiplier for used_good should be 0.70
    assert report.condition_multiplier == 0.70
    # Box multiplier for no_box should be 0.80
    assert report.box_multiplier == 0.80
    
    # StockX does not accept used/no-box shoes, so best platform should NOT be StockX
    assert any(name in report.best_platform_to_sell for name in ["Vinted", "GOAT", "eBay"])
