# ReVision AI

**Turn any lecture video into a complete, agent-generated study pack — grounded clips, an AI explainer video, flashcards, cue cards, and a summary — from a single natural-language prompt.**

Built for the Global Media Intelligence Hackathon, powered end-to-end by [VideoDB](https://videodb.io).

---

## Table of Contents

1. [What it does](#1-what-it-does)
2. [Demo](#2-demo)
3. [What gets generated](#3-what-gets-generated)
4. [System architecture](#4-system-architecture)
5. [Request flow](#5-request-flow)
6. [How VideoDB is used](#6-how-videodb-is-used)
7. [Repository structure & file-by-file guide](#7-repository-structure--file-by-file-guide)
8. [API reference](#8-api-reference)
9. [Setup — backend](#9-setup--backend)
10. [Setup — frontend](#10-setup--frontend)
11. [Setup — Telegram (optional)](#11-setup--telegram-optional)
12. [Example prompts](#12-example-prompts)
13. [Configuration reference](#13-configuration-reference)
14. [What's next — roadmap & quality](#14-whats-next--roadmap--quality)

---

## 1. What it does

Students and self-learners drown in long lecture videos. ReVision AI is an **agentic study companion**: you give it a lecture (a YouTube link or an uploaded file) and ask, in plain English, for whatever you need — "give me a summary reel on backpropagation," "make an animated explainer on how digits are recognized," or "full study pack with flashcards and a video." An LLM agent interprets the request, calls the right generation tools, and streams live progress while it works.

Everything it produces is **grounded in the actual lecture** — clips are real footage, summaries and cards are built from the transcript, and the AI explainer is scripted from the lecture's own content. Nothing is hallucinated from thin air.

Three things make it distinctive:

- **Agentic composition** — one chat interface, not a menu of buttons. The agent decides which tools to run based on intent, and can even deliver results to Telegram when asked.
- **Deep VideoDB usage** — it spans nearly the whole platform: upload, transcription, semantic indexing, natural-language search, grounded Q&A, programmable video editing (Timeline/Track/Clip), sandboxed generative models (text, image, TTS), and auto-captioning.

---

## 2. Demo

> _Add your demo video link and screenshots here._

| ReVision AI — study pack UI | Telegram delivery |
| --- | --- |
| ![UI screenshot](docs/images/ui.png) | ![Telegram screenshot](docs/images/telegram.png) |

**Demo video:** _[link]_

---

## 3. What gets generated

From one prompt, ReVision can produce any subset of the following. The UI renders **only what the agent actually created** — ask for a reel and you get a reel; ask for everything and the panel fills in.

| Output | What it is | How it's made |
| --- | --- | --- |
| **Jump to Moment** | One tight clip of the single best moment a topic is explained — real lecture footage. | `ask()`-cited moment → `generate_stream()` on a clamped range. |
| **Highlights** (summary reel) | Key moments of a topic stitched from **across** the lecture into one continuous highlight clip — real footage. | Topic decomposed into sub-points → precise moment per sub-point → chronological stitch via a multi-range `generate_stream()`. |
| **AI Explainer** (summary video) | A newly **generated** explainer video: AI images + narrated voiceover + auto-captions + fade transitions. | Storyboard (GPT-4o) → per-slide image (FLUX) + narration (TTS) on a VideoDB **Timeline** → re-index + **CaptionAsset** auto-subtitles. |
| **Summary** | A grounded prose summary of the topic. | VideoDB `collection.ask()` over the indexed transcript. |
| **Flashcards** | Q/A cards with a concept illustration header. | Sandbox `generate_text` + a dedicated `generate_image`. |
| **Cue cards** | Short revision bullet points. | Sandbox `generate_text`. |
| **Telegram delivery** | The whole pack (summary + links + cards) pushed to a Telegram chat. | Telegram Bot API — triggered by the agent (when asked) or the UI button. |

---

## 4. System architecture

ReVision is a three-layer system: a **React frontend**, a **FastAPI backend** that streams progress, and a **shared pipeline library** that wraps VideoDB. The agent sits between the API and the pipeline, turning natural language into tool calls.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND  (React + TS, Vite)                │
│   Ingest panel · Chat + live trace · Dynamic results · HLS players   │
└───────────────┬─────────────────────────────────────────────────────┘
                │  POST /upload      POST /chat (SSE)      POST /telegram
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        BACKEND  (FastAPI)                           │
│   routes/upload · routes/chat (SSE stream) · routes/telegram        │
│                          │                                          │
│                          ▼                                          │
│                 AGENT  (tool-loop, GPT-4o via VideoDB proxy)        │
│        prompts · tools (ingest / search / clip / reel / video /     │
│                         study_pack / telegram) · revision_agent     │
└───────────────┬─────────────────────────────────────────────────────┘
                │  (function calls)
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    SHARED PIPELINE  (shared/)                       │
│   retrieval (ingest/search)   generate (clips, reel, video, cards)  │
│   videodb_service (SDK adapter)   sandbox   progress   models        │
└───────────────┬─────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                            VideoDB                                   │
│  upload · transcription · semantic index · search · ask ·           │
│  Timeline/Track/Clip editing · sandbox (text/image/TTS) · captions  │
│  + LLM proxy (gpt-4o-2024-11-20) for the agent & content scripting  │
└─────────────────────────────────────────────────────────────────────┘
```

**Design principles**

- **Thin backend, smart agent.** The API is a small wrapper; all intelligence lives in the agent + pipeline. There is no per-feature endpoint — everything routes through `/chat` and the agent decides.
- **One progress bus.** `shared/progress.py` emits events that print to the terminal *and* stream to the UI, so both show identical traces.
- **One sandbox per job.** All generative work (text/image/TTS for a study pack) runs inside a single reused VideoDB sandbox session — provisioning is paid once, not per call.
- **Grounded by construction.** Clips come from real footage; summaries/cards come from `ask()` over the transcript; the explainer is scripted from lecture content.

---

## 5. Request flow

A full "study pack with video" request flows like this:

1. **Ingest** (once per lecture) — `POST /upload` → `retrieval.ingest()` uploads the video to VideoDB, runs `understand()` (transcription), and builds a semantic `index()`. Returns a `video_id`.
2. **Ask** — `POST /chat` (SSE) sends the prompt + `video_id`. The agent runs in a background thread; a progress listener streams every step to the browser.
3. **Agent decides** — GPT-4o (via the VideoDB proxy) reads the prompt and calls a tool, e.g. `make_study_pack(topic, include_video=true)`.
4. **Pipeline executes** —
   - `make_summary` → `collection.ask()`
   - `make_precise_clip` / `make_summary_reel` → `ask()`-cited moments → `generate_stream()`
   - `make_flashcards` / `make_cue_cards` → sandbox `generate_text`
   - concept image → sandbox `generate_image` (FLUX)
   - `make_learning_video` → storyboard → per-slide image + TTS on a **Timeline** → re-ingest + `index_spoken_words()` + **CaptionAsset** captions.
5. **Stream + render** — progress events stream the whole time; on completion a `result` event carries the URLs + cards, and the UI renders each dynamically. HLS (`.m3u8`) streams play in-browser via `hls.js`.
6. **(Optional) Deliver** — if the prompt mentions Telegram, the agent calls `send_to_telegram`; otherwise the user can click the "Send to Telegram" button.

---

## 6. How VideoDB is used

ReVision exercises VideoDB broadly — from ingestion through generative editing. This breadth is the core of the project.

| Capability | VideoDB feature / call | Where in code | Purpose |
| --- | --- | --- | --- |
| **Upload** | `collection.upload(url=…/file_path=…)` | `videodb_service.upload`, `retrieval.ingest` | Ingest a YouTube link or uploaded file. |
| **Transcription** | `video.understand(analyzers=[spoken_words])` | `videodb_service.understand_transcript` | Produce a speech transcript (analyzer selected by type). |
| **Semantic index** | `video.index(source=…, name="transcript", use_for=[semantic,query])` | `videodb_service.build_index` | Make the transcript searchable. |
| **Semantic search** | `video.semantic_search(query, index_names, top_k, score_threshold)` | `videodb_service.semantic_search`, `retrieval.find_topic` | Locate where a topic is discussed. |
| **Grounded Q&A** | `collection.ask(question, include_sources=True)` | `videodb_service.ask` | Grounded summaries + **cited source moments** for precise clipping. |
| **Clipping** | `video.generate_stream([(start,end), …])` | `videodb_service.clip`, `generate.make_*_clip/reel` | Single clips and multi-range highlight reels from real footage. |
| **Programmable editing** | `Timeline / Track / Clip / ImageAsset / AudioAsset / Transition` | `generate.make_learning_video` | Compose the AI explainer video from images + narration + fades. |
| **Sandbox — text** | `collection.generate_text(prompt, sandbox_id)` | `videodb_service.generate_text` | Flashcards & cue cards. |
| **Sandbox — image** | `collection.generate_image(prompt, model_name="…FLUX.1-dev", sandbox_id, config)` | `videodb_service.generate_image` | Slide images + concept illustration (uncapped sandbox FLUX). |
| **Sandbox — TTS** | `collection.generate_voice(text, sandbox_id)` | `videodb_service.generate_voice` | Narration audio for the explainer. |
| **Auto-captions** | `video.index_spoken_words()` + `CaptionAsset(src="auto")` | `generate._add_auto_captions` | Word-synced subtitles on the generated video. |
| **LLM proxy** | `OpenAI(base_url=VIDEO_DB_BASE_URL)`, `gpt-4o-2024-11-20` | `videodb_service.agent_client`, `llm_complete` | Powers the agent's tool-calling **and** content scripting — billed to VideoDB credits, no separate key. |

---

## 7. Repository structure & file-by-file guide

```
ReVisionAI/
├── shared/                 # the pipeline (VideoDB-facing logic)
├── backend/                # FastAPI app + the agent
├── frontend/               # React + TypeScript UI
├── tests/                  # Phase-0 validation + probes
├── docs/                   # architecture notes, confirmed API signatures
├── requirements.txt
└── .env.example
```

### `shared/` — the pipeline

| File | What it does |
| --- | --- |
| **`config.py`** | Central configuration: proxy base URL, agent model, sandbox tiers, retrieval/clip/video tunables. Reads from `.env`. |
| **`videodb_service.py`** | The VideoDB **adapter** — every SDK interaction lives here: connect, upload, understand, index, search, ask, clip, sandbox sessions, `generate_text/image/voice`, and the agent LLM client. |
| **`retrieval.py`** | `ingest()` (upload → understand → index → `VideoRef`), `find_topic`, `best_topics`. |
| **`generate.py`** | The content engine: `make_summary`, `make_flashcards`, `make_cue_cards`, `make_precise_clip`, `make_summary_reel`, `plan_storyboard`, `make_learning_video` (with two-pass captions & transitions), and the all-in-one `build_study_pack`. |
| **`sandbox.py`** | Sandbox lifecycle helpers — one-off (`sandbox_for`) and multi-category reusable sessions (`sandbox_session`). |
| **`models.py`** | Dataclasses: `VideoRef`, `TopicHit`, `Clip`, `Flashcard`, `CueCard`, `Summary`, `Slide`, `StudyPack`. |
| **`progress.py`** | The progress event bus — `emit()`, `step()`, `subscribe()`. Terminal logging + UI streaming from one source. |
| **`telegram_service.py`** | Formats a study pack and sends it via the Telegram Bot API. Fails soft if unconfigured. |

### `backend/` — API + agent

| File | What it does |
| --- | --- |
| **`main.py`** | FastAPI app, CORS, mounts routes, `/health`. |
| **`routes/upload.py`** | `POST /upload` (URL) and `POST /upload/file` (file) → `retrieval.ingest`. |
| **`routes/chat.py`** | `POST /chat` — runs the agent in a background thread and **streams progress + result over SSE** (with keep-alives). |
| **`routes/telegram.py`** | `POST /telegram` — pushes a study pack to Telegram. |
| **`agent/tools.py`** | Wraps pipeline functions as LLM tools (`ingest_lecture`, `search_topic`, `make_clip`, `make_summary_reel`, `make_learning_video`, `make_study_pack`, `send_to_telegram`) with OpenAI tool schemas. |
| **`agent/prompts.py`** | The agent's system prompt — when to use each tool. |
| **`agent/revision_agent.py`** | The tool-loop: send message + tools → model picks tools → execute → feed back → repeat until a final answer. Injects the active `video_id`; feeds accumulated results into the Telegram tool. |

### `frontend/` — React + TypeScript

| File | What it does |
| --- | --- |
| **`src/App.tsx`** | Layout + state; wires the SSE stream to live progress and dynamic results. |
| **`src/lib/api.ts`** | `ingest`, `uploadFile`, and the `chatStream` SSE reader (fetch + stream parser). |
| **`src/types.ts`** | Display/event types matching the backend payloads. |
| **`src/components/IngestPanel.tsx`** | Click-to-upload / drag-drop file zone + YouTube-link ingest. |
| **`src/components/ChatPanel.tsx`** | Example-prompt chips, input, and the live progress trace. |
| **`src/components/ResultsPanel.tsx`** | **Dynamic** results — renders only what the agent produced. |
| **`src/components/VideoPlayer.tsx`** | HLS playback via `hls.js` (with native-HLS fallback for Safari). |
| **`src/components/ClipCard.tsx`** | A titled, click-to-play video card. |
| **`src/components/StudyCard.tsx`** | Flashcards (flip), cue cards, summary. |
| **`src/styles.css`** | Dark theme + layout. |

### `tests/` — validation

`tests/phase0/*` are the incremental Phase-0 scripts that validated every VideoDB primitive (connect, upload, understand, index, search, ask, clip, sandbox text/image/TTS, timeline video) before the app was built. `caption_probe.py` / `caption_asset_probe.py` validated the captioning approaches.

---

## 8. API reference

Base URL (dev): `http://localhost:8000`

The API is small on purpose — the agent does the heavy lifting, so there is one endpoint to ingest a lecture, one to talk to the agent, and one to deliver to Telegram.

| Method & path | What it does | Request | Response |
| --- | --- | --- | --- |
| `GET /health` | Checks the server is up and reports the active model. | — | `{ "status": "ok", "service": "revision", "model": "gpt-4o-2024-11-20" }` |
| `POST /upload` | Indexes a lecture from a YouTube or direct video **link** (upload → transcribe → index). Returns the `video_id` used for all later requests. | `{ "url": "https://youtu.be/…" }` | `{ "video_id": "m-z-…", "title": "…", "length": 477.0 }` |
| `POST /upload/file` | Same as above but for an uploaded video **file** (`multipart/form-data`, field `file`). | a video file | `{ "video_id": "m-z-…", "title": "…", "length": 477.0 }` |
| `POST /chat` | The main endpoint. Runs the agent on your prompt and **streams live progress**, then the final result, over Server-Sent Events (SSE). | `{ "message": "summary reel on neural networks", "video_id": "m-z-…" }` | a stream of events (see below) |
| `POST /telegram` | Sends an already-produced study pack to your Telegram chat. | `{ "displays": [ … ] }` | `{ "ok": true, "message": "Sent to Telegram." }` |

**`POST /chat` stream format.** The response is a live stream. Each line is a JSON event in the `data:` field:

| Event `type` | When it fires | Contains |
| --- | --- | --- |
| `progress` | Repeatedly, as the agent works | `message` (e.g. "Reel: finding moment 2/4…") and a `kind` label |
| `result` | Once, when generation finishes | `reply` (the agent's text) and `displays` (the produced items) |
| `done` | At the very end | — (closes the stream) |
| `error` | If something fails | `message` |

The `displays` array holds the produced outputs, each tagged by `kind` — `clip`, `reel`, `learning_video`, `study_pack`, `search`, or `telegram` — carrying the relevant video URLs, flashcards, and cue cards. The frontend renders each one based on its `kind`.

---

## 9. Setup — backend

**Prerequisites:** Python 3.11+ and a VideoDB API key.

```bash
# 1. clone
git clone https://github.com/<you>/ReVision-AI.git
cd ReVision-AI

# 2. (recommended) create an environment
conda create -n revision python=3.12 -y && conda activate revision
#   or: python -m venv .venv && source .venv/bin/activate

# 3. install
pip install -r requirements.txt

# 4. configure
cp .env.example .env
#   edit .env and set VIDEO_DB_API_KEY=…   (get one at https://videodb.io)

# 5. run
uvicorn backend.main:app --port 8000
#   dev with auto-reload: uvicorn backend.main:app --reload --port 8000
```

Verify: open `http://localhost:8000/health`.

> The agent's LLM is served through VideoDB's proxy (`gpt-4o-2024-11-20`) and billed to your VideoDB credits — **no separate OpenAI key is required.**

---

## 10. Setup — frontend

**Prerequisites:** Node.js 18+.

```bash
cd frontend
npm install
npm run dev
```

Open the printed URL (default `http://localhost:5173`). The Vite dev server **proxies** `/upload`, `/chat`, `/telegram`, `/health` to the backend on `:8000`, so no CORS setup is needed. The app loads with a pre-indexed demo lecture so you can start prompting immediately.

---

## 11. Setup — Telegram (optional)

1. In Telegram, message **@BotFather** → `/newbot` → follow the prompts → copy the **bot token**.
2. Send your new bot any message, then open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` and read `chat.id` — that's your **chat ID**.
3. Add both to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF…
   TELEGRAM_CHAT_ID=123456789
   ```
4. Restart the backend.

Now the "Send to Telegram" button works, and prompts like _"…and send it to my Telegram"_ let the agent deliver automatically. Without configuration the feature fails soft (a friendly "not configured" message — never an error).

---

## 12. Example prompts

The chat routes intent to tools automatically. Some examples:

| Prompt | Produces |
| --- | --- |
| `Give me a summary reel of neural networks` | Highlights (real footage) — fast, free |
| `Where is the output layer explained?` | Timestamped moments |
| `Make an animated explainer video on how digits are recognized` | AI Explainer (images + narration + captions) |
| `Flashcards and cue cards on activations` | Cards |
| `Full study pack on neural networks with an animated video` | Everything |
| `Give me a summary reel on backprop and send it to my Telegram` | Highlights + Telegram delivery |

_You can also describe the visual style you want for the explainer video, and it will follow it — for example: "an animated 3D-cartoon video" or "a whiteboard-style explainer."_

---

## 13. Configuration reference

Key `.env` / `config.py` values:

| Variable | Default | Meaning |
| --- | --- | --- |
| `VIDEO_DB_API_KEY` | — | **Required.** VideoDB key (also powers the agent). |
| `VIDEO_DB_BASE_URL` | `https://api.videodb.io` | Proxy base for the agent LLM. |
| `AGENT_MODEL` | `gpt-4o-2024-11-20` | Agent + scripting model (via proxy). |
| `AGENT_MAX_STEPS` | `6` | Tool-loop safety cap. |
| `TEXT/TTS_SANDBOX_TIER` | `small` | Sandbox tiers for text & TTS. |
| `IMAGE_SANDBOX_TIER` | `medium` | Sandbox tier for FLUX images. |
| `TOP_K` | `5` | Search results per query. |
| `MIN_SCORE` | `0.2`–`0.6` | Retrieval score floor (transcript scores run low). |
| `MAX_CLIP_S` | `90` | Cap on a single clip's length. |
| `VIDEO_RESOLUTION` | `1280x720` | Explainer render resolution. |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | — | Optional Telegram delivery. |

---

## 14. What's next — roadmap & quality

The core is complete and working. Planned improvements, grouped by theme:

### Retrieval & clip quality
- **Custom fine-grained index.** VideoDB's default transcript segmentation is coarse, so cited moments can run long. Building a custom index from sentence-level timestamps (`video.index(source=custom_records)`) would yield surgically tight clips and reels.
- **Parallel `ask()` calls.** The summary reel currently locates its sub-point moments sequentially; running them concurrently would cut reel time roughly 4×.

### Generation quality
- **Sharper explainer images.** FLUX renders concepts well but garbles dense labels/numbers. Planned: steer prompts toward clean conceptual visuals + overlay precise facts as text, rather than asking the image model to draw them.
- **Caption polish.** Auto-captions work via the two-pass `CaptionAsset` flow; further styling (animation presets, brand colors) is a quick win.
- **Adaptive slide count.** Let the agent choose the number of slides from topic complexity instead of a fixed default.

### Product & scale
- **Collections dropdown.** Persist and switch between previously indexed lectures without re-indexing.
- **Multi-lecture packs.** `ingest_many` already supports several videos in one collection; expose cross-lecture study packs.
- **Progress in Telegram.** Stream generation progress to Telegram, not just final links.
- **Long-form testing.** Validate on full-length podcasts/lectures (indexing time, clip tightness) and tune accordingly.

### Engineering
- **Caching.** Cache `ask()`/search results per (video, topic) to make repeat prompts instant.
- **Auth & multi-user.** Per-user collections and history for a hosted deployment.

---

_Built with [VideoDB](https://videodb.io) · FastAPI · React · TypeScript._