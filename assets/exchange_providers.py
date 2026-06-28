"""
assets/exchange_providers.py
-------------------------------
Implementacje dostawców danych dla giełd kryptowalut i indeksów metali/surowców.

Działają BEZ klucza API:
  - KrakenCryptoProvider  -> api.kraken.com (publiczne REST API, brak wymaganego klucza)
  - CoinbaseCryptoProvider -> api.coinbase.com v2 (publiczne ceny spot)
  - CoinPaprikaCryptoProvider -> api.coinpaprika.com (darmowe, brak klucza)
"""

from __future__ import annotations

import requests

from assets.asset_provider_base import (
    AssetCategory,
    AssetProvider,
    AssetQuote,
    AssetSearchResult,
    AssetUnavailableError,
)

# ──────────────────────────────────────────────
# Stałe API
# ──────────────────────────────────────────────
KRAKEN_API   = "https://api.kraken.com/0/public"
COINBASE_API = "https://api.coinbase.com/v2"
PAPRIKA_API  = "https://api.coinpaprika.com/v1"

# Mapowanie symbol -> para Kraken (Kraken używa XBT dla BTC)
_KRAKEN_PAIR_MAP: dict[str, str] = {
    "BTC":  "XBTUSD",
    "ETH":  "ETHUSD",
    "SOL":  "SOLUSD",
    "XRP":  "XRPUSD",
    "ADA":  "ADAUSD",
    "DOGE": "DOGEUSD",
    "DOT":  "DOTUSD",
    "MATIC":"MATICUSD",
    "AVAX": "AVAXUSD",
    "LINK": "LINKUSD",
    "LTC":  "LTCUSD",
    "BCH":  "BCHUSD",
    "ATOM": "ATOMUSD",
    "UNI":  "UNIUSD",
    "AAVE": "AAVEUSD",
}

# Mapowanie base -> id CoinPaprika
_PAPRIKA_ID_MAP: dict[str, str] = {
    "BTC":  "btc-bitcoin",
    "ETH":  "eth-ethereum",
    "SOL":  "sol-solana",
    "XRP":  "xrp-xrp",
    "ADA":  "ada-cardano",
    "DOGE": "doge-dogecoin",
    "DOT":  "dot-polkadot",
    "MATIC":"matic-polygon",
    "AVAX": "avax-avalanche",
    "BNB":  "bnb-binance-coin",
    "LINK": "link-chainlink",
    "LTC":  "ltc-litecoin",
    "BCH":  "bch-bitcoin-cash",
    "ATOM": "atom-cosmos",
    "UNI":  "uni-uniswap",
    "AAVE": "aave-new",
    "SHIB": "shib-shiba-inu",
    "TRX":  "trx-tron",
    "TON":  "ton-the-open-network",
    "SUI":  "sui-sui",
}


