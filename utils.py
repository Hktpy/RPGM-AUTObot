import json
import time
from typing import Any


class RateLimiter:
    """Simple rate limiter based on a minimum interval in milliseconds."""

    def __init__(self, min_interval_ms: int):
        self._interval = max(0, int(min_interval_ms)) / 1000.0
        self._last = 0.0

    def allow(self) -> bool:
        """Return True if enough time has passed since the last allow."""
        now = time.perf_counter()
        if now - self._last >= self._interval:
            self._last = now
            return True
        return False


def log_line(data: Any, as_json: bool = False) -> None:
    """Print a data object either as raw text or JSON."""
    if as_json:
        try:
            print(json.dumps(data, ensure_ascii=False))
        except TypeError:
            print(json.dumps(str(data), ensure_ascii=False))
    else:
        print(data)
