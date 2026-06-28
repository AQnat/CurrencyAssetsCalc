import unittest
from unittest.mock import patch

from assets.crypto_market_providers import BinanceCryptoProvider
from assets.yahoo_assets import YahooCryptoProvider


class TestCryptoSearch(unittest.TestCase):
    def test_binance_search_does_not_require_hashable_instance(self):
        provider = BinanceCryptoProvider()
        with patch.object(provider, "_exchange_symbols", return_value=["GRASSUSDT", "BTCUSDT"]):
            rows = provider.search_assets("grass", limit=10)

        self.assertTrue(rows)
        self.assertEqual(rows[0].symbol, "GRASS-USD")
        self.assertEqual(rows[0].engine, "SOL")
        self.assertEqual(rows[0].protocol, "SPL")

    def test_yahoo_crypto_search_has_manual_fallback(self):
        provider = YahooCryptoProvider()
        with patch("assets.yahoo_assets._search_yahoo", side_effect=[[], []]):
            rows = provider.search_assets("grass", limit=10)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].symbol, "GRASS-USD")
        self.assertEqual(rows[0].engine, "SOL")
        self.assertEqual(rows[0].protocol, "SPL")


if __name__ == "__main__":
    unittest.main()


