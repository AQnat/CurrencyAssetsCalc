"""
assets/yahoo_assets.py
-------------------------
Jedyny W PEŁNI DZIAŁAJĄCY backend modułu "Other Assets" w wersji 1.
Pokrywa 4 kategorie naraz, bo Yahoo Finance używa jednego, konsekwentnego
systemu tickerów:

    Akcje        -> zwykły ticker giełdowy, np. "AAPL", "CDR.WA" (CD Projekt na GPW)
    Krypto       -> "{SYMBOL}-USD", np. "BTC-USD", "ETH-USD"
    Surowce      -> "{KOD}=F" (kontrakty futures), np. "CL=F" (ropa WTI)
    Metale       -> również "{KOD}=F", np. "GC=F" (złoto), "SI=F" (srebro)

To jest świadomie OKROJONA implementacja (krótka lista przykładowych symboli,
nie cała giełda) — pełne wyszukiwanie tickerów to praca na kolejny etap.
"""

from __future__ import annotations

import requests

from assets.asset_provider_base import (
    AssetProvider, AssetCategory, AssetQuote, AssetSearchResult, AssetUnavailableError,
    PlaceholderAssetProvider
)

YAHOO_SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"
CRYPTO_ENGINE_MAP = {
    # Bazowe coiny/sieci
    "BTC": "BTC",
    "ETH": "ETH",
    "SOL": "SOL",
    "XRP": "XRP",
    "ADA": "ADA",
    "DOGE": "DOGE",
    "DOT": "DOT",
    "MATIC": "MATIC",
    "AVAX": "AVAX",
    "BNB": "BNB",
    "LINK": "LINK",
    # Przykładowe mniejsze coiny i ich silnik bazowy
    "GRASS": "SOL",
    "JESUS": "BTC",
}
CRYPTO_PROTOCOL_MAP = {
    "BTC": "BTC",
    "ETH": "ERC20",
    "SOL": "SPL",
    "XRP": "XRP Ledger",
    "ADA": "Cardano Native",
    "DOGE": "DOGE",
    "DOT": "Polkadot",
    "MATIC": "ERC20 (Polygon)",
    "AVAX": "AVAX C-Chain",
    "BNB": "BEP20",
    "LINK": "ERC20",
    "GRASS": "SPL",
    "JESUS": "BRC20",
}


def _import_yfinance():
    try:
        import yfinance as yf
        return yf
    except ImportError as exc:
        raise AssetUnavailableError(
            "Ten moduł wymaga biblioteki 'yfinance'. Zainstaluj: pip install yfinance"
        ) from exc


def _fetch_last_price_and_currency(yf_module, ticker: str) -> tuple[float, str]:
    t = yf_module.Ticker(ticker)
    hist = t.history(period="5d", interval="1d")
    if hist is None or hist.empty:
        raise AssetUnavailableError(f"Brak danych dla symbolu '{ticker}'.")
    price = float(hist["Close"].dropna().iloc[-1])

    currency = "USD"
    try:
        info = t.fast_info
        currency = getattr(info, "currency", None) or currency
    except Exception:
        pass

    return price, currency


def _fetch_historical(yf_module, ticker: str, provider_name: str, period: str = "1mo") -> list[AssetQuote]:
    t = yf_module.Ticker(ticker)
    data = t.history(period=period)
    if data.empty:
        raise AssetUnavailableError(f"Brak danych historycznych dla symbolu '{ticker}'.")
        
    currency = "USD"
    try:
        currency = getattr(t.fast_info, "currency", None) or currency
    except Exception:
        pass
        
    quotes = []
    for timestamp, row in data.iterrows():
        quotes.append(AssetQuote(
            provider_name=provider_name,
            symbol=ticker,
            display_name=ticker,
            price=float(row["Close"]),
            currency=currency,
            timestamp=str(timestamp.date()),
            url=f"https://finance.yahoo.com/quote/{ticker}"
        ))
    return quotes


