import time
from collections import defaultdict, deque


class LoginLimiter:
    """Failed logins per (email, IP) in a sliding window (in memory: per process)."""

    def __init__(self, max_failures: int, window_s: float) -> None:
        self.max_failures = max_failures
        self.window_s = window_s
        self._failures: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def _recent(self, key: tuple[str, str]) -> deque[float]:
        q = self._failures[key]
        cutoff = time.monotonic() - self.window_s
        while q and q[0] < cutoff:
            q.popleft()
        return q

    def blocked(self, email: str, ip: str) -> bool:
        return len(self._recent((email, ip))) >= self.max_failures

    def failed(self, email: str, ip: str) -> None:
        self._recent((email, ip)).append(time.monotonic())

    def reset(self, email: str, ip: str) -> None:
        self._failures.pop((email, ip), None)
