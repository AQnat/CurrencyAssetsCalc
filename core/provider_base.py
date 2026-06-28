"""
core/provider_base.py
----------------------
Bazowy interfejs (kontrakt) dla wszystkich źródeł danych (providerów).

Każdy nowy provider (bank centralny, fintech, giełda, agregator...) musi
zaimplementować klasę dziedziczącą po DataProvider. Dodanie nowego źródła
sprowadza się do napisania jednej klasy w katalogu providers/ i zarejestrowania
jej w providers/registry.py — bez modyfikowania GUI, logiki kalkulatora itd.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ProviderCategory(str, Enum):
    """Kategoria źródła danych — używana do grupowania w GUI."""
    CENTRAL_BANK = "Central Banks"
    COMMERCIAL_BANK = "Commercial Banks"
    FINTECH = "FinTech / Exchange Platforms"
    FINANCIAL_MARKET = "Financial Markets"
    AGGREGATOR = "Aggregators"

    def __str__(self) -> str:
        return self.value


class UserProfile(str, Enum):
    """Profil użytkownika — filtruje sugerowane źródła danych."""
    EVERYDAY = "Everyday exchange"
    TRAVEL = "Travel"
    ACCOUNTING = "Accounting"
    INVESTMENTS = "Investments"
    BUSINESS = "Business"
    RESEARCH = "Research"

    def __str__(self) -> str:
        return self.value


@dataclass
class Quote:
    """
    Wynik zapytania o kurs jednej waluty/aktywa względem drugiej.

    rate: ile jednostek 'quote_symbol' za 1 jednostkę 'base_symbol'
    is_estimate: True jeśli provider nie daje realnego kursu (np. placeholder)
    """
    provider_name: str
    base_symbol: str
    quote_symbol: str
    rate: float
    timestamp: Optional[str] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    is_estimate: bool = False
    note: Optional[str] = None
    url: Optional[str] = None


class ProviderUnavailableError(Exception):
    """Podnoszony, gdy provider nie może obecnie dostarczyć danych
    (brak sieci, brak klucza API, źródło wymaga rejestracji, etc.)."""
    pass


@dataclass
class DataProvider(ABC):
    """
    Wspólny interfejs dla wszystkich źródeł danych.

    Subklasy ustawiają `name` i `category` jako atrybuty klasy (lub w __init__),
    oraz implementują get_supported_assets() i get_quote().
    get_historical() ma domyślną implementację rzucającą NotImplementedError,
    bo wiele darmowych źródeł jej nie wspiera — providery, które ją wspierają,
    nadpisują tę metodę.
    """

    name: str = field(default="Unnamed Provider")
    category: ProviderCategory = field(default=ProviderCategory.AGGREGATOR)
    # Profile, dla których ten provider jest sugerowany w GUI (filtr, nie blokada)
    suggested_profiles: tuple = field(default_factory=tuple)
    # Czy provider realnie zwraca dane, czy jest to placeholder/stub
    is_live: bool = True
    requires_api_key: bool = False
    description: str = ""

    @abstractmethod
    def get_supported_assets(self) -> list[str]:
        """Zwraca listę symboli/kodów walut lub aktywów wspieranych przez provider."""
        raise NotImplementedError

    @abstractmethod
    def get_quote(self, base_symbol: str, quote_symbol: str) -> Quote:
        """Zwraca aktualny kurs base_symbol -> quote_symbol."""
        raise NotImplementedError

    def get_historical(self, base_symbol: str, quote_symbol: str,
                        start: str, end: str) -> list[Quote]:
        """Opcjonalna: dane historyczne. Domyślnie nieobsługiwane."""
        raise NotImplementedError(
            f"{self.name} nie obsługuje danych historycznych w tej wersji."
        )

    def __str__(self) -> str:
        return self.name
