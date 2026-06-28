"""
providers/ecb_provider.py
---------------------------
European Central Bank reference rates, serwowane przez Frankfurter API
(https://api.frankfurter.dev) — darmowe, open-source, bez klucza API.

OGRANICZENIA:
- ECB publikuje rates raz dziennie, ok. 16:00 CET, w dni robocze.
- ~30 głównych walut (nie ma np. egzotycznych par 1:1).
- Frankfurter pozwala podać `base` (walutę odniesienia) bezpośrednio
  w URL, więc — w przeciwieństwie do NBP — nie trzeba liczyć cross-rate
  ręcznie, API robi to za nas.
"""

from __future__ import annotations
import requests

from core.provider_base import (
    DataProvider, ProviderCategory, Quote, ProviderUnavailableError
)
from core.cache import cached_quote, cached_historical

FRANKFURTER_BASE_URL = "https://api.frankfurter.dev/v2"

# Lista walut wspieranych przez Frankfurter/ECB (stan orientacyjny — pobierana
# też dynamicznie przez get_supported_assets, z fallbackiem na tę listę).
ECB_CURRENCIES_FALLBACK = [
    "AUD", "BGN", "BRL", "CAD", "CHF", "CNY", "CZK", "DKK", "EUR", "GBP",
    "HKD", "HUF", "IDR", "ILS", "INR", "ISK", "JPY", "KRW", "MXN", "MYR",
    "NOK", "NZD", "PHP", "PLN", "RON", "SEK", "SGD", "THB", "TRY", "USD",
    "ZAR",
]


class ECBProvider(DataProvider):
    """Provider danych ECB (przez Frankfurter API)."""

    def __init__(self):
        super().__init__(
            name="European Central Bank (Frankfurter)",
            category=ProviderCategory.CENTRAL_BANK,
            suggested_profiles=("Everyday exchange", "Accounting", "Investments", "Business"),
            is_live=True,
            requires_api_key=False,
            description=(
                "Referencyjne kursy Europejskiego Banku Centralnego, serwowane "
                "przez darmowe API Frankfurter. Aktualizacja raz dziennie (~16:00 CET), "
                "brak danych w weekendy/święta ECB."
            ),
        )

    def get_supported_assets(self) -> list[str]:
        try:
            resp = requests.get(f"{FRANKFURTER_BASE_URL}/currencies", timeout=8)
            if resp.status_code == 200:
                return sorted(resp.json().keys())
        except requests.RequestException:
            pass
        return sorted(ECB_CURRENCIES_FALLBACK)

    @cached_historical(ttl=3600)
    def get_historical(self, base_symbol: str, quote_symbol: str) -> list[Quote]:
        """Pobiera ostatnie 30 dni danych historycznych z Frankfurter."""
        base_symbol = base_symbol.upper()
        quote_symbol = quote_symbol.upper()

        # Frankfurter wspiera zakresy dat lub notowania z ostatnich n dni
        # Pobierzmy ostatnie 30 notowań (używając okresu ok 45 dni by mieć pewność 30 dni roboczych)
        url = f"{FRANKFURTER_BASE_URL}/latest?from={base_symbol}&to={quote_symbol}&amount=1"
        # Frankfurter /latest daje tylko dzisiejszy. 
        # Dla historii używamy /[date].. lub /[date]
        # Aby pobrać ostatnie 30 notowań, najprościej użyć zakresu dat.
        import datetime
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=45)
        
        url = f"{FRANKFURTER_BASE_URL}/{start_date}..?from={base_symbol}&to={quote_symbol}"
        
        try:
            resp = requests.get(url, timeout=8)
            if resp.status_code != 200:
                 raise ProviderUnavailableError(f"ECB/Frankfurter: błąd historii HTTP {resp.status_code}")
            data = resp.json()
            rates_dict = data.get("rates", {})
            
            quotes = []
            for date_str, rate_data in rates_dict.items():
                rate = float(rate_data.get(quote_symbol))
                quotes.append(Quote(
                    provider_name=self.name,
                    base_symbol=base_symbol,
                    quote_symbol=quote_symbol,
                    rate=rate,
                    timestamp=date_str,
                    url=f"https://www.frankfurter.app/charts/{base_symbol}{quote_symbol}"
                ))
            return sorted(quotes, key=lambda x: x.timestamp)
        except Exception as exc:
             raise ProviderUnavailableError(f"ECB/Frankfurter: błąd historii ({exc})")

    @cached_quote(ttl=3600)
    def get_quote(self, base_symbol: str, quote_symbol: str) -> Quote:
        base_symbol = base_symbol.upper()
        quote_symbol = quote_symbol.upper()

        if base_symbol == quote_symbol:
            return Quote(
                provider_name=self.name, base_symbol=base_symbol,
                quote_symbol=quote_symbol, rate=1.0,
            )

        url = f"{FRANKFURTER_BASE_URL}/rate/{base_symbol}/{quote_symbol}"
        try:
            resp = requests.get(url, timeout=8)
        except requests.RequestException as exc:
            raise ProviderUnavailableError(f"ECB/Frankfurter: błąd połączenia ({exc})") from exc

        if resp.status_code != 200:
            raise ProviderUnavailableError(
                f"ECB/Frankfurter: para {base_symbol}/{quote_symbol} niedostępna "
                f"(HTTP {resp.status_code})."
            )

        data = resp.json()
        try:
            rate = float(data["rate"])
            date = data.get("date")
        except (KeyError, ValueError, TypeError) as exc:
            raise ProviderUnavailableError(
                "ECB/Frankfurter: nieoczekiwany format odpowiedzi"
            ) from exc

        return Quote(
            provider_name=self.name,
            base_symbol=base_symbol,
            quote_symbol=quote_symbol,
            rate=rate,
            timestamp=date,
            note="Kurs referencyjny ECB (publikacja dzienna).",
            url="https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html"
        )
