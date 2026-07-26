"""
backend/routes/chat.py — the main endpoint: run the agent, stream live progress.

POST /chat  {"message": "...", "video_id": "m-..."}  (SSE response)

The agent runs in a BACKGROUND THREAD. While it works, every progress.emit() event
(the same traces you see in the terminal — "Slide 2/5: generating image…") is pushed
onto a queue and streamed to the browser as a Server-Sent Event. When the agent
finishes, a final "result" event carries the reply text + display payloads
(clip/reel/video URLs, flashcards, cue cards), then a "done" event closes the stream.

SSE event shapes (all JSON in the `data:` field):
  {"type": "progress", "message": "...", "kind": "step"}
  {"type": "result", "reply": "...", "displays": [ ... ]}
  {"type": "error",   "message": "..."}
  {"type": "done"}
"""
from __future__ import annotations

import json
import logging
import queue
import threading

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from shared import progress
from backend.agent.revision_agent import run_agent

logger = logging.getLogger("revision.api.chat")
router = APIRouter()

_SENTINEL = object()   # marks end of stream


class ChatRequest(BaseModel):
    message: str
    video_id: str = ""


def _sse(payload: dict) -> str:
    """Format a dict as one SSE 'data:' frame."""
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/chat")
def chat(req: ChatRequest):
    """Run the agent and stream progress + final result as SSE."""
    q: "queue.Queue" = queue.Queue()

    # progress listener: push every emit() event onto this request's queue
    def on_event(event: dict):
        q.put({"type": "progress",
               "message": event.get("message", ""),
               "kind": event.get("kind", "step")})

    def worker():
        progress.subscribe(on_event)
        try:
            reply, displays, _history = run_agent(req.message, video_id=req.video_id)
            q.put({"type": "result", "reply": reply, "displays": displays})
        except Exception as e:
            logger.exception("agent run failed")
            q.put({"type": "error", "message": str(e)})
        finally:
            progress.unsubscribe(on_event)
            q.put(_SENTINEL)

    threading.Thread(target=worker, daemon=True).start()

    def event_stream():
        # initial ping so the client knows the stream is open
        yield _sse({"type": "progress", "message": "Starting…", "kind": "step"})
        while True:
            try:
                item = q.get(timeout=8)      # wake every 8s to send a heartbeat
            except queue.Empty:
                # keep the connection alive during long silent steps (e.g. ask() calls)
                yield ": keepalive\n\n"
                continue
            if item is _SENTINEL:
                yield _sse({"type": "done"})
                break
            yield _sse(item)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no",
                 "Connection": "keep-alive"},
    )