from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

_STORE_LOCK = Lock()
_STORE_DIR = Path(__file__).resolve().parent.parent / "user_data"
_STORE_PATH = _STORE_DIR / "custom_assets.json"


def _default_payload() -> dict[str, Any]:
    return {"items": []}


def load_asset_memory() -> list[dict[str, str]]:
    """Load user-added assets persisted across sessions."""
    if not _STORE_PATH.exists():
        return []

    try:
        payload = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    items = payload.get("items", []) if isinstance(payload, dict) else []
    valid_items: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        category = str(item.get("category", "")).strip()
        symbol = str(item.get("symbol", "")).strip()
        label = str(item.get("label", "")).strip()
        source = str(item.get("source", "manual")).strip() or "manual"
        engine = str(item.get("engine", "")).strip()
        if not category or not symbol or not label:
            continue
        valid_items.append(
            {
                "category": category,
                "symbol": symbol,
                "label": label,
                "source": source,
                "engine": engine,
            }
        )
    return valid_items


def save_asset_memory(items: list[dict[str, str]]) -> None:
    _STORE_DIR.mkdir(parents=True, exist_ok=True)
    payload = _default_payload()
    payload["items"] = items
    _STORE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert_asset_memory_item(
    *,
    category: str,
    symbol: str,
    label: str,
    source: str,
    engine: str = "",
) -> list[dict[str, str]]:
    """Insert or update one stored asset and return the full list."""
    category = category.strip()
    symbol = symbol.strip().upper()
    label = label.strip()
    source = source.strip() or "manual"
    engine = engine.strip()
    if not category or not symbol or not label:
        return load_asset_memory()

    with _STORE_LOCK:
        items = load_asset_memory()
        replaced = False
        for item in items:
            if item.get("category") == category and item.get("symbol") == symbol:
                item["label"] = label
                item["source"] = source
                item["engine"] = engine
                replaced = True
                break
        if not replaced:
            items.append(
                {
                    "category": category,
                    "symbol": symbol,
                    "label": label,
                    "source": source,
                    "engine": engine,
                }
            )
        save_asset_memory(items)
        return items

