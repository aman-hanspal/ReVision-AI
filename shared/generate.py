"""
shared/generate.py — turn topics into study-pack content.

WHAT:  the content-generation layer. Given a lecture + a topic it produces a
       grounded summary, flashcards, cue cards, a clip, and (stretch) a learning
       video — assembled into a StudyPack. Built on videodb_service + retrieval.
USED BY: the agent tools (make_summary / make_flashcards / make_learning_video),
       backend routes (/studypack), and the frontend via StudyPack.to_dict().
KEY EXPORTS:
       make_summary(topic)            -> Summary        (grounded, via ask())
       make_flashcards(topic, n)      -> list[Flashcard] (sandbox generate_text)
       make_cue_cards(topic, n)       -> list[CueCard]
       make_clip(video_id, hit|topic) -> Clip           (clamped stream)
       build_study_pack(video_id, topic) -> StudyPack   (clip+summary+cards)
       make_learning_video(storyboard)-> (url, slides)  (Timeline; needs img quota)
NOTES:
  * Content comes from ask() (reads transcript internally) — semantic_search hits
    have empty .text, so we never rely on hit text for content.
  * generate_text returns {"output": "..."}; cards are parsed from a robust
    "Q: / A:" line format (malformed lines are skipped, never crash the set).
  * Learning video: slide duration = its narration length (proven in test 14);
    assets use id= on the editor; sandboxes auto-stop via videodb_service.
RUN:   python -m shared.generate --summary "<video_id>" "gradient descent"
       python -m shared.generate --cards   "<video_id>" "gradient descent"
       python -m shared.generate --pack    "<video_id>" "gradient descent"
"""
from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from typing import List, Optional, Tuple


@contextmanager
def _nullcontext(obj):
    """Yield an already-open sandbox without closing it (caller owns its lifecycle)."""
    yield obj

from shared import config
from shared import videodb_service as vdb
from shared import retrieval
from shared.models import (
    VideoRef, TopicHit, Clip, Flashcard, CueCard, Summary, Slide, StudyPack,
)

logger = logging.getLogger("revision.generate")


# ---------------------------------------------------------------------------
# Summary (grounded, via ask)
# ---------------------------------------------------------------------------
def make_summary(topic: str) -> Summary:
    """Grounded summary of a topic across the collection, with source moments."""
    question = (f"Give a clear, concise study summary of '{topic}' as taught in "
                f"the lecture. Focus on the core idea and why it matters.")
    answer, sources = vdb.ask(question, include_sources=True)
    hits = [TopicHit.from_shot(s) for s in sources]
    return Summary(text=answer.strip(), sources=hits)


def _topic_context(topic: str) -> str:
    """Grounded text about a topic to feed into card generation."""
    answer, _ = vdb.ask(
        f"Explain '{topic}' from the lecture in enough detail to write study "
        f"questions about it. Be factual and specific.",
        include_sources=False,
    )
    return answer.strip()


# ---------------------------------------------------------------------------
# Storyboard planner — the DYNAMIC brain of the learning video.
# The agent (GPT-4o via the proxy) writes a multi-slide storyboard: a SPECIFIC
# image prompt + one narration sentence per slide, grounded in the lecture and
# styled to the user's request. Replaces the old hardcoded 1-slide stub.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Flashcards / cue cards (sandbox generate_text)
# ---------------------------------------------------------------------------
_QA_RE = re.compile(r"^\s*Q\s*[:\-|]\s*(.+?)\s*(?:\n|)\s*A\s*[:\-|]\s*(.+)$",
                    re.IGNORECASE | re.DOTALL)


def _parse_flashcards(text: str) -> List[Flashcard]:
    """Parse 'Q: ... A: ...' pairs robustly. Skips malformed lines."""
    cards: List[Flashcard] = []
    # split into blocks on blank lines OR on 'Q:' starts
    blocks = re.split(r"\n\s*\n|(?=^\s*Q\s*[:\-|])", text, flags=re.IGNORECASE | re.MULTILINE)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # try inline "Q: ... A: ..." (also handles "Q | A" and "Q - A")
        m = re.search(r"Q\s*[:\-|]\s*(.+?)\s*A\s*[:\-|]\s*(.+)",
                      block, re.IGNORECASE | re.DOTALL)
        if m:
            front = " ".join(m.group(1).split())
            back = " ".join(m.group(2).split())
            if front and back:
                cards.append(Flashcard(front=front, back=back))
            continue
        # fallback: a single line "question | answer"
        if "|" in block:
            f, _, b = block.partition("|")
            if f.strip() and b.strip():
                cards.append(Flashcard(front=f.strip(), back=b.strip()))
    return cards


