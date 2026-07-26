# ReVision — Confirmed VideoDB signatures (verified from docs, Jul 2026)

## Agent LLM — TOOL-CALLING ONLY (VideoDB proxy = GPT-4o on your credits)
from openai import OpenAI
agent = OpenAI(api_key=VIDEO_DB_API_KEY, base_url="https://api.videodb.io")
resp = agent.chat.completions.create(
    model="gpt-4o-2024-11-20",          # confirmed from videodb_proxy.py
    messages=messages, tools=tool_schemas, tool_choice="auto",
    temperature=0.9, max_tokens=4096,
)
# NOTE: proxy is used ONLY for the agent's tool-calling. Content generation = sandbox models.

## Connect / ingest
conn  = videodb.connect(api_key=VIDEO_DB_API_KEY)
coll  = conn.get_collection()
video = coll.upload(url="https://www.youtube.com/watch?v=...")   # or file_path="..."
# each YouTube link = one upload = one Video (m-...). No playlist object — loop over links.

## Understand (hosted; spoken_words is the lecture workhorse)
u = video.understand(analyzers=[{"type":"spoken_words"}, {"type":"vlm"}, {"type":"ocr"}])
u.wait_until_complete()
analyzer = u.get_analyzer("spoken_words")   # by analyzer name
# vlm/ocr optional — add for slide-heavy lectures (captures on-screen formulas/text)

## Index
idx = video.index(
    source=analyzer,                    # analyzer obj | {understanding_id, analyzer_id} | temporal records
    name="transcript",                  # per-collection schema name
    use_for=["semantic","query"],       # semantic (alias: search) | query | aggregate
    fields={...},                       # optional; derived from data if omitted
    callback_url=None,
)
idx.wait_until_complete(timeout=1800, poll_interval=10)
# idx.is_successful / idx.status ("building"->query ok | "ready"->semantic ok | "failed") / idx.error

## SEARCH — three ways
# 1) Intelligent (best for the agent): VideoDB plans retrieval
resp = collection.search(query="gradient descent", top_k=10,
                         return_fields=["transcript","scene"])   # mode="deepsearch" optional
for shot in resp:
    shot.video_id, shot.start, shot.end, shot.generate_stream()
# resp.response_type ("shots"|"aggregate"), resp.results, resp.shots

# 2) Direct semantic (you pick the index)
res = video.semantic_search(query="gradient descent",
                            index_names=["transcript"], top_k=10,
                            score_threshold=0.7, filter=[...])
shots = res.get_shots()

# 3) Grounded answer (this is your SUMMARY generator)
ans = collection.ask(question="Summarise the gradient descent section",
                     include_sources=True)
ans.answer            # text
ans.sources           # list[Shot] with .generate_stream()

## Shot object (what every match returns)
shot.video_id, shot.video_length, shot.video_title, shot.start, shot.end,
shot.text, shot.search_score, shot.scene_index_id, shot.scene_index_name,
shot.metadata["indexes"], shot.stream_url, shot.player_url
shot.play(); shot.generate_stream()    # HLS clip for THIS moment

## CLIPS  (the clip comes straight off the result — no separate step)
clip_url = shot.generate_stream()                       # one topic
reel_url = video.generate_stream([(s,e),(s,e),...])     # multi-topic reel from timestamps
reel_url = resp.results.compile()                       # stream from all results
# HLS: https://stream.videodb.io/v3/published/manifests/{id}.m3u8

## GENERATION (rule: sandbox models for generation; proxy is tool-calling only)
# Summary  -> collection.ask(...)            (grounded, native, with source clips)
# Cards    -> sandbox text model (Gemma/Qwen) fed the transcript slice / ask answer
#   sandbox = conn.create_sandbox(tier=SandboxTier.small, model_categories=["text_generation"])
#   sandbox.wait_for_ready(); ...generate...; sandbox.stop()   # ALWAYS stop (runtime-billed)

## STRETCH — learning video (all confirmed in PDF: Timeline/Aspect/Clip/Caption/Text)
# FLUX image (sandbox, medium) + OmniVoice TTS (sandbox, small) ->
# Timeline(conn); Track; Clip; ImageAsset/AudioAsset/TextAsset/CaptionAsset ->
# timeline.generate_stream()

## Scope
# video.*  -> one video     |    collection.*  -> across all indexed videos
