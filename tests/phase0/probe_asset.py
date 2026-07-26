# tests/phase0/probe_asset.py
import sys, pathlib, inspect
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import _helpers as h
from videodb.editor import ImageAsset, AudioAsset, VideoAsset, TextAsset, Clip, Track

def sig(cls):
    try: h.info(f"{cls.__name__}{inspect.signature(cls.__init__)}")
    except Exception as e: h.info(f"{cls.__name__}: {e}")

def main():
    h.banner("probe: editor asset signatures")
    for c in (ImageAsset, AudioAsset, VideoAsset, TextAsset, Clip, Track):
        sig(c)

if __name__ == "__main__":
    main()