def make_flashcards(topic: str, n: int = 5, context: Optional[str] = None,
                    sandbox=None) -> List[Flashcard]:
    """Generate n Q/A flashcards for a topic. Pass sandbox= to reuse a session."""
    ctx = context or _topic_context(topic)
    prompt = (
        f"You are creating study flashcards about '{topic}'.\n"
        f"Using ONLY the material below, write exactly {n} flashcards.\n"
        f"Format each on its own block as:\nQ: <question>\nA: <answer>\n\n"
        f"Keep questions specific and answers one or two sentences.\n\n"
        f"MATERIAL:\n{ctx}"
    )
    raw = vdb.generate_text(prompt, sandbox=sandbox)
    cards = _parse_flashcards(raw)
    if not cards:
        logger.warning("flashcard parse produced 0 cards; raw head: %s", raw[:200])
    return cards[:n]


def make_cue_cards(topic: str, n: int = 5, context: Optional[str] = None,
                   sandbox=None) -> List[CueCard]:
    """Generate n short cue/key-point cards. Pass sandbox= to reuse a session."""
    ctx = context or _topic_context(topic)
    prompt = (
        f"From the material below about '{topic}', list exactly {n} short "
        f"key-point cue cards. One point per line, no numbering, each under 15 words.\n\n"
        f"MATERIAL:\n{ctx}"
    )
    raw = vdb.generate_text(prompt, sandbox=sandbox)
    points = [ln.strip(" -•\t") for ln in raw.splitlines() if ln.strip()]
    points = [p for p in points if len(p.split()) >= 2]  # drop junk lines
    return [CueCard(text=p) for p in points[:n]]


# ---------------------------------------------------------------------------
# Clip
# ---------------------------------------------------------------------------
def make_clip(video_id: str, topic: Optional[str] = None,
              hit: Optional[TopicHit] = None) -> Optional[Clip]:
    """Build a clip for a topic: pick the best hit (or use a supplied one),
    clamp it to the video length + MAX_CLIP_S, and return a playable Clip."""
    video = vdb.get_video(video_id)
    if hit is None:
        if not topic:
            raise ValueError("make_clip needs a topic or a hit")
        hits = retrieval.find_topic(video_id, topic, top_k=1)
        if not hits:
            return None
        hit = hits[0]
    stream = vdb.clip(video, [(hit.start, hit.end)])
    # reflect the clamped window in the returned Clip
    vlen = float(getattr(video, "length", 0) or 0)
    rng = vdb.clamp_range(hit.start, hit.end, vlen)
    s, e = rng if rng else (hit.start, hit.end)
    return Clip(title=(topic or "clip").title(), stream_url=stream, start=s, end=e)


# ---------------------------------------------------------------------------
# PRECISE clips — the "make-or-break" quality path.
# Instead of clipping a coarse semantic segment (which can be 10 min long),
# we ask() a focused question and clip the moments ask() actually CITES as
# answering it. Those cited sources are tighter and more on-topic than raw
# semantic hits — NotebookLM-style grounded precision.
# ---------------------------------------------------------------------------
def _merge_ranges(ranges, gap: float = 2.0):
    """Merge overlapping/adjacent (start,end) ranges (gap seconds apart)."""
    if not ranges:
        return []
    ordered = sorted(ranges)
    merged = [list(ordered[0])]
    for s, e in ordered[1:]:
        if s <= merged[-1][1] + gap:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def find_precise_moments(video_id: str, topic: str):
    """Return tight, on-topic (start,end) ranges for a topic via ask() citations.

    ask(question, include_sources=True) returns the exact shots the model used to
    answer — these are more precise than raw semantic hits. We clamp each to the
    video length + MAX_CLIP_S and merge adjacent ones.
    """
    video = vdb.get_video(video_id)
    vlen = float(getattr(video, "length", 0) or 0)

    _, sources = vdb.ask(
        f"Where in the lecture is '{topic}' explained? Point to the exact moments.",
        include_sources=True,
    )
    raw = [(float(s.start), float(s.end)) for s in sources
           if getattr(s, "start", None) is not None]
    if not raw:
        # fall back to the best semantic hit if ask() cited nothing
        hits = retrieval.find_topic(video_id, topic, top_k=1)
        raw = [(h.start, h.end) for h in hits[:1]]

    clamped = [r for r in (vdb.clamp_range(s, e, vlen) for (s, e) in raw) if r]
    return _merge_ranges(clamped)


