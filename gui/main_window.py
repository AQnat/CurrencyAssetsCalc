"""
gui/main_window.py
---------------------
Główne okno aplikacji "Currency Calculator" (Tkinter).

Układ zgodny z założeniami:
1. Profil użytkownika (filtruje listę providerów)
2. Kategoria źródła danych (Central Banks / Commercial Banks / FinTech / ...)
3. Vendor / Data Source (konkretny provider w danej kategorii)
4. Main Currency (waluta bazowa)
5. 5 komórek "Comparison" (waluty do porównania)
6. Przycisk "Przelicz" + tabela wyników
7. Zakładka "Other Assets" — szkielet modułu Stocks/Crypto/Commodities/Metals

Wszystkie listy rozwijane są sortowane alfabetycznie, zgodnie z wymaganiem.
GUI nigdy nie woła providerów bezpośrednio — zawsze przez core.calculator.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser
import re

from core.provider_base import ProviderCategory, UserProfile
from core.currency_list import all_currency_codes_sorted, format_currency_label
from core.calculator import run_comparison, ComparisonResult
from core.profiles import get_recommended_provider_names
from core.i18n import _, set_language
from providers.registry import (
    get_providers_by_category, get_all_categories,
)
from assets.asset_provider_base import AssetUnavailableError
from assets.yahoo_assets import ALL_ASSET_PROVIDERS as YAHOO_ASSET_PROVIDERS
from assets.crypto_market_providers import CoinGeckoCryptoProvider, BinanceCryptoProvider
from assets.exchange_providers import (
    KrakenCryptoProvider,
    CoinbaseCryptoProvider,
    CoinPaprikaCryptoProvider,
)
from core.asset_memory import load_asset_memory, upsert_asset_memory_item
from core.price_alerts import add_price_alert, evaluate_price_alerts

NUM_COMPARISON_SLOTS = 5
APP_TITLE = "Financial Data Hub — Currency Calculator"
ALL_SOURCES_LABEL = "Wszystkie źródła"
ALL_ASSET_PROVIDERS = [
    *YAHOO_ASSET_PROVIDERS,
    CoinGeckoCryptoProvider(),
    BinanceCryptoProvider(),
    KrakenCryptoProvider(),
    CoinbaseCryptoProvider(),
    CoinPaprikaCryptoProvider(),
]


def extract_links(text: str) -> list[str]:
    return re.findall(r"\[Link:\s*(https?://[^]\s]+)]", text or "")


def classify_trend(current_rate: float, previous_rate: float | None, avg7_rate: float | None) -> tuple[str, str]:
    reference = avg7_rate if avg7_rate and avg7_rate > 0 else previous_rate
    if not reference or reference <= 0:
        return "flat", "trend: n/a"

    change = ((current_rate - reference) / reference) * 100.0
    if change > 0.1:
        return "up", f"trend: +{change:.2f}%"
    if change < -0.1:
        return "down", f"trend: {change:.2f}%"
    return "flat", f"trend: {change:.2f}%"


def format_price(value: float) -> str:
    abs_v = abs(value)
    if abs_v >= 1000:
        return f"{value:,.2f}"
    if abs_v >= 1:
        return f"{value:,.6f}"
    if abs_v >= 0.0001:
        return f"{value:,.8f}"
    return f"{value:.4e}"


def _median_of_three(a: float, b: float, c: float) -> float:
    return sorted((a, b, c))[1]


def smooth_micro_series(rates: list[float], *, enabled: bool) -> list[float]:
    if not enabled or len(rates) < 3:
        return rates
    abs_rates = sorted(abs(v) for v in rates)
    median_abs = abs_rates[len(abs_rates) // 2]
    if median_abs >= 0.01:
        return rates

    smoothed = rates[:]
    for i in range(1, len(rates) - 1):
        smoothed[i] = _median_of_three(rates[i - 1], rates[i], rates[i + 1])
    return smoothed


class Tooltip:
    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self._show)
        self.widget.bind("<Leave>", self._hide)

    def _show(self, _event=None):
        if self.tip_window:
            return
        x = self.widget.winfo_rootx() + 14
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 2
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify="left", bg="#ffffe0", relief="solid", borderwidth=1)
        label.pack(ipadx=6, ipady=3)

    def _hide(self, _event=None):
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None


class AutocompleteCombobox(ttk.Combobox):
    """
    Combobox z autouzupełnianiem i obsługą wprowadzania ręcznego.
    """
    def set_completion_list(self, completion_list):
        self._completion_list = sorted(completion_list, key=str.lower)
        self["values"] = self._completion_list

    def _on_keyrelease(self, event):
        if event.keysym in (
            "Left", "Right", "Up", "Down", "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R"
        ):
            return
        if event.keysym == "Return":
            return

        val = self.get()
        if not val:
            self["values"] = self._completion_list
            return

        lower_val = val.lower()
        prefix_hits = [item for item in self._completion_list if item.lower().startswith(lower_val)]
        contains_hits = [item for item in self._completion_list if lower_val in item.lower() and item not in prefix_hits]
        hits = prefix_hits + contains_hits

        if hits:
            self["values"] = hits[:100]
            if event.keysym not in ("BackSpace", "Delete") and prefix_hits:
                best = prefix_hits[0]
                self.set(best)
                self.icursor(len(val))
                self.select_range(len(val), len(best))
        else:
            self["values"] = self._completion_list

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self._completion_list = []
        self.bind("<KeyRelease>", self._on_keyrelease)


def open_chart_window(parent, base, quote, dates, rates, apply_micro_smoothing: bool = False):
    """Wspólna funkcja do otwierania okna wykresu."""
    try:
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    except ImportError:
        messagebox.showerror("Błąd", "Biblioteka matplotlib nie jest dostępna.")
        return

    win = tk.Toplevel(parent)
    win.title(f"{_('chart_title')}: {base}/{quote}")
    win.geometry("800x600")
    
    fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
    plot_rates = smooth_micro_series([float(r) for r in rates], enabled=apply_micro_smoothing)
    x_values = list(range(len(dates)))
    ax.plot(x_values, plot_rates, marker='o', linestyle='-', color='#1a73e8')
    ax.set_title(f"{base} / {quote}")
    ax.set_xlabel("Data")
    ax.set_ylabel("Kurs / Cena")
    step = max(1, len(dates) // 8)
    ticks = list(range(0, len(dates), step))
    if len(dates) - 1 not in ticks:
        ticks.append(len(dates) - 1)
    ax.set_xticks(ticks)
    ax.set_xticklabels([dates[i] for i in ticks], rotation=45, ha="right")
    fig.tight_layout()
    
    canvas = FigureCanvasTkAgg(fig, master=win)
    canvas.draw()
    
    toolbar = NavigationToolbar2Tk(canvas, win)
    toolbar.update()

    def _on_scroll(event):
        if event.inaxes != ax or event.xdata is None:
            return
        if event.key:
            key = str(event.key).lower()
            if "control" in key or "ctrl" in key or "shift" in key or "alt" in key:
                return
        x_min, x_max = ax.get_xlim()
        center = float(event.xdata)
        current_width = max(2.0, x_max - x_min)
        scale = 0.85 if event.button == "up" else 1.15
        new_width = min(max(2.0, current_width * scale), max(3.0, float(len(x_values))))
        left = max(-0.5, center - (new_width / 2.0))
        right = min(float(len(x_values)) - 0.5, center + (new_width / 2.0))
        ax.set_xlim(left, right)
        canvas.draw_idle()

    fig.canvas.mpl_connect("scroll_event", _on_scroll)

    canvas.get_tk_widget().pack(fill="both", expand=True)


class CurrencyCalculatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(_("app_title"))
        self.geometry("1024x768")
        self.minsize(880, 640)

        self._build_style()
        self._build_menu()

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.currency_tab = CurrencyCalculatorTab(notebook)
        self.assets_tab = OtherAssetsTab(notebook)

        notebook.add(self.currency_tab, text=_("currency_tab"))
        notebook.add(self.assets_tab, text=_("assets_tab"))
        self.bind_all("<Control-c>", self._on_copy)

    def _build_menu(self):
        menubar = tk.Menu(self)
        lang_menu = tk.Menu(menubar, tearoff=0)
        lang_menu.add_command(label="Polski", command=lambda: self._change_lang("pl"))
        lang_menu.add_command(label="English", command=lambda: self._change_lang("en"))
        menubar.add_cascade(label="Language / Język", menu=lang_menu)
        self.config(menu=menubar)

    def _change_lang(self, lang_code):
        set_language(lang_code)
        messagebox.showinfo("Language / Język", "Please restart the application to apply all language changes.\nProszę zrestartować aplikację, aby zastosować wszystkie zmiany języka.")
        # W idealnym świecie odświeżylibyśmy UI bez restartu, ale dla prostoty v1 restart jest pewniejszy.
        # Ale spróbujmy chociaż zmienić tytuł okna.
        self.title(_("app_title"))

    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Result.TLabel", font=("Consolas", 10))
        style.configure("Error.TLabel", foreground="#b00020")
        style.configure("Note.TLabel", foreground="#555555", font=("Segoe UI", 8))

    def _on_copy(self, _event=None):
        widget = self.focus_get()
        if widget is None:
            return
        if isinstance(widget, ttk.Treeview):
            selected = widget.selection()
            if not selected:
                return
            rows = []
            for item in selected:
                values = [str(v) for v in widget.item(item, "values")]
                rows.append("\t".join(values))
            self.clipboard_clear()
            self.clipboard_append("\n".join(rows))
            return
        if isinstance(widget, tk.Text):
            try:
                selected_text = widget.selection_get()
            except tk.TclError:
                return
            self.clipboard_clear()
            self.clipboard_append(selected_text)


class CurrencyCalculatorTab(ttk.Frame):
    """Zakładka właściwego kalkulatora walut."""

    def __init__(self, parent):
        super().__init__(parent, padding=12)

        self.profile_var = tk.StringVar()
        self.category_var = tk.StringVar()
        self.vendor_var = tk.StringVar()
        self.main_currency_var = tk.StringVar(value="PLN")
        self.amount_var = tk.StringVar(value="100")
        self.comparison_vars = [tk.StringVar() for _ in range(NUM_COMPARISON_SLOTS)]

        self.show_trend_var = tk.BooleanVar(value=True)
        self._current_provider = None  # ustawiane po wyborze vendor

        self._build_profile_row()
        self._build_category_vendor_row()
        self._build_main_currency_row()
        self._build_comparison_rows()
        self._build_action_row()
        self._build_results_area()

        # Inicjalne wypełnienie list
        self._on_profile_changed()

    # ---------- budowa UI ----------

    def _build_profile_row(self):
        frame = ttk.LabelFrame(self, text=_("profile_header"), padding=8)
        frame.pack(fill="x", pady=(0, 8))

        ttk.Label(frame, text=_("profile_label")).pack(side="left", padx=(0, 8))

        profile_values = sorted([str(p) for p in UserProfile])
        combo = ttk.Combobox(frame, textvariable=self.profile_var, values=profile_values,
                              state="readonly", width=28)
        combo.pack(side="left")
        combo.set(str(UserProfile.RESEARCH))
        combo.bind("<<ComboboxSelected>>", lambda e: self._on_profile_changed())

    def _build_category_vendor_row(self):
        frame = ttk.LabelFrame(self, text=_("category_header"), padding=8)
        frame.pack(fill="x", pady=(0, 8))

        ttk.Label(frame, text=_("category_label")).grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
        cat_values = sorted([str(c) for c in get_all_categories()])
        self.category_combo = ttk.Combobox(frame, textvariable=self.category_var,
                                            values=cat_values, state="readonly", width=32)
        self.category_combo.grid(row=0, column=1, sticky="w", pady=4)
        self.category_combo.bind("<<ComboboxSelected>>", lambda e: self._on_category_changed())

        ttk.Label(frame, text=_("vendor_label")).grid(row=0, column=2, sticky="w", padx=(16, 6), pady=4)
        self.vendor_combo = ttk.Combobox(frame, textvariable=self.vendor_var,
                                          values=[], state="readonly", width=36)
        self.vendor_combo.grid(row=0, column=3, sticky="w", pady=4)
        self.vendor_combo.bind("<<ComboboxSelected>>", lambda e: self._on_vendor_changed())

        self.vendor_info_label = ttk.Label(frame, text="", style="Note.TLabel", wraplength=820, justify="left")
        self.vendor_info_label.grid(row=1, column=0, columnspan=4, sticky="w", pady=(6, 0))

    def _build_main_currency_row(self):
        frame = ttk.LabelFrame(self, text=_("main_currency_header"), padding=8)
        frame.pack(fill="x", pady=(0, 8))

        ttk.Label(frame, text=_("main_currency_label")).grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.main_currency_combo = AutocompleteCombobox(frame, textvariable=self.main_currency_var,
                                                 width=28)
        self.main_currency_combo.grid(row=0, column=1, sticky="w")

        ttk.Label(frame, text=_("amount_label")).grid(row=0, column=2, sticky="w", padx=(16, 6))
        ttk.Entry(frame, textvariable=self.amount_var, width=14).grid(row=0, column=3, sticky="w")

    def _build_comparison_rows(self):
        frame = ttk.LabelFrame(self, text=_("comparison_header"), padding=8)
        frame.pack(fill="x", pady=(0, 8))

        self.comparison_combos = []
        for i in range(NUM_COMPARISON_SLOTS):
            ttk.Label(frame, text=f"#{i + 1}:").grid(row=i // 3, column=(i % 3) * 2, sticky="w", padx=(0, 4), pady=3)
            combo = AutocompleteCombobox(frame, textvariable=self.comparison_vars[i],
                                  width=26)
            combo.grid(row=i // 3, column=(i % 3) * 2 + 1, sticky="w", padx=(0, 16), pady=3)
            self.comparison_combos.append(combo)

        ttk.Label(frame, text=_("comparison_note"),
                  style="Note.TLabel").grid(row=2, column=0, columnspan=6, sticky="w", pady=(4, 0))

    def _build_action_row(self):
        frame = ttk.Frame(self)
        frame.pack(fill="x", pady=(0, 8))

        self.calculate_btn = ttk.Button(frame, text=_("calculate_btn"), command=self._on_calculate_clicked)
        self.calculate_btn.pack(side="left")

        ttk.Checkbutton(frame, text="Pokaż trend cen", variable=self.show_trend_var).pack(side="left", padx=(12, 0))

        self.status_label = ttk.Label(frame, text="", style="Note.TLabel")
        self.status_label.pack(side="left", padx=(12, 0))

    def _build_results_area(self):
        frame = ttk.LabelFrame(self, text=_("results_header"), padding=8)
        frame.pack(fill="both", expand=True)

        columns = ("currency", "rate", "converted", "note")
        self.results_tree = ttk.Treeview(frame, columns=columns, show="headings", height=8)
        self.results_tree.heading("currency", text=_("col_currency"))
        self.results_tree.heading("rate", text=_("col_rate"))
        self.results_tree.heading("converted", text=_("col_converted"))
        self.results_tree.heading("note", text=_("col_note"))
        self.results_tree.column("currency", width=140, anchor="w")
        self.results_tree.column("rate", width=120, anchor="e")
        self.results_tree.column("converted", width=160, anchor="e")
        self.results_tree.column("note", width=420, anchor="w")
        self.results_tree.pack(fill="both", expand=True)

        self.results_tree.tag_configure("error_row", foreground="#b00020")
        self.results_tree.tag_configure("up_row", foreground="#0a7a2f")
        self.results_tree.tag_configure("down_row", foreground="#c62828")
        self.results_tree.tag_configure("flat_row", foreground="#1565c0")

        self.results_tree.bind("<Double-1>", self._on_tree_double_click)
        self.results_tree.bind("<Button-3>", self._on_tree_right_click)

    def _on_tree_double_click(self, event):
        item_id = self.results_tree.identify_row(event.y)
        if not item_id:
            return
        
        values = self.results_tree.item(item_id, "values")
        note = values[3]

        links = extract_links(note)
        if links:
            webbrowser.open(links[0])
            
    def _on_tree_right_click(self, event):
        item_id = self.results_tree.identify_row(event.y)
        if not item_id:
            return
        
        self.results_tree.selection_set(item_id)
        
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label=_("show_chart"), command=lambda: self._show_chart_for_item(item_id))
        menu.add_command(label="Kopiuj wiersz", command=lambda: self._copy_row(item_id))

        values = self.results_tree.item(item_id, "values")
        note = values[3]

        links = extract_links(note)

        if links:
            for url in links:
                short_url = url[:30] + "..." if len(url) > 33 else url
                submenu = tk.Menu(menu, tearoff=0)
                submenu.add_command(label="Otwórz", command=lambda u=url: webbrowser.open(u))
                submenu.add_command(label="Kopiuj", command=lambda u=url: self.clipboard_clear() or self.clipboard_append(u))
                menu.add_cascade(label=f"URL: {short_url}", menu=submenu)
            
        menu.post(event.x_root, event.y_root)

    def _copy_row(self, item_id):
        values = [str(v) for v in self.results_tree.item(item_id, "values")]
        self.clipboard_clear()
        self.clipboard_append("\t".join(values))

    def _show_chart_for_item(self, item_id):
        values = self.results_tree.item(item_id, "values")
        quote_symbol = values[0]
        main_label = self.main_currency_var.get()
        main_code = self._currency_label_to_code.get(main_label, main_label)
        
        provider = self._current_provider
        if not provider:
            return

        threading.Thread(target=self._fetch_and_plot, args=(provider, main_code, quote_symbol), daemon=True).start()

    def _fetch_and_plot(self, provider, base, quote):
        try:
            quotes = provider.get_historical(base, quote)
            if not quotes:
                return
                
            dates = [q.timestamp for q in quotes]
            rates = [q.rate for q in quotes]
            
            self.after(0, open_chart_window, self, base, quote, dates, rates, False)
        except Exception as e:
            self.after(0, messagebox.showerror, "Błąd", f"Nie udało się pobrać danych historycznych: {e}")


    # ---------- logika / handlery ----------

    def _on_profile_changed(self):
        self._on_category_changed()

    def _on_category_changed(self):
        category_str = self.category_var.get()
        if not category_str:
            # Domyślnie: pierwsza kategoria alfabetycznie
            cats = sorted([str(c) for c in get_all_categories()])
            if cats:
                self.category_var.set(cats[0])
                category_str = cats[0]

        category = next((c for c in ProviderCategory if str(c) == category_str), None)
        if category is None:
            return

        providers_in_cat = get_providers_by_category(category)
        profile_str = self.profile_var.get()
        profile = next((p for p in UserProfile if str(p) == profile_str), None)
        recommended = get_recommended_provider_names(profile) if profile else set()

        # Sortowanie alfabetyczne, z dopiskiem "★" dla polecanych w danym profilu
        def label_for(p):
            star = "★ " if (recommended and p.name in recommended) else ""
            live_tag = "" if p.is_live else "  [brak publicznego API]"
            return f"{star}{p.name}{live_tag}"

        sorted_providers = sorted(providers_in_cat, key=lambda p: p.name)
        labels = [label_for(p) for p in sorted_providers]
        self._vendor_label_to_provider = {label_for(p): p for p in sorted_providers}

        self.vendor_combo["values"] = labels
        if labels:
            self.vendor_var.set(labels[0])
        else:
            self.vendor_var.set("")
        self._on_vendor_changed()

    def _on_vendor_changed(self):
        label = self.vendor_var.get()
        provider = self._vendor_label_to_provider.get(label) if hasattr(self, "_vendor_label_to_provider") else None
        self._current_provider = provider

        if provider is None:
            self.vendor_info_label.config(text="")
            self.main_currency_combo["values"] = []
            for combo in self.comparison_combos:
                combo["values"] = []
            return

        # Info o providerze
        info_parts = [provider.description]
        if not provider.is_live:
            info_parts.append(_("placeholder_warning"))
            if provider.category == ProviderCategory.COMMERCIAL_BANK:
                info_parts.append(_("commercial_bank_error"))
            elif provider.category == ProviderCategory.FINTECH:
                info_parts.append(_("fintech_api_error"))
        
        self.vendor_info_label.config(text=" ".join(info_parts))

        # Wypełnij listy walut na podstawie wspieranych assetów danego providera
        try:
            supported = provider.get_supported_assets()
        except Exception:
            supported = all_currency_codes_sorted()

        supported_sorted = sorted(supported)
        labels = [format_currency_label(code) for code in supported_sorted]
        self._currency_label_to_code = dict(zip(labels, supported_sorted))

        self.main_currency_combo["values"] = labels
        if labels:
            current = self.main_currency_var.get()
            if current not in labels:
                # Domyślnie PLN jeśli dostępny, inaczej pierwszy alfabetycznie
                default_label = format_currency_label("PLN")
                self.main_currency_var.set(default_label if default_label in labels else labels[0])

        for combo in self.comparison_combos:
            combo.set_completion_list([""] + labels)
        self.main_currency_combo.set_completion_list(labels)

    def _on_calculate_clicked(self):
        provider = self._current_provider
        if provider is None:
            messagebox.showwarning(APP_TITLE, "Wybierz najpierw źródło danych (Vendor).")
            return

        main_label = self.main_currency_var.get()
        main_code = self._currency_label_to_code.get(main_label, main_label)

        try:
            amount = float(self.amount_var.get().replace(",", "."))
        except ValueError:
            messagebox.showerror(APP_TITLE, "Kwota musi być liczbą, np. 100 lub 100.50")
            return

        comparison_codes = []
        for var in self.comparison_vars:
            label = var.get()
            if not label:
                continue
            comparison_codes.append(self._currency_label_to_code.get(label, label))

        if not comparison_codes:
            messagebox.showwarning(APP_TITLE, "Wybierz przynajmniej jedną walutę do porównania.")
            return

        self.calculate_btn.config(state="disabled")
        self.status_label.config(text=f"Pobieranie kursów z: {provider.name} ...")
        self.results_tree.delete(*self.results_tree.get_children())

        def worker():
            results = run_comparison(provider, main_code, amount, comparison_codes)
            trend_info = self._build_trend_map(provider, main_code, results) if self.show_trend_var.get() else {}
            self.after(0, self._display_results, results, trend_info)

        threading.Thread(target=worker, daemon=True).start()

    def _build_trend_map(self, provider, base_code: str, results: list[ComparisonResult]) -> dict[str, tuple[str, str]]:
        trend_map: dict[str, tuple[str, str]] = {}
        for row in results:
            if not row.success:
                continue
            try:
                history = provider.get_historical(base_code, row.quote_symbol)
            except Exception:
                continue
            if not history:
                continue
            rates = [q.rate for q in history if getattr(q, "rate", None) is not None]
            if len(rates) < 2:
                continue
            previous_rate = rates[-2]
            tail = rates[-8:-1]
            avg7_rate = (sum(tail) / len(tail)) if tail else None
            if row.rate is None:
                continue
            trend_map[row.quote_symbol] = classify_trend(float(row.rate), previous_rate, avg7_rate)
        return trend_map

    def _display_results(self, results: list[ComparisonResult], trend_info: dict[str, tuple[str, str]] | None = None):
        self.calculate_btn.config(state="normal")
        self.status_label.config(text=_("results_header") + ": " + (results[0].timestamp if results and results[0].timestamp else ""))
        trend_info = trend_info or {}

        for r in results:
            note = r.note or ""
            if r.url:
                note = f"{note} [Link: {r.url}]"
            
            if r.success:
                display_note = re.sub(r"\[Link: https?://[^]]+]", "[Link]", note)
                trend_tag, trend_text = trend_info.get(r.quote_symbol, ("flat", "trend: n/a"))
                if display_note:
                    display_note = f"{display_note} | {trend_text}"
                else:
                    display_note = trend_text

                self.results_tree.insert("", "end", values=(
                    r.quote_symbol,
                    f"{r.rate:.6f}",
                    f"{r.converted_amount:,.2f}",
                    display_note,
                ), tags=(f"{trend_tag}_row",))
            else:
                self.results_tree.insert("", "end", values=(
                    r.quote_symbol, "—", "—", r.error_message,
                ), tags=("error_row",))


class OtherAssetsTab(ttk.Frame):
    """Rozszerzona zakładka Other Assets z wyszukiwaniem i porównaniem źródeł."""

    def __init__(self, parent):
        super().__init__(parent, padding=12)

        ttk.Label(
            self,
            text=_("other_assets_header"),
            style="Header.TLabel",
        ).pack(anchor="w", pady=(0, 10))

        self.category_var = tk.StringVar()
        self.provider_var = tk.StringVar()
        self.symbol_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.search_status_var = tk.StringVar(value="")
        self.alert_status_var = tk.StringVar(value="")
        self.hide_http_errors_var = tk.BooleanVar(value=False)
        self.smooth_micro_chart_var = tk.BooleanVar(value=False)
        self.alert_condition_var = tk.StringVar(value="above")
        self.alert_threshold_var = tk.StringVar(value="")

        row = ttk.Frame(self)
        row.pack(fill="x", pady=(0, 10))

        ttk.Label(row, text=_("asset_category")).pack(side="left", padx=(0, 6))
        cat_values = sorted({p.category.value for p in ALL_ASSET_PROVIDERS})
        self.category_combo = ttk.Combobox(row, textvariable=self.category_var,
                                            values=cat_values, state="readonly", width=24)
        self.category_combo.pack(side="left")
        self.category_combo.bind("<<ComboboxSelected>>", lambda e: self._on_category_changed())

        ttk.Label(row, text=_("source_label")).pack(side="left", padx=(16, 6))
        self.provider_combo = ttk.Combobox(row, textvariable=self.provider_var, values=[], state="readonly", width=22)
        self.provider_combo.pack(side="left")
        self.provider_combo.bind("<<ComboboxSelected>>", lambda e: self._on_provider_changed())

        ttk.Label(row, text=_("asset_symbol")).pack(side="left", padx=(16, 6))
        self.symbol_combo = AutocompleteCombobox(row, textvariable=self.symbol_var,
                                          width=32)
        self.symbol_combo.pack(side="left")

        ttk.Button(row, text=_("fetch_btn"), command=self._on_fetch_clicked).pack(side="left", padx=(16, 0))
        ttk.Button(row, text="Porownaj zrodla", command=self._on_compare_sources_clicked).pack(side="left", padx=(8, 0))
        ttk.Button(row, text=_("show_chart"), command=self._on_chart_clicked).pack(side="left", padx=(8, 0))

        opts_row = ttk.Frame(self)
        opts_row.pack(fill="x", pady=(0, 8))
        ttk.Checkbutton(
            opts_row,
            text="Ukryj zrodla z bledem HTTP",
            variable=self.hide_http_errors_var,
            command=self._refresh_compare_tree,
        ).pack(side="left")
        ttk.Checkbutton(
            opts_row,
            text="Wygladzanie mikrocen (mediana 3D)",
            variable=self.smooth_micro_chart_var,
        ).pack(side="left", padx=(12, 0))

        search_row = ttk.Frame(self)
        search_row.pack(fill="x", pady=(0, 8))
        ttk.Label(search_row, text="Search:").pack(side="left", padx=(0, 6))
        search_entry = ttk.Entry(search_row, textvariable=self.search_var, width=36)
        search_entry.pack(side="left")
        Tooltip(search_entry, "Jesli brak na liscie, wyszukaj recznie")
        ttk.Button(search_row, text="Szukaj", command=self._on_search_clicked).pack(side="left", padx=(8, 0))
        ttk.Button(search_row, text="Dodaj do listy", command=self._on_add_search_result_clicked).pack(side="left", padx=(8, 0))
        self.search_progress = ttk.Progressbar(search_row, mode="indeterminate", length=120)
        self.search_progress.pack(side="left", padx=(10, 0))
        ttk.Label(search_row, textvariable=self.search_status_var, style="Note.TLabel").pack(side="left", padx=(8, 0))

        alert_row = ttk.Frame(self)
        alert_row.pack(fill="x", pady=(0, 8))
        ttk.Label(alert_row, text="Alert cenowy:").pack(side="left", padx=(0, 6))
        ttk.Combobox(
            alert_row,
            textvariable=self.alert_condition_var,
            values=["above", "below"],
            state="readonly",
            width=10,
        ).pack(side="left")
        ttk.Entry(alert_row, textvariable=self.alert_threshold_var, width=14).pack(side="left", padx=(6, 0))
        ttk.Button(alert_row, text="Dodaj alert", command=self._on_add_alert_clicked).pack(side="left", padx=(8, 0))
        ttk.Label(alert_row, textvariable=self.alert_status_var, style="Note.TLabel").pack(side="left", padx=(10, 0))

        self.search_tree = ttk.Treeview(self, columns=("source", "symbol", "name", "engine", "protocol", "note"), show="headings", height=6)
        self.search_tree.heading("source", text="Zrodlo")
        self.search_tree.heading("symbol", text="Symbol")
        self.search_tree.heading("name", text="Nazwa")
        self.search_tree.heading("engine", text="Silnik")
        self.search_tree.heading("protocol", text="Chain/Protocol")
        self.search_tree.heading("note", text="Uwaga")
        self.search_tree.column("source", width=130, anchor="w")
        self.search_tree.column("symbol", width=120, anchor="w")
        self.search_tree.column("name", width=220, anchor="w")
        self.search_tree.column("engine", width=110, anchor="w")
        self.search_tree.column("protocol", width=140, anchor="w")
        self.search_tree.column("note", width=180, anchor="w")
        self.search_tree.pack(fill="x", pady=(0, 8))

        self.compare_tree = ttk.Treeview(self, columns=("provider", "price", "currency", "note"), show="headings", height=4)
        self.compare_tree.heading("provider", text="Zrodlo")
        self.compare_tree.heading("price", text="Cena")
        self.compare_tree.heading("currency", text="Waluta")
        self.compare_tree.heading("note", text="Uwagi")
        self.compare_tree.column("provider", width=160, anchor="w")
        self.compare_tree.column("price", width=120, anchor="e")
        self.compare_tree.column("currency", width=80, anchor="center")
        self.compare_tree.column("note", width=420, anchor="w")
        self.compare_tree.pack(fill="x", pady=(0, 8))

        self.result_text = tk.Text(self, height=3, wrap="word")
        self.result_text.pack(fill="x", pady=(8, 0))
        self._make_text_selectable_readonly(self.result_text)

        self.note_text = tk.Text(self, height=3, wrap="word", cursor="hand2")
        self.note_text.pack(fill="x", pady=(4, 0))
        self._make_text_selectable_readonly(self.note_text)
        self.note_text.bind("<Button-1>", self._on_note_clicked)

        self.search_tree.bind("<Double-1>", lambda _e: self._on_add_search_result_clicked())

        self._init_default_selection(cat_values)

    def _make_text_selectable_readonly(self, widget: tk.Text):
        widget.configure(state="normal")
        widget.bind("<Key>", lambda _e: "break")
        widget.bind("<<Paste>>", lambda _e: "break")

    def _on_note_clicked(self, event):
        full_note = getattr(self, "_last_full_note", "")
        links = extract_links(full_note)
        if links:
            webbrowser.open(links[0])

    def _init_default_selection(self, cat_values):
        if cat_values:
            self.category_var.set(cat_values[0])
            self._on_category_changed()

    def _providers_for_category(self, category_value: str):
        return [p for p in ALL_ASSET_PROVIDERS if p.category.value == category_value]

    def _active_providers(self):
        providers = self._providers_for_category(self.category_var.get())
        if self.provider_var.get() == ALL_SOURCES_LABEL:
            return providers
        return [p for p in providers if p.name == self.provider_var.get()]

    def _provider_for_selection(self):
        providers = self._active_providers()
        return providers[0] if providers else None

    def _on_category_changed(self):
        providers = self._providers_for_category(self.category_var.get())
        if not providers:
            self.provider_combo["values"] = []
            self.symbol_combo["values"] = []
            return
        provider_names = [ALL_SOURCES_LABEL, *sorted({p.name for p in providers})]
        self.provider_combo["values"] = provider_names
        if self.provider_var.get() not in provider_names:
            self.provider_var.set(provider_names[0])
        self._refresh_symbols_for_category()

    def _on_provider_changed(self):
        self._refresh_symbols_for_category()

    def _refresh_symbols_for_category(self):
        providers = self._active_providers()

        examples = {}
        for provider in providers:
            examples.update(provider.get_example_symbols())

        for row in load_asset_memory():
            if row.get("category") != self.category_var.get():
                continue
            examples[row["symbol"]] = row["label"]

        sorted_items = sorted(examples.items(), key=lambda kv: kv[1].lower())
        labels = [label for _, label in sorted_items]
        self._symbol_label_to_code = {label: code for code, label in sorted_items}
        self.symbol_combo.set_completion_list(labels)
        if labels:
            self.symbol_var.set(labels[0])

    def _on_fetch_clicked(self):
        provider = self._provider_for_selection()
        label = self.symbol_var.get()
        if provider is None or not label:
            return
        code = provider.normalize_symbol(self._symbol_label_to_code.get(label, label))

        self._set_text(self.result_text, "Pobieranie...")
        self._set_text(self.note_text, "")
        self.compare_tree.delete(*self.compare_tree.get_children())

        def worker():
            try:
                quote = provider.get_quote(code)
                text = f"{quote.display_name}: {format_price(quote.price)} {quote.currency}"
                full_note = quote.note or ""
                display_note = full_note
                if quote.url:
                    full_note = f"{full_note} [Link: {quote.url}]"
                    display_note = f"{display_note} [Link]"
                alert_message = self._evaluate_alerts_for_quote(code, label, quote.price)
                self.after(0, self._apply_fetch_result, text, display_note, full_note, alert_message)
                return
            except AssetUnavailableError as exc:
                for alt_provider in self._active_providers():
                    if alt_provider.name == provider.name:
                        continue
                    try:
                        norm_code = alt_provider.normalize_symbol(self._symbol_label_to_code.get(label, label))
                        quote = alt_provider.get_quote(norm_code)
                        text = f"{quote.display_name}: {format_price(quote.price)} {quote.currency}"
                        full_note = quote.note or ""
                        display_note = full_note
                        if quote.url:
                            full_note = f"{full_note} [Link: {quote.url}]"
                            display_note = f"{display_note} [Link]"
                        alert_message = self._evaluate_alerts_for_quote(norm_code, label, quote.price)
                        self.after(0, self._apply_fetch_result, text, display_note, full_note, alert_message)
                        return
                    except Exception:
                        continue
                self.after(0, self._apply_fetch_result, "Błąd", str(exc), str(exc))
                return
            except Exception as exc:  # noqa: BLE001
                msg = f"Nieoczekiwany błąd: {exc}"
                self.after(0, self._apply_fetch_result, "Błąd", msg, msg)
                return

        threading.Thread(target=worker, daemon=True).start()

    def _set_text(self, widget: tk.Text, text: str):
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _apply_fetch_result(self, text: str, display_note: str, full_note: str, alert_message: str = ""):
        self._set_text(self.result_text, text)
        self._set_text(self.note_text, display_note)
        self._last_full_note = full_note
        if alert_message:
            self.alert_status_var.set(alert_message)
            messagebox.showinfo("Alert cenowy", alert_message)

    def _on_add_alert_clicked(self):
        if self.category_var.get().lower() != "crypto":
            self.alert_status_var.set("Alerty cenowe sa obecnie dostepne dla kategorii Crypto")
            return

        provider = self._provider_for_selection()
        label = self.symbol_var.get().strip()
        if provider is None or not label:
            self.alert_status_var.set("Wybierz symbol")
            return

        try:
            threshold = float(self.alert_threshold_var.get().replace(",", "."))
        except ValueError:
            self.alert_status_var.set("Nieprawidlowy prog alertu")
            return

        symbol = provider.normalize_symbol(self._symbol_label_to_code.get(label, label))
        condition = self.alert_condition_var.get().strip().lower()
        if condition not in {"above", "below"}:
            condition = "above"

        add_price_alert(
            category=self.category_var.get(),
            symbol=symbol,
            label=label,
            condition=condition,
            threshold=threshold,
        )
        sign = ">=" if condition == "above" else "<="
        self.alert_status_var.set(f"Alert zapisany: {symbol} {sign} {format_price(threshold)}")

    def _evaluate_alerts_for_quote(self, symbol: str, label: str, price: float) -> str:
        if self.category_var.get().lower() != "crypto":
            return ""

        candidates = {symbol.upper()}
        mapped = self._symbol_label_to_code.get(label, "")
        if mapped:
            candidates.add(str(mapped).upper())

        triggered = []
        for candidate in candidates:
            triggered.extend(
                evaluate_price_alerts(
                    category=self.category_var.get(),
                    symbol=candidate,
                    price=float(price),
                )
            )

        if not triggered:
            return ""

        parts = []
        for alert in triggered:
            sign = ">=" if alert.condition == "above" else "<="
            parts.append(f"{alert.symbol} {sign} {format_price(alert.threshold)}")
        return f"Aktywowano alert: {', '.join(parts)}"

    def _on_search_clicked(self):
        query = self.search_var.get().strip()
        if len(query) < 2:
            self.search_status_var.set("Wpisz min. 2 znaki")
            return

        self.search_tree.delete(*self.search_tree.get_children())
        providers = self._providers_for_category(self.category_var.get())
        self.search_status_var.set("Wyszukiwanie...")
        self.search_progress.start(10)

        def worker():
            merged = []
            seen = set()
            for provider in providers:
                try:
                    rows = provider.search_assets(query, limit=25)
                except Exception:
                    rows = []
                for row in rows:
                    key = (row.symbol, row.source)
                    if key in seen:
                        continue
                    seen.add(key)
                    merged.append(row)
            merged.sort(key=lambda x: (x.symbol, x.source))
            self.after(0, self._display_search_results, merged)

        threading.Thread(target=worker, daemon=True).start()

    def _display_search_results(self, rows):
        self.search_progress.stop()
        for row in rows:
            self.search_tree.insert(
                "",
                "end",
                values=(row.source, row.symbol, row.display_name, row.engine, row.protocol, row.note),
            )
        self.search_status_var.set(f"Znaleziono: {len(rows)}")

    def _on_add_search_result_clicked(self):
        selected = self.search_tree.selection()
        if not selected:
            return
        item_id = selected[0]
        source, symbol, name, engine, protocol, _note = self.search_tree.item(item_id, "values")
        label = f"{name} ({symbol})"

        upsert_asset_memory_item(
            category=self.category_var.get(),
            symbol=str(symbol),
            label=label,
            source=str(source),
            engine=str(protocol or engine),
        )
        self._refresh_symbols_for_category()
        self.symbol_var.set(label)

    def _on_compare_sources_clicked(self):
        label = self.symbol_var.get()
        if not label:
            return
        code = self._symbol_label_to_code.get(label, label)
        providers = self._providers_for_category(self.category_var.get())
        if not providers:
            return
        self.compare_tree.delete(*self.compare_tree.get_children())

        def worker():
            rows = []
            for provider in providers:
                normalized = provider.normalize_symbol(code)
                try:
                    quote = provider.get_quote(normalized)
                    note = quote.note or ""
                    if quote.url:
                        note = f"{note} [Link]"
                    rows.append({
                        "provider": provider.name,
                        "price": format_price(quote.price),
                        "currency": quote.currency,
                        "note": note,
                        "is_http_error": False,
                    })
                except Exception as exc:  # noqa: BLE001
                    err = str(exc)
                    rows.append({
                        "provider": provider.name,
                        "price": "—",
                        "currency": "—",
                        "note": err,
                        "is_http_error": "HTTP" in err.upper(),
                    })
            self.after(0, self._display_compare_rows, rows)

        threading.Thread(target=worker, daemon=True).start()

    def _display_compare_rows(self, rows):
        self._last_compare_rows = rows
        self._refresh_compare_tree()

    def _refresh_compare_tree(self):
        self.compare_tree.delete(*self.compare_tree.get_children())
        rows = getattr(self, "_last_compare_rows", [])
        hide_http = self.hide_http_errors_var.get()
        for row in rows:
            if hide_http and row.get("is_http_error"):
                continue
            self.compare_tree.insert(
                "",
                "end",
                values=(row.get("provider"), row.get("price"), row.get("currency"), row.get("note")),
            )


    def _on_chart_clicked(self):
        provider = self._provider_for_selection()
        label = self.symbol_var.get()
        if provider is None or not label:
            return
        code = provider.normalize_symbol(self._symbol_label_to_code.get(label, label))

        threading.Thread(target=self._fetch_and_plot_asset, args=(provider, code), daemon=True).start()

    def _fetch_and_plot_asset(self, provider, symbol):
        try:
            quotes = provider.get_historical(symbol)
            if not quotes:
                return
            dates = [q.timestamp for q in quotes]
            prices = [q.price for q in quotes]
            self.after(
                0,
                open_chart_window,
                self,
                symbol,
                quotes[0].currency,
                dates,
                prices,
                self.smooth_micro_chart_var.get(),
            )
        except Exception as e:
            self.after(0, messagebox.showerror, "Błąd", f"Nie udało się pobrać danych historycznych: {e}")


def run_app():
    app = CurrencyCalculatorApp()
    app.mainloop()