class KrakenCryptoProvider(AssetProvider):
    """
    Giełda Kraken — ceny spot kryptowalut.
    Publiczne REST API, nie wymaga klucza API.
    Dokumentacja: https://docs.kraken.com/api/docs/rest-api/get-ticker-information
    """

    def __init__(self):
        super().__init__(
            name="Kraken",
            category=AssetCategory.CRYPTO,
            is_live=True,
            requires_api_key=False,
        )
        self._pairs_cache: dict[str, str] | None = None

    # ------------------------------------------------------------------
    def get_example_symbols(self) -> dict[str, str]:
        return {
            "BTC-USD": "Bitcoin (BTC/USD on Kraken)",
            "ETH-USD": "Ethereum (ETH/USD on Kraken)",
            "SOL-USD": "Solana (SOL/USD on Kraken)",
            "XRP-USD": "XRP (XRP/USD on Kraken)",
            "ADA-USD": "Cardano (ADA/USD on Kraken)",
            "DOGE-USD": "Dogecoin (DOGE/USD on Kraken)",
            "LINK-USD": "Chainlink (LINK/USD on Kraken)",
            "DOT-USD": "Polkadot (DOT/USD on Kraken)",
            "LTC-USD": "Litecoin (LTC/USD on Kraken)",
        }

    def normalize_symbol(self, symbol: str) -> str:
        normalized = symbol.strip().upper()
        if "-" not in normalized:
            return f"{normalized}-USD"
        return normalized

    def _to_kraken_pair(self, symbol: str) -> str:
        """Zamienia 'BTC-USD' na parę Kraken, np. 'XBTUSD'."""
        base = self.normalize_symbol(symbol).split("-")[0]
        if base in _KRAKEN_PAIR_MAP:
            return _KRAKEN_PAIR_MAP[base]
        return f"{base}USD"

    def get_quote(self, symbol: str) -> AssetQuote:
        symbol = self.normalize_symbol(symbol)
        pair = self._to_kraken_pair(symbol)
        try:
            resp = requests.get(
                f"{KRAKEN_API}/Ticker",
                params={"pair": pair},
                timeout=10,
            )
        except requests.RequestException as exc:
            raise AssetUnavailableError(f"Kraken: błąd połączenia ({exc})") from exc

        if resp.status_code != 200:
            raise AssetUnavailableError(f"Kraken: HTTP {resp.status_code}")

        data = resp.json()
        if data.get("error"):
            raise AssetUnavailableError(f"Kraken: {data['error']}")

        result = data.get("result", {})
        if not result:
            raise AssetUnavailableError(f"Kraken: brak danych dla pary {pair}")

        # Wynik może mieć różną nazwę klucza (np. XXBTZUSD lub XBTUSD)
        ticker_key = next(iter(result))
        ticker = result[ticker_key]
        # 'c' = [last trade price, lot volume]
        price = float(ticker["c"][0])

        return AssetQuote(
            provider_name=self.name,
            symbol=symbol,
            display_name=f"{symbol} (Kraken: {pair})",
            price=price,
            currency="USD",
            note=f"Cena spot z Kraken. Para: {pair}.",
            url=f"https://www.kraken.com/prices/{symbol.split('-')[0].lower()}",
        )

    def _fetch_all_pairs(self) -> dict[str, str]:
        """Pobiera pełną listę par z Kraken. Zwraca {para: wsname}."""
        if self._pairs_cache is not None:
            return self._pairs_cache
        try:
            resp = requests.get(f"{KRAKEN_API}/AssetPairs", timeout=15)
            if resp.status_code != 200:
                return {}
            cache: dict[str, str] = {
                k: v.get("wsname", k)
                for k, v in resp.json().get("result", {}).items()
                if str(v.get("quote", "")).upper() in ("ZUSD", "USD")
            }
            self._pairs_cache = cache
            return cache
        except requests.RequestException:
            return {}

    def search_assets(self, query: str, limit: int = 15) -> list[AssetSearchResult]:
        q = query.strip().upper()
        if len(q) < 2:
            return []
        out: list[AssetSearchResult] = []
        for pair, wsname in self._fetch_all_pairs().items():
            parts = wsname.replace("XBT", "BTC").split("/")
            base = parts[0] if parts else pair
            if q not in base:
                continue
            out.append(
                AssetSearchResult(
                    source=self.name,
                    symbol=f"{base}-USD",
                    display_name=f"{base} / USD (Kraken)",
                    engine=base,
                    protocol="",
                    note=f"Para Kraken: {pair}",
                )
            )
            if len(out) >= limit:
                break
        if not out:
            symbol_try = _KRAKEN_PAIR_MAP.get(q)
            if symbol_try:
                out.append(
                    AssetSearchResult(
                        source=self.name,
                        symbol=f"{q}-USD",
                        display_name=f"{q} / USD (Kraken)",
                        engine=q,
                        protocol="",
                        note=f"Para Kraken: {symbol_try}",
                    )
                )
        return out


