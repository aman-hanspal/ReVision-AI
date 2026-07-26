# tests/phase0/probe_track.py
import sys, pathlib, inspect
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import _helpers as h
from videodb.editor import Track
h.banner("Track methods")
h.info(f"add_clip{inspect.signature(Track.add_clip)}")
for m in [x for x in dir(Track) if not x.startswith('_')]:
    try: h.info(f"{m}{inspect.signature(getattr(Track, m))}")
    except Exception: h.info(m)