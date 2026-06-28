"""
core/currency_list.py
------------------------
Lista walut ISO 4217 (kod -> pełna nazwa PL) do wypełnienia list wyboru w GUI.
Nie wszystkie providery wspierają wszystkie te waluty — GUI filtruje listę
do przecięcia z `provider.get_supported_assets()` po wybraniu konkretnego
źródła danych.
"""

from __future__ import annotations

CURRENCY_NAMES: dict[str, str] = {
    "AUD": "Dolar australijski (AUD)",
    "BGN": "Lew bułgarski (BGN)",
    "BRL": "Real brazylijski (BRL)",
    "CAD": "Dolar kanadyjski (CAD)",
    "CHF": "Frank szwajcarski (CHF)",
    "CLP": "Peso chilijskie (CLP)",
    "CNY": "Yuan chiński (CNY)",
    "CZK": "Korona czeska (CZK)",
    "DKK": "Korona duńska (DKK)",
    "EUR": "Euro (EUR)",
    "GBP": "Funt brytyjski (GBP)",
    "HKD": "Dolar hongkoński (HKD)",
    "HRK": "Kuna chorwacka (HRK)",
    "HUF": "Forint węgierski (HUF)",
    "IDR": "Rupia indonezyjska (IDR)",
    "ILS": "Szekel izraelski (ILS)",
    "INR": "Rupia indyjska (INR)",
    "ISK": "Korona islandzka (ISK)",
    "JPY": "Jen japoński (JPY)",
    "KRW": "Won południowokoreański (KRW)",
    "MXN": "Peso meksykańskie (MXN)",
    "MYR": "Ringgit malezyjski (MYR)",
    "NOK": "Korona norweska (NOK)",
    "NZD": "Dolar nowozelandzki (NZD)",
    "PHP": "Peso filipińskie (PHP)",
    "PLN": "Złoty polski (PLN)",
    "RON": "Lej rumuński (RON)",
    "SEK": "Korona szwedzka (SEK)",
    "SGD": "Dolar singapurski (SGD)",
    "THB": "Bat tajski (THB)",
    "TRY": "Lira turecka (TRY)",
    "UAH": "Hrywna ukraińska (UAH)",
    "USD": "Dolar amerykański (USD)",
    "XDR": "SDR MFW (XDR)",
    "ZAR": "Rand południowoafrykański (ZAR)",
}


def format_currency_label(code: str) -> str:
    """Zwraca etykietę do wyświetlenia w GUI, np. 'Euro (EUR)'."""
    return CURRENCY_NAMES.get(code.upper(), code.upper())


def all_currency_codes_sorted() -> list[str]:
    """Wszystkie znane kody walut, sortowane alfabetycznie po kodzie."""
    return sorted(CURRENCY_NAMES.keys())
