"""
shared/telegram_service.py — push study-pack links to Telegram.

WHAT:  sends a study pack's outputs (summary + video/clip/reel links + cards) to a
       Telegram chat via the Bot API. Failure-isolated: if Telegram isn't configured
       or the send fails, it returns a soft error — it never crashes the app.
USED BY: backend/routes/telegram.py (the /telegram endpoint).
KEY EXPORTS: is_configured(), send_study_pack(displays) -> (ok, message).
CONFIG (.env):
       TELEGRAM_BOT_TOKEN=123456:ABC...     (from @BotFather)
       TELEGRAM_CHAT_ID=123456789           (your chat/user id)
NOTES: get a token from @BotFather; get your chat_id by messaging the bot then
       visiting https://api.telegram.org/bot<TOKEN>/getUpdates and reading chat.id.
"""
from __future__ import annotations

import logging
import os
from typing import List, Dict, Tuple

import requests

logger = logging.getLogger("revision.telegram")

_API = "https://api.telegram.org/bot{token}/sendMessage"


def _token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "").strip()


def _chat_id() -> str:
    return os.getenv("TELEGRAM_CHAT_ID", "").strip()


def is_configured() -> bool:
    return bool(_token() and _chat_id())


def _format(displays: List[Dict]) -> str:
    """Turn the study-pack displays into a readable Telegram message (HTML)."""
    lines = ["<b>📚 ReVision study pack</b>"]
    for d in displays:
        kind = d.get("kind")
        if kind == "study_pack":
            if d.get("topic"):
                lines.append(f"\n<b>Topic:</b> {d['topic']}")
            if d.get("summary"):
                lines.append(f"\n<b>Summary:</b> {d['summary'][:600]}")
            if d.get("single_clip_url"):
                lines.append(f"\n🎬 <a href=\"{d['single_clip_url']}\">Jump to moment</a>")
            if d.get("summary_reel_url"):
                lines.append(f"✂️ <a href=\"{d['summary_reel_url']}\">Highlights</a>")
            if d.get("learning_video_url"):
                lines.append(f"🎥 <a href=\"{d['learning_video_url']}\">AI explainer</a>")
            if d.get("flashcards"):
                lines.append("\n<b>Flashcards:</b>")
                for c in d["flashcards"][:8]:
                    lines.append(f"• <b>Q:</b> {c.get('front','')}  <b>A:</b> {c.get('back','')}")
            if d.get("cue_cards"):
                lines.append("\n<b>Cue cards:</b>")
                for t in d["cue_cards"][:8]:
                    lines.append(f"• {t}")
        elif kind == "reel" and d.get("summary_reel_url"):
            lines.append(f"\n✂️ <a href=\"{d['summary_reel_url']}\">Highlights — {d.get('topic','')}</a>")
        elif kind == "clip" and d.get("clip_url"):
            lines.append(f"\n🎬 <a href=\"{d['clip_url']}\">Clip — {d.get('topic','')}</a>")
        elif kind == "learning_video" and d.get("learning_video_url"):
            lines.append(f"\n🎥 <a href=\"{d['learning_video_url']}\">AI explainer — {d.get('topic','')}</a>")
    return "\n".join(lines)


def send_study_pack(displays: List[Dict]) -> Tuple[bool, str]:
    """Send the pack to Telegram. Returns (ok, message). Never raises."""
    if not is_configured():
        return False, "Telegram not configured (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)."
    try:
        text = _format(displays or [])
        resp = requests.post(
            _API.format(token=_token()),
            json={"chat_id": _chat_id(), "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=15,
        )
        if resp.status_code == 200 and resp.json().get("ok"):
            return True, "Sent to Telegram."
        logger.warning("telegram send failed: %s", resp.text[:300])
        return False, f"Telegram error: {resp.status_code}"
    except Exception as e:
        logger.exception("telegram send crashed")
        return False, f"Telegram send failed: {e}"