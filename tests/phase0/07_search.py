"""Phase 0 / 07 — intelligent search (collection.search).

WHAT: lets VideoDB plan retrieval for a natural-language ask ("key topics").
      This is the call the agent will lean on. Prints shots + response_type.
PASS: returns shots for a natural-language query.
RUN:  python tests/phase0/07_search.py
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import _helpers as h
import os, time

def main():
    h.banner("07  intelligent search")
    coll = h.get_coll()
    q = "the most important topics taught in this lecture"
    resp = coll.search(query=q, top_k=h.TOP_K, return_fields=["transcript"])
    h.info(f"response_type: {getattr(resp,'response_type',None)}")
    shots = list(resp)  # SearchResponse is iterable over shots
    h.info(f"{len(shots)} shots")
    for s in shots[:h.TOP_K]:
        h.info(f"  {getattr(s,'video_id','?')} {s.start:.1f}-{s.end:.1f} {getattr(s,'text',None)!r}")
    if not shots:
        h.die("no shots from intelligent search")
    h.passed("intelligent search returned shots")

if __name__ == "__main__":
    main()