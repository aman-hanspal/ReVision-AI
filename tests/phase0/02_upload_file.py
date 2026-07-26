"""Phase 0 / 02 — upload a local video file.

WHAT: uploads TEST_VIDEO_FILE and stores its video_id for later tests.
PASS: returns an 'm-...' id.
SETUP: in .env set  TEST_VIDEO_FILE=/abs/path/to/lecture.mp4
RUN:  python tests/phase0/02_upload_file.py
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import _helpers as h
import os, time

def main():
    h.banner("02  upload local file")
    if not h.TEST_VIDEO_FILE:
        h.die("set TEST_VIDEO_FILE=/abs/path/to/lecture.mp4 in .env")
    if not pathlib.Path(h.TEST_VIDEO_FILE).exists():
        h.die(f"file not found: {h.TEST_VIDEO_FILE}")
    coll = h.get_coll()
    t = time.time()
    v = coll.upload(file_path=h.TEST_VIDEO_FILE)
    vid = getattr(v, "id", None)
    h.info(f"upload took {time.time()-t:.1f}s")
    h.info(f"video id: {vid}")
    h.info(f"length(s): {getattr(v, 'length', None)}")
    if not vid:
        h.die("no video id returned")
    h.save_state("video_id", vid)
    h.passed("uploaded local file")

if __name__ == "__main__":
    main()