def _search_yahoo(query: str, *, quote_types: set[str] | None = None, limit: int = 15) -> list[AssetSearchResult]:
    query = query.strip()
    if len(query) < 2:
        return []

    try:
        response = requests.get(
            YAHOO_SEARCH_URL,
            params={"q": query, "quotesCount": max(5, min(limit * 2, 40)), "newsCount": 0},
            timeout=8,
        )
    except requests.RequestException:
        return []

    if response.status_code != 200:
        return []

    payload = response.json() if response.content else {}
    out: list[AssetSearchResult] = []
    for item in payload.get("quotes", []):
        symbol = str(item.get("symbol", "")).strip().upper()
        name = str(item.get("shortname") or item.get("longname") or symbol).strip()
        quote_type = str(item.get("quoteType", "")).upper()
        if not symbol:
            continue
        if quote_types and quote_type not in quote_types:
            continue
        out.append(AssetSearchResult(source="Yahoo Finance", symbol=symbol, display_name=name))
        if len(out) >= limit:
            break
    return out


class YahooStocksProvider(AssetProvider):
    def __init__(self):
        super().__init__(name="Yahoo Finance — Stocks", category=AssetCategory.STOCKS)

    def get_example_symbols(self) -> dict[str, str]:
        return {
            "AAPL": "Apple Inc. (AAPL)",
            "MSFT": "Microsoft Corp. (MSFT)",
            "GOOGL": "Alphabet Inc. (GOOGL)",
            "NVDA": "NVIDIA Corp. (NVDA)",
            "AMZN": "Amazon.com Inc. (AMZN)",
            "CDR.WA": "CD Projekt S.A. (GPW: CDR)",
            "PKO.WA": "PKO BP S.A. (GPW: PKO)",
        }

    def get_quote(self, symbol: str) -> AssetQuote:
        yf = _import_yfinance()
        symbol = self.normalize_symbol(symbol)
        price, currency = _fetch_last_price_and_currency(yf, symbol)
        return AssetQuote(
            provider_name=self.name, symbol=symbol, display_name=symbol,
            price=price, currency=currency,
            note="Cena zamknięcia z ostatniej sesji (dane dzienne, z opóźnieniem).",
            url=f"https://finance.yahoo.com/quote/{symbol}"
        )

    def get_historical(self, symbol: str, period: str = "1mo") -> list[AssetQuote]:
        yf = _import_yfinance()
        return _fetch_historical(yf, self.normalize_symbol(symbol), self.name, period)

    def search_assets(self, query: str, limit: int = 15) -> list[AssetSearchResult]:
        return _search_yahoo(query, quote_types={"EQUITY", "ETF"}, limit=limit)


class YahooCryptoProvider(AssetProvider):
    def __init__(self):
        super().__init__(name="Yahoo Finance — Crypto", category=AssetCategory.CRYPTO)

    def get_example_symbols(self) -> dict[str, str]:
        return {
            "BTC-USD": "Bitcoin (BTC/USD)",
            "ETH-USD": "Ethereum (ETH/USD)",
            "SOL-USD": "Solana (SOL/USD)",
            "XRP-USD": "Ripple (XRP/USD)",
            "ADA-USD": "Cardano (ADA/USD)",
            "DOGE-USD": "Dogecoin (DOGE/USD)",
            "DOT-USD": "Polkadot (DOT/USD)",
            "MATIC-USD": "Polygon (MATIC/USD)",
            "AVAX-USD": "Avalanche (AVAX/USD)",
            "BNB-USD": "BNB (BNB/USD)",
            "LINK-USD": "Chainlink (LINK/USD)",
            "GRASS-USD": "Grass (GRASS/USD)",
            "JESUS-USD": "Jesus Coin (JESUS/USD)",
        }

    def get_quote(self, symbol: str) -> AssetQuote:
        yf = _import_yfinance()
        symbol = self.normalize_symbol(symbol)
        price, currency = _fetch_last_price_and_currency(yf, symbol)
        return AssetQuote(
            provider_name=self.name, symbol=symbol, display_name=symbol,
            price=price, currency=currency,
            note="Krypto handlowane 24/7 — cena może być nieco opóźniona względem giełd live.",
            url=f"https://finance.yahoo.com/quote/{symbol}"
        )

    def get_historical(self, symbol: str, period: str = "1mo") -> list[AssetQuote]:
        yf = _import_yfinance()
        symbol = self.normalize_symbol(symbol)
        return _fetch_historical(yf, symbol, self.name, period)

    def normalize_symbol(self, symbol: str) -> str:
        normalized = symbol.strip().upper()
        if "-" not in normalized:
            return f"{normalized}-USD"
        return normalized

    def search_assets(self, query: str, limit: int = 15) -> list[AssetSearchResult]:
        query = query.strip()
        results = _search_yahoo(query, quote_types={"CRYPTOCURRENCY"}, limit=limit)
        if not results:
            # Yahoo nie zawsze opisuje altcoiny jako CRYPTOCURRENCY, więc fallback jest szerszy.
            all_hits = _search_yahoo(query, quote_types=None, limit=max(limit * 2, 20))
            for hit in all_hits:
                symbol = hit.symbol.upper()
                if symbol.endswith("-USD") or query.upper() in symbol or query.lower() in hit.display_name.lower():
                    results.append(hit)
                if len(results) >= limit:
                    break
        if not results and query:
            results = [
                AssetSearchResult(
                    source=self.name,
                    symbol=self.normalize_symbol(query),
                    display_name=f"{query.upper()} (manual candidate)",
                    note="Brak pewnego dopasowania, ale symbol mozna dodac recznie",
                )
            ]
        for row in results:
            base = row.symbol.split("-")[0]
            row.engine = CRYPTO_ENGINE_MAP.get(base, base)
            row.protocol = CRYPTO_PROTOCOL_MAP.get(base, row.engine)
            row.note = f"Engine: {row.engine}"
        return results


