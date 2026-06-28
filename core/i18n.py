"""
core/i18n.py
-------------
Prosty mechanizm tłumaczeń dla Financial Data Hub.
"""

from typing import Dict

class I18n:
    def __init__(self):
        self.current_lang = "pl"
        self.translations: Dict[str, Dict[str, str]] = {
            "pl": {
                "app_title": "Currency Assets Calc",
                "currency_tab": "💱 Kalkulator Walutowy",
                "assets_tab": "Inne Aktywa (Akcje / Krypto / Surowce)",
                "profile_header": "1. Profil użytkownika (Cel)",
                "profile_label": "Wybierz profil — filtruje sugerowane źródła danych:",
                "category_header": "2. Kategoria i źródło danych (Dostawca)",
                "category_label": "Kategoria:",
                "vendor_label": "Dostawca:",
                "main_currency_header": "3. Waluta główna i kwota",
                "main_currency_label": "Waluta główna:",
                "amount_label": "Kwota:",
                "comparison_header": "4. Porównanie — do 5 walut",
                "comparison_note": "(Puste pola są ignorowane przy przeliczaniu.)",
                "calculate_btn": "Przelicz →",
                "results_header": "Wyniki",
                "col_currency": "Waluta",
                "col_rate": "Kurs",
                "col_converted": "Przeliczona kwota",
                "col_note": "Uwagi / błąd / URL",
                "placeholder_warning": "⚠ To źródło jest obecnie placeholderem — nie zwraca realnych kursów.",
                "fetch_error": "Błąd połączenia",
                "not_found": "Nie znaleziono",
                "other_assets_header": "Moduł przeliczania aktywów.",
                "asset_category": "Kategoria:",
                "asset_symbol": "Symbol:",
                "fetch_btn": "Pobierz cenę →",
                "source_label": "Źródło danych:",
                "commercial_bank_error": "Banki komercyjne rzadko udostępniają darmowe API kursów dla detalistów.",
                "fintech_api_error": "Dostęp do API platform fintech często wymaga klucza API (Wise, Revolut).",
                "show_chart": "Pokaż wykres",
                "chart_title": "Zmiany ceny w czasie",
                "open_link_btn": "Otwórz link",
                "copy_url_btn": "Kopiuj URL",
            },
            "en": {
                "app_title": "Financial Data Hub — Currency Calculator",
                "currency_tab": "💱 Currency Calculator",
                "assets_tab": "📈 Other Assets (Stocks / Crypto / Commodities)",
                "profile_header": "1. User Profile (Purpose)",
                "profile_label": "Select profile — filters suggested data sources:",
                "category_header": "2. Category and Data Source (Vendor)",
                "category_label": "Category:",
                "vendor_label": "Vendor:",
                "main_currency_header": "3. Main Currency & Amount",
                "main_currency_label": "Main Currency:",
                "amount_label": "Amount:",
                "comparison_header": "4. Comparison — up to 5 currencies",
                "comparison_note": "(Empty fields are ignored during calculation.)",
                "calculate_btn": "Calculate →",
                "results_header": "Results",
                "col_currency": "Currency",
                "col_rate": "Rate",
                "col_converted": "Converted Amount",
                "col_note": "Notes / Error / URL",
                "placeholder_warning": "⚠ This source is currently a placeholder — it does not return real rates.",
                "fetch_error": "Connection error",
                "not_found": "Not found",
                "other_assets_header": "Module under construction — architecture ready for expansion.",
                "asset_category": "Category:",
                "asset_symbol": "Symbol:",
                "fetch_btn": "Fetch Price →",
                "source_label": "Data Source:",
                "commercial_bank_error": "Commercial banks rarely provide free public APIs for retail users.",
                "fintech_api_error": "Access to Fintech APIs often requires an API key (Wise, Revolut).",
                "predictions_tab": "🔮 Predictions & Analysis",
                "predictions_header": "Financial Analysis and Market Suggestions",
                "predictions_desc": "Current analyses generated from live market data; sample entries are only an emergency fallback.",
                "col_title": "Title / Topic",
                "col_summary": "Summary and Conclusions",
                "show_chart": "Show Chart",
                "chart_title": "Price changes over time",
                "open_link_btn": "Open Link",
                "copy_url_btn": "Copy URL",
                "fkb_tab": "🧠 Knowledge Base (FKB)",
                "fkb_header": "Financial Knowledge Base",
                "fkb_desc": "Integrated base of theses, arguments and connections between assets.",
                "col_source": "Source",
                "col_reliability": "Reliability",
                "col_topic": "Topic",
                "col_sentiment": "Sentiment",
                "col_confidence": "AI Confidence",
                "details_header": "Thesis details and argumentation:",
                "thesis_label": "THESIS:",
                "arguments_label": "ARGUMENTS:",
                "assets_label": "RELATED ASSETS:",
                "confirmed_label": "CONFIRMED BY:",
                "trend_forecast_header": "Trend Forecast (Time Horizon):",
                "worth_it_label": "Is it worth it?",
                "worth_it_yes": "PROFITABLE ✅",
                "worth_it_no": "NOT PROFITABLE ❌",
                "worth_it_neutral": "NEUTRAL / WAIT ⏳",
                "period_1m": "1m",
                "period_3m": "3m",
                "period_6m": "6m",
                "period_1y": "1y",
                "period_long": "Long-term",
            }
        }

    def t(self, key: str) -> str:
        return self.translations.get(self.current_lang, self.translations["en"]).get(key, key)

    def set_language(self, lang: str):
        if lang in self.translations:
            self.current_lang = lang

_translator = I18n()

def _(key: str) -> str:
    return _translator.t(key)

def set_language(lang: str):
    _translator.set_language(lang)

