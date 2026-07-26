"""Free caption probe — NO image gen. Tests 2-line wrap in a bottom black bar.
Run:  python tests/phase0/caption_probe.py <existing_image_id>
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from shared import videodb_service as vdb
from videodb.editor import (Timeline, Track, Clip, ImageAsset, TextAsset, Font,
                            Background, Alignment, HorizontalAlignment,
                            VerticalAlignment, TextAlignment, Offset)

img_id = sys.argv[1] if len(sys.argv) > 1 else None
if not img_id:
    print("usage: python tests/phase0/caption_probe.py <img-id>"); sys.exit(1)

conn = vdb.get_conn()
DUR = 5.0
# a deliberately LONG caption to verify it wraps to 2 lines inside the box
CAP = ("Each pixel's grayscale value becomes that neuron's activation, "
       "from zero for black to one for white")

CAP_W = 940      # narrow enough to force wrap; away from the bottom-right logo

tl = Timeline(conn)
vt = Track(); tt = Track(z_index=1)
vt.add_clip(0, Clip(asset=ImageAsset(id=img_id), duration=DUR))

cap = TextAsset(
    text=CAP,
    font=Font(family="Lato", size=24, color="#FFFFFF"),
    background=Background(width=CAP_W, height=130, color="#000000",   # 2-line tall
                         opacity=1.0, text_alignment=TextAlignment.center),
    alignment=Alignment(horizontal=HorizontalAlignment.center,
                        vertical=VerticalAlignment.bottom),
    width=CAP_W,
)
tt.add_clip(0, Clip(asset=cap, duration=DUR, offset=Offset(x=0, y=-0.06)))

tl.add_track(vt); tl.add_track(tt)
print("CAPTION TEST:", tl.generate_stream())