"""
providers/nbp_provider.py
--------------------------
Narodowy Bank Polski — Web API (https://api.nbp.pl).
Darmowe, bez rejestracji, bez klucza API.

WAŻNE OGRANICZENIE NBP:
- NBP podaje kursy WYŁĄCZNIE względem PLN (PLN jest niejawną bazą).
  Nie ma sensu pytać NBP o np. USD -> EUR bezpośrednio — trzeba przeliczyć
  przez PLN (cross-rate). Ta klasa robi to automatycznie.
- Tabela A: kursy średnie (jeden kurs, brak spreadu) — aktualizowana raz dziennie
  w dni robocze (ok. 11:45-12:00).
- Tabela C: kursy kupna/sprzedaży (bid/ask) — też raz dziennie, mniej walut.
- Weekendy/święta: brak nowej tabeli, NBP zwraca ostatnią dostępną.
"""

from __future__ import annotations
import requests

from core.provider_base import (
    DataProvider, ProviderCategory, Quote, ProviderUnavailableError
)
from core.cache import cached_quote, cached_historical

NBP_BASE_URL = "https://api.nbp.pl/api/exchangerates/rates"

# Pełna lista walut wspieranych przez tabelę A NBP (stan orientacyjny,
# NBP może dodawać/usuwać waluty — lista służy do wypełnienia GUI).
NBP_TABLE_A_CURRENCIES = [
    "AUD", "BGN", "BRL", "CAD", "CHF", "CLP", "CNY", "CZK", "DKK",
    "EUR", "GBP", "HKD", "HRK", "HUF", "IDR", "ILS", "INR", "ISK",
    "JPY", "KRW", "MXN", "MYR", "NOK", "NZD", "PHP", "PLN", "RON",
    "SEK", "SGD", "THB", "TRY", "UAH", "USD", "XDR", "ZAR",
]


