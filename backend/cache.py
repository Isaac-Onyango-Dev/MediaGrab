import time
import threading
from typing import Any, Dict, Optional

class SimpleCache:
    """ A thread-safe, in-memory cache with TTL support. """
    def __init__(self, default_ttl: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            
            item = self._cache[key]
            if time.time() > item["expiry"]:
                del self._cache[key]
                return None
            
            return item["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        with self._lock:
            expiry = time.time() + (ttl if ttl is not None else self._default_ttl)
            self._cache[key] = {
                "value": value,
                "expiry": expiry
            }

    def cleanup_expired(self):
        """ Remove all expired items from the cache. """
        with self._lock:
            now = time.time()
            expired_keys = [k for k, v in self._cache.items() if now > v["expiry"]]
            for k in expired_keys:
                del self._cache[k]

# Global instances as requested by the backend system
url_analysis_cache = SimpleCache(default_ttl=3600)  # 1 hour
format_cache = SimpleCache(default_ttl=1800)        # 30 mins
