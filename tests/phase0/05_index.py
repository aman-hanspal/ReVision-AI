"""Phase 0 / 05 — build a searchable index.

WHAT: self-contained — re-runs understand([spoken_words]) then video.index(...),
      waits for the semantic index to reach 'ready', saves the index name.
PASS: index.is_successful is True (status 'ready').
RUN:  python tests/phase0/05_index.py
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import _helpers as h
import os, time

def _get_spoken_analyzer(u):
    """Pick the transcript analyzer by type (name has a random suffix each run)."""
    for a in getattr(u, "analyzers", []) or []:
        if getattr(a, "type", "") == "speech_transcription":
            return a
    analyzers = getattr(u, "analyzers", []) or []
    return analyzers[0] if analyzers else None

def main():
    h.banner("05  index transcript")
    coll = h.get_coll()
    vid = h.need("video_id")
    v = coll.get_video(vid)
    u = v.understand(analyzers=[{"type": "spoken_words"}])
    u.wait_until_complete()
    analyzer = _get_spoken_analyzer(u)
    if analyzer is None:
        h.die("could not get spoken_words analyzer (see test 04 dump for the real name)")
    idx = v.index(source=analyzer, name="transcript", use_for=["semantic", "query"])
    h.info(f"index created, status={getattr(idx,'status',None)} — waiting for embeddings...")
    idx.wait_until_complete(timeout=1800, poll_interval=10)
    h.info(f"status={getattr(idx,'status',None)}  is_successful={getattr(idx,'is_successful',None)}")
    if not getattr(idx, "is_successful", False):
        h.die(f"indexing failed: {getattr(idx,'error',None)}")
    h.save_state("index_name", "transcript")
    h.passed("index ready for semantic search")

if __name__ == "__main__":
    main()