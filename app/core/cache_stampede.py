import threading
from contextlib import contextmanager
from typing import Dict, Optional


class LockAcquisitionTimeout(Exception):
    pass


class StampedeGuard:
    def __init__(self):
        self._locks: Dict[str, threading.Lock] = {}
        self._lock = threading.Lock()

    def _get_lock(self, key: str) -> threading.Lock:
        with self._lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]

    def _cleanup_lock(self, key: str) -> None:
        with self._lock:
            lock = self._locks.get(key)
            if lock and not lock.locked():
                acquired = lock.acquire(blocking=False)
                if acquired:
                    lock.release()
                    del self._locks[key]

    def acquire(self, key: str, timeout: float = 5.0) -> "StampedeContext":
        return StampedeContext(self, key, timeout)

    def is_locked(self, key: str) -> bool:
        lock = self._locks.get(key)
        return lock is not None and lock.locked()


class StampedeContext:
    def __init__(self, guard: StampedeGuard, key: str, timeout: float):
        self.guard = guard
        self.key = key
        self.timeout = timeout
        self._lock: Optional[threading.Lock] = None
        self._acquired = False

    def __enter__(self):
        self._lock = self.guard._get_lock(self.key)
        acquired = self._lock.acquire(blocking=True, timeout=self.timeout)
        if not acquired:
            raise LockAcquisitionTimeout(
                f"Could not acquire stampede lock for '{self.key}' within {self.timeout}s"
            )
        self._acquired = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._acquired and self._lock:
            try:
                self._lock.release()
            except RuntimeError:
                pass
            finally:
                self._acquired = False
                self.guard._cleanup_lock(self.key)


_GUARD = StampedeGuard()


def stampede(key: str, timeout: float = 5.0) -> StampedeContext:
    return _GUARD.acquire(key, timeout)