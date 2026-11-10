from datetime import date

import pytest

from mijnarchief.formatting import (
    format_amount, format_amount_plain, format_date_long, format_date_short, parse_amount, warranty_status,
)


@pytest.mark.parametrize("text, value", [
    ("", None), ("  ", None), ("12,50", 12.5), ("1.149,00", 1149.0), ("1149.5", 1149.5),
    ("€ 87,30", 87.3), ("1.000", 1000.0), ("1,000.25", 1000.25), ("-5", -5.0), ("0", 0.0),
])
def test_parse_amount(text, value):
    assert parse_amount(text) == value


@pytest.mark.parametrize("text", ["abc", "1,2,3", "12.5.6,7x"])
def test_parse_amount_invalid(text):
    with pytest.raises(ValueError):
        parse_amount(text)


def test_format_amount():
    assert format_amount(1149) == "€ 1.149,00"
    assert format_amount(64.12) == "€ 64,12"
    assert format_amount(None) == "—"
    assert format_amount_plain(87.3) == "87,30"


def test_dates():
    today = date(2026, 11, 10)
    assert format_date_long("2026-09-03") == "3 september 2026"
    assert format_date_short("2026-09-03", today) == "3 sep"
    assert format_date_short("2025-12-02", today) == "2 dec 2025"


def test_warranty_status():
    today = date(2026, 11, 10)
    assert warranty_status(None, today) is None
    assert warranty_status("2031-09-03", today) == ("ok", "Garantie t/m september 2031")
    assert warranty_status("2026-12-20", today) == ("warn", "Garantie nog 40 dagen")
    assert warranty_status("2026-11-11", today) == ("warn", "Garantie nog 1 dag")
    assert warranty_status("2026-01-01", today)[0] == "bad"
