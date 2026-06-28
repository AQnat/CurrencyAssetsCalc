"""
core/profiles.py
------------------
Mapowanie profili użytkownika na sugerowane kategorie i nazwy providerów.

To jest tylko WARSTWA SUGESTII (UX): w GUI, kiedy user wybierze profil
np. "Travel", lista providerów w danej kategorii zostaje przefiltrowana
do tych najbardziej odpowiednich. Użytkownik może zawsze przełączyć
na "Wszystkie" i zobaczyć resztę.
"""

from __future__ import annotations
from core.provider_base import UserProfile, ProviderCategory

# Profil -> zbiór nazw providerów, które są dla niego "polecane".
# Nazwy muszą odpowiadać atrybutowi `name` klas providerów (providers/*.py).
PROFILE_RECOMMENDATIONS: dict[UserProfile, set[str]] = {
    UserProfile.EVERYDAY: {
        "NBP (Narodowy Bank Polski)",
        "European Central Bank (Frankfurter)",
    },
    UserProfile.TRAVEL: {
        "Revolut (placeholder)",
        "Wise (placeholder)",
        "NBP (Narodowy Bank Polski)",
    },
    UserProfile.ACCOUNTING: {
        "NBP (Narodowy Bank Polski)",
        "European Central Bank (Frankfurter)",
    },
    UserProfile.INVESTMENTS: {
        "Yahoo Finance",
        "European Central Bank (Frankfurter)",
    },
    UserProfile.BUSINESS: {
        "NBP (Narodowy Bank Polski)",
        "European Central Bank (Frankfurter)",
        "Yahoo Finance",
    },
    UserProfile.RESEARCH: set(),  # puste = pokaż WSZYSTKIE providery
}


def get_recommended_provider_names(profile: UserProfile) -> set[str]:
    """Zwraca zbiór nazw providerów polecanych dla danego profilu.
    Pusty zbiór oznacza 'wszystkie' (np. profil Research)."""
    return PROFILE_RECOMMENDATIONS.get(profile, set())