class NBPProvider(DataProvider):
    """Provider danych z Narodowego Banku Polskiego."""

    def __init__(self):
        super().__init__(
            name="NBP (Narodowy Bank Polski)",
            category=ProviderCategory.CENTRAL_BANK,
            suggested_profiles=("Everyday exchange", "Accounting", "Travel", "Business"),
            is_live=True,
            requires_api_key=False,
            description=(
                "Oficjalne kursy referencyjne Narodowego Banku Polskiego. "
                "Tabela A — kursy średnie, aktualizowane raz dziennie w dni robocze. "
                "Wszystkie kursy są publikowane względem PLN."
            ),
        )

    def get_supported_assets(self) -> list[str]:
        return sorted(NBP_TABLE_A_CURRENCIES)

    def _fetch_mid_rate_to_pln(self, code: str) -> float:
        """Zwraca kurs średni (mid) danej waluty do PLN z tabeli A.
        Dla PLN zwraca 1.0 (PLN do PLN)."""
        code = code.upper()
        if code == "PLN":
            return 1.0
        url = f"{NBP_BASE_URL}/A/{code}/today/?format=json"
        try:
            resp = requests.get(url, timeout=8)
        except requests.RequestException as exc:
            raise ProviderUnavailableError(f"NBP: błąd połączenia ({exc})") from exc

        if resp.status_code == 404:
            # Często oznacza, że dzisiejsza tabela nie jest jeszcze opublikowana
            # (np. wczesny ranek) — próbujemy bez /today/, NBP wtedy zwraca
            # ostatnią dostępną tabelę dla danego kodu.
            url_fallback = f"{NBP_BASE_URL}/A/{code}/?format=json"
            resp = requests.get(url_fallback, timeout=8)

        if resp.status_code != 200:
            raise ProviderUnavailableError(
                f"NBP: kod {code} niedostępny (HTTP {resp.status_code}). "
                f"Sprawdź, czy kod waluty jest poprawny."
            )

        data = resp.json()
        try:
            return float(data["rates"][0]["mid"])
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise ProviderUnavailableError(
                f"NBP: nieoczekiwany format odpowiedzi dla {code}"
            ) from exc

    def _fetch_historical_pln(self, code: str, last_n: int = 30) -> list[dict]:
        """Pobiera ostatnie N notowań danej waluty względem PLN."""
        code = code.upper()
        if code == "PLN":
            return [{"effectiveDate": None, "mid": 1.0}] * last_n
            
        url = f"{NBP_BASE_URL}/A/{code}/last/{last_n}/?format=json"
        try:
            resp = requests.get(url, timeout=8)
            if resp.status_code != 200:
                return []
            return resp.json().get("rates", [])
        except Exception:
            return []

    @cached_historical(ttl=3600)
    def get_historical(self, base_symbol: str, quote_symbol: str) -> list[Quote]:
        """Implementacja danych historycznych dla NBP (ostatnie 30 notowań)."""
        base_symbol = base_symbol.upper()
        quote_symbol = quote_symbol.upper()
        
        rates_base = self._fetch_historical_pln(base_symbol)
        rates_quote = self._fetch_historical_pln(quote_symbol)
        
        if not rates_base or not rates_quote:
            raise ProviderUnavailableError(f"NBP: brak danych historycznych dla {base_symbol}/{quote_symbol}")
            
        # NBP może zwrócić różną liczbę notowań jeśli waluta została niedawno dodana
        # Synchronizujemy po datach
        data_base = {r["effectiveDate"]: r["mid"] for r in rates_base}
        data_quote = {r["effectiveDate"]: r["mid"] for r in rates_quote}
        
        common_dates = sorted(set(data_base.keys()) & set(data_quote.keys()))
        if not common_dates:
             # Jeśli jedna z walut to PLN, effectiveDate może być None w moich mockach
             if base_symbol == "PLN":
                 common_dates = sorted(data_quote.keys())
                 data_base = {d: 1.0 for d in common_dates}
             elif quote_symbol == "PLN":
                 common_dates = sorted(data_base.keys())
                 data_quote = {d: 1.0 for d in common_dates}

        quotes = []
        for d in common_dates:
            rate = data_base[d] / data_quote[d]
            quotes.append(Quote(
                provider_name=self.name,
                base_symbol=base_symbol,
                quote_symbol=quote_symbol,
                rate=rate,
                timestamp=d,
                url=f"https://nbp.pl/archiwum-kursow/?data={base_symbol if base_symbol != 'PLN' else quote_symbol}"
            ))
        return quotes

    @cached_quote(ttl=3600)
    def get_quote(self, base_symbol: str, quote_symbol: str) -> Quote:
        base_symbol = base_symbol.upper()
        quote_symbol = quote_symbol.upper()

        # Każdą walutę przeliczamy do PLN, a potem robimy cross-rate.
        base_to_pln = self._fetch_mid_rate_to_pln(base_symbol)
        quote_to_pln = self._fetch_mid_rate_to_pln(quote_symbol)

        if quote_to_pln == 0:
            raise ProviderUnavailableError("NBP: nieprawidłowy kurs (dzielenie przez zero)")

        rate = base_to_pln / quote_to_pln
        
        # Generowanie URL do weryfikacji (dla tabeli A)
        verification_url = None
        if base_symbol != "PLN":
            verification_url = f"https://nbp.pl/archiwum-kursow/?data={base_symbol}" # Uproszczony link do wyszukiwarki NBP
        elif quote_symbol != "PLN":
            verification_url = f"https://nbp.pl/archiwum-kursow/?data={quote_symbol}"

        return Quote(
            provider_name=self.name,
            base_symbol=base_symbol,
            quote_symbol=quote_symbol,
            rate=rate,
            note="Kurs średni (tabela A), przeliczony krzyżowo przez PLN." if "PLN" not in (base_symbol, quote_symbol) else "Kurs średni NBP (tabela A).",
            url=verification_url
        )
