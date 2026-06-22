import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.core.timing import TimingCollector

logger = logging.getLogger("uit.timing.middleware")

_COLD_START_TIME: float = time.perf_counter()
_COLD_START_RECORDED: bool = False


def record_cold_start() -> dict:
    global _COLD_START_RECORDED
    elapsed_ms = (time.perf_counter() - _COLD_START_TIME) * 1000.0
    data = {
        "cold_start_ms": round(elapsed_ms, 1),
        "cold_start_time": _COLD_START_TIME,
    }
    if not _COLD_START_RECORDED:
        logger.info("[TIMING] Cold Start (module import -> first request): %.1f ms", elapsed_ms)
        _COLD_START_RECORDED = True
    return data


class TimingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.app_init_time = time.perf_counter()

    async def dispatch(self, request: Request, call_next) -> Response:
        collector = TimingCollector()
        collector.start("Request Received")
        cold_start = record_cold_start()
        collector.start("Auth / Header Parsing")
        request.state.timing = collector
        request.state.cold_start_ms = cold_start["cold_start_ms"]
        collector.stop("Auth / Header Parsing")

        collector.start("Route Handler / Service Logic")
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            collector.stop("Route Handler / Service Logic")
            collector.start("Error Response")
            raise
        finally:
            if collector._active:
                while collector._active:
                    collector.stop()

        collector.stop("Route Handler / Service Logic")
        collector.start("Response Build / Serialization")

        timings = collector.as_dict()
        total_ms = collector.total_ms
        report = collector.report()
        logger.info("\n%s\n  %-40s %10.1f ms\n  %-40s %10.1f ms",
                     report, "Cold Start (init)", cold_start["cold_start_ms"],
                     "Total (wall-clock)", total_ms)

        response.headers["X-Timing-Total-Ms"] = str(round(total_ms, 1))
        response.headers["X-Timing-Cold-Start-Ms"] = str(cold_start["cold_start_ms"])
        for name, ms in timings.items():
            safe_name = name.replace(" ", "_").replace("/", "_")[:40]
            response.headers[f"X-Timing-{safe_name}"] = str(ms)

        collector.stop("Response Build / Serialization")
        return response