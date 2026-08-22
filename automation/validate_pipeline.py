#!/usr/bin/env python3
"""Validate wuxia production outputs with deterministic checks.

This validator does not create story content. It checks scene structure, counts,
silent markers, Flow/video alignment, video audio bans, and metadata packaging.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


SCENE_RE = re.compile(r"^\s*\[장면\s+(\d+)\]\s*$")
KO_RE = re.compile(r"^\s*\[한국어 번역\]\s*(.*)$")
EN_RE = re.compile(r"^\s*\[영어 이미지 프롬프트\]\s*(.*)$")
LABEL_RE = re.compile(r"^\s*\[[^\]]+\]")
DIALOGUE_RE = re.compile(r"\[[^|\]]+\|[^\]]+\]\"[^\"]+\"")
SILENT_MARKERS = {"[CTA]", "[END]"}
STYLE_PREFIX = "Korean dark-fantasy martial-arts action manhwa webtoon style"
GENERIC_ERROR_RE = re.compile(
    r"(?:I'm sorry|I cannot|I can't|unable to|as an AI|죄송(?:합니다|하지만)?|생성할 수 없|도와드릴 수 없)",
    re.IGNORECASE,
)
AUDIO_RE = re.compile(
    r"\b(?:audio|voice|spoken|speaks?|says?|shouts?|dialogue|lip[- ]?sync|tts|sfx|bgm|soundtrack|music|sound effect)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Issue:
    level: str
    code: str
    message: str
    entity: str = ""


@dataclass(frozen=True)
class Scene:
    number: int
    ko: str
    en: str


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def normalize(parts: Iterable[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(part.strip() for part in parts if part.strip())).strip()


def parse_visual(text: str) -> tuple[list[Scene], list[Issue], dict[str, int]]:
    scenes: list[Scene] = []
    issues: list[Issue] = []
    markers = {"[CTA]": 0, "[END]": 0}
    current: int | None = None
    ko_parts: list[str] = []
    en_parts: list[str] = []
    mode: str | None = None

    def flush() -> None:
        nonlocal current, ko_parts, en_parts, mode
        if current is None:
            return
        ko, en = normalize(ko_parts), normalize(en_parts)
        if not ko:
            issues.append(Issue("ERROR", "visual_missing_ko", "한국어 번역이 없습니다.", f"scene:{current}"))
        if not en:
            issues.append(Issue("ERROR", "visual_missing_en", "영어 이미지 프롬프트가 없습니다.", f"scene:{current}"))
        if en and not en.startswith(STYLE_PREFIX):
            issues.append(Issue("ERROR", "visual_style_prefix", "고정 화풍 문구로 시작하지 않습니다.", f"scene:{current}"))
        if GENERIC_ERROR_RE.search(ko + " " + en):
            issues.append(Issue("ERROR", "generic_error_text", "범용 오류·거절 문구가 있습니다.", f"scene:{current}"))
        scenes.append(Scene(current, ko, en))
        current, ko_parts, en_parts, mode = None, [], [], None

    for raw in text.splitlines():
        line = raw.strip()
        if line in SILENT_MARKERS:
            flush()
            markers[line] += 1
            mode = None
            continue
        scene_match = SCENE_RE.match(line)
        if scene_match:
            flush()
            current = int(scene_match.group(1))
            continue
        ko_match = KO_RE.match(line)
        if ko_match:
            if current is None:
                issues.append(Issue("ERROR", "visual_ko_without_scene", "장면 번호 없이 한국어 번역이 있습니다."))
            mode = "ko"
            if ko_match.group(1).strip():
                ko_parts.append(ko_match.group(1))
            continue
        en_match = EN_RE.match(line)
        if en_match:
            if current is None:
                issues.append(Issue("ERROR", "visual_en_without_scene", "장면 번호 없이 영어 프롬프트가 있습니다."))
            mode = "en"
            if en_match.group(1).strip():
                en_parts.append(en_match.group(1))
            continue
        if line and LABEL_RE.match(line):
            issues.append(Issue("ERROR", "visual_unknown_label", f"허용되지 않은 라벨: {line[:80]}"))
            mode = None
            continue
        if line and mode == "ko":
            ko_parts.append(line)
        elif line and mode == "en":
            en_parts.append(line)
    flush()

    numbers = [scene.number for scene in scenes]
    expected = list(range(1, len(scenes) + 1))
    if numbers != expected:
        issues.append(Issue("ERROR", "visual_scene_numbers", "장면 번호가 1부터 연속되지 않습니다."))
    if markers["[CTA]"] > 1 or markers["[END]"] > 1:
        issues.append(Issue("ERROR", "visual_marker_count", "CTA 또는 END가 두 개 이상입니다."))
    return scenes, issues, markers


def prompt_blocks(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", block).strip() for block in re.split(r"\n\s*\n", text.strip()) if block.strip()]


def validate_flow(text: str, scenes: list[Scene]) -> tuple[list[str], list[Issue]]:
    blocks = prompt_blocks(text)
    issues: list[Issue] = []
    if len(blocks) != len(scenes):
        issues.append(Issue("ERROR", "flow_count", f"Flow {len(blocks)}개, 시각화 {len(scenes)}개로 수가 다릅니다."))
    for index, block in enumerate(blocks, 1):
        if any(marker in block for marker in SILENT_MARKERS) or LABEL_RE.match(block):
            issues.append(Issue("ERROR", "flow_label", "Flow에 라벨 또는 CTA·END가 남았습니다.", f"flow:{index}"))
        if GENERIC_ERROR_RE.search(block):
            issues.append(Issue("ERROR", "flow_generic_error", "범용 오류·거절 문구가 있습니다.", f"flow:{index}"))
    return blocks, issues


def validate_video(text: str, scenes: list[Scene], minimum_words: int, maximum_words: int) -> tuple[list[str], list[Issue]]:
    blocks = prompt_blocks(text)
    issues: list[Issue] = []
    if len(blocks) != len(scenes):
        issues.append(Issue("ERROR", "video_count", f"영상 프롬프트 {len(blocks)}개, 시각화 {len(scenes)}개로 수가 다릅니다."))
    for index, block in enumerate(blocks, 1):
        words = len(block.split())
        if not minimum_words <= words <= maximum_words:
            issues.append(Issue("WARNING", "video_word_count", f"{words}단어입니다. 허용 범위는 {minimum_words}~{maximum_words}입니다.", f"video:{index}"))
        if AUDIO_RE.search(block):
            issues.append(Issue("ERROR", "video_audio", "오디오·대사·TTS·립싱크 관련 표현이 있습니다.", f"video:{index}"))
        if any(marker in block for marker in SILENT_MARKERS) or LABEL_RE.match(block):
            issues.append(Issue("ERROR", "video_label", "영상 프롬프트에 라벨 또는 CTA·END가 있습니다.", f"video:{index}"))
        if GENERIC_ERROR_RE.search(block):
            issues.append(Issue("ERROR", "video_generic_error", "범용 오류·거절 문구가 있습니다.", f"video:{index}"))
    return blocks, issues


def validate_metadata(data: dict) -> list[Issue]:
    issues: list[Issue] = []
    titles = data.get("titles")
    expected_types = ["의문형", "직설형", "숫자·역전형"]
    if not isinstance(titles, list) or len(titles) != 3:
        issues.append(Issue("ERROR", "metadata_titles", "제목은 정확히 3안이어야 합니다."))
    else:
        types = [item.get("type") if isinstance(item, dict) else None for item in titles]
        if types != expected_types:
            issues.append(Issue("ERROR", "metadata_title_types", "제목 유형 순서는 의문형, 직설형, 숫자·역전형이어야 합니다."))
        texts = [str(item.get("text", "")) if isinstance(item, dict) else "" for item in titles]
        if texts and "?" not in texts[0]:
            issues.append(Issue("ERROR", "metadata_question_title", "의문형 제목에 ?가 없습니다."))
        if len(texts) >= 3 and not re.search(r"\d", texts[2]):
            issues.append(Issue("ERROR", "metadata_number_title", "숫자·역전형 제목에 실제 숫자가 없습니다."))
        if len(set(texts)) != len(texts):
            issues.append(Issue("ERROR", "metadata_duplicate_titles", "제목 3안이 서로 다르지 않습니다."))
        for index, title in enumerate(texts, 1):
            if not 15 <= len(title) <= 100:
                issues.append(Issue("WARNING", "metadata_title_length", f"제목 길이가 {len(title)}자입니다.", f"title:{index}"))
    sections = data.get("descriptionSections")
    if not isinstance(sections, list) or len(sections) != 12:
        issues.append(Issue("ERROR", "metadata_sections", "설명란 섹션은 정확히 12개여야 합니다."))
    timeline = data.get("timeline")
    if not isinstance(timeline, list) or not 5 <= len(timeline) <= 8:
        issues.append(Issue("ERROR", "metadata_timeline", "타임라인은 5~8개여야 합니다."))
    hashtags = data.get("hashtags")
    if not isinstance(hashtags, list) or len(hashtags) != 12 or len(set(hashtags)) != 12:
        issues.append(Issue("ERROR", "metadata_hashtags", "중복 없는 해시태그가 정확히 12개여야 합니다."))
    elif any(not isinstance(tag, str) or not tag.startswith("#") for tag in hashtags):
        issues.append(Issue("ERROR", "metadata_hashtag_format", "모든 해시태그는 #으로 시작해야 합니다."))
    if data.get("signature") != "🗡️ 무협스튜디오 — 강호는 멈추지 않는다.":
        issues.append(Issue("ERROR", "metadata_signature", "고정 서명이 없거나 다릅니다."))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="무협 제작 파이프라인 산출물을 검수합니다.")
    parser.add_argument("--visual", type=Path)
    parser.add_argument("--flow", type=Path)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--expected-scenes", type=int)
    parser.add_argument("--video-min-words", type=int, default=40)
    parser.add_argument("--video-max-words", type=int, default=120)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    issues: list[Issue] = []
    scenes: list[Scene] = []
    markers = {"[CTA]": 0, "[END]": 0}
    flow_blocks: list[str] = []
    video_blocks: list[str] = []

    if args.visual:
        scenes, found, markers = parse_visual(read(args.visual))
        issues.extend(found)
        if args.expected_scenes is not None and len(scenes) != args.expected_scenes:
            issues.append(Issue("ERROR", "expected_scene_count", f"예상 {args.expected_scenes}, 실제 {len(scenes)} 장면입니다."))
    if args.flow:
        if not scenes:
            issues.append(Issue("ERROR", "flow_needs_visual", "Flow 검수에는 --visual이 필요합니다."))
        else:
            flow_blocks, found = validate_flow(read(args.flow), scenes)
            issues.extend(found)
    if args.video:
        if not scenes:
            issues.append(Issue("ERROR", "video_needs_visual", "영상 검수에는 --visual이 필요합니다."))
        else:
            video_blocks, found = validate_video(read(args.video), scenes, args.video_min_words, args.video_max_words)
            issues.extend(found)
    if args.metadata:
        issues.extend(validate_metadata(json.loads(read(args.metadata))))

    errors = [issue for issue in issues if issue.level == "ERROR"]
    warnings = [issue for issue in issues if issue.level == "WARNING"]
    summary = {
        "ok": not errors,
        "counts": {
            "visualScenes": len(scenes),
            "flowPrompts": len(flow_blocks),
            "videoPrompts": len(video_blocks),
            "cta": markers["[CTA]"],
            "end": markers["[END]"],
            "errors": len(errors),
            "warnings": len(warnings)
        },
        "issues": [asdict(issue) for issue in issues]
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        for issue in issues:
            suffix = f" ({issue.entity})" if issue.entity else ""
            print(f"[{issue.level}] {issue.code}: {issue.message}{suffix}")
        print(json.dumps(summary["counts"], ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
