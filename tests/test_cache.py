import unittest
from core.cache import SimpleCache

class TestSimpleCache(unittest.TestCase):
    def test_set_and_get(self):
        cache = SimpleCache(default_ttl=10)
        cache.set(("key1",), "value1")
        self.assertEqual(cache.get(("key1",)), "value1")

    def test_expiration(self):
        cache = SimpleCache(default_ttl=0) # Natychmiastowe wygaśnięcie
        cache.set(("key1",), "value1")
        self.assertIsNone(cache.get(("key1",)))

    def test_none_for_missing_key(self):
        cache = SimpleCache()
        self.assertIsNone(cache.get(("missing",)))

    def test_custom_ttl_override(self):
        cache = SimpleCache(default_ttl=3600)
        cache.set(("key2",), "value2", ttl=0)
        self.assertIsNone(cache.get(("key2",)))

if __name__ == '__main__':
    unittest.main()