class CoinbaseCryptoProvider(AssetProvider):
    """
    Coinbase — ceny spot przez publiczne API v2.
    Nie wymaga klucza API.
    Dokumentacja: https://docs.cdp.coinbase.com/sign-in-with-coinbase/docs/api-prices
    """

    def __init__(self):
        super().__init__(
            name="Coinbase",
            category=AssetCategory.CRYPTO,
            is_live=True,
            requires_api_key=False,
        )

    def get_example_symbols(self) -> dict[str, str]:
        return {
            "BTC-USD": "Bitcoin (BTC/USD on Coinbase)",
            "ETH-USD": "Ethereum (ETH/USD on Coinbase)",
            "SOL-USD": "Solana (SOL/USD on Coinbase)",
            "XRP-USD": "XRP (XRP/USD on Coinbase)",
            "DOGE-USD": "Dogecoin (DOGE/USD on Coinbase)",
            "ADA-USD": "Cardano (ADA/USD on Coinbase)",
            "LINK-USD": "Chainlink (LINK/USD on Coinbase)",
            "MATIC-USD": "Polygon (MATIC/USD on Coinbase)",
            "AVAX-USD": "Avalanche (AVAX/USD on Coinbase)",
            "LTC-USD": "Litecoin (LTC/USD on Coinbase)",
        }

    def normalize_symbol(self, symbol: str) -> str:
        normalized = symbol.strip().upper()
        if "-" not in normalized:
            return f"{normalized}-USD"
        return normalized

    def get_quote(self, symbol: str) -> AssetQuote:
        symbol = self.normalize_symbol(symbol)
        try:
            resp = requests.get(
                f"{COINBASE_API}/prices/{symbol}/spot",
                timeout=10,
            )
        except requests.RequestException as exc:
            raise AssetUnavailableError(f"Coinbase: błąd połączenia ({exc})") from exc

        if resp.status_code == 404:
            raise AssetUnavailableError(f"Coinbase: para {symbol} nie istnieje")
        if resp.status_code != 200:
            raise AssetUnavailableError(f"Coinbase: HTTP {resp.status_code}")

        data = resp.json().get("data", {})
        price_str = data.get("amount")
        if price_str is None:
            raise AssetUnavailableError(f"Coinbase: brak pola 'amount' dla {symbol}")

        price = float(price_str)
        base = data.get("base", symbol.split("-")[0])
        currency = data.get("currency", "USD")

        return AssetQuote(
            provider_name=self.name,
            symbol=symbol,
            display_name=f"{base} / {currency} (Coinbase)",
            price=price,
            currency=currency,
            note="Cena spot z Coinbase (API v2).",
            url=f"https://www.coinbase.com/price/{base.lower()}",
        )

    def search_assets(self, query: str, limit: int = 15) -> list[AssetSearchResult]:
        q = query.strip().upper()
        if len(q) < 2:
            return []
        # Coinbase nie ma publicznego endpointu wyszukiwania bez klucza.
        # Zwracamy jeden kandydat na podstawie zapytania.
        return [
            AssetSearchResult(
                source=self.name,
                symbol=f"{q}-USD",
                display_name=f"{q} / USD (Coinbase)",
                engine=q,
                protocol="",
                note="Kandydat (weryfikowany przy pobraniu ceny)",
            )
        ]


