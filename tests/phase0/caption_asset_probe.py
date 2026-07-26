"""Probe: can we get VideoDB's clean auto-CaptionAsset on our LEARNING VIDEO?

Two-pass flow (CaptionAsset needs an INDEXED video with spoken words):
  1. take an already-rendered learning-video stream URL (.m3u8) OR a video_id
  2. upload it back into the collection as a Video (if given a URL)
  3. video.index_spoken_words()   <-- required for src="auto"
  4. rebuild a Timeline: VideoAsset(that video) + CaptionAsset(src="auto")
  5. generate_stream() -> a captioned version

Run:
  # from an existing learning-video stream URL:
  python tests/phase0/caption_asset_probe.py --url "https://play.videodb.io/v1/....m3u8"
  # or from a video_id already in the collection:
  python tests/phase0/caption_asset_probe.py --video m-z-...
"""
import sys, pathlib, argparse, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from shared import videodb_service as vdb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="rendered learning-video .m3u8 stream URL to caption")
    ap.add_argument("--video", help="an existing video_id (m-...) to caption")
    ap.add_argument("--animation", default="reveal",
                    help="reveal|karaoke|supersize|box_highlight|impact|color_highlight")
    args = ap.parse_args()

    conn = vdb.get_conn()
    coll = conn.get_collection()

    # --- get an indexable Video ---
    if args.video:
        video = coll.get_video(args.video)
        print("using existing video:", video.id)
    elif args.url:
        print("uploading rendered stream back as a video (may take a bit)...")
        video = coll.upload(url=args.url)
        print("uploaded video:", video.id, "length:", getattr(video, "length", "?"))
    else:
        print("pass --url <m3u8> or --video <m-id>"); sys.exit(1)

    # --- index spoken words (REQUIRED for CaptionAsset src=auto) ---
    print("indexing spoken words (required for auto captions)...")
    t = time.time()
    try:
        video.index_spoken_words()
        print(f"index_spoken_words done in {time.time()-t:.1f}s")
    except Exception as e:
        print("index_spoken_words FAILED:", repr(e)); sys.exit(1)

    # --- build timeline: video + auto caption ---
    from videodb.editor import (Timeline, Track, Clip, VideoAsset, CaptionAsset,
                                CaptionAnimation)
    dur = float(getattr(video, "length", 0) or 15)

    anim = getattr(CaptionAnimation, args.animation, None)
    cap_kwargs = {"src": "auto"}
    if anim is not None:
        cap_kwargs["animation"] = anim
        cap_kwargs["primary_color"] = "&H00FFFFFF"      # white
        cap_kwargs["secondary_color"] = "&H0000FFFF"    # yellow highlight

    tl = Timeline(conn)
    vt = Track(); ct = Track(z_index=1)
    vt.add_clip(0, Clip(asset=VideoAsset(id=video.id), duration=dur))
    ct.add_clip(0, Clip(asset=CaptionAsset(**cap_kwargs), duration=dur))
    tl.add_track(vt); tl.add_track(ct)

    print("rendering captioned version...")
    url = tl.generate_stream()
    print("\nCAPTIONED VIDEO:", url)


if __name__ == "__main__":
    main()