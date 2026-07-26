"""Phase 0 / 01 — connect + collection.

WHAT: proves your VIDEO_DB_API_KEY authenticates and a collection resolves.
PASS: prints a collection id with no error.
RUN:  python tests/phase0/01_connect.py
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import _helpers as h
import os, time

def main():
    h.banner("01  connect + collection")
    conn = h.connect()
    h.passed("connected to VideoDB")
    coll = conn.get_collection()
    cid = getattr(coll, "id", None) or getattr(getattr(coll, "meta", None), "id", "?")
    h.info(f"collection id: {cid}")
    h.save_state("collection_id", str(cid))
    h.passed("collection resolved")

if __name__ == "__main__":
    main()