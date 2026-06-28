"""
assets/asset_provider_base.py
---------------------------------
SZKIELET modułu "Other Assets" (Stocks / Crypto / Commodities / Metals).

To jest pierwszy krok w stronę pełnej struktury z Twojego diagramu:

    Financial Data Hub
    ├── Currency        <- już zaimplementowane (Currency Calculator)
    ├── Stocks          <- szkielet poniżej
    ├── ETFs            <- do zrobienia w kolejnym etapie
    ├── Crypto          <- szkielet poniżej
    ├── Commodities     <- szkielet poniżej
    ├── Metals          <- szkielet poniżej (w praktyce = commodities futures)
    ├── Bonds           <- do zrobienia w kolejnym etapie
    ├── Economic Indicators  <- do zrobienia w kolejnym etapie
    └── News            <- do zrobienia w kolejnym etapie

Te klasy NIE są DataProvider z core/provider_base.py (to dotyczy par walutowych
i interfejsu get_quote(base, quote)). Asset-y mają inny model: pojedynczy symbol
(ticker) i jedna cena w walucie notowania — stąd osobna, prostsza klasa bazowa
AssetCategory + AssetQuote.

W v1 mamy tylko jeden, ale w pełni działający backend: Yahoo Finance — bo to
jedyne darmowe, bezkluczowe źródło, które jednym API pokrywa wszystkie 4
kategorie (akcje, krypto, surowce, metale). Reszta (np. dedykowane giełdy
kryptowalut, Alpha Vantage dla akcji) to gotowe miejsca do podłączenia kolejnych
pluginów w drugim etapie, zgodnie z tą samą filozofią co providers/registry.py.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class AssetCategory(str, Enum):
    STOCKS = "Stock Markets"
    CRYPTO = "Crypto Exchanges"
    COMMODITIES = "Commodity Markets"
    METALS = "Metals"

    def __str__(self) -> str:
        return self.value


@dataclass
class AssetQuote:
    provider_name: str
    symbol: str
    display_name: str
    price: float
    currency: str
    timestamp: str | None = None
    note: str | None = None
    url: str | None = None


@dataclass
class AssetSearchResult:
    source: str
    symbol: str
    display_name: str
    engine: str = ""
    protocol: str = ""
    note: str = ""


class AssetUnavailableError(Exception):
    pass


@dataclass
class AssetProvider(ABC):
    """Interfejs analogiczny do core.provider_base.DataProvider, ale dla
    pojedynczych aktywów (ticker -> cena), nie par walutowych."""

    name: str = field(default="Unnamed Asset Provider")
    category: AssetCategory = field(default=AssetCategory.STOCKS)
    is_live: bool = True
    requires_api_key: bool = False

    @abstractmethod
    def get_example_symbols(self) -> dict[str, str]:
        """Zwraca przykładowe symbole jako {symbol_wewnetrzny: etykieta_czytelna}.
        W v1 to tylko krótka, przykładowa lista (nie pełna giełda)."""
        raise NotImplementedError

    @abstractmethod
    def get_quote(self, symbol: str) -> AssetQuote:
        raise NotImplementedError

    def search_assets(self, query: str, limit: int = 15) -> list[AssetSearchResult]:
        """Opcjonalne: wyszukiwanie symboli w zewnętrznym źródle."""
        return []

    def normalize_symbol(self, symbol: str) -> str:
        """Opcjonalne: normalizacja symbolu wejściowego z UI."""
        return symbol.strip().upper()

    def get_historical(self, symbol: str, period: str = "1mo") -> list[AssetQuote]:
        """Opcjonalna metoda do pobierania danych historycznych."""
        raise NotImplementedError(f"{self.name} nie wspiera danych historycznych.")


class PlaceholderAssetProvider(AssetProvider):
    """Placeholder dla dostawców aktywów, którzy wymagają klucza API lub nie są jeszcze zaimplementowani."""

    def __init__(self, name: str, category: AssetCategory, reason: str):
        super().__init__(
            name=name,
            category=category,
            is_live=False,
            requires_api_key=True
        )
        self._reason = reason

    def get_example_symbols(self) -> dict[str, str]:
        return {}

    def get_quote(self, symbol: str) -> AssetQuote:
        raise AssetUnavailableError(f"{self.name}: {self._reason}")
