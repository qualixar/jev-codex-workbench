import unittest
from cache import TTLCache

class CacheTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.cache = TTLCache(lambda: self.now)
    def test_fresh_value(self):
        self.cache.put('item', 'value', 5)
        self.now = 104.0
        self.assertEqual(self.cache.get('item'), 'value')
    def test_after_expiry(self):
        self.cache.put('item', 'value', 5)
        self.now = 105.1
        self.assertIsNone(self.cache.get('item'))
    def test_at_exact_expiry(self):
        self.cache.put('item', 'value', 5)
        self.now = 105.0
        self.assertIsNone(self.cache.get('item'))
    def test_negative_ttl_rejected(self):
        with self.assertRaises(ValueError):
            self.cache.put('item', 'value', -1)

if __name__ == '__main__':
    unittest.main()
