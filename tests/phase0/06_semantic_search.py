"""Phase 0 / 06 — semantic_search  [HIGHEST-RISK: is retrieval good?].

WHAT: searches the transcript index for a topic and prints timestamped shots.
      If data/demo_annotations.csv has rows, checks whether any returned shot
      overlaps a ground-truth [start,end] (soft check, prints MATCH).
PASS: returns >=1 shot; you eyeball that the top hit is actually about the topic.
SETUP: optional .env  TEST_TOPIC="gradient descent"
RUN:  python tests/phase0/06_semantic_search.py
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import _helpers as h
import os, time

import csv

def _annotations():
    p = h.ROOT / "data" / "demo_annotations.csv"
    if not p.exists():
        return []
    with open(p) as f:
        return list(csv.DictReader(f))

def main():
    h.banner("06  semantic_search")
    coll = h.get_coll()
    vid = h.need("video_id")
    iname = h.load_state("index_name", "transcript")
    v = coll.get_video(vid)
    res = v.semantic_search(query=h.TEST_TOPIC, index_names=[iname], top_k=h.TOP_K)
    shots = res.get_shots()
    h.info(f"query: {h.TEST_TOPIC!r} -> {len(shots)} shots")
    for s in shots[:h.TOP_K]:
        h.info(f"  {s.start:.1f}-{s.end:.1f}  score={getattr(s,'search_score',None)}  {getattr(s,'text',None)!r}")
    if not shots:
        h.die("no shots returned — retrieval empty (check index/query)")
    for row in _annotations():
        try:
            gs, ge = float(row["start_seconds"]), float(row["end_seconds"])
        except Exception:
            continue
        if any(s.start <= ge and s.end >= gs for s in shots):
            h.info(f"  MATCH ground-truth [{gs}-{ge}] '{row.get('event')}'")
    h.passed("semantic_search returned shots (verify the top hit is on-topic)")

if __name__ == "__main__":
    main()