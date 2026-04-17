from __future__ import annotations

import time
from enum import Enum
from threading import Lock
from typing import Callable, TypeVar

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpen(RuntimeError):
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout_s: float = 15.0) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout_s = recovery_timeout_s
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at = 0.0
        self._lock = Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    def call(self, fn: Callable[..., T], *args, **kwargs) -> T:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if (time.time() - self._opened_at) >= self._recovery_timeout_s:
                    self._state = CircuitState.HALF_OPEN
                else:
                    raise CircuitBreakerOpen("Circuit breaker is OPEN")

        try:
            result = fn(*args, **kwargs)
        except Exception:
            with self._lock:
                self._failures += 1
                if self._failures >= self._failure_threshold:
                    self._state = CircuitState.OPEN
                    self._opened_at = time.time()
            raise

        with self._lock:
            self._failures = 0
            self._state = CircuitState.CLOSED
        return result


def retry_with_backoff(
    fn: Callable[..., T],
    *args,
    max_attempts: int = 2,
    initial_delay_s: float = 0.05,
    **kwargs,
) -> T:
    attempt = 1
    delay = initial_delay_s
    while True:
        try:
            return fn(*args, **kwargs)
        except Exception:
            if attempt >= max_attempts:
                raise
            time.sleep(delay)
            delay *= 2
            attempt += 1