def make_precise_clip(video_id: str, topic: str) -> Optional[Clip]:
    """A single tight clip for a topic, built from ask()-cited moments."""
    ranges = find_precise_moments(video_id, topic)
    if not ranges:
        return None
    video = vdb.get_video(video_id)
    # use the tightest cited moment as THE clip
    s, e = min(ranges, key=lambda r: r[1] - r[0])
    stream = vdb.clip(video, [(s, e)])
    return Clip(title=topic.title(), stream_url=stream, start=s, end=e)


def make_summary_reel(video_id: str, topic: str, n_points: int = 4) -> Optional[Clip]:
    """The 'final summarised clip': decompose the topic into sub-points, find the
    precise cited moment for each, and stitch them into ONE tight highlight reel.

    This is a *summarised* clip built from precise pieces across the lecture —
    not one coarse chunk.
    """
    # 1) let the agent break the topic into the key sub-points to show
    raw = vdb.llm_complete(
        f"Break the topic '{topic}' into the {n_points} most important sub-points a "
        f"student should see explained, as a JSON array of short search phrases. "
        f"Return ONLY the JSON array.",
        system="You output only a JSON array of short strings.",
    )
    subpoints = _parse_json_array(raw) or [topic]
    subpoints = [str(p) for p in subpoints][:n_points]

    # 2) find the precise cited moment for each sub-point
    video = vdb.get_video(video_id)
    vlen = float(getattr(video, "length", 0) or 0)
    ranges = []
    from shared.progress import emit
    emit(f"Reel: locating {len(subpoints)} key moments…")
    for idx, p in enumerate(subpoints, 1):
        emit(f"Reel: finding moment {idx}/{len(subpoints)} — '{p}'…")
        ms = find_precise_moments(video_id, p)
        if ms:
            ranges.append(min(ms, key=lambda r: r[1] - r[0]))  # tightest per point
    emit("Reel: stitching moments into one clip…")
    ranges = _merge_ranges(ranges)
    if not ranges:
        return None

    # 3) stitch into one reel (chronological)
    ranges.sort()
    stream = vdb.clip(video, ranges)
    total = sum(e - s for s, e in ranges)
    return Clip(title=f"{topic.title()} — Summary Reel", stream_url=stream,
                start=ranges[0][0], end=ranges[-1][1])


# ---------------------------------------------------------------------------
# Full study pack
# ---------------------------------------------------------------------------
def build_study_pack(video_id: str, topic: str,
                     n_flash: int = 5, n_cue: int = 5,
                     with_video: bool = False,
                     video_style: str = "clean educational",
                     n_slides: int = 5) -> StudyPack:
    """Assemble clip + grounded summary + flashcards + cue cards for a topic."""
    from shared.progress import emit
    video = vdb.get_video(video_id)
    ref = VideoRef(video_id=video_id,
                   title=getattr(video, "name", "") or "",
                   length=float(getattr(video, "length", 0) or 0))

    emit(f"Building study pack for '{topic}'")
    emit("Writing grounded summary…")
    summary = make_summary(topic)
    ctx = summary.text
    emit("Finding the best clip…")
    clip = make_precise_clip(video_id, topic)
    emit("Building the summary reel (this stitches several moments)…")
    reel = make_summary_reel(video_id, topic)

    emit("Opening a generation sandbox…")
    with vdb.open_session() as sb:
        emit("Writing flashcards…")
        flashcards = make_flashcards(topic, n_flash, context=ctx, sandbox=sb)
        emit("Writing cue cards…")
        cue_cards = make_cue_cards(topic, n_cue, context=ctx, sandbox=sb)
        pack = StudyPack(topic=topic, video=ref, clip=clip, summary_reel=reel,
                         summary=summary, flashcards=flashcards, cue_cards=cue_cards)

        # dedicated concept image for the flashcard header (its own generation,
        # distinct from the AI explainer's slides)
        emit("Illustrating the topic…")
        try:
            concept_prompt = (
                f"A clean, modern, minimal educational illustration representing "
                f"the concept of '{topic}'. Flat vector style, uncluttered, no text "
                f"or labels, suitable as a topic banner.")
            _img_id, concept_url = vdb.generate_image(concept_prompt, sandbox=sb)
            pack.concept_image_url = concept_url
        except Exception as e:
            emit(f"Concept image skipped: {e}", kind="warning")

        if with_video:
            emit(f"Planning a {n_slides}-slide learning video…")
            storyboard = plan_storyboard(topic, style=video_style, n_slides=n_slides)
            emit(f"Storyboard ready: {len(storyboard)} slides")
            try:
                url, slides = make_learning_video(storyboard, sandbox=sb)
                pack.learning_video_url = url
                pack.slides = slides
            except Exception as e:
                emit(f"Learning video skipped: {e}", kind="warning")
    emit("Study pack complete ✓", kind="done")
    return pack


