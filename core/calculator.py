"""
core/calculator.py
---------------------
Logika "Currency Calculator" — łączy wybrany provider z listą walut do
porównania i zwraca gotowe wyniki (lub czytelne błędy) dla GUI.

GUI nie powinno bezpośrednio wołać providerów — zawsze przez tę warstwę,
żeby błędy sieciowe/API były jednolicie obsłużone i sformatowane.
"""

from __future__ import annotations
from dataclasses import dataclass

from core.provider_base import DataProvider, Quote, ProviderUnavailableError


@dataclass
class ComparisonResult:
    """Wynik przeliczenia jednej waluty porównawczej."""
    quote_symbol: str
    success: bool
    rate: float | None = None
    converted_amount: float | None = None
    error_message: str | None = None
    note: str | None = None
    timestamp: str | None = None
    url: str | None = None


def run_comparison(
    provider: DataProvider,
    main_currency: str,
    amount: float,
    comparison_currencies: list[str],
) -> list[ComparisonResult]:
    """
    Dla danego providera i kwoty w main_currency, pobiera kurs do każdej
    z walut porównawczych i przelicza kwotę.

    Waluty puste/None w comparison_currencies są ignorowane (użytkownik może
    nie wypełnić wszystkich 5 komórek).
    """
    results: list[ComparisonResult] = []

    for quote_symbol in comparison_currencies:
        if not quote_symbol:
            continue

        if quote_symbol.upper() == main_currency.upper():
            results.append(ComparisonResult(
                quote_symbol=quote_symbol,
                success=True,
                rate=1.0,
                converted_amount=amount,
                note="Waluta główna i porównawcza są identyczne.",
            ))
            continue

        try:
            quote: Quote = provider.get_quote(main_currency, quote_symbol)
            results.append(ComparisonResult(
                quote_symbol=quote_symbol,
                success=True,
                rate=quote.rate,
                converted_amount=amount * quote.rate,
                note=quote.note,
                timestamp=quote.timestamp,
                url=quote.url,
            ))
        except ProviderUnavailableError as exc:
            results.append(ComparisonResult(
                quote_symbol=quote_symbol,
                success=False,
                error_message=str(exc),
            ))
        except Exception as exc:  # noqa: BLE001 — chcemy złapać też nieoczekiwane błędy
            results.append(ComparisonResult(
                quote_symbol=quote_symbol,
                success=False,
                error_message=f"Nieoczekiwany błąd: {exc}",
            ))

    return results
