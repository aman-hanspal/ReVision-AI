# Tests

## Phase 0 — run FIRST at kickoff, real keys, BEFORE app code. All must PASS.
Core (upload-only ed-tech):
01_connect -> 02_upload_file -> 03_upload_youtube -> 04_understand -> 05_index
  -> 06_semantic_search -> 07_search -> 08_ask -> 09_clip -> 10_cards_sandbox -> 11_proxy_toolcall

Highest-risk (do these carefully): 06 (search lands on the right moment),
05 (index reaches ready), 10 (sandbox card quality), 11 (proxy tool-calling).

## Stretch — only after core passes and Phase 1-4 are solid
tests/stretch: 12_sandbox_image -> 13_sandbox_tts -> 14_timeline_video

Ground truth for 06 lives in data/demo_annotations.csv (record a lecture, log topic timestamps).
