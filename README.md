# ReVision — Revise important concepts from any lecture

Upload a lecture (file or YouTube links), and ReVision's agent finds the key topics
and builds a study pack: a clip, a grounded summary, and cue/flash cards for each —
delivered in the app and optionally to Telegram. Built on the VideoDB SDK.

## Progressive setup
- **Level 1 — core (works immediately):** VIDEO_DB_API_KEY only. Upload -> ask -> clip + summary + cards.
- **Level 2 — learning video (stretch):** sandbox FLUX + OmniVoice + Timeline.
- **Level 3 — Telegram:** TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID.

## Run
1. pip install -r requirements.txt
2. cp .env.example .env  and set VIDEO_DB_API_KEY
3. uvicorn backend.main:app --reload
4. cd frontend && npm install && npm run dev

## VideoDB usage (depth)
upload, understand([spoken_words,vlm,ocr]), index, semantic_search / search / ask,
shot.generate_stream / video.generate_stream, sandbox (cards + FLUX + OmniVoice),
Timeline (learning video), and the VideoDB LLM proxy (gpt-4o) for the agent's tool-calling.
See docs/confirmed_signatures.md.

## Architecture
VideoDB-native agent (Path B). Director is NOT forked; only its agent patterns informed the design.

single clip = ONE moment. "Jump to the single best spot where neural networks are explained." One continuous cut. Good for "show me the explanation."
SUMMARY REEL = MULTIPLE moments stitched. "Grab the 4 key sub-points from across the lecture and splice them into one highlight." Good for "give me a tour of the topic."
