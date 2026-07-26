# tests/phase0/probe_job.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import _helpers as h

def main():
    h.banner("probe: image GenerationJob")
    conn = h.connect(); coll = conn.get_collection(); sb = None
    try:
        import videodb
        sb = conn.create_sandbox(tier="medium", model_categories=["image_generation"])
        sb.wait_for_ready(timeout=300, interval=5)
        job = coll.generate_image(
            prompt="A clean labeled diagram of a downward gradient-descent curve on a loss surface",
            sandbox_id=sb.id,
        )
        h.info(f"job repr: {job!r}")
        h.dump_attrs(job, "job")                       # show all fields/methods
        # try to wait + fetch, guarded so we learn the real names
        for m in ("wait_until_complete", "wait", "refresh"):
            if hasattr(job, m):
                try:
                    getattr(job, m)(); h.info(f"job.{m}() -> ok")
                except Exception as e:
                    h.info(f"job.{m}() -> {e}")
        h.dump_attrs(job, "job (after wait)")          # fields now populated?
    finally:
        if sb is not None:
            try: sb.stop(); h.info("sandbox stopped")
            except Exception as e: h.info(f"stop -> {e}")

if __name__ == "__main__":
    main()