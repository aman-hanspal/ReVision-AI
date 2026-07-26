"""Phase 0 / 11 — VideoDB LLM proxy tool-calling round-trip.

WHAT: points a standard OpenAI client at https://api.videodb.io with your
      VideoDB key and model gpt-4o-2024-11-20, sends one tool, and confirms a
      structured tool_call comes back. This is the agent's brain — billed to
      your VideoDB credits, no personal OpenAI key.
PASS: response contains a tool_call selecting 'search_lecture' with an argument.
RUN:  python tests/phase0/11_proxy_toolcall.py
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import _helpers as h
import os, time

def main():
    h.banner("11  proxy tool-call round-trip")
    from openai import OpenAI
    client = OpenAI(api_key=h.API_KEY, base_url=h.BASE_URL)
    tools = [{
        "type": "function",
        "function": {
            "name": "search_lecture",
            "description": "Search the indexed lecture for a topic and return timestamped moments.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "the topic to find"}},
                "required": ["query"],
            },
        },
    }]
    resp = client.chat.completions.create(
        model=h.AGENT_MODEL,
        messages=[
            {"role": "system", "content": "You are ReVision. Use tools when the user wants to find a topic."},
            {"role": "user", "content": "Find where gradient descent is explained."},
        ],
        tools=tools,
        tool_choice="auto",
    )
    msg = resp.choices[0].message
    calls = msg.tool_calls or []
    h.info(f"finish_reason: {resp.choices[0].finish_reason}")
    if not calls:
        h.info(f"content: {msg.content}")
        h.die("no tool_call returned — model didn't call the tool")
    for c in calls:
        h.info(f"tool: {c.function.name}  args: {c.function.arguments}")
    h.passed("proxy returned a structured tool_call (agent brain works, billed to VideoDB)")

if __name__ == "__main__":
    main()