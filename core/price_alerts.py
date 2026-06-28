from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Literal

AlertCondition = Literal["above", "below"]


@dataclass
class PriceAlert:
    category: str
    symbol: str
    label: str
    condition: AlertCondition
    threshold: float
    is_active: bool = True
    created_at: str = ""
    triggered_at: str = ""


_DEFAULT_ALERTS_PATH = Path("user_data") / "price_alerts.json"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_price_alerts(path: Path | str | None = None) -> list[PriceAlert]:
    storage = Path(path) if path else _DEFAULT_ALERTS_PATH
    if not storage.exists():
        return []
    try:
        payload = json.loads(storage.read_text(encoding="utf-8"))
    except Exception:
        return []
    alerts: list[PriceAlert] = []
    for row in payload if isinstance(payload, list) else []:
        try:
            alerts.append(PriceAlert(**row))
        except Exception:
            continue
    return alerts


def save_price_alerts(alerts: list[PriceAlert], path: Path | str | None = None) -> None:
    storage = Path(path) if path else _DEFAULT_ALERTS_PATH
    _ensure_parent(storage)
    payload = [asdict(a) for a in alerts]
    storage.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def add_price_alert(
    *,
    category: str,
    symbol: str,
    label: str,
    condition: AlertCondition,
    threshold: float,
    path: Path | str | None = None,
) -> PriceAlert:
    alerts = load_price_alerts(path)
    alert = PriceAlert(
        category=category,
        symbol=symbol.upper(),
        label=label,
        condition=condition,
        threshold=float(threshold),
        is_active=True,
        created_at=_now_iso(),
        triggered_at="",
    )
    alerts.append(alert)
    save_price_alerts(alerts, path)
    return alert


def evaluate_price_alerts(
    *,
    category: str,
    symbol: str,
    price: float,
    path: Path | str | None = None,
) -> list[PriceAlert]:
    alerts = load_price_alerts(path)
    triggered: list[PriceAlert] = []
    symbol_upper = symbol.upper()
    changed = False

    for alert in alerts:
        if not alert.is_active:
            continue
        if alert.category.lower() != category.lower():
            continue
        if alert.symbol.upper() != symbol_upper:
            continue

        hit = (alert.condition == "above" and price >= alert.threshold) or (
            alert.condition == "below" and price <= alert.threshold
        )
        if hit:
            alert.is_active = False
            alert.triggered_at = _now_iso()
            triggered.append(alert)
            changed = True

    if changed:
        save_price_alerts(alerts, path)
    return triggered


