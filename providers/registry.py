"""
providers/registry.py
-----------------------
Centralny rejestr wszystkich providerów dostępnych w aplikacji.

DODANIE NOWEGO PROVIDERA W PRZYSZŁOŚCI:
1. Stwórz nowy plik providers/twoj_provider.py z klasą dziedziczącą po DataProvider.
2. Zaimportuj klasę poniżej i dodaj jej instancję do listy ALL_PROVIDERS.
To wszystko — GUI, filtrowanie po kategorii/profilu i kalkulator automatycznie
zobaczą nowy provider, bez żadnych innych zmian w kodzie.
"""

from __future__ import annotations

from core.provider_base import DataProvider, ProviderCategory
from providers.nbp_provider import NBPProvider
from providers.ecb_provider import ECBProvider
from providers.yahoo_provider import YahooFinanceProvider
from providers.placeholder_providers import (
    RevolutPlaceholder, WisePlaceholder, PekaoPlaceholder,
)

# Tutaj rejestrujemy WSZYSTKIE providery dostępne w aplikacji.
ALL_PROVIDERS: list[DataProvider] = [
    NBPProvider(),
    ECBProvider(),
    YahooFinanceProvider(),
    RevolutPlaceholder(),
    WisePlaceholder(),
    PekaoPlaceholder(),
]


def get_providers_by_category(category: ProviderCategory) -> list[DataProvider]:
    """Zwraca providery z danej kategorii, posortowane alfabetycznie po nazwie."""
    return sorted(
        (p for p in ALL_PROVIDERS if p.category == category),
        key=lambda p: p.name,
    )


def get_all_categories() -> list[ProviderCategory]:
    """Zwraca kategorie, które mają przynajmniej jeden zarejestrowany provider,
    posortowane alfabetycznie po nazwie wyświetlanej."""
    present = {p.category for p in ALL_PROVIDERS}
    return sorted(present, key=lambda c: c.value)

