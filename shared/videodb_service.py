"""
shared/videodb_service.py — the single adapter around VideoDB.

Every VideoDB call the app makes goes through here, using the exact signatures we
proved in Phase-0. Higher-level files (retrieval.py, generate.py, the agent) call
these functions and never touch the raw SDK — so if a signature changes, it
changes in ONE place.

Covers: connection, the agent proxy (tool-calling) client, upload, understand
(analyzer picked by TYPE), index, semantic_search / search / ask, clamped clips,
and the three sandboxed generation calls (text, image, voice).
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import List, Optional, Tuple

import videodb
from openai import OpenAI

from shared import config
from shared.sandbox import sandbox_for, sandbox_session

logger = logging.getLogger("revision.videodb")


def enable_logging(level: int = logging.INFO) -> None:
    """Turn on readable progress logs for the whole app (call once at startup)."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


# ---------------------------------------------------------------------------
# Connection (cached singletons)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_conn():
    config.validate()
    return videodb.connect(api_key=config.VIDEO_DB_API_KEY)


@lru_cache(maxsize=1)
def get_coll():
    return get_conn().get_collection()


@lru_cache(maxsize=1)
def agent_client() -> OpenAI:
    """OpenAI-compatible client pointed at the VideoDB proxy (GPT-4o, on credits)."""
    config.validate()
    return OpenAI(api_key=config.VIDEO_DB_API_KEY, base_url=config.VIDEO_DB_BASE_URL)


def llm_complete(prompt: str, system: str = "", temperature: float = 0.7,
                 max_tokens: int = 2048) -> str:
    """Plain (non-tool) completion via the VideoDB proxy (GPT-4o, on credits).

    Used for tasks that need reliable structured output (e.g. storyboard JSON),
    where a full agent tool-loop isn't needed. Returns the message text.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = agent_client().chat.completions.create(
        model=config.AGENT_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------
def upload(url: Optional[str] = None, file_path: Optional[str] = None):
    """Upload a YouTube/any URL or a local file. Returns a Video."""
    coll = get_coll()
    if url:
        logger.info("uploading url=%s", url)
        return coll.upload(url=url)
    if file_path:
        logger.info("uploading file=%s", file_path)
        return coll.upload(file_path=file_path)
    raise ValueError("upload() needs url or file_path")


def get_video(video_id: str):
    return get_coll().get_video(video_id)


def understand_transcript(video):
    """Run spoken-word understanding; return the transcript analyzer.

    Selected by TYPE ('speech_transcription'); the analyzer's NAME carries a
    random suffix each run, so we never match on name.
    """
    u = video.understand(analyzers=[{"type": "spoken_words"}])
    u.wait_until_complete()
    for a in getattr(u, "analyzers", []) or []:
        if getattr(a, "type", "") == config.TRANSCRIPT_ANALYZER_TYPE:
            return a
    analyzers = getattr(u, "analyzers", []) or []
    if analyzers:
        return analyzers[0]
    raise RuntimeError("understand() produced no analyzer")


def build_index(video, analyzer, name: Optional[str] = None):
    """Create a semantic+query index from an analyzer and wait until ready."""
    idx = video.index(
        source=analyzer,
        name=name or config.TRANSCRIPT_INDEX_NAME,
        use_for=["semantic", "query"],
    )
    idx.wait_until_complete(
        timeout=config.INDEX_WAIT_TIMEOUT,
        poll_interval=config.INDEX_WAIT_INTERVAL,
    )
    if not getattr(idx, "is_successful", False):
        raise RuntimeError(f"indexing failed: {getattr(idx, 'error', 'unknown')}")
    return idx


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
def semantic_search(video, query: str, index_name: Optional[str] = None,
                    top_k: Optional[int] = None,
                    score_threshold: Optional[float] = None) -> List:
    """Direct semantic search on one video's index. Returns a list of Shots."""
    res = video.semantic_search(
        query=query,
        index_names=[index_name or config.TRANSCRIPT_INDEX_NAME],
        top_k=top_k or config.TOP_K,
        score_threshold=score_threshold if score_threshold is not None else config.MIN_SCORE,
    )
    return res.get_shots()


def search(query: str, top_k: Optional[int] = None, return_fields=None) -> List:
    """Intelligent collection search (VideoDB plans retrieval). Returns list of Shots."""
    resp = get_coll().search(
        query=query,
        top_k=top_k or config.TOP_K,
        return_fields=return_fields or [config.TRANSCRIPT_INDEX_NAME],
    )
    return list(resp)


