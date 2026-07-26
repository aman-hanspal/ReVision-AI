# tests/phase0/probe_editor.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import _helpers as h

def main():
    h.banner("probe: videodb.editor Timeline surface")
    conn = h.connect()
    import videodb.editor as ed
    h.info(f"videodb.editor exports: {[n for n in dir(ed) if not n.startswith('_')]}")
    from videodb.editor import Timeline
    tl = Timeline(conn)
    h.dump_attrs(tl, "editor.Timeline")
    for cls in ("Track", "Clip", "VideoAsset", "AudioAsset", "ImageAsset", "TextAsset"):
        obj = getattr(ed, cls, None)
        h.info(f"{cls}: {'FOUND' if obj else 'missing'}"
               + (f"  doc={ (obj.__doc__ or '').strip()[:120] }" if obj else ""))

if __name__ == "__main__":
    main()