# ---------------------------------------------------------------------------
# Storyboard planning (the video's "brain") — dynamic, grounded, styled.
# GPT-4o (via proxy) writes SPECIFIC per-slide image prompts + narration.
# This is what turns a vague blob into real explanatory diagrams.
# ---------------------------------------------------------------------------
_STORYBOARD_SYSTEM = (
    "You are an expert educational video storyboard writer. You turn lecture "
    "material into a short sequence of slides for an AI-generated explainer video. "
    "You return ONLY a JSON array — no prose, no markdown fences."
)


def _parse_json_array(raw: str) -> list:
    """Parse a JSON array from an LLM response, tolerating markdown fences/prose."""
    import json
    s = raw.strip()
    # strip ```json ... ``` fences if present
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.IGNORECASE | re.MULTILINE).strip()
    # grab the outermost [...] if the model added stray text
    m = re.search(r"\[.*\]", s, re.DOTALL)
    if m:
        s = m.group(0)
    try:
        data = json.loads(s)
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning("storyboard JSON parse failed: %s; head: %s", e, raw[:200])
        return []


def plan_storyboard(topic: str, style: str = "clean flat-vector educational",
                    n_slides: int = 5) -> List[Slide]:
    """Agent-written storyboard: grounded content -> specific image prompts + narration.

    - Pulls real lecture content for `topic` via ask() (so it's grounded, not invented).
    - Asks GPT-4o (proxy) for `n_slides` slides as strict JSON.
    - `style` is threaded into every image prompt (e.g. "animated", "realistic",
      "whiteboard", "3D render").
    Returns List[Slide]; falls back to a single grounded slide if parsing fails.
    """
    content, _ = vdb.ask(
        f"Explain '{topic}' from the lecture in clear detail, covering the core "
        f"idea, how it works, and why it matters.",
        include_sources=False,
    )
    content = (content or "").strip()

    prompt = (
        f"TOPIC: {topic}\n"
        f"VISUAL STYLE: {style}\n\n"
        f"LECTURE MATERIAL:\n{content}\n\n"
        f"Write a storyboard of exactly {n_slides} slides that teaches this topic, "
        f"progressing intro -> mechanism -> conclusion. Return ONLY a JSON array where "
        f"each element is:\n"
        f'{{"image_prompt": "<a SPECIFIC, detailed prompt for an image generator that '
        f"depicts THIS slide's idea concretely (objects, labels, layout), in the "
        f"'{style}' style — not decorative>\", "
        f'"narration": "<one clear spoken sentence, ~15-22 words, grounded in the '
        f'material>"}}.\n'
        f"Make each image_prompt visually distinct and directly illustrative of its "
        f"narration."
    )

    raw = vdb.llm_complete(prompt, system=_STORYBOARD_SYSTEM, temperature=0.7)
    items = _parse_json_array(raw)

    slides: List[Slide] = []
    for it in items:
        ip = (it.get("image_prompt") or "").strip()
        nar = (it.get("narration") or "").strip()
        if ip and nar:
            slides.append(Slide(image_prompt=ip, narration=nar))

    if not slides:
        # graceful fallback: one grounded slide (still better than a vague stub)
        logger.warning("storyboard empty; using single-slide fallback")
        slides = [Slide(
            image_prompt=f"A specific, labeled {style} diagram that concretely "
                         f"illustrates {topic}, with clear components and labels",
            narration=(content[:200] or f"An overview of {topic}."),
        )]
    return slides[:n_slides]



