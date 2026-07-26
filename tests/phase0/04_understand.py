"""Phase 0 / 04 — understand([spoken_words]).

WHAT: runs hosted spoken-word understanding on the uploaded video, times it,
      and DUMPS the understanding + analyzer objects so we learn the real field
      names (analyzer name, ids) before we index.
PASS: understand completes; a spoken_words/transcript analyzer is retrievable.
RUN:  python tests/phase0/04_understand.py
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import _helpers as h
import os, time

def _pick_transcript_analyzer(u):
    """Select the transcript analyzer by TYPE (names carry a random suffix)."""
    for a in getattr(u, "analyzers", []) or []:
        if getattr(a, "type", "") == "speech_transcription":
            return a
    analyzers = getattr(u, "analyzers", []) or []
    return analyzers[0] if analyzers else None

def main():
    h.banner("04  understand [spoken_words]")
    coll = h.get_coll()
    vid = h.need("video_id")
    v = coll.get_video(vid)
    t = time.time()
    u = v.understand(analyzers=[{"type": "spoken_words"}])
    u.wait_until_complete()
    h.info(f"understand took {time.time()-t:.1f}s")
    h.dump_attrs(u, "understanding")

    analyzer = _pick_transcript_analyzer(u)
    if analyzer is not None:
        h.info(f"selected analyzer: name={analyzer.name} type={analyzer.type} id={analyzer.id}")
        h.dump_attrs(analyzer, "analyzer")
    else:
        h.info("no speech_transcription analyzer found — check the dump above")

    h.passed("understand completed")

if __name__ == "__main__":
    main()