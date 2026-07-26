# ReVision architecture

VideoDB-native agent (Path B). Upload-only (files + YouTube links). Director not forked.

## Flow
ingest (upload/links) -> understand([spoken_words(,vlm,ocr)]) -> index(use_for=[semantic,query])
-> agent(tool-calling via VideoDB proxy gpt-4o) chooses tools:
   search_lecture (collection.search / semantic_search) -> Shots
   make_clip      (shot.generate_stream / video.generate_stream)
   make_summary   (collection.ask, grounded + source clips)
   make_flashcards(sandbox text model: Gemma/Qwen)
   make_learning_video (STRETCH: FLUX + OmniVoice + Timeline)
-> StudyPack -> app (SSE progress) + optional Telegram.

## Split of responsibilities
- VideoDB: all media + retrieval + summary(ask) + generation(sandbox) + video(Timeline).
- Proxy (gpt-4o on credits): ONLY the agent's tool-selection reasoning.
- External keys: none required beyond VIDEO_DB_API_KEY for the core.

## shared/
config, models, videodb_service (adapter + proxy client), retrieval, generate, clip, sandbox, telegram_service.
## backend/
main; agent/ (revision_agent loop, tools, prompts); routes/ (upload, studypack, chat, progress-SSE).
## frontend/
IngestPanel (upload + links), ChatPanel, StudyCard (clip+summary+cards), AgentActivity.
