import time
from collections import defaultdict, deque


class RateLimiter:
    """Basit, süreç-içi kayan pencere. Tek uvicorn worker için yeterlidir."""

    def __init__(self) -> None:
        self._events: dict[tuple, deque] = defaultdict(deque)

    def allow(self, key: tuple, limit: int, window: float = 60.0) -> bool:
        now = time.monotonic()
        dq = self._events[key]
        while dq and now - dq[0] > window:
            dq.popleft()
        if len(dq) >= limit:
            return False
        dq.append(now)
        return True


rate_limiter = RateLimiter()
