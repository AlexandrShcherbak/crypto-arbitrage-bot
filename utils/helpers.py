from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Deque, Dict, Generic, Optional, TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")


@dataclass
class CacheItem(Generic[T]):
    value: T
    expires_at: float


class AsyncTTLCache(Generic[T]):
    """Простой async-safe TTL cache."""

    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._data: Dict[str, CacheItem[T]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[T]:
        async with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            if item.expires_at < time.time():
                self._data.pop(key, None)
                return None
            return item.value

    async def set(self, key: str, value: T, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        async with self._lock:
            self._data[key] = CacheItem(value=value, expires_at=time.time() + ttl)


class AsyncRateLimiter:
    """Token bucket-like limiter: не более `max_calls` за `period_sec`."""

    def __init__(self, max_calls: int, period_sec: float) -> None:
        self.max_calls = max_calls
        self.period_sec = period_sec
        self._calls: Deque[float] = deque()
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            while self._calls and now - self._calls[0] > self.period_sec:
                self._calls.popleft()

            if len(self._calls) >= self.max_calls:
                sleep_for = self.period_sec - (now - self._calls[0])
                await asyncio.sleep(max(sleep_for, 0))
            self._calls.append(time.monotonic())


def retry_async(retries: int = 3, delay: float = 1.0, backoff: float = 2.0) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay
            last_error: Exception | None = None
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    logger.warning("Retry %s/%s for %s due to: %s", attempt + 1, retries, func.__name__, exc)
                    if attempt < retries - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            assert last_error is not None
            raise last_error

        return wrapper

    return decorator
