"""Phase 0 / 09 — clips from results.

WHAT: proves the clip pipeline. Builds clips via video.generate_stream([(start,end)])
      with ranges CLAMPED to the video length, so a shot whose end overshoots the
      true duration (a known tail-rounding edge) can never crash the clip.
PASS: single-shot clip AND multi-topic reel both return playable .m3u8 URLs.
RUN:  python tests/phase0/09_clip.py
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import _helpers as h
import os, time

def main():
    h.banner("09  clips")
    coll = h.get_coll()
    vid = h.need("video_id")
    iname = h.load_state("index_name", "transcript")
    v = coll.get_video(vid)

    shots = v.semantic_search(query=h.TEST_TOPIC, index_names=[iname], top_k=3).get_shots()
    if not shots:
        h.die("no shots to clip (run 05/06 first)")

    vlen = float(getattr(v, "length", 0) or 0)
    h.info(f"video length: {vlen}s")

    def clamp(start, end):
        """Keep ranges inside [0, video_length]; drop degenerate ones."""
        e = min(float(end), vlen) if vlen else float(end)
        s = max(0.0, min(float(start), e - 0.1))
        return (s, e) if e > s else None

    # single shot (clamped) -> build via video.generate_stream for consistency
    s0 = clamp(shots[0].start, shots[0].end)
    if not s0:
        h.die("top shot produced a degenerate range after clamping")
    one = v.generate_stream([s0])
    h.info(f"single-shot clip {s0}: {one}")

    # reel from clamped ranges
    ranges = [c for c in (clamp(s.start, s.end) for s in shots[:3]) if c]
    h.info(f"clamped ranges: {ranges}")
    if not ranges:
        h.die("no valid ranges after clamping")
    reel = v.generate_stream(ranges)
    h.info(f"reel ({len(ranges)} ranges): {reel}")

    if not (one and reel):
        h.die("a stream URL came back empty")
    h.passed("clip + reel stream URLs generated (ranges clamped to video length)")

if __name__ == "__main__":
    main()