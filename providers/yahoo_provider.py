"""
providers/yahoo_provider.py
-----------------------------
Yahoo Finance — przez bibliotekę `yfinance` (nieoficjalny, ale szeroko używany
wrapper). Dane "rynkowe" (Financial Markets), zbliżone do międzybankowych /
Forex, z opóźnieniem typowym dla darmowych feedów (kilkanaście minut).

WAŻNE:
- yfinance nie wymaga klucza API, ale zależy od nieoficjalnego, niezadokumentowanego
  endpointu Yahoo — może się czasem wywalić, jeśli Yahoo zmieni coś po swojej stronie.
  Stąd owijamy wszystko w try/except i podnosimy ProviderUnavailableError.
- Tickery walutowe w Yahoo Finance: "{BASE}{QUOTE}=X" (np. "EURUSD=X" = ile USD
  za 1 EUR). Dla par z USD jako bazą czasem wystarczy "{QUOTE}=X" — ale
  "{BASE}{QUOTE}=X" działa konsekwentnie dla większości par, więc używamy tego
  wzorca, a w razie niepowodzenia próbujemy odwrotnej pary i odwracamy wynik.
- Ten sam provider jest też używany jako backend modułu "Other Assets"
  (akcje/krypto/metale) — patrz assets/yahoo_assets.py.
"""

from __future__ import annotations

from core.provider_base import (
    DataProvider, ProviderCategory, Quote, ProviderUnavailableError
)
from core.cache import cached_quote, cached_historical

# Popularne waluty wspierane jako pary FX na Yahoo Finance.
YAHOO_FX_CURRENCIES = [
    "AUD", "BRL", "CAD", "CHF", "CNY", "CZK", "DKK", "EUR", "GBP", "HKD",
    "HUF", "IDR", "ILS", "INR", "JPY", "KRW", "MXN", "MYR", "NOK", "NZD",
    "PHP", "PLN", "RON", "SEK", "SGD", "THB", "TRY", "USD", "ZAR",
]


class YahooFinanceProvider(DataProvider):
    """Provider danych FX z Yahoo Finance (przez yfinance)."""

    def __init__(self):
        super().__init__(
            name="Yahoo Finance",
            category=ProviderCategory.FINANCIAL_MARKET,
            suggested_profiles=("Investments", "Research", "Business"),
            is_live=True,
            requires_api_key=False,
            description=(
                "Kursy rynkowe z Yahoo Finance (dane z typowym opóźnieniem "
                "kilkunastu minut dla darmowego dostępu). Wymaga biblioteki "
                "'yfinance' (pip install yfinance)."
            ),
        )

    def get_supported_assets(self) -> list[str]:
        return sorted(YAHOO_FX_CURRENCIES)

    def _import_yfinance(self):
        try:
            import yfinance as yf
            return yf
        except ImportError as exc:
            raise ProviderUnavailableError(
                "Yahoo Finance: biblioteka 'yfinance' nie jest zainstalowana. "
                "Zainstaluj ją przez: pip install yfinance"
            ) from exc

    def _fetch_ticker_last_price(self, yf_module, ticker: str) -> float | None:
        """Próbuje pobrać ostatnią cenę dla danego tickera. Zwraca None, jeśli
        ticker nie istnieje / brak danych (a NIE jeśli to błąd sieci — ten
        propagujemy wyżej)."""
        try:
            data = yf_module.Ticker(ticker).history(period="5d", interval="1d")
            if data is None or data.empty:
                return None
            return float(data["Close"].dropna().iloc[-1])
        except Exception:
            return None

    @cached_historical(ttl=3600)
    def get_historical(self, base_symbol: str, quote_symbol: str,
                       period: str = "1mo") -> list[Quote]:
        """
        Pobiera dane historyczne z Yahoo Finance.
        period: "1mo", "3mo", "1y", "5y", "max" itp.
        """
        base_symbol = base_symbol.upper()
        quote_symbol = quote_symbol.upper()
        yf = self._import_yfinance()

        ticker = f"{base_symbol}{quote_symbol}=X"
        data = yf.Ticker(ticker).history(period=period)
        
        invert = False
        if data.empty:
            ticker = f"{quote_symbol}{base_symbol}=X"
            data = yf.Ticker(ticker).history(period=period)
            invert = True
            
        if data.empty:
            raise ProviderUnavailableError(f"Yahoo Finance: brak danych historycznych dla {base_symbol}/{quote_symbol}")

        quotes = []
        for timestamp, row in data.iterrows():
            rate = float(row["Close"])
            if invert and rate > 0:
                rate = 1.0 / rate
            
            quotes.append(Quote(
                provider_name=self.name,
                base_symbol=base_symbol,
                quote_symbol=quote_symbol,
                rate=rate,
                timestamp=str(timestamp.date()),
                url=f"https://finance.yahoo.com/quote/{ticker}"
            ))
        return quotes

    @cached_quote(ttl=300)
    def get_quote(self, base_symbol: str, quote_symbol: str) -> Quote:
        base_symbol = base_symbol.upper()
        quote_symbol = quote_symbol.upper()

        if base_symbol == quote_symbol:
            return Quote(
                provider_name=self.name, base_symbol=base_symbol,
                quote_symbol=quote_symbol, rate=1.0,
            )

        yf = self._import_yfinance()

        # Próba 1: ticker BASEQUOTE=X -> ile QUOTE za 1 BASE
        direct_ticker = f"{base_symbol}{quote_symbol}=X"
        price = self._fetch_ticker_last_price(yf, direct_ticker)
        if price is not None and price > 0:
            return Quote(
                provider_name=self.name, base_symbol=base_symbol,
                quote_symbol=quote_symbol, rate=price,
                note=f"Yahoo Finance, ticker {direct_ticker} (dane dzienne, z opóźnieniem).",
                url=f"https://finance.yahoo.com/quote/{direct_ticker}"
            )

        # Próba 2: odwrotny ticker QUOTEBASE=X -> odwracamy wynik
        inverse_ticker = f"{quote_symbol}{base_symbol}=X"
        inverse_price = self._fetch_ticker_last_price(yf, inverse_ticker)
        if inverse_price is not None and inverse_price > 0:
            return Quote(
                provider_name=self.name, base_symbol=base_symbol,
                quote_symbol=quote_symbol, rate=1.0 / inverse_price,
                note=f"Yahoo Finance, odwrócony ticker {inverse_ticker}.",
                url=f"https://finance.yahoo.com/quote/{inverse_ticker}"
            )

        raise ProviderUnavailableError(
            f"Yahoo Finance: nie znaleziono danych dla pary "
            f"{base_symbol}/{quote_symbol} (sprawdzono {direct_ticker} i {inverse_ticker})."
        )
