import time
import logging
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger("uit.timing")


class TimingSpan:
    __slots__ = ("name", "start", "elapsed_ms")

    def __init__(self, name: str, start: float):
        self.name = name
        self.start = start
        self.elapsed_ms: Optional[float] = None

    def stop(self, now: Optional[float] = None) -> float:
        if now is None:
            now = time.perf_counter()
        self.elapsed_ms = (now - self.start) * 1000.0
        return self.elapsed_ms

    @property
    def ms(self) -> float:
        return self.elapsed_ms if self.elapsed_ms is not None else 0.0

    def __repr__(self) -> str:
        return f"[TIMING] {self.name}: {self.ms:.1f} ms"

    def __str__(self) -> str:
        return self.__repr__()


class TimingCollector:
    def __init__(self):
        self.spans: list[TimingSpan] = []
        self._active: list[TimingSpan] = []

    def start(self, name: str) -> TimingSpan:
        span = TimingSpan(name, time.perf_counter())
        self._active.append(span)
        return span

    def stop(self, name: Optional[str] = None) -> Optional[TimingSpan]:
        if not self._active:
            return None
        span = self._active.pop()
        span.stop()
        self.spans.append(span)
        return span

    def span(self, name: str) -> "TimingContextManager":
        return TimingContextManager(self, name)

    def report(self) -> str:
        if not self.spans:
            return "[TIMING] No measurements collected."
        lines = ["[TIMING] Request Lifecycle:"]
        for s in self.spans:
            lines.append(f"  {s.name:40s} {s.ms:10.1f} ms")
        total_measured = sum(s.ms for s in self.spans)
        lines.append(f"  {'TOTAL (measured)':40s} {total_measured:10.1f} ms")
        lines.append(f"  {'TOTAL (wall-clock)':40s} {self.total_ms:10.1f} ms")
        return "\n".join(lines)

    @property
    def total_ms(self) -> float:
        if not self.spans:
            return 0.0
        first = self.spans[0].start
        last = self.spans[-1].start + (self.spans[-1].elapsed_ms or 0) / 1000.0
        return (last - first) * 1000.0

    def as_dict(self) -> dict[str, float]:
        return {s.name: round(s.ms, 1) for s in self.spans}


class TimingContextManager:
    def __init__(self, collector: TimingCollector, name: str):
        self.collector = collector
        self.name = name
        self.span: Optional[TimingSpan] = None

    def __enter__(self) -> TimingSpan:
        self.span = self.collector.start(self.name)
        return self.span

    def __exit__(self, *args) -> None:
        if self.span:
            self.span.stop()
            self.collector.spans.append(self.span)

    def __repr__(self) -> str:
        return f"<TimingContextManager '{self.name}'>"


_request_collector: "threading.local" = None


def get_current_collector() -> TimingCollector:
    import threading
    global _request_collector
    if _request_collector is None:
        _request_collector = threading.local()
    if not hasattr(_request_collector, "collector"):
        _request_collector.collector = TimingCollector()
    return _request_collector.collector


def reset_collector() -> None:
    import threading
    global _request_collector
    if _request_collector is not None:
        _request_collector.collector = TimingCollector()


@contextmanager
def time_block(name: str, log: bool = True):
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = (time.perf_counter() - start) * 1000.0
        if log:
            logger.info("[TIMING] %s: %.1f ms", name, elapsed)


def time_func(func):
    import functools
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = (time.perf_counter() - start) * 1000.0
            logger.debug("[TIMING] %s: %.1f ms", func.__name__, elapsed)
    return wrapper