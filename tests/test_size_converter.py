import pytest
from snkrs.size_converter import SizeConverter
from snkrs.models import SizeSystem


def test_parse_explicit_systems():
    sys, val = SizeConverter.parse_size_string("US 10")
    assert sys == SizeSystem.US_MEN
    assert val == 10.0

    sys, val = SizeConverter.parse_size_string("EU 44")
    assert sys == SizeSystem.EU
    assert val == 44.0

    sys, val = SizeConverter.parse_size_string("UK 9.5")
    assert sys == SizeSystem.UK
    assert val == 9.5

    sys, val = SizeConverter.parse_size_string("US W 8.5")
    assert sys == SizeSystem.US_WOMEN
    assert val == 8.5


def test_implicit_inference():
    # If number >= 35, infer EU
    sys, val = SizeConverter.parse_size_string("42.5")
    assert sys == SizeSystem.EU
    assert val == 42.5

    # If number < 35, infer US Men
    sys, val = SizeConverter.parse_size_string("10.5")
    assert sys == SizeSystem.US_MEN
    assert val == 10.5


def test_normalize():
    norm = SizeConverter.normalize("EU 44")
    assert norm["us_m"] == 10.0
    assert norm["eu"] == 44.0
    assert norm["uk"] == 9.0

    norm_us = SizeConverter.normalize("US 10")
    assert norm_us["eu"] == 44.0
