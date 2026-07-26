"""
shared/config.py — central configuration for ReVision.

Loads environment variables (from .env at the project root) and exposes them,
alongside the values we PROVED in Phase-0 testing: the VideoDB proxy endpoint,
the agent model name, per-capability sandbox tiers, and the clip/duration rules.

Nothing here makes a network call. Import it everywhere; call validate() once at
startup to fail loudly if a required key is missing.

    from shared import config
    config.validate()
    print(config.summary())
"""
from __future__ import annotations

import os
import pathlib

from dotenv import load_dotenv, find_dotenv

# --- locate + load .env (walks up from CWD, so it works from any folder) -----
_ENV_PATH = find_dotenv(usecwd=True)
if _ENV_PATH:
    load_dotenv(_ENV_PATH)

PROJECT_ROOT = pathlib.Path(_ENV_PATH).parent if _ENV_PATH else pathlib.Path.cwd()

# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------
VIDEO_DB_API_KEY: str = os.getenv("VIDEO_DB_API_KEY", "")

# ---------------------------------------------------------------------------
# Agent LLM — VideoDB proxy (OpenAI-compatible, routes to GPT-4o, billed to
# your VideoDB credits). Proven in Phase-0 test 11.
#   OpenAI(api_key=VIDEO_DB_API_KEY, base_url=VIDEO_DB_BASE_URL), model=AGENT_MODEL
# ---------------------------------------------------------------------------
VIDEO_DB_BASE_URL: str = os.getenv("VIDEO_DB_BASE_URL", "https://api.videodb.io")
AGENT_MODEL: str = os.getenv("AGENT_MODEL", "gpt-4o-2024-11-20")
AGENT_TEMPERATURE: float = float(os.getenv("AGENT_TEMPERATURE", "0.7"))
AGENT_MAX_TOKENS: int = int(os.getenv("AGENT_MAX_TOKENS", "4096"))
AGENT_MAX_STEPS: int = int(os.getenv("AGENT_MAX_STEPS", "6"))  # tool-loop safety cap

# ---------------------------------------------------------------------------
# Sandbox tiers — cheapest tier that works per capability (proven in Phase-0).
#   text generation / TTS  -> small  ($1/hr)
#   image generation (FLUX) -> medium ($3.50/hr, required)
# All generation runs INSIDE a sandbox (see shared/sandbox.py).
# ---------------------------------------------------------------------------
TEXT_SANDBOX_TIER: str = os.getenv("TEXT_SANDBOX_TIER", "small")
TTS_SANDBOX_TIER: str = os.getenv("TTS_SANDBOX_TIER", "small")
IMAGE_SANDBOX_TIER: str = os.getenv("IMAGE_SANDBOX_TIER", "medium")

SANDBOX_WAIT_TIMEOUT: int = int(os.getenv("SANDBOX_WAIT_TIMEOUT", "300"))
SANDBOX_WAIT_INTERVAL: int = int(os.getenv("SANDBOX_WAIT_INTERVAL", "5"))

# ---------------------------------------------------------------------------
# Understanding / indexing (proven).
# The transcript analyzer is selected by TYPE, never by name (names carry a
# random suffix each run).
# ---------------------------------------------------------------------------
TRANSCRIPT_ANALYZER_TYPE: str = "speech_transcription"
TRANSCRIPT_INDEX_NAME: str = os.getenv("TRANSCRIPT_INDEX_NAME", "transcript")
INDEX_WAIT_TIMEOUT: int = int(os.getenv("INDEX_WAIT_TIMEOUT", "1800"))
INDEX_WAIT_INTERVAL: int = int(os.getenv("INDEX_WAIT_INTERVAL", "10"))

# ---------------------------------------------------------------------------
# Retrieval / clips
# ---------------------------------------------------------------------------
TOP_K: int = int(os.getenv("TOP_K", "5"))
MIN_SCORE: float = float(os.getenv("MIN_SCORE", "0.6"))
CLIP_PAD_S: float = float(os.getenv("CLIP_PAD_S", "2"))
# Search over transcripts can return very broad passages; cap a topic clip so it
# stays watchable rather than 10 minutes long.
MAX_CLIP_S: float = float(os.getenv("MAX_CLIP_S", "90"))

# ---------------------------------------------------------------------------
# Learning video (stretch). Slide length is driven by its narration length;
# this is just the floor so a very short line still shows the image a beat.
# ---------------------------------------------------------------------------
MIN_SLIDE_S: float = float(os.getenv("MIN_SLIDE_S", "2.0"))
VIDEO_RESOLUTION: str = os.getenv("VIDEO_RESOLUTION", "1280x720")

# ---------------------------------------------------------------------------
# Telegram (optional; Level 3)
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_ENABLED: bool = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def validate() -> None:
    """Fail fast if required configuration is missing. Call once at startup."""
    missing = []
    if not VIDEO_DB_API_KEY:
        missing.append("VIDEO_DB_API_KEY")
    if missing:
        raise RuntimeError(
            "Missing required env var(s): "
            + ", ".join(missing)
            + f"\nAdd them to your .env at {PROJECT_ROOT / '.env'}"
        )


def summary() -> str:
    """Secret-free snapshot of the active config (safe to log)."""
    return (
        "ReVision config:\n"
        f"  proxy         : {VIDEO_DB_BASE_URL}  model={AGENT_MODEL}\n"
        f"  api key set   : {bool(VIDEO_DB_API_KEY)}\n"
        f"  sandbox tiers : text={TEXT_SANDBOX_TIER} tts={TTS_SANDBOX_TIER} image={IMAGE_SANDBOX_TIER}\n"
        f"  retrieval     : top_k={TOP_K} min_score={MIN_SCORE} max_clip_s={MAX_CLIP_S}\n"
        f"  telegram      : {'on' if TELEGRAM_ENABLED else 'off'}\n"
        f"  project root  : {PROJECT_ROOT}"
    )


if __name__ == "__main__":
    print(summary())
    validate()
    print("config OK")