# 09. 산출물 지도

```text
projects/<slug>/
  project_manifest.json
  PROJECT_CONTEXT.md
  stage_status.json
  canon/canon_registry.json
  synopsis/synopsis.md
  script/chunks/chunk_01.md ... chunk_21.md
  script/state/chunk_01.state.json ... chunk_21.state.json
  script/script_full.md
  characters/main/character_<한글명>.json
  characters/main/images/
  characters/support_anchors.json
  visualization/source_sentences.jsonl
  visualization/chunks/visual_chunk_01.txt ... visual_chunk_21.txt
  visualization/state/visual_chunk_01.state.json ...
  visualization/visualization_full.txt
  flow/flow_full.txt
  video/video_prompts_full.txt
  metadata/youtube_metadata.json
  reports/*.json
  exports/release.zip
```

## 불변 연결 키

- 대본 문장: `S000001` 형식의 안정적 ID
- 장면: 전편 연속 정수 `scene_number`
- 주요 인물: `fixed_ko_name`
- 보조 인물: `support_anchor_id`
- 청크: 대본 `script_chunk`, 시각화 `visual_chunk`

모든 시각화 장면은 `script_sentence_ids`를 보유한다. 모든 Flow·영상 프롬프트는 `scene_number`와 원본 장면 해시를 보유한다.