def ask(question: str, include_sources: bool = True) -> Tuple[str, List]:
    """Grounded answer + source shots. Returns (answer_text, sources)."""
    ans = get_coll().ask(question=question, include_sources=include_sources)
    return getattr(ans, "answer", ""), (getattr(ans, "sources", []) or [])


# ---------------------------------------------------------------------------
# Clips — ALWAYS clamped to the video length, capped in length so a clip is
# never a 10-minute passage (proven necessary in Phase-0 tests 08/09).
# ---------------------------------------------------------------------------
def clamp_range(start: float, end: float, video_length: float,
                max_len: Optional[float] = None) -> Optional[Tuple[float, float]]:
    """Return a safe (start, end) inside [0, video_length], capped to max_len.
    Returns None if the range is degenerate.
    """
    cap = max_len if max_len is not None else config.MAX_CLIP_S
    e = min(float(end), float(video_length)) if video_length else float(end)
    s = max(0.0, min(float(start), e - 0.1))
    if cap and (e - s) > cap:
        s = max(0.0, e - cap)  # keep the tail (usually the payoff) within the cap
    return (s, e) if e > s else None


def clip(video, ranges: List[Tuple[float, float]]) -> str:
    """Build a playable HLS stream from (start, end) ranges, clamped to length."""
    vlen = float(getattr(video, "length", 0) or 0)
    safe = [r for r in (clamp_range(s, e, vlen) for (s, e) in ranges) if r]
    if not safe:
        raise ValueError("no valid ranges after clamping")
    return video.generate_stream(safe)


def shot_range(shot) -> Tuple[float, float]:
    return (float(shot.start), float(shot.end))


# ---------------------------------------------------------------------------
# Generation — ALWAYS inside a sandbox (auto-created, auto-stopped).
# Asset URLs are fetched AFTER the sandbox stops (assets persist; proven).
# ---------------------------------------------------------------------------
ALL_GEN_CATEGORIES = ["text_generation", "image_generation", "text_to_speech"]


def open_session(categories=None):
    """Open ONE reusable sandbox for a batch of generations (study pack / video).

    Use as:  with vdb.open_session() as sb:  generate_text(..., sandbox=sb); ...
    Pays sandbox provisioning ONCE for the whole job instead of per call.
    """
    return sandbox_session(get_conn(), categories or ALL_GEN_CATEGORIES)


def generate_text(prompt: str, sandbox=None) -> str:
    """Text generation on a sandbox model. Returns the text string.
    Pass sandbox= to reuse an open session; otherwise a one-off sandbox is used.
    Proven return shape: {"output": "..."}.
    """
    coll = get_coll()
    if sandbox is not None:
        out = coll.generate_text(prompt=prompt, sandbox_id=sandbox.id)
    else:
        with sandbox_for(get_conn(), "text_generation") as sb:
            out = coll.generate_text(prompt=prompt, sandbox_id=sb.id)
    if isinstance(out, dict):
        return out.get("output", "")
    return str(out)


def generate_image(prompt: str, sandbox=None,
                   model_name: str = "black-forest-labs/FLUX.1-dev") -> Tuple[str, str]:
    """FLUX image on a sandbox (UNCAPPED). Returns (image_id, url). Pass sandbox= to reuse.

    IMPORTANT: passing model_name routes to the SANDBOX FLUX model (uncapped, on
    credits). WITHOUT model_name the request goes to the managed model, which has
    a small hard image cap. Generation is async: the call returns a job; we wait()
    for the Image (inside the sandbox context, before it stops).
    """
    coll = get_coll()
    cfg = {"size": "1280x720", "num_inference_steps": 28, "guidance_scale": 4.0}

    def _run(sb):
        result = coll.generate_image(prompt=prompt, model_name=model_name,
                                     sandbox_id=sb.id, config=cfg)
        return result.wait(timeout=900, interval=5) if hasattr(result, "wait") else result

    if sandbox is not None:
        img = _run(sandbox)
    else:
        with sandbox_for(get_conn(), "image_generation") as sb:
            img = _run(sb)
    return img.id, img.generate_url()  # url valid after stop


def generate_voice(text: str, sandbox=None) -> Tuple[str, float, str]:
    """OmniVoice TTS on a sandbox. Returns (audio_id, length_seconds, url). Pass sandbox= to reuse."""
    coll = get_coll()
    if sandbox is not None:
        aud = coll.generate_voice(text=text, sandbox_id=sandbox.id)
    else:
        with sandbox_for(get_conn(), "text_to_speech") as sb:
            aud = coll.generate_voice(text=text, sandbox_id=sb.id)
    length = float(getattr(aud, "length", 0) or 0)
    return aud.id, length, aud.generate_url()