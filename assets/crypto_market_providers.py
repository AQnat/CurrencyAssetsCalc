from __future__ import annotations

import requests

from assets.asset_provider_base import (
    AssetCategory,
    AssetProvider,
    AssetQuote,
    AssetSearchResult,
    AssetUnavailableError,
)


COINGECKO_API = "https://api.coingecko.com/api/v3"
BINANCE_API = "https://api.binance.com/api/v3"
ENGINE_OVERRIDES = {
    "GRASS": "SOL",
    "JESUS": "BTC",
}
PROTOCOL_OVERRIDES = {
    "LINK": "ERC20",
    "MATIC": "ERC20 (Polygon)",
    "GRASS": "SPL",
    "JESUS": "BRC20",
    "ETH": "ERC20",
    "SOL": "SPL",
    "BNB": "BEP20",
}


class CoinGeckoCryptoProvider(AssetProvider):
    def __init__(self):
        super().__init__(name="CoinGecko", category=AssetCategory.CRYPTO)

    def get_example_symbols(self) -> dict[str, str]:
        return {
            "BTC-USD": "Bitcoin (BTC/USD)",
            "ETH-USD": "Ethereum (ETH/USD)",
            "SOL-USD": "Solana (SOL/USD)",
            "XRP-USD": "XRP (XRP/USD)",
            "DOGE-USD": "Dogecoin (DOGE/USD)",
            "AVAX-USD": "Avalanche (AVAX/USD)",
            "MATIC-USD": "Polygon (MATIC/USD)",
            "LINK-USD": "Chainlink (LINK/USD)",
            "GRASS-USD": "Grass (GRASS/USD)",
        }

    def normalize_symbol(self, symbol: str) -> str:
        normalized = symbol.strip().upper()
        if "-" not in normalized:
            return f"{normalized}-USD"
        return normalized

    def get_quote(self, symbol: str) -> AssetQuote:
        symbol = self.normalize_symbol(symbol)
        base = symbol.split("-")[0].lower()
        try:
            resp = requests.get(
                f"{COINGECKO_API}/coins/markets",
                params={"vs_currency": "usd", "symbols": base, "per_page": 1, "page": 1},
                timeout=10,
            )
        except requests.RequestException as exc:
            raise AssetUnavailableError(f"CoinGecko: błąd połączenia ({exc})") from exc

        if resp.status_code != 200:
            raise AssetUnavailableError(f"CoinGecko: HTTP {resp.status_code}")

        rows = resp.json() if resp.content else []
        if not rows:
            raise AssetUnavailableError(f"CoinGecko: brak danych dla {symbol}")

        row = rows[0]
        price = float(row.get("current_price"))
        name = str(row.get("name") or symbol)
        return AssetQuote(
            provider_name=self.name,
            symbol=symbol,
            display_name=f"{name} ({symbol})",
            price=price,
            currency="USD",
            note="Spot price z CoinGecko (USD).",
            url=f"https://www.coingecko.com/en/coins/{row.get('id', '')}",
        )

    def search_assets(self, query: str, limit: int = 15) -> list[AssetSearchResult]:
        query = query.strip()
        if len(query) < 2:
            return []

        try:
            resp = requests.get(f"{COINGECKO_API}/search", params={"query": query}, timeout=10)
        except requests.RequestException:
            return []

        if resp.status_code != 200:
            return []

        out: list[AssetSearchResult] = []
        for coin in resp.json().get("coins", []):
            base = str(coin.get("symbol", "")).upper()
            symbol = f"{base}-USD"
            name = str(coin.get("name") or symbol)
            if "-USD" == symbol:
                continue
            engine = ENGINE_OVERRIDES.get(base, base)
            out.append(
                AssetSearchResult(
                    source=self.name,
                    symbol=symbol,
                    display_name=name,
                    engine=engine,
                    protocol=PROTOCOL_OVERRIDES.get(base, engine),
                    note=f"Rank: {coin.get('market_cap_rank', 'n/a')}",
                )
            )
            if len(out) >= limit:
                break
        return out


