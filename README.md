# CurrencyAssetsCalc

## Struktura projektu (podgląd)

Poniższy podgląd pomija puste pliki `__init__.py` oraz katalogi `__pycache__`.

```text
CurrencyAssetsCalc/
├── main.py
├── pyproject.toml
├── requirements.txt
├── README.md
├── assets/
│   ├── asset_provider_base.py
│   ├── yahoo_assets.py
│   ├── crypto_market_providers.py
│   └── exchange_providers.py
├── core/
│   ├── provider_base.py
│   ├── calculator.py
│   ├── cache.py
│   ├── currency_list.py
│   ├── i18n.py
│   ├── profiles.py
│   ├── asset_memory.py
│   └── price_alerts.py
├── gui/
│   └── main_window.py
├── providers/
│   ├── registry.py
│   ├── nbp_provider.py
│   ├── ecb_provider.py
│   ├── yahoo_provider.py
│   └── placeholder_providers.py
└── tests/
    ├── test_cache.py
    ├── test_asset_memory.py
    ├── test_price_alerts.py
    ├── test_chart_smoothing.py
    └── test_crypto_search.py
```

## Opis

`CurrencyAssetsCalc` to wydzielony projekt do:
- przeliczania walut z wielu źródeł,
- wyceny aktywów (akcje, krypto, surowce, metale),
- prezentacji danych historycznych na wykresach,
- obsługi lokalnej pamięci symboli i alertów cenowych.

## Zastosowane rozwiązania

| Rozwiązanie (nazwa) | Opis / wyjaśnienie działania w projekcie |
|---|---|
| `core.provider_base.DataProvider` | Bazowy kontrakt dla providerów walut (quote, historical, metadane źródła). |
| `providers.registry.ALL_PROVIDERS` | Centralny rejestr providerów walut używany przez GUI do budowy list źródeł. |
| `core.calculator.run_comparison` | Warstwa logiki obliczeń; izoluje GUI od bezpośrednich wywołań providerów i ujednolica obsługę błędów. |
| `core.cache.cached_quote` / `core.cache.cached_historical` | Dekoratory cache TTL dla zapytań kursowych i danych historycznych. |
| `assets.asset_provider_base.AssetProvider` | Kontrakt providerów dla modułu „Other Assets” (ticker -> cena), niezależny od par walutowych. |
| `assets.yahoo_assets` | Działające providery Yahoo dla Stocks/Crypto/Commodities/Metals + wyszukiwarka Yahoo. |
| `assets.crypto_market_providers` | Dodatkowe działające providery crypto: CoinGecko i Binance (bez klucza API). |
| `assets.exchange_providers` | Dodatkowe działające providery crypto: Kraken, Coinbase, CoinPaprika (publiczne endpointy). |
| `core.asset_memory` | Trwała pamięć własnych symboli użytkownika (`user_data/custom_assets.json`). |
| `core.price_alerts` | Trwałe alerty cenowe i jednorazowa aktywacja po spełnieniu progu (`user_data/price_alerts.json`). |
| `gui.main_window` | Interfejs Tkinter z dwoma zakładkami: kalkulator walut i moduł aktywów. |
| `core.i18n` | Prosty mechanizm i18n (PL/EN) oparty o słownik tłumaczeń. |

## Źródła danych używane przy obliczeniach

### Kursy walut
- **NBP API** - https://api.nbp.pl
- **Frankfurter (ECB reference rates)** - https://api.frankfurter.dev
- **Yahoo Finance FX** - https://finance.yahoo.com

### Aktywa (Stocks / Crypto / Commodities / Metals)
- **Yahoo Finance Search API** - https://query2.finance.yahoo.com/v1/finance/search
- **CoinGecko API** - https://www.coingecko.com/en/api/documentation
- **Binance Public API** - https://developers.binance.com/docs/binance-spot-api-docs/rest-api
- **Kraken REST API** - https://docs.kraken.com/api/docs/rest-api
- **Coinbase Prices API (v2)** - https://docs.cdp.coinbase.com/sign-in-with-coinbase/docs/api-prices
- **CoinPaprika API** - https://api.coinpaprika.com

### Źródła placeholder (nieaktywne bez własnej integracji/API key)
- **Wise API docs** - https://api-docs.wise.com
- **Alpha Vantage** - https://www.alphavantage.co
- **Polygon.io** - https://polygon.io
- **Twelve Data** - https://twelvedata.com
- **Finnhub** - https://finnhub.io
- **EOD Historical Data** - https://eodhd.com
- **GoldAPI** - https://www.goldapi.io
- **MetalPriceAPI** - https://metalpriceapi.com
- **London Metal Exchange (LME)** - https://www.lme.com
- **CME Group** - https://www.cmegroup.com
- **Nasdaq Data Link** - https://data.nasdaq.com
- **CoinMarketCap** - https://coinmarketcap.com/api
- **Trading Economics** - https://developer.tradingeconomics.com

## Zależności (spójne z `pyproject.toml`)

- `requests>=2.31.0`
- `yfinance>=0.2.40`
- `matplotlib>=3.7.1`

## Instalacja

```bash
pip install -r requirements.txt
```

## Uruchomienie

```bash
python main.py
```

## Testy

```bash
python -m pytest -q
```
