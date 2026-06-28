import time
from functools import wraps
from typing import Dict, Any, Tuple

class SimpleCache:
    """Prosty mechanizm cache'owania w pamięci."""
    def __init__(self, default_ttl: int = 3600):
        # value = (expires_at_timestamp, payload)
        self._cache: Dict[Tuple[Any, ...], Tuple[float, Any]] = {}
        self.default_ttl = default_ttl

    def get(self, key: Tuple[Any, ...]) -> Any:
        if key in self._cache:
            expires_at, value = self._cache[key]
            if time.time() < expires_at:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: Tuple[Any, ...], value: Any, ttl: int | None = None):
        ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + max(0, ttl)
        self._cache[key] = (expires_at, value)

_global_cache = SimpleCache()


def cached_quote(ttl: int = 3600):
    """Dekorator do cache'owania wyników get_quote."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, base_symbol: str, quote_symbol: str, *args, **kwargs):
            key = (self.name, "quote", base_symbol, quote_symbol)
            cached_val = _global_cache.get(key)
            if cached_val is not None:
                return cached_val
            
            result = func(self, base_symbol, quote_symbol, *args, **kwargs)
            _global_cache.set(key, result, ttl)
            return result
        return wrapper
    return decorator

def cached_historical(ttl: int = 3600):
    """Dekorator do cache'owania wyników get_historical."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, base_symbol: str, quote_symbol: str, *args, **kwargs):
            # Tworzymy klucz uwzględniając argumenty pozycyjne i nazwane (np. period)
            key = (self.name, "historical", base_symbol, quote_symbol, args, tuple(sorted(kwargs.items())))
            cached_val = _global_cache.get(key)
            if cached_val is not None:
                return cached_val
            
            result = func(self, base_symbol, quote_symbol, *args, **kwargs)
            _global_cache.set(key, result, ttl)
            return result
        return wrapper
    return decorator
