# tests/phase0/probe_url.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import _helpers as h

def main():
    h.banner("probe: Image.generate_url()")
    conn = h.connect(); coll = conn.get_collection(); sb = None
    try:
        sb = conn.create_sandbox(tier="medium", model_categories=["image_generation"])
        sb.wait_for_ready(timeout=300, interval=5)
        img = coll.generate_image(
            prompt="A clean labeled diagram of a downward gradient-descent curve on a loss surface",
            sandbox_id=sb.id,
        )
        h.info(f"image id: {img.id}")
        # URL BEFORE stopping the sandbox
        try:
            u1 = img.generate_url()
            h.info(f"generate_url() BEFORE stop -> {u1}")
        except Exception as e:
            h.info(f"generate_url() before stop -> {e}")
    finally:
        if sb is not None:
            try: sb.stop(); h.info("sandbox stopped")
            except Exception as e: h.info(f"stop -> {e}")

    # URL AFTER stopping the sandbox (re-fetch the asset by id if possible)
    try:
        u2 = img.generate_url()
        h.info(f"generate_url() AFTER stop -> {u2}")
    except Exception as e:
        h.info(f"generate_url() after stop -> {e}")

if __name__ == "__main__":
    main()