def _add_auto_captions(conn, clean_stream_url: str,
                       animation: str = "reveal",
                       primary_color: str = "&H00FFFFFF",     # white
                       secondary_color: str = "&H0000FFFF"    # yellow highlight
                       ) -> str:
    """Second pass: take a rendered (clean) learning video, upload it back, index its
    spoken words, and overlay VideoDB's auto-generated CaptionAsset subtitles.

    CaptionAsset(src="auto") is the PROPER subtitle tool: it transcribes the narration
    and renders clean, auto-synced captions (word-level). It REQUIRES an indexed video
    (index_spoken_words), which is why we re-upload the rendered stream first.
    Returns the captioned stream URL (or the original if anything fails).
    """
    try:
        coll = conn.get_collection()
        from shared.progress import emit
        emit("Captions: uploading rendered video…")
        video = coll.upload(url=clean_stream_url)
        emit("Captions: transcribing narration…")
        video.index_spoken_words()
        # re-fetch the video so its spoken-words index is visible to CaptionAsset
        # (the warning fires when the caption is built before the index registers)
        try:
            video = coll.get_video(video.id)
        except Exception:
            pass

        from videodb.editor import (Timeline, Track, Clip as EClip, VideoAsset,
                                    CaptionAsset, CaptionAnimation)
        dur = float(getattr(video, "length", 0) or 0)

        cap_kwargs = {"src": "auto"}
        anim = getattr(CaptionAnimation, animation, None)
        if anim is not None:
            cap_kwargs["animation"] = anim
            cap_kwargs["primary_color"] = primary_color
            cap_kwargs["secondary_color"] = secondary_color

        tl = Timeline(conn)
        vt = Track(); ct = Track(z_index=1)
        vt.add_clip(0, EClip(asset=VideoAsset(id=video.id), duration=dur))
        ct.add_clip(0, EClip(asset=CaptionAsset(**cap_kwargs), duration=dur))
        tl.add_track(vt); tl.add_track(ct)

        emit("Captions: rendering final captioned video…")
        return tl.generate_stream()
    except Exception as e:
        logger.warning("auto-captions failed (%s); returning uncaptioned video", e)
        return clean_stream_url


def make_learning_video(storyboard: List[Slide], sandbox=None,
                        captions: bool = True, transitions: bool = True
                        ) -> Tuple[str, List[Slide]]:
    """Build a learning video from a storyboard (list of Slide(image_prompt, narration)).

    Pass 1: generate image + narration per slide, compose a clean Timeline (images +
            audio + optional fade transitions).
    Pass 2 (captions=True): re-ingest the rendered video, index_spoken_words(), and
            overlay VideoDB's CaptionAsset(src="auto") — clean, auto-synced subtitles.
    Returns (stream_url, filled_slides). Pass sandbox= to reuse an open session.
    """
    from videodb.editor import Timeline, Track, Clip as EClip, ImageAsset, AudioAsset

    conn = vdb.get_conn()

    own_session = sandbox is None
    session_cm = vdb.open_session(["image_generation", "text_to_speech"]) if own_session \
        else _nullcontext(sandbox)

    with session_cm as sb:
        for i, sl in enumerate(storyboard):
            from shared.progress import emit
            emit(f"Slide {i+1}/{len(storyboard)}: generating image…")
            img_id, img_url = vdb.generate_image(sl.image_prompt, sandbox=sb)
            emit(f"Slide {i+1}/{len(storyboard)}: generating narration…")
            aud_id, alen, _aud_url = vdb.generate_voice(sl.narration, sandbox=sb)
            sl.image_id = img_id
            sl.audio_id = aud_id
            sl.image_url = img_url
            sl.duration = max(config.MIN_SLIDE_S, alen - 0.05)
            emit(f"Slide {i+1}/{len(storyboard)}: ready ({sl.duration:.1f}s)")

    def _transition():
        if not transitions:
            return None
        try:
            from videodb.editor import Transition
            return Transition(in_="fade", out="fade", duration=0.4)
        except Exception as e:
            logger.warning("transition unavailable: %s", e)
            return None

    # PASS 1 — clean timeline: images + audio + transitions (NO burned-in captions)
    timeline = Timeline(conn)
    vtrack, atrack = Track(), Track()
    start = 0.0
    for sl in storyboard:
        tr = _transition()
        if tr is not None:
            img_clip = EClip(asset=ImageAsset(id=sl.image_id), duration=sl.duration, transition=tr)
        else:
            img_clip = EClip(asset=ImageAsset(id=sl.image_id), duration=sl.duration)
        vtrack.add_clip(start, img_clip)
        atrack.add_clip(start, EClip(asset=AudioAsset(id=sl.audio_id), duration=sl.duration))
        start += sl.duration
    timeline.add_track(vtrack)
    timeline.add_track(atrack)
    stream_url = timeline.generate_stream()

    # PASS 2 — auto captions via CaptionAsset (the proper subtitle tool)
    if captions:
        stream_url = _add_auto_captions(conn, stream_url)

    return stream_url, storyboard


