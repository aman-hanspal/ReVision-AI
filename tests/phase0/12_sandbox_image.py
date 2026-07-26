"""Stretch / 12 — FLUX image generation (sandbox)  [DISCOVERY].

WHAT: creates a medium image-generation sandbox and probes the image-gen call
      (FLUX.1-dev) to make a topic illustration (e.g. a gradient-descent curve).
      Dumps members if the call name is unknown; ALWAYS stops the sandbox.
PASS: returns an image asset / URL.
RUN:  python tests/stretch/12_sandbox_image.py
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import _helpers as h
import os, time

def main():
    h.banner("12  FLUX image (stretch)")
    conn = h.connect(); coll = conn.get_collection(); sandbox = None
    try:
        import videodb
        tier = getattr(getattr(videodb, "SandboxTier", None), "medium", "medium")
        sandbox = conn.create_sandbox(tier=tier, model_categories=["image_generation"])
        h.dump_attrs(sandbox, "sandbox")
        if hasattr(sandbox, "wait_for_ready"): sandbox.wait_for_ready(timeout=300, interval=5)
        sid = getattr(sandbox, "id", None)
        prompt = "A clean diagram of a downward gradient-descent curve on a loss surface, minimal, labeled"
        for label, fn in [
            ("coll.generate_image", lambda: coll.generate_image(prompt=prompt, model_name="black-forest-labs/FLUX.1-dev", sandbox_id=sid)),
            ("conn.generate_image", lambda: conn.generate_image(prompt=prompt, sandbox_id=sid)),
        ]:
            try:
                out = fn(); h.info(f"{label} -> OK: {out}"); h.passed("image generated"); return
            except Exception as e:
                h.info(f"{label} -> {type(e).__name__}: {e}")
        h.failed("no image-gen call succeeded — see dumped members; tell me the real method")
    finally:
        if sandbox is not None:
            for m in ("stop", "delete"):
                try: getattr(sandbox, m)(); h.info(f"sandbox.{m}() ok"); break
                except Exception as e: h.info(f"sandbox.{m}() -> {e}")

if __name__ == "__main__":
    main()