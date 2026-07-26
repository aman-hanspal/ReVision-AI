"""
backend/agent/revision_agent.py — the ReVision agent tool-loop.

WHAT:  the agent brain. Sends the user's message + tool schemas to GPT-4o (via the
       VideoDB proxy), lets it choose tools, runs them (real pipeline), feeds
       results back, and repeats until it produces a final answer. Path B: our own
       ~40-line loop, no Director.
USED BY: terminal (this file's __main__) now; the FastAPI backend later.
KEY EXPORTS: run_agent(user_message, video_id, history) -> (reply_text, displays, history)
FLOW:
   user message
     -> LLM (proxy, gpt-4o) picks tool(s)
     -> execute_tool runs the real pipeline
     -> results fed back to LLM
     -> repeat (max AGENT_MAX_STEPS) until LLM returns final text
RUN (terminal, video already indexed):
   # one-shot:
   python -m backend.agent.revision_agent --video <VIDEO_ID> --prompt "flashcards + a summary reel on neural networks"
   # interactive chat:
   python -m backend.agent.revision_agent --video <VIDEO_ID>
   # (omit --video to auto-read the last indexed video from tests/.state.json)
"""
from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional, Tuple

from shared import config
from shared import videodb_service as vdb
from backend.agent import tools as toolmod
from backend.agent.prompts import system_prompt
from shared.progress import emit

logger = logging.getLogger("revision.agent")


def run_agent(user_message: str, video_id: str = "",
              history: Optional[List[Dict]] = None
              ) -> Tuple[str, List[Dict], List[Dict]]:
    """Run one agent turn (may involve several tool calls).

    Returns (reply_text, display_payloads, updated_history).
    display_payloads = list of dicts from tools (URLs, cards) for the UI/terminal.
    """
    client = vdb.agent_client()
    messages: List[Dict] = history[:] if history else [
        {"role": "system", "content": system_prompt(video_id)}
    ]
    messages.append({"role": "user", "content": user_message})

    displays: List[Dict] = []

    for step in range(config.AGENT_MAX_STEPS):
        emit("Thinking about what to do next…", kind="thinking")
        resp = client.chat.completions.create(
            model=config.AGENT_MODEL,
            messages=messages,
            tools=toolmod.TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=config.AGENT_TEMPERATURE,
        )
        msg = resp.choices[0].message
        tool_calls = msg.tool_calls or []

        # record the assistant turn (with any tool calls)
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": c.id, "type": "function",
                 "function": {"name": c.function.name, "arguments": c.function.arguments}}
                for c in tool_calls
            ] if tool_calls else None,
        })

        if not tool_calls:
            # final answer
            return (msg.content or "", displays, messages)

        # run each requested tool, feed results back
        for c in tool_calls:
            try:
                args = json.loads(c.function.arguments or "{}")
            except Exception:
                args = {}
            # inject the current video_id if the model omitted it
            if "video_id" in _tool_params(c.function.name) and not args.get("video_id") and video_id:
                args["video_id"] = video_id
            # the telegram tool needs the results produced so far this run
            if c.function.name == "send_to_telegram":
                args["displays"] = displays
            print(f"  \033[96m→ {c.function.name}({_short(args)})\033[0m")
            result_text, display = toolmod.execute_tool(c.function.name, args)
            if display:
                displays.append(display)
            messages.append({
                "role": "tool",
                "tool_call_id": c.id,
                "content": result_text,
            })

    # hit the step cap
    return ("(agent reached its step limit)", displays, messages)


def _tool_params(name: str) -> set:
    for t in toolmod.TOOL_SCHEMAS:
        if t["function"]["name"] == name:
            return set(t["function"]["parameters"]["properties"].keys())
    return set()


def _short(args: Dict) -> str:
    return ", ".join(f"{k}={str(v)[:40]}" for k, v in args.items())


# ---------------------------------------------------------------------------
# Pretty-print the tool outputs (URLs, cards) for the terminal
# ---------------------------------------------------------------------------
def print_displays(displays: List[Dict]) -> None:
    for d in displays:
        kind = d.get("kind")
        print("\n" + "-" * 60)
        if kind == "study_pack":
            print(f"STUDY PACK — {d.get('topic')}")
            if d.get("summary"):
                print(f"\nSummary: {d['summary'][:300]}")
            print(f"\nSingle clip : {d.get('single_clip_url')}")
            print(f"Summary reel: {d.get('summary_reel_url')}")
            print(f"Summary video (FLUX+TTS): {d.get('learning_video_url')}")
            print(f"Concept image: {d.get('concept_image_url')}")
            if d.get("flashcards"):
                print("\nFlashcards:")
                for c in d["flashcards"]:
                    print(f"  Q: {c['front']}\n  A: {c['back']}")
            if d.get("cue_cards"):
                print("\nCue cards:")
                for t in d["cue_cards"]:
                    print(f"  - {t}")
        elif kind == "reel":
            print(f"SUMMARY REEL — {d.get('topic')}\n  {d.get('summary_reel_url')}")
        elif kind == "clip":
            print(f"CLIP — {d.get('topic')}\n  {d.get('clip_url')}")
        elif kind == "learning_video":
            print(f"LEARNING VIDEO — {d.get('topic')} ({d.get('slides')} slides)\n"
                  f"  {d.get('learning_video_url')}")
        elif kind == "search":
            print(f"MOMENTS — {d.get('query')}")
            for m in d.get("moments", []):
                print(f"  {m}")
        elif kind == "ingest":
            print(f"INDEXED — {d.get('title')}  video_id={d.get('video_id')}")
        elif kind == "error":
            print(f"ERROR in {d.get('tool')}: {d.get('error')}")


# ---------------------------------------------------------------------------
# Terminal runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse, pathlib

    vdb.enable_logging()

    ap = argparse.ArgumentParser(description="ReVision agent (terminal)")
    ap.add_argument("--video", help="video_id of the already-indexed lecture")
    ap.add_argument("--prompt", help="one-shot prompt; omit for interactive chat")
    args = ap.parse_args()

    # resolve video_id: --video, else last indexed from tests/.state.json
    video_id = args.video or ""
    if not video_id:
        state = pathlib.Path("tests/.state.json")
        if state.exists():
            try:
                video_id = json.loads(state.read_text()).get("video_id", "")
            except Exception:
                pass
    if video_id:
        print(f"Using lecture video_id: {video_id}")
    else:
        print("No video_id set — give a URL in your prompt to index one, or pass --video.")

    def turn(prompt, history):
        print(f"\n\033[93mYou:\033[0m {prompt}")
        reply, displays, history = run_agent(prompt, video_id=video_id, history=history)
        print_displays(displays)
        print(f"\n\033[92mReVision:\033[0m {reply}")
        return history

    if args.prompt:
        turn(args.prompt, None)
    else:
        print("\nReVision agent — type a request (or 'quit').")
        hist = None
        while True:
            try:
                p = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if p.lower() in {"quit", "exit", "q"}:
                break
            if p:
                hist = turn(p, hist)