class BinanceCryptoProvider(AssetProvider):
    def __init__(self):
        super().__init__(name="Binance", category=AssetCategory.CRYPTO)
        self._exchange_symbols_cache: list[str] | None = None

    def get_example_symbols(self) -> dict[str, str]:
        return {
            "BTC-USD": "Bitcoin (BTC/USDT on Binance)",
            "ETH-USD": "Ethereum (ETH/USDT on Binance)",
            "SOL-USD": "Solana (SOL/USDT on Binance)",
            "XRP-USD": "XRP (XRP/USDT on Binance)",
            "DOGE-USD": "Dogecoin (DOGE/USDT on Binance)",
            "BNB-USD": "BNB (BNB/USDT on Binance)",
            "MATIC-USD": "Polygon (MATIC/USDT on Binance)",
            "LINK-USD": "Chainlink (LINK/USDT on Binance)",
            "GRASS-USD": "Grass (GRASS/USDT on Binance)",
        }

    def normalize_symbol(self, symbol: str) -> str:
        normalized = symbol.strip().upper()
        if "-" not in normalized:
            return f"{normalized}-USD"
        return normalized

    def _to_binance_pair(self, symbol: str) -> str:
        base = self.normalize_symbol(symbol).split("-")[0]
        return f"{base}USDT"

    def get_quote(self, symbol: str) -> AssetQuote:
        symbol = self.normalize_symbol(symbol)
        pair = self._to_binance_pair(symbol)
        try:
            resp = requests.get(f"{BINANCE_API}/ticker/price", params={"symbol": pair}, timeout=10)
        except requests.RequestException as exc:
            raise AssetUnavailableError(f"Binance: błąd połączenia ({exc})") from exc

        if resp.status_code != 200:
            raise AssetUnavailableError(f"Binance: para {pair} niedostępna (HTTP {resp.status_code})")

        payload = resp.json()
        price = float(payload.get("price"))
        return AssetQuote(
            provider_name=self.name,
            symbol=symbol,
            display_name=f"{symbol} ({pair})",
            price=price,
            currency="USD",
            note="Cena spot z Binance (pary USDT).",
            url=f"https://www.binance.com/en/trade/{pair[:-4]}_USDT",
        )

    def _exchange_symbols(self) -> list[str]:
        if self._exchange_symbols_cache is not None:
            return self._exchange_symbols_cache
        try:
            resp = requests.get(f"{BINANCE_API}/exchangeInfo", timeout=15)
            if resp.status_code != 200:
                return []
            symbols = [str(item.get("symbol", "")).upper() for item in resp.json().get("symbols", [])]
            self._exchange_symbols_cache = [s for s in symbols if s.endswith("USDT")]
            return self._exchange_symbols_cache
        except requests.RequestException:
            return []

    def search_assets(self, query: str, limit: int = 15) -> list[AssetSearchResult]:
        q = query.strip().upper()
        if len(q) < 2:
            return []

        out: list[AssetSearchResult] = []
        for pair in self._exchange_symbols():
            base = pair[:-4]
            if q not in base:
                continue
            out.append(
                AssetSearchResult(
                    source=self.name,
                    symbol=f"{base}-USD",
                    display_name=f"{base} / USDT",
                    engine=ENGINE_OVERRIDES.get(base, base),
                    protocol=PROTOCOL_OVERRIDES.get(base, ENGINE_OVERRIDES.get(base, base)),
                    note="Binance spot pair",
                )
            )
            if len(out) >= limit:
                break

        # Fallback: jeśli API nie zwróciło wyników, pozwól dodać ręcznie symbol.
        if not out:
            out.append(
                AssetSearchResult(
                    source=self.name,
                    symbol=f"{q}-USD",
                    display_name=f"{q} / USDT",
                    engine=ENGINE_OVERRIDES.get(q, q),
                    protocol=PROTOCOL_OVERRIDES.get(q, ENGINE_OVERRIDES.get(q, q)),
                    note="Manual candidate (sprawdzany przy pobraniu ceny)",
                )
            )
        return out

