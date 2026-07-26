"""
shared/progress.py — one place to emit progress/trace events.

WHAT:  a tiny pub-sub for progress events. Pipeline code calls emit("message")
       at each meaningful step. By default events print to the terminal (via the
       logger). The backend can register a listener to stream the SAME events to
       the frontend (SSE/websocket) — so terminal and UI show identical traces.
USED BY: shared/generate.py, retrieval.py, videodb_service.py (emit points);
       backend routes (register a listener to forward to the client).
KEY EXPORTS: emit(msg, **data), step(msg) context manager, subscribe(fn), unsubscribe(fn).
"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Callable, Dict, List

logger = logging.getLogger("revision.progress")

_listeners: List[Callable[[Dict], None]] = []


def subscribe(fn: Callable[[Dict], None]) -> None:
    """Register a listener (e.g. the backend forwarding events to the UI)."""
    if fn not in _listeners:
        _listeners.append(fn)


def unsubscribe(fn: Callable[[Dict], None]) -> None:
    if fn in _listeners:
        _listeners.remove(fn)


def emit(message: str, kind: str = "step", **data) -> None:
    """Emit a progress event: logs to terminal AND notifies any listeners."""
    event = {"ts": time.time(), "kind": kind, "message": message, **data}
    # terminal
    logger.info("• %s", message)
    # listeners (frontend stream, etc.) — never let a bad listener break the pipeline
    for fn in list(_listeners):
        try:
            fn(event)
        except Exception:
            logger.debug("progress listener failed", exc_info=True)


@contextmanager
def step(message: str, **data):
    """Context manager that emits start + done (with elapsed) for a step."""
    emit(message, kind="step_start", **data)
    t = time.time()
    try:
        yield
    finally:
        emit(f"{message} — done ({time.time()-t:.1f}s)", kind="step_done", **data)