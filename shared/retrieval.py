"""
shared/retrieval.py — ingest lectures and find topics.

WHAT:  turns a lecture (file or YouTube URL) into a searchable index, and finds
       timestamped topic moments in it. The "understand + search" half of
       ReVision. Built entirely on shared/videodb_service.py.
USED BY: the agent tools (search_lecture), backend routes (/upload, /studypack),
       and generate.py.
KEY EXPORTS:
       ingest(url|file_path)     -> VideoRef        (upload -> understand -> index)
       find_topic(video_id, q)   -> list[TopicHit]  (semantic search, one video)
       find_across(q)            -> list[TopicHit]  (intelligent search, collection)
       best_topics(video_id, n)  -> list[TopicHit]  ("key moments" discovery)
NOTES:
  * Transcript semantic scores run LOW (~0.2-0.45 is a good match). We therefore
    do NOT hard-filter on a score threshold — we take top-k and keep score as
    info. Hard thresholds are fragile on this range.
  * Shots come back with EMPTY .text from semantic_search; timestamps are what we
    clip on. Actual transcript text/summary comes from ask() in generate.py.
  * Some hits are very long passages (coarse transcript granularity); clip length
    is capped later by videodb_service.clip() (MAX_CLIP_S), so clips stay short.
RUN:   python -m shared.retrieval --ingest "<youtube-url>"
       python -m shared.retrieval --topic  "<video_id>" "gradient descent"
       python -m shared.retrieval --best   "<video_id>"
"""
from __future__ import annotations

import logging
from typing import List, Optional

from shared import config
from shared import videodb_service as vdb
from shared.models import VideoRef, TopicHit

logger = logging.getLogger("revision.retrieval")


# ---------------------------------------------------------------------------
# Ingest: upload -> understand (transcript) -> index
# ---------------------------------------------------------------------------
def ingest(url: Optional[str] = None, file_path: Optional[str] = None) -> VideoRef:
    """Upload a lecture, transcribe it, and build a semantic index.
    Blocks until the index is ready (minutes for a long lecture)."""
    video = vdb.upload(url=url, file_path=file_path)
    logger.info("uploaded video_id=%s", video.id)

    analyzer = vdb.understand_transcript(video)
    logger.info("transcript ready for %s", video.id)

    vdb.build_index(video, analyzer)
    logger.info("index ready for %s", video.id)

    return VideoRef(
        video_id=video.id,
        title=getattr(video, "name", "") or getattr(video, "title", "") or "",
        length=float(getattr(video, "length", 0) or 0),
        source_url=url,
    )


def ingest_many(urls: List[str]) -> List[VideoRef]:
    """Ingest several YouTube links into one collection (looped upload).
    No playlist dependency — each link is its own video, searchable together."""
    refs: List[VideoRef] = []
    for u in urls:
        try:
            refs.append(ingest(url=u))
        except Exception as e:
            logger.exception("ingest failed for %s: %s", u, e)
    return refs


# ---------------------------------------------------------------------------
# Find topics  (top-k, score kept as info; no fragile hard threshold)
# ---------------------------------------------------------------------------
def find_topic(video_id: str, query: str, top_k: Optional[int] = None) -> List[TopicHit]:
    """Semantic search for a topic within ONE lecture. Returns ranked TopicHits."""
    video = vdb.get_video(video_id)
    shots = vdb.semantic_search(video, query, top_k=top_k, score_threshold=0.0)
    return [TopicHit.from_shot(s) for s in shots]


def find_across(query: str, top_k: Optional[int] = None) -> List[TopicHit]:
    """Intelligent search across ALL indexed lectures (agent-friendly)."""
    shots = vdb.search(query, top_k=top_k)
    return [TopicHit.from_shot(s) for s in shots]


def best_topics(video_id: str, n: int = 5,
                prefer_tight: bool = True) -> List[TopicHit]:
    """Surface the n most salient moments to seed 'key topics' study packs.

    prefer_tight: gently favour crisp moments over huge transcript passages, so a
    ~1min hit can outrank a 10min chunk of similar score.
    """
    video = vdb.get_video(video_id)
    shots = vdb.semantic_search(
        video,
        "the most important concepts and key ideas taught in this lecture",
        top_k=max(n * 2, n),           # over-fetch, then re-rank + trim
        score_threshold=0.0,
    )
    hits = [TopicHit.from_shot(s) for s in shots]

    if prefer_tight and hits:
        # rank by score but down-weight very long spans (soft length penalty)
        def key(h: TopicHit):
            length_penalty = 1.0 / (1.0 + max(0.0, h.duration - config.MAX_CLIP_S) / 120.0)
            return h.score * length_penalty
        hits.sort(key=key, reverse=True)

    return hits[:n]


# ---------------------------------------------------------------------------
# Manual smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse, json

    ap = argparse.ArgumentParser(description="ReVision retrieval smoke test")
    ap.add_argument("--ingest", metavar="URL", help="ingest a YouTube/URL lecture")
    ap.add_argument("--topic", nargs=2, metavar=("VIDEO_ID", "QUERY"),
                    help="find a topic in a video")
    ap.add_argument("--best", metavar="VIDEO_ID", help="list best topics for a video")
    args = ap.parse_args()

    def show(hits):
        if not hits:
            print("(no hits)")
        for h in hits:
            print(f"{h.start:8.1f}-{h.end:8.1f}  dur={h.duration:6.1f}s  "
                  f"score={h.score:.3f}  {h.text[:70]!r}")

    if args.ingest:
        ref = ingest(url=args.ingest)
        print("ingested:", json.dumps(ref.__dict__, indent=2))
    elif args.topic:
        vid, q = args.topic
        show(find_topic(vid, q))
    elif args.best:
        show(best_topics(args.best))
    else:
        ap.print_help()