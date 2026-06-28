from pathlib import Path
import tempfile
import unittest

from core.price_alerts import add_price_alert, evaluate_price_alerts, load_price_alerts


class TestPriceAlerts(unittest.TestCase):
    def test_alert_is_persisted_and_triggers_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = Path(tmp) / "alerts.json"
            add_price_alert(
                category="Crypto",
                symbol="GRASS-USD",
                label="Grass (GRASS-USD)",
                condition="above",
                threshold=0.5,
                path=storage,
            )
            alerts = load_price_alerts(storage)
            self.assertEqual(len(alerts), 1)
            self.assertTrue(alerts[0].is_active)

            triggered = evaluate_price_alerts(category="Crypto", symbol="GRASS-USD", price=0.6, path=storage)
            self.assertEqual(len(triggered), 1)

            triggered_again = evaluate_price_alerts(category="Crypto", symbol="GRASS-USD", price=0.7, path=storage)
            self.assertEqual(triggered_again, [])


if __name__ == "__main__":
    unittest.main()

