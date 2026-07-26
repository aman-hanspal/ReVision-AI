"""
backend/main.py — FastAPI entrypoint for ReVision.

WHAT:  HTTP + SSE API wrapping the ReVision agent/pipeline. The frontend calls
       these routes; long operations stream live progress (the same progress.emit
       events you see in the terminal) over Server-Sent Events.
USED BY: the frontend (frontend/src/lib/api.ts).
ROUTES:
       GET  /health              -> sanity check
       POST /upload              -> ingest a lecture (URL) -> {video_id, title, length}
       POST /chat  (SSE)         -> run the agent; streams progress, ends with result
KEY EXPORTS: app (the FastAPI instance).
RUN:   uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared import videodb_service as vdb
from backend.routes import chat, upload

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(name)s  %(message)s", datefmt="%H:%M:%S")

app = FastAPI(title="ReVision API", version="1.0")

# CORS — allow the local frontend (Vite dev server) to call us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # tighten for production; fine for the hackathon
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Lightweight sanity check + config summary (no secrets)."""
    return {"status": "ok", "service": "revision", "model": _safe_model()}


def _safe_model():
    try:
        from shared import config
        return config.AGENT_MODEL
    except Exception:
        return "unknown"


app.include_router(upload.router)
app.include_router(chat.router)