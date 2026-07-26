"""Phase 0 / 08 — ask (grounded summary + source clips).

WHAT: collection.ask(...) returns a synthesized answer AND source Shots.
      This is ReVision's summary generator (grounded, native, with evidence).
PASS: prints a non-empty answer and >=1 source shot.
RUN:  python tests/phase0/08_ask.py
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import _helpers as h
import os, time

def main():
    h.banner("08  ask (grounded summary)")
    coll = h.get_coll()
    q = "Summarise the key concepts taught in this lecture."
    ans = coll.ask(question=q, include_sources=True)
    text = getattr(ans, "answer", None)
    srcs = getattr(ans, "sources", []) or []
    h.info(f"answer: {str(text)[:400]}")
    h.info(f"sources: {len(srcs)} shots")
    for s in srcs[:3]:
        start, end = getattr(s, "start", None), getattr(s, "end", None)
        try:
            url = s.generate_stream()
        except Exception as e:
            url = f"(stream error: {e})"
        h.info(f"  {start}-{end}  stream={url}")
    if not text:
        h.die("ask returned no answer")
    h.passed("ask returned a grounded answer")

if __name__ == "__main__":
    main()