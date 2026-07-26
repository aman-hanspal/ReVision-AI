"""Stretch / 13 — OmniVoice TTS (sandbox). Confirms audio asset + URL."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import _helpers as h
import os, time

def main():
    h.banner("13  OmniVoice TTS (stretch)")
    conn = h.connect(); coll = conn.get_collection(); sandbox = None
    audio = None
    try:
        import videodb
        tier = getattr(getattr(videodb, "SandboxTier", None), "small", "small")
        sandbox = conn.create_sandbox(tier=tier, model_categories=["text_to_speech"])
        if hasattr(sandbox, "wait_for_ready"):
            sandbox.wait_for_ready(timeout=300, interval=5)
        sid = getattr(sandbox, "id", None)
        text = "Gradient descent minimises the loss by stepping downhill along the negative gradient."
        for label, fn in [
            ("coll.generate_voice", lambda: coll.generate_voice(text=text, sandbox_id=sid)),
            ("coll.generate_audio", lambda: coll.generate_audio(text=text, sandbox_id=sid)),
        ]:
            try:
                audio = fn()
                h.info(f"{label} -> OK: {audio!r}")
                break
            except Exception as e:
                h.info(f"{label} -> {type(e).__name__}: {e}")
        if audio is None:
            h.failed("no TTS call succeeded — dump above shows what was tried")
            return
        h.dump_attrs(audio, "audio asset")
    finally:
        if sandbox is not None:
            try: sandbox.stop(); h.info("sandbox.stop() ok")
            except Exception as e: h.info(f"stop -> {e}")

    # fetch URL AFTER stop (assets are collection-scoped, like images)
    try:
        h.info(f"audio url: {audio.generate_url()}")
        h.save_state("demo_audio_id", getattr(audio, "id", None))
        h.passed("TTS generated + URL fetched")
    except Exception as e:
        h.info(f"generate_url() -> {e}")
        h.failed("audio asset made but URL fetch failed — paste the dump above")

if __name__ == "__main__":
    main()