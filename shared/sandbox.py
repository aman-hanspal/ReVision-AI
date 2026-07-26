"""
shared/sandbox.py — safe sandbox lifecycle for ALL generation calls.

RULE: generation runs inside a sandbox that is ALWAYS stopped afterwards (even on
error) so runtime billing never leaks.

Two entry points:
  * sandbox_for(conn, category)      -> one-off: open a single-category sandbox,
                                        use it, auto-stop. Good for a single call.
  * sandbox_session(conn, categories)-> BATCH: open ONE sandbox that holds several
                                        model categories, reuse it for many calls,
                                        auto-stop once at the end. Use this for a
                                        whole study pack / learning video so you
                                        pay ~60s provisioning ONCE, not per call.

A single sandbox can hold multiple categories (verified), e.g.
    ["text_generation", "image_generation", "text_to_speech"].

Generated assets persist in the collection after the sandbox stops, so
.generate_url() works outside the `with` block.
"""
from __future__ import annotations

import contextlib
import logging
from typing import Iterator, List, Optional

import videodb

from shared import config

logger = logging.getLogger("revision.sandbox")

_TIER_FOR = {
    "text_generation": config.TEXT_SANDBOX_TIER,
    "text_to_speech": config.TTS_SANDBOX_TIER,
    "image_generation": config.IMAGE_SANDBOX_TIER,
}


def _resolve_tier(name: str):
    enum = getattr(videodb, "SandboxTier", None)
    return getattr(enum, name, name) if enum is not None else name


def _highest_tier(categories: List[str]) -> str:
    """A multi-category sandbox must use a tier that satisfies the priciest need.
    image_generation needs medium; text/tts are fine on small."""
    if any(_TIER_FOR.get(c) == "medium" for c in categories) or \
       "image_generation" in categories:
        return "medium"
    return "small"


@contextlib.contextmanager
def sandbox_for(conn, category: str, tier: Optional[str] = None) -> Iterator[object]:
    """One-off single-category sandbox; yields it and ALWAYS stops it."""
    with sandbox_session(conn, [category], tier=tier) as sb:
        yield sb


@contextlib.contextmanager
def sandbox_session(conn, categories: List[str],
                    tier: Optional[str] = None) -> Iterator[object]:
    """Open ONE sandbox for all `categories`, yield it for reuse, ALWAYS stop it."""
    tier_name = tier or _highest_tier(categories)
    sb = None
    try:
        logger.info("creating sandbox categories=%s tier=%s", categories, tier_name)
        sb = conn.create_sandbox(
            tier=_resolve_tier(tier_name),
            model_categories=list(categories),
        )
        sb.wait_for_ready(
            timeout=config.SANDBOX_WAIT_TIMEOUT,
            interval=config.SANDBOX_WAIT_INTERVAL,
        )
        logger.info("sandbox ready id=%s", getattr(sb, "id", "?"))
        yield sb
    finally:
        if sb is not None:
            try:
                sb.stop()
                logger.info("sandbox stopped id=%s", getattr(sb, "id", "?"))
            except Exception as e:
                logger.warning("sandbox stop FAILED id=%s: %s", getattr(sb, "id", "?"), e)