class YahooCommoditiesProvider(AssetProvider):
    def __init__(self):
        super().__init__(name="Yahoo Finance — Commodities", category=AssetCategory.COMMODITIES)

    def get_example_symbols(self) -> dict[str, str]:
        return {
            # Energia
            "CL=F":  "Ropa WTI (Crude Oil futures)",
            "BZ=F":  "Ropa Brent (Brent Crude futures)",
            "NG=F":  "Gaz ziemny (Natural Gas futures)",
            "MTF=F": "Węgiel (Rotterdam Coal futures)",
            # Rolnicze
            "ZW=F":  "Pszenica (Wheat futures)",
            "ZC=F":  "Kukurydza (Corn futures)",
            "ZS=F":  "Soja (Soybeans futures)",
            "KC=F":  "Kawa (Coffee C futures)",
            "CC=F":  "Kakao (Cocoa futures)",
            "CT=F":  "Bawełna (Cotton No.2 futures)",
            "SB=F":  "Cukier (Sugar No.11 futures)",
            # Przemysłowe
            "LBS=F": "Drewno (Lumber futures)",
            "HRC=F": "Stal (US Steel HRC futures)",
        }

    def get_quote(self, symbol: str) -> AssetQuote:
        yf = _import_yfinance()
        symbol = self.normalize_symbol(symbol)
        price, currency = _fetch_last_price_and_currency(yf, symbol)
        return AssetQuote(
            provider_name=self.name, symbol=symbol, display_name=symbol,
            price=price, currency=currency,
            note="Cena kontraktu futures (nie cena spot) — może odbiegać od ceny fizycznej.",
            url=f"https://finance.yahoo.com/quote/{symbol}"
        )

    def get_historical(self, symbol: str, period: str = "1mo") -> list[AssetQuote]:
        yf = _import_yfinance()
        return _fetch_historical(yf, self.normalize_symbol(symbol), self.name, period)

    def search_assets(self, query: str, limit: int = 15) -> list[AssetSearchResult]:
        return _search_yahoo(query, quote_types={"FUTURE"}, limit=limit)


