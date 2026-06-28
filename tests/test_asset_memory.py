import tempfile
import unittest
from pathlib import Path

import core.asset_memory as asset_memory


class TestAssetMemory(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

        self.orig_store_dir = asset_memory._STORE_DIR
        self.orig_store_path = asset_memory._STORE_PATH

        store_dir = Path(self.tmp_dir.name)
        asset_memory._STORE_DIR = store_dir
        asset_memory._STORE_PATH = store_dir / "custom_assets.json"

    def tearDown(self):
        asset_memory._STORE_DIR = self.orig_store_dir
        asset_memory._STORE_PATH = self.orig_store_path

    def test_upsert_and_load(self):
        asset_memory.upsert_asset_memory_item(
            category="Crypto Exchanges",
            symbol="btc-usd",
            label="Bitcoin (BTC/USD)",
            source="Yahoo Finance",
            engine="Bitcoin",
        )

        rows = asset_memory.load_asset_memory()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["symbol"], "BTC-USD")
        self.assertEqual(rows[0]["engine"], "Bitcoin")

    def test_upsert_replaces_existing_item(self):
        asset_memory.upsert_asset_memory_item(
            category="Crypto Exchanges",
            symbol="BTC-USD",
            label="Bitcoin old",
            source="Yahoo Finance",
        )
        asset_memory.upsert_asset_memory_item(
            category="Crypto Exchanges",
            symbol="BTC-USD",
            label="Bitcoin new",
            source="CoinGecko",
        )

        rows = asset_memory.load_asset_memory()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["label"], "Bitcoin new")
        self.assertEqual(rows[0]["source"], "CoinGecko")


if __name__ == "__main__":
    unittest.main()

