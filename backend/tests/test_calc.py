from datetime import date

import pytest

from app import calc


def test_celsius_to_kelvin():
    assert calc.celsius_to_kelvin(0) == 273.15
    assert calc.celsius_to_kelvin(16) == 289.15


def test_kelvin_to_celsius():
    assert calc.kelvin_to_celsius(289.15) == 16.0


def test_celsius_to_fahrenheit():
    assert calc.celsius_to_fahrenheit(0) == 32.0
    assert calc.celsius_to_fahrenheit(100) == 212.0


def test_nights_between_strings():
    assert calc.nights_between("2026-07-10", "2026-07-12") == 2


def test_nights_between_dates():
    assert calc.nights_between(date(2026, 8, 1), date(2026, 8, 5)) == 4


def test_nights_between_invalid():
    with pytest.raises(ValueError):
        calc.nights_between("2026-07-12", "2026-07-10")


def test_format_price_eur():
    assert calc.format_price_eur(15) == "15,00 €"
    assert calc.format_price_eur(1234.5) == "1.234,50 €"


def test_total_price():
    assert calc.total_price(100.0, "2026-07-10", "2026-07-12") == 200.0
