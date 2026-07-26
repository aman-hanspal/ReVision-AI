"""Phase 0 / 14 — assemble a REAL multi-slide learning video (VideoDB Timeline).

Assets take id=; duration lives on Clip; clips placed via add_clip(start, clip).
Each slide's length = its narration's actual audio length (captured at generation),
so the image and its voice-over stay in sync. Narration is short (~4-5s each),
which is exactly why the video is multi-segment.
PASS: timeline.generate_stream() returns a playable URL (with audio).
RUN:  python tests/phase0/14_timeline_video.py
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import _helpers as h
import os, time

SLIDES = [
    ("A clean 2D diagram of a loss surface with a red ball at the top, flat-vector animated style",
     "Gradient descent starts high on the loss surface, where the error is large."),
    ("A clean 2D diagram of a red ball resting at the bottom of a valley, flat-vector animated style",
     "It steps downhill along the negative gradient until it reaches the minimum."),
]
MIN_SLIDE_SECONDS = 2.0   # floor so a very short narration still shows the image a beat


def gen_image_id(conn, coll, prompt):
    sb = conn.create_sandbox(tier="medium", model_categories=["image_generation"])
    try:
        sb.wait_for_ready(timeout=300, interval=5)
        return coll.generate_image(prompt=prompt, sandbox_id=sb.id).id
    finally:
        try: sb.stop()
        except Exception as e: h.info(f"image sandbox stop -> {e}")


def gen_audio(conn, coll, text):
    """Return (audio_id, length_seconds). Length captured from the returned asset."""
    sb = conn.create_sandbox(tier="small", model_categories=["text_to_speech"])
    try:
        sb.wait_for_ready(timeout=300, interval=5)
        aud = coll.generate_voice(text=text, sandbox_id=sb.id)
        length = getattr(aud, "length", None)
        if not length:
            h.info(f"audio {aud.id} exposed no .length -> using fallback; members: "
                   f"{[m for m in dir(aud) if not m.startswith('_')]}")
            length = 5.0
        return aud.id, float(length)
    finally:
        try: sb.stop()
        except Exception as e: h.info(f"audio sandbox stop -> {e}")


def main():
    h.banner("14  multi-slide learning video")
    conn = h.connect()
    coll = conn.get_collection()
    from videodb.editor import Timeline, Track, Clip, ImageAsset, AudioAsset

    # --- generate assets; keep image ids, audio ids + real lengths ---
    slides = []  # list of (img_id, aud_id, duration)
    for i, (iprompt, narration) in enumerate(SLIDES):
        t0 = time.time()
        h.info(f"slide {i}: image...")
        img_id = gen_image_id(conn, coll, iprompt)
        h.info(f"slide {i}: audio...")
        aud_id, alen = gen_audio(conn, coll, narration)
        dur = max(MIN_SLIDE_SECONDS, round(alen, 3))
        slides.append((img_id, aud_id, dur))
        h.info(f"slide {i} ready in {time.time()-t0:.1f}s  (narration {alen:.2f}s -> slide {dur:.2f}s)")

    h.info(f"slides: {slides}")
    timeline = Timeline(conn)

    # --- VISUAL track: image duration matches its narration ---
    vtrack = Track()
    start = 0.0
    for img_id, _aud_id, dur in slides:
        vtrack.add_clip(start, Clip(asset=ImageAsset(id=img_id), duration=dur))
        start += dur
    timeline.add_track(vtrack)
    h.info(f"visual track: {len(slides)} clips over {start:.2f}s")

    # prove visual-only renders first
    try:
        visual_only = timeline.generate_stream()
        h.info(f"visual-only video: {visual_only}")
    except Exception as e:
        h.info(f"visual-only assembly error: {e}")
        h.dump_attrs(timeline, "timeline")
        h.die("visual assembly failed — paste dump")

    # --- AUDIO track: clip duration = the narration's real length ---
    atrack = Track()
    start = 0.0
    for _img_id, aud_id, dur in slides:
        atrack.add_clip(start, Clip(asset=AudioAsset(id=aud_id), duration=dur))
        start += dur
    timeline.add_track(atrack)

    try:
        final = timeline.generate_stream()
        h.info(f"LEARNING VIDEO (with audio): {final}")
    except Exception as e:
        h.info(f"audio assembly error: {e}")
        h.die("audio track assembly failed — paste this")

    if not final:
        h.die("generate_stream returned empty")
    h.save_state("demo_learning_video", final)
    h.passed("assembled a multi-slide learning video (image + audio, narration-synced)")


if __name__ == "__main__":
    main()