"""Lightweight in-process runtime metrics for admin dashboards."""

from __future__ import annotations

from collections import deque
from threading import Lock
from time import monotonic
from typing import Deque, Tuple

from sqlalchemy import event
from sqlalchemy.engine import Engine

WINDOW_SECONDS = 60.0
MAX_REQUEST_SAMPLES = 5000
MAX_DB_SAMPLES = 5000


class RuntimeMetrics:
    """Thread-safe rolling metrics snapshots for request and DB performance."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._request_samples: Deque[Tuple[float, float, bool]] = deque(maxlen=MAX_REQUEST_SAMPLES)
        self._db_samples: Deque[Tuple[float, float]] = deque(maxlen=MAX_DB_SAMPLES)

    def record_request(self, duration_ms: float, status_code: int) -> None:
        now = monotonic()
        is_error = status_code >= 400
        with self._lock:
            self._request_samples.append((now, duration_ms, is_error))
            self._prune_locked(now)

    def record_db_query(self, duration_ms: float) -> None:
        now = monotonic()
        with self._lock:
            self._db_samples.append((now, duration_ms))
            self._prune_locked(now)

    def snapshot(self) -> dict[str, float]:
        now = monotonic()
        with self._lock:
            self._prune_locked(now)
            req_count = len(self._request_samples)
            db_count = len(self._db_samples)

            requests_per_sec = req_count / WINDOW_SECONDS
            avg_response_ms = (
                sum(sample[1] for sample in self._request_samples) / req_count if req_count else 0.0
            )
            error_rate_percent = (
                (sum(1 for sample in self._request_samples if sample[2]) / req_count) * 100.0
                if req_count
                else 0.0
            )
            avg_db_query_ms = (
                sum(sample[1] for sample in self._db_samples) / db_count if db_count else 0.0
            )

        return {
            "requests_per_sec": requests_per_sec,
            "avg_response_ms": avg_response_ms,
            "error_rate_percent": error_rate_percent,
            "avg_db_query_ms": avg_db_query_ms,
        }

    def _prune_locked(self, now: float) -> None:
        cutoff = now - WINDOW_SECONDS

        while self._request_samples and self._request_samples[0][0] < cutoff:
            self._request_samples.popleft()

        while self._db_samples and self._db_samples[0][0] < cutoff:
            self._db_samples.popleft()


_RUNTIME_METRICS = RuntimeMetrics()


def get_runtime_metrics() -> dict[str, float]:
    """Return a rolling snapshot of runtime metrics."""
    return _RUNTIME_METRICS.snapshot()


def record_request_metric(duration_ms: float, status_code: int) -> None:
    """Record a completed HTTP request."""
    _RUNTIME_METRICS.record_request(duration_ms=duration_ms, status_code=status_code)


def register_sqlalchemy_metrics(engine: Engine) -> None:
    """Attach SQLAlchemy listeners to capture DB query durations."""
    if getattr(engine, "_kenji_metrics_registered", False):
        return

    @event.listens_for(engine, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("_kenji_query_start_times", []).append(monotonic())

    @event.listens_for(engine, "after_cursor_execute")
    def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        start_times = conn.info.get("_kenji_query_start_times", None)
        if not start_times:
            return

        start_time = start_times.pop()
        _RUNTIME_METRICS.record_db_query((monotonic() - start_time) * 1000.0)

    @event.listens_for(engine, "handle_error")
    def _handle_error(exception_context):
        conn = exception_context.connection
        if conn is None:
            return

        start_times = conn.info.get("_kenji_query_start_times", None)
        if not start_times:
            return

        start_time = start_times.pop()
        _RUNTIME_METRICS.record_db_query((monotonic() - start_time) * 1000.0)

    setattr(engine, "_kenji_metrics_registered", True)
