"""Phase 0 / 10 — sandbox text generation (flash/cue cards)  [DISCOVERY].

WHAT: creates a small text-generation sandbox and tries to generate flashcards
      from a transcript slice. The exact generate-text call name isn't in our
      docs yet, so this probes several likely method names and DUMPS what's
      available, then ALWAYS stops the sandbox (runtime-billed).
PASS: a sandbox becomes ready AND one generation call returns text.
NOTE: if all call attempts fail, read the dumped members to find the real method,
      tell me the name, and I'll finalise generate.py against it.
RUN:  python tests/phase0/10_cards_sandbox.py
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import _helpers as h
import os, time

def _try_generate(conn, coll, sandbox_id, prompt):
    attempts = [
        ("coll.generate_text", lambda: coll.generate_text(prompt=prompt, sandbox_id=sandbox_id)),
        ("conn.generate_text", lambda: conn.generate_text(prompt=prompt, sandbox_id=sandbox_id)),
        ("coll.generate_text+model", lambda: coll.generate_text(prompt=prompt, model_name="Qwen/Qwen3-4B", sandbox_id=sandbox_id)),
    ]
    for label, fn in attempts:
        try:
            out = fn()
            h.info(f"{label} -> OK")
            return out
        except Exception as e:
            h.info(f"{label} -> {type(e).__name__}: {e}")
    return None

def main():
    h.banner("10  sandbox text-gen (cards)  [discovery]")
    conn = h.connect()
    coll = conn.get_collection()
    sandbox = None
    try:
        import videodb
        tier = getattr(getattr(videodb, "SandboxTier", None), h.SANDBOX_TIER, h.SANDBOX_TIER)
        h.info("creating text-generation sandbox...")
        sandbox = conn.create_sandbox(tier=tier, model_categories=["text_generation"])
        h.dump_attrs(sandbox, "sandbox")
        if hasattr(sandbox, "wait_for_ready"):
            sandbox.wait_for_ready(timeout=300, interval=5)
        sid = getattr(sandbox, "id", None)
        h.info(f"sandbox id: {sid}")
        prompt = ("From this lecture transcript slice, write 3 flashcards as "
                  "Q|A lines:\n\n'Gradient descent minimises a loss function by "
                  "stepping in the negative gradient direction.'")
        out = _try_generate(conn, coll, sid, prompt)
        if out is None:
            h.failed("no generate-text call succeeded — see dumped members above; tell me the real method")
            return
        h.info(f"generated: {str(out)[:400]}")
        h.passed("sandbox text generation works")
    finally:
        if sandbox is not None:
            for m in ("stop", "delete"):
                try:
                    getattr(sandbox, m)()
                    h.info(f"sandbox.{m}() -> ok (billing stopped)")
                    break
                except Exception as e:
                    h.info(f"sandbox.{m}() -> {e}")

if __name__ == "__main__":
    main()