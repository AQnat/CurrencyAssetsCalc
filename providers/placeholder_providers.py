"""
providers/placeholder_providers.py
-------------------------------------
Placeholdery dla źródeł, które NIE udostępniają publicznego, darmowego API
kursów dla użytkowników detalicznych (Revolut, Wise, Pekao, ING...).

Te klasy istnieją, żeby:
1) pokazać użytkownikowi w GUI, że dany provider "istnieje koncepcyjnie"
   w architekturze (kategoria, profil), ale jest obecnie niedostępny;
2) dać programistom gotowy punkt podłączenia, gdyby w przyszłości chcieli
   dodać własne źródło (np. scraping ich własnego konta, płatne B2B API,
   ręczne wprowadzanie kursu z apki banku).

WAŻNE ETYCZNIE: te klasy NIE zgadują, NIE symulują i NIE udają realnych
kursów rynkowych. get_quote() zawsze rzuca ProviderUnavailableError z czytelnym
komunikatem — nigdy nie zwracają fałszywych/zmyślonych liczb.
"""

from __future__ import annotations

from core.provider_base import DataProvider, ProviderCategory, Quote, ProviderUnavailableError


class PlaceholderProvider(DataProvider):
    """Bazowa klasa dla providerów-placeholderów (brak publicznego API)."""

    def __init__(self, name: str, category: ProviderCategory,
                 suggested_profiles: tuple, reason: str):
        super().__init__(
            name=name,
            category=category,
            suggested_profiles=suggested_profiles,
            is_live=False,
            requires_api_key=False,
            description=reason,
        )
        self._reason = reason

    def get_supported_assets(self) -> list[str]:
        # Lista orientacyjna — nie pobieramy jej z realnego API.
        return ["EUR", "USD", "GBP", "PLN", "CHF", "JPY"]

    def get_quote(self, base_symbol: str, quote_symbol: str) -> Quote:
        raise ProviderUnavailableError(
            f"{self.name}: {self._reason}"
        )


class RevolutPlaceholder(PlaceholderProvider):
    def __init__(self):
        super().__init__(
            name="Revolut (placeholder)",
            category=ProviderCategory.FINTECH,
            suggested_profiles=("Travel", "Everyday exchange"),
            reason=(
                "Revolut nie udostępnia publicznego, darmowego API kursów dla "
                "użytkowników detalicznych. Kurs w aplikacji Revolut jest "
                "widoczny tylko po zalogowaniu się do konta. Aby podłączyć "
                "realne dane, zaimplementuj tę klasę np. przez własny scraper "
                "lub płatne API partnerskie."
            ),
        )


class WisePlaceholder(PlaceholderProvider):
    def __init__(self):
        super().__init__(
            name="Wise (placeholder)",
            category=ProviderCategory.FINTECH,
            suggested_profiles=("Travel", "Business"),
            reason=(
                "Wise udostępnia API kursów (api-docs.wise.com), ale wymaga "
                "rejestracji i klucza API. Możesz użyć biblioteki 'wise-api-client' "
                "lub bezpośrednio requests do endpointu /v1/rates."
            ),
        )


class PekaoPlaceholder(PlaceholderProvider):
    def __init__(self):
        super().__init__(
            name="Bank Pekao S.A. (placeholder)",
            category=ProviderCategory.COMMERCIAL_BANK,
            suggested_profiles=("Travel", "Everyday exchange"),
            reason=(
                "Pekao S.A. nie udostępnia publicznego API kursów walutowych. "
                "Kursy banków komercyjnych w Polsce są zwykle dostępne tylko "
                "jako tabele HTML/PDF na stronie banku, bez ustrukturyzowanego "
                "API — podłączenie realnych danych wymagałoby web scrapingu "
                "(z uwzględnieniem regulaminu strony banku) lub umowy B2B."
            ),
        )
