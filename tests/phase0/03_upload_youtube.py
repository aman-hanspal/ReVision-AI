"""Phase 0 / 03 — upload a YouTube link.

WHAT: uploads TEST_YOUTUBE_URL (a lecture) and stores its video_id.
PASS: returns an 'm-...' id.
SETUP: in .env set  TEST_YOUTUBE_URL=https://www.youtube.com/watch?v=...
NOTE: sets state['video_id'] (last upload wins) — downstream tests use this one.
RUN:  python tests/phase0/03_upload_youtube.py
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import _helpers as h
import os, time

def main():
    h.banner("03  upload YouTube link")
    if not h.TEST_YOUTUBE_URL:
        h.die("set TEST_YOUTUBE_URL=https://www.youtube.com/watch?v=... in .env")
    coll = h.get_coll()
    t = time.time()
    v = coll.upload(url=h.TEST_YOUTUBE_URL)
    vid = getattr(v, "id", None)
    h.info(f"upload took {time.time()-t:.1f}s")
    h.info(f"video id: {vid}")
    h.info(f"length(s): {getattr(v, 'length', None)}")
    if not vid:
        h.die("no video id returned")
    h.save_state("video_id", vid)
    h.passed("uploaded YouTube video")

if __name__ == "__main__":
    main()