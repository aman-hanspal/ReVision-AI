"""Shared helpers for Phase-0 / stretch tests.

- loads .env (VIDEO_DB_API_KEY etc.)
- connect() / get_coll(): VideoDB handles
- state file (tests/.state.json) chains tests: e.g. 02 saves video_id, 05 saves index_name,
  later tests reuse them instead of re-uploading/re-indexing.
- dump_attrs(): prints an object's fields/methods so we DISCOVER real signatures live.
"""
import json, os, sys, pathlib
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1].parent   # tests/ -> project root
load_dotenv(ROOT / ".env")

API_KEY   = os.getenv("VIDEO_DB_API_KEY", "")
BASE_URL  = os.getenv("VIDEO_DB_BASE_URL", "https://api.videodb.io")
AGENT_MODEL = os.getenv("AGENT_MODEL", "gpt-4o-2024-11-20")
TOP_K     = int(os.getenv("TOP_K", "5"))
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.6"))
CLIP_PAD_S = float(os.getenv("CLIP_PAD_S", "2"))
SANDBOX_TIER = os.getenv("SANDBOX_TIER", "small")
TEST_VIDEO_FILE  = os.getenv("TEST_VIDEO_FILE", "")
TEST_YOUTUBE_URL = os.getenv("TEST_YOUTUBE_URL", "")
TEST_TOPIC = os.getenv("TEST_TOPIC", "the main concept explained in this lecture")

STATE = pathlib.Path(__file__).resolve().parent / ".state.json"

def banner(n): print("\n" + "=" * 62 + f"\n {n}\n" + "=" * 62)
def passed(m=""): print(f"\033[92m[PASS]\033[0m {m}")
def failed(m=""): print(f"\033[91m[FAIL]\033[0m {m}")
def info(m=""):  print(f"   {m}")
def die(m): failed(m); sys.exit(1)

def require_key():
    if not API_KEY:
        die("VIDEO_DB_API_KEY not set. Add it to .env at the project root.")

def connect():
    require_key()
    import videodb
    return videodb.connect(api_key=API_KEY)

def get_coll():
    return connect().get_collection()

def load_state(key=None, default=None):
    data = json.loads(STATE.read_text() or "{}") if STATE.exists() else {}
    return data.get(key, default) if key else data

def save_state(key, val):
    data = load_state() or {}
    data[key] = val
    STATE.write_text(json.dumps(data, indent=2))
    info(f"saved state[{key}] = {val}")

def need(key):
    v = load_state(key)
    if not v:
        die(f"state['{key}'] missing — run the earlier test that produces it first.")
    return v

def dump_attrs(obj, label="object"):
    info(f"{label}: type={type(obj).__name__}")
    names = [a for a in dir(obj) if not a.startswith("_")]
    info(f"{label} members: {names}")
    for a in names:
        try:
            v = getattr(obj, a)
            if not callable(v):
                info(f"   .{a} = {v!r}")
        except Exception:
            pass