class YahooMetalsProvider(AssetProvider):
    def __init__(self):
        super().__init__(name="Yahoo Finance — Metals", category=AssetCategory.METALS)

    def get_example_symbols(self) -> dict[str, str]:
        return {
            # Metale szlachetne
            "GC=F": "Złoto (Gold futures)",
            "SI=F": "Srebro (Silver futures)",
            "PL=F": "Platyna (Platinum futures)",
            "PA=F": "Pallad (Palladium futures)",
            # Metale przemysłowe
            "HG=F": "Miedź (Copper futures)",
            "ALI=F": "Aluminium (Aluminium futures)",
        }

    def get_quote(self, symbol: str) -> AssetQuote:
        yf = _import_yfinance()
        symbol = self.normalize_symbol(symbol)
        price, currency = _fetch_last_price_and_currency(yf, symbol)
        return AssetQuote(
            provider_name=self.name, symbol=symbol, display_name=symbol,
            price=price, currency=currency,
            note="Cena kontraktu futures na metal (nie fizyczny kurs kruszcu).",
            url=f"https://finance.yahoo.com/quote/{symbol}"
        )

    def get_historical(self, symbol: str, period: str = "1mo") -> list[AssetQuote]:
        yf = _import_yfinance()
        return _fetch_historical(yf, self.normalize_symbol(symbol), self.name, period)

    def search_assets(self, query: str, limit: int = 15) -> list[AssetSearchResult]:
        return _search_yahoo(query, quote_types={"FUTURE"}, limit=limit)


# Rejestr modułu assets — analogicznie do providers/registry.py
ALL_ASSET_PROVIDERS: list[AssetProvider] = [
    YahooStocksProvider(),
    YahooCryptoProvider(),
    YahooCommoditiesProvider(),
    YahooMetalsProvider(),

    # --- STOCK MARKETS ---
    PlaceholderAssetProvider("Alpha Vantage", AssetCategory.STOCKS, "Wymaga darmowego klucza API. Alpha Vantage oferuje szeroki zakres danych giełdowych i wskaźników ekonomicznych."),
    PlaceholderAssetProvider("Polygon.io", AssetCategory.STOCKS, "Wymaga klucza API. Polygon zapewnia dane rynkowe w czasie rzeczywistym i historyczne dla akcji, krypto i walut."),
    PlaceholderAssetProvider("Twelve Data", AssetCategory.STOCKS, "Wymaga klucza API. Twelve Data oferuje globalne dane rynkowe z niskimi opóźnieniami."),
    PlaceholderAssetProvider("Finnhub", AssetCategory.STOCKS, "Wymaga klucza API. Finnhub dostarcza dane o akcjach, walutach i krypto oraz analizy finansowe."),
    PlaceholderAssetProvider("EODHD", AssetCategory.STOCKS, "Wymaga klucza API. EOD Historical Data oferuje szerokie pokrycie rynków światowych."),

    # --- METALS (precious + industrial) ---
    PlaceholderAssetProvider("GoldAPI.io", AssetCategory.METALS, "Wymaga klucza API. Dedykowane API dla cen spot metali szlachetnych (Gold, Silver, Platinum, Palladium)."),
    PlaceholderAssetProvider("MetalPriceAPI", AssetCategory.METALS, "Wymaga klucza API. Real-time metal prices i dane historyczne."),
    PlaceholderAssetProvider("London Metal Exchange (LME)", AssetCategory.METALS, "Dostęp do oficjalnych cen metali przemysłowych zwykle wymaga płatnej subskrypcji/B2B."),
    PlaceholderAssetProvider("CME Group Metals", AssetCategory.METALS, "Dane futures metali (m.in. Copper, Gold) dostępne przez CME DataMine / partnerów."),
    PlaceholderAssetProvider("Nasdaq Data Link (Quandl) — Metals", AssetCategory.METALS, "Wymaga klucza API. Zbiory metali przemysłowych i szlachetnych."),

    # --- CRYPTO ---
    PlaceholderAssetProvider("CoinMarketCap", AssetCategory.CRYPTO, "Wymaga klucza API. Standard rynkowy dla kapitalizacji i cen kryptowalut."),

    # --- COMMODITIES (energy/agri/industrial) ---
    PlaceholderAssetProvider("Trading Economics", AssetCategory.COMMODITIES, "Wymaga subskrypcji API. Szerokie dane makroekonomiczne i ceny towarów."),
    PlaceholderAssetProvider("CME Group Commodities", AssetCategory.COMMODITIES, "Dane futures: energia, rolnictwo, metale; pełny dostęp zwykle płatny."),
    PlaceholderAssetProvider("Nasdaq Data Link (Quandl)", AssetCategory.COMMODITIES, "Wymaga klucza API. Profesjonalne zbiory danych finansowych i ekonomicznych."),
]