# ---------------------------------------------------------------------------
# Manual smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse, json

    vdb.enable_logging()  # show live progress (sandbox create/ready/stop, each slide)

    ap = argparse.ArgumentParser(description="ReVision generate smoke test")
    ap.add_argument("--summary", nargs=2, metavar=("VIDEO_ID", "TOPIC"))
    ap.add_argument("--cards", nargs=2, metavar=("VIDEO_ID", "TOPIC"))
    ap.add_argument("--pack", nargs=2, metavar=("VIDEO_ID", "TOPIC"))
    ap.add_argument("--storyboard", nargs=2, metavar=("VIDEO_ID", "TOPIC"),
                    help="plan the video storyboard ONLY (no image/audio generated)")
    ap.add_argument("--precise", nargs=2, metavar=("VIDEO_ID", "TOPIC"),
                    help="find precise ask()-cited moments + a tight clip")
    ap.add_argument("--reel", nargs=2, metavar=("VIDEO_ID", "TOPIC"),
                    help="build a summary highlight reel from precise moments")
    ap.add_argument("--style", default="clean flat-vector educational",
                    help="visual style for the storyboard (e.g. animated, realistic)")
    args = ap.parse_args()

    if args.precise:
        vid, topic = args.precise
        ranges = find_precise_moments(vid, topic)
        print(f"PRECISE MOMENTS for '{topic}':")
        for s, e in ranges:
            print(f"  {s:8.1f}-{e:8.1f}  ({e-s:.1f}s)")
        clip = make_precise_clip(vid, topic)
        print("CLIP:", clip.stream_url if clip else None,
              f"({clip.start:.1f}-{clip.end:.1f})" if clip else "")
    elif args.reel:
        vid, topic = args.reel
        reel = make_summary_reel(vid, topic)
        if reel:
            print(f"SUMMARY REEL: {reel.stream_url}\n  spans {reel.start:.1f}-{reel.end:.1f}")
        else:
            print("no reel produced")
    elif args.storyboard:
        _, topic = args.storyboard
        slides = plan_storyboard(topic, style=args.style)
        print(f"STORYBOARD for '{topic}' (style: {args.style}) — {len(slides)} slides:\n")
        for i, s in enumerate(slides, 1):
            print(f"[{i}] NARRATION: {s.narration}")
            print(f"    IMAGE:     {s.image_prompt}\n")
    elif args.summary:
        _, topic = args.summary
        s = make_summary(topic)
        print("SUMMARY:\n", s.text, "\nsources:", len(s.sources))
    elif args.cards:
        _, topic = args.cards
        print("FLASHCARDS:")
        for c in make_flashcards(topic):
            print(f"  Q: {c.front}\n  A: {c.back}\n")
        print("CUE CARDS:")
        for c in make_cue_cards(topic):
            print(f"  - {c.text}")
    elif args.pack:
        vid, topic = args.pack
        pack = build_study_pack(vid, topic)
        d = pack.to_dict()
        print("STUDY PACK keys:", list(d.keys()))
        print("summary:", (pack.summary.text[:160] if pack.summary else None))
        print("clip:", pack.clip.stream_url if pack.clip else None)
        print("flashcards:", len(pack.flashcards), " cue_cards:", len(pack.cue_cards))
    else:
        ap.print_help()