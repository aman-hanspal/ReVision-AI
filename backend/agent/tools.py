"""
backend/agent/tools.py — the agent's toolbox.

WHAT:  wraps ReVision's pipeline (shared/) as high-level tools the LLM can call.
       Each tool has (a) an OpenAI tool schema the model sees, and (b) an impl
       that runs the real pipeline and returns BOTH a short text result (fed back
       to the model) and a display payload (URLs/cards the runner shows the user).
USED BY: backend/agent/revision_agent.py (the tool-loop).
KEY EXPORTS: TOOL_SCHEMAS (list for the LLM), execute_tool(name, args) -> (text, display).
NOTES: tools are high-level on purpose (ingest / study_pack / learning_video /
       reel / search) so the model composes intent, never raw SDK calls.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Tuple

from shared import retrieval, generate, telegram_service
from shared.progress import emit
from shared import videodb_service as vdb

logger = logging.getLogger("revision.agent.tools")


# ---------------------------------------------------------------------------
# Tool implementations — each returns (text_for_model, display_payload)
# ---------------------------------------------------------------------------
def _ingest_lecture(url: str = None, **_) -> Tuple[str, Dict]:
    ref = retrieval.ingest(url=url)
    return (f"Indexed lecture. video_id={ref.video_id}, title='{ref.title}', "
            f"length={ref.length:.0f}s. Use this video_id for further tools.",
            {"kind": "ingest", "video_id": ref.video_id, "title": ref.title})


def _search_topic(video_id: str, query: str, **_) -> Tuple[str, Dict]:
    hits = retrieval.find_topic(video_id, query, top_k=5)
    lines = [f"{h.start:.0f}-{h.end:.0f}s (score {h.score:.2f})" for h in hits]
    return (f"Found {len(hits)} moments for '{query}': " + "; ".join(lines or ["none"]),
            {"kind": "search", "query": query, "moments": lines})


def _make_summary_reel(video_id: str, topic: str, **_) -> Tuple[str, Dict]:
    reel = generate.make_summary_reel(video_id, topic)
    if not reel:
        return (f"Could not build a summary reel for '{topic}'.", {"kind": "reel"})
    return (f"Built a summary reel for '{topic}' spanning {reel.start:.0f}-{reel.end:.0f}s.",
            {"kind": "reel", "topic": topic, "summary_reel_url": reel.stream_url})


def _make_clip(video_id: str, topic: str, **_) -> Tuple[str, Dict]:
    clip = generate.make_precise_clip(video_id, topic)
    if not clip:
        return (f"Could not build a clip for '{topic}'.", {"kind": "clip"})
    return (f"Built a clip for '{topic}' ({clip.start:.0f}-{clip.end:.0f}s).",
            {"kind": "clip", "topic": topic, "clip_url": clip.stream_url})


def _make_learning_video(video_id: str, topic: str,
                         style: str = "clean flat-vector educational",
                         n_slides: int = 5, **_) -> Tuple[str, Dict]:
    storyboard = generate.plan_storyboard(topic, style=style, n_slides=n_slides)
    url, slides = generate.make_learning_video(storyboard)
    return (f"Generated a {len(slides)}-slide learning video for '{topic}' "
            f"(style: {style}).",
            {"kind": "learning_video", "topic": topic, "learning_video_url": url,
             "slides": len(slides)})


def _make_study_pack(video_id: str, topic: str, include_video: bool = False,
                     style: str = "clean flat-vector educational", **_) -> Tuple[str, Dict]:
    pack = generate.build_study_pack(video_id, topic, with_video=include_video,
                                     video_style=style)
    display = {
        "kind": "study_pack",
        "topic": topic,
        "summary": pack.summary.text if pack.summary else None,
        "single_clip_url": pack.clip.stream_url if pack.clip else None,
        "summary_reel_url": pack.summary_reel.stream_url if pack.summary_reel else None,
        "learning_video_url": pack.learning_video_url,
        "concept_image_url": pack.concept_image_url,
        "flashcards": [{"front": c.front, "back": c.back} for c in pack.flashcards],
        "cue_cards": [c.text for c in pack.cue_cards],
    }
    text = (f"Built study pack for '{topic}': summary + {len(pack.flashcards)} "
            f"flashcards + {len(pack.cue_cards)} cue cards; "
            f"clip={'yes' if pack.clip else 'no'}, "
            f"reel={'yes' if pack.summary_reel else 'no'}, "
            f"learning_video={'yes' if pack.learning_video_url else 'no'}.")
    return text, display


# ---------------------------------------------------------------------------
# Registry: name -> impl
# ---------------------------------------------------------------------------

def _send_to_telegram(displays=None, **_) -> Tuple[str, Dict]:
    """Send the study-pack results produced so far in THIS run to Telegram.
    The agent loop injects `displays` (everything generated earlier this turn)."""
    ok, message = telegram_service.send_study_pack(displays or [])
    return (message, {"kind": "telegram", "ok": ok, "message": message})


_REGISTRY = {
    "ingest_lecture": _ingest_lecture,
    "search_topic": _search_topic,
    "make_clip": _make_clip,
    "make_summary_reel": _make_summary_reel,
    "make_learning_video": _make_learning_video,
    "make_study_pack": _make_study_pack,
    "send_to_telegram": _send_to_telegram,
}


def execute_tool(name: str, args: Dict[str, Any]) -> Tuple[str, Dict]:
    """Run a tool by name. Returns (text_for_model, display_payload)."""
    fn = _REGISTRY.get(name)
    if fn is None:
        return (f"Unknown tool: {name}", {"kind": "error", "tool": name})
    try:
        logger.info("tool %s args=%s", name, args)
        emit(f"Running: {name}", kind="tool_start", tool=name, args=args)
        result = fn(**args)
        emit(f"Finished: {name}", kind="tool_done", tool=name)
        return result
    except Exception as e:
        logger.exception("tool %s failed", name)
        return (f"Tool {name} failed: {e}", {"kind": "error", "tool": name, "error": str(e)})


# ---------------------------------------------------------------------------
# OpenAI tool schemas (what the model sees)
# ---------------------------------------------------------------------------
def _fn(name, desc, props, required):
    return {"type": "function", "function": {
        "name": name, "description": desc,
        "parameters": {"type": "object", "properties": props, "required": required}}}

TOOL_SCHEMAS = [
    _fn("ingest_lecture",
        "Index a NEW lecture from a URL (YouTube or direct). Only call this if the "
        "user provides a link to a video that isn't indexed yet. Returns a video_id.",
        {"url": {"type": "string", "description": "the video URL to index"}},
        ["url"]),
    _fn("search_topic",
        "Find the timestamped moments in a lecture where a topic is discussed. "
        "Use to locate content before clipping, or to answer 'where is X'.",
        {"video_id": {"type": "string"},
         "query": {"type": "string", "description": "the topic to find"}},
        ["video_id", "query"]),
    _fn("make_clip",
        "Make ONE tight clip of the single best moment where a topic is explained "
        "(real lecture footage).",
        {"video_id": {"type": "string"}, "topic": {"type": "string"}},
        ["video_id", "topic"]),
    _fn("make_summary_reel",
        "Make a SUMMARY REEL: stitch the key moments of a topic from across the "
        "lecture into one highlight clip (real lecture footage).",
        {"video_id": {"type": "string"}, "topic": {"type": "string"}},
        ["video_id", "topic"]),
    _fn("make_learning_video",
        "Generate an AI explainer video (FLUX images + narration) for a topic. "
        "Slow (~1 min/slide). Use only when the user explicitly wants a generated "
        "video/animation. 'style' can be e.g. 'animated', 'realistic', 'whiteboard'.",
        {"video_id": {"type": "string"}, "topic": {"type": "string"},
         "style": {"type": "string"}, "n_slides": {"type": "integer"}},
        ["video_id", "topic"]),
    _fn("make_study_pack",
        "Build a FULL study pack for a topic: grounded summary + flashcards + cue "
        "cards + a precise clip + a summary reel. Set include_video=true to also "
        "generate the AI explainer video (slower). This is the main all-in-one tool.",
        {"video_id": {"type": "string"}, "topic": {"type": "string"},
         "include_video": {"type": "boolean"},
         "style": {"type": "string", "description": "style if include_video"}},
        ["video_id", "topic"]),
    _fn("send_to_telegram",
        "Send the results just produced (clips, reel, video, flashcards, cue cards) "
        "to the user's Telegram. Call this when the user asks to send/share to Telegram, "
        "AFTER producing the content.",
        {}, []),
]