class CoinPaprikaCryptoProvider(AssetProvider):
    """
    CoinPaprika — niezależny agregator danych krypto.
    Darmowe publiczne API, nie wymaga klucza.
    Dokumentacja: https://api.coinpaprika.com/
    """

    def __init__(self):
        super().__init__(
            name="CoinPaprika",
            category=AssetCategory.CRYPTO,
            is_live=True,
            requires_api_key=False,
        )
        self._coin_list_cache: list[dict] | None = None

    def get_example_symbols(self) -> dict[str, str]:
        return {
            "BTC-USD": "Bitcoin (BTC) — CoinPaprika",
            "ETH-USD": "Ethereum (ETH) — CoinPaprika",
            "SOL-USD": "Solana (SOL) — CoinPaprika",
            "XRP-USD": "XRP — CoinPaprika",
            "ADA-USD": "Cardano (ADA) — CoinPaprika",
            "DOGE-USD": "Dogecoin (DOGE) — CoinPaprika",
            "MATIC-USD": "Polygon (MATIC) — CoinPaprika",
            "LINK-USD": "Chainlink (LINK) — CoinPaprika",
            "AVAX-USD": "Avalanche (AVAX) — CoinPaprika",
            "SHIB-USD": "Shiba Inu (SHIB) — CoinPaprika",
            "TON-USD": "Toncoin (TON) — CoinPaprika",
            "SUI-USD": "Sui (SUI) — CoinPaprika",
        }

    def normalize_symbol(self, symbol: str) -> str:
        normalized = symbol.strip().upper()
        if "-" not in normalized:
            return f"{normalized}-USD"
        return normalized

    def _resolve_paprika_id(self, base: str) -> str | None:
        """Zwraca CoinPaprika ID dla danego symbolu (np. 'BTC' -> 'btc-bitcoin')."""
        base_upper = base.upper()
        if base_upper in _PAPRIKA_ID_MAP:
            return _PAPRIKA_ID_MAP[base_upper]
        # Próba z listy coinów
        coins = self._load_coin_list()
        for coin in coins:
            if str(coin.get("symbol", "")).upper() == base_upper:
                return str(coin.get("id", ""))
        return None

    def _load_coin_list(self) -> list[dict]:
        if self._coin_list_cache is not None:
            return self._coin_list_cache
        try:
            resp = requests.get(f"{PAPRIKA_API}/coins", timeout=15)
            if resp.status_code == 200:
                cache = resp.json()
                self._coin_list_cache = cache
                return cache
        except requests.RequestException:
            pass
        self._coin_list_cache = []
        return []

    def get_quote(self, symbol: str) -> AssetQuote:
        symbol = self.normalize_symbol(symbol)
        base = symbol.split("-")[0]
        coin_id = self._resolve_paprika_id(base)
        if not coin_id:
            raise AssetUnavailableError(f"CoinPaprika: nieznany symbol '{base}'. Podaj pełne ID (np. btc-bitcoin).")

        try:
            resp = requests.get(f"{PAPRIKA_API}/tickers/{coin_id}", timeout=10)
        except requests.RequestException as exc:
            raise AssetUnavailableError(f"CoinPaprika: błąd połączenia ({exc})") from exc

        if resp.status_code == 404:
            raise AssetUnavailableError(f"CoinPaprika: coin '{coin_id}' nie znaleziony")
        if resp.status_code != 200:
            raise AssetUnavailableError(f"CoinPaprika: HTTP {resp.status_code}")

        data = resp.json()
        quotes = data.get("quotes", {}).get("USD", {})
        price = float(quotes.get("price", 0) or 0)
        name = str(data.get("name") or base)
        rank = data.get("rank", "n/a")

        if price == 0:
            raise AssetUnavailableError(f"CoinPaprika: zerowa cena dla {coin_id}")

        return AssetQuote(
            provider_name=self.name,
            symbol=symbol,
            display_name=f"{name} ({symbol})",
            price=price,
            currency="USD",
            note=f"Cena USD z CoinPaprika. Rank #{rank}.",
            url=f"https://coinpaprika.com/coin/{coin_id}/",
        )

    def search_assets(self, query: str, limit: int = 15) -> list[AssetSearchResult]:
        query = query.strip()
        if len(query) < 2:
            return []
        try:
            resp = requests.get(
                f"{PAPRIKA_API}/search",
                params={"q": query, "c": "currencies", "limit": min(limit * 2, 30)},
                timeout=10,
            )
        except requests.RequestException:
            return []

        if resp.status_code != 200:
            return []

        out: list[AssetSearchResult] = []
        for item in resp.json().get("currencies", []):
            sym = str(item.get("symbol", "")).upper()
            name = str(item.get("name") or sym)
            coin_id = str(item.get("id", ""))
            rank = item.get("rank", "n/a")
            if not sym:
                continue
            out.append(
                AssetSearchResult(
                    source=self.name,
                    symbol=f"{sym}-USD",
                    display_name=name,
                    engine=sym,
                    protocol="",
                    note=f"ID: {coin_id} | Rank: {rank}",
                )
            )
            if len(out) >= limit:
                break
        return out

