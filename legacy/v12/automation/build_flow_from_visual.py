#!/usr/bin/env python3
"""Convert finalized visualization prompts into Google Flow prompt blocks.

Expected source structure::

    [장면 1]
    [한국어 번역] ...
    [영어 이미지 프롬프트] ...

`[CTA]` and `[END]` are silent separators and never become Flow entries.
The output contains exactly one English prompt per scene, separated by one
empty line.  Scene numbering and common generation-error text are validated.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


SCENE_RE = re.compile(r"^\s*\[장면\s+(\d+)\]\s*$")
EN_LABEL_RE = re.compile(
    r"^\s*\[(?:영어\s*이미지\s*프롬프트|영문\s*프롬프트|English\s+Image\s+Prompt)\]\s*(.*)$",
    re.IGNORECASE,
)
ANY_LABEL_RE = re.compile(r"^\s*\[[^\]]+\]\s*(.*)$")
SILENT_MARKERS = {"[CTA]", "[END]"}
CHECKPOINT_RE = re.compile(r"^\s*체크포인트\s*:")
GENERIC_ERROR_RE = re.compile(
    r"(?:"
    r"\bI(?:'|’)m\s+sorry\b|"
    r"\bI\s+(?:cannot|can(?:'|’)t)\s+"
    r"(?:help|assist|comply|generate|create|provide|complete)\b|"
    r"\bI(?:'|’)m\s+unable\s+to\s+"
    r"(?:help|assist|comply|generate|create|provide|complete)\b|"
    r"^\s*unable\s+to\s+(?:comply|generate|create|assist|help)\b|"
    r"\bas\s+an\s+AI\b|"
    r"죄송(?:합니다|하지만)?|생성할\s+수\s+없|도와드릴\s+수\s+없"
    r")",
    re.IGNORECASE,
)


class FlowBuildError(ValueError):
    """Raised when the visualization source violates a locked invariant."""


@dataclass(frozen=True)
class Scene:
    number: int
    prompt: str


def _clean_prompt(parts: list[str]) -> str:
    text = " ".join(part.strip() for part in parts if part.strip())
    return re.sub(r"\s+", " ", text).strip()


def parse_visualization(source: str) -> list[Scene]:
    scenes: list[Scene] = []
    current_number: int | None = None
    prompt_parts: list[str] = []
    collecting_english = False

    def flush() -> None:
        nonlocal current_number, prompt_parts, collecting_english
        if current_number is None:
            return
        prompt = _clean_prompt(prompt_parts)
        if not prompt:
            raise FlowBuildError(
                f"장면 {current_number}: 영어 이미지 프롬프트가 없습니다."
            )
        if GENERIC_ERROR_RE.search(prompt):
            raise FlowBuildError(
                f"장면 {current_number}: 범용 오류 문구가 감지되었습니다."
            )
        scenes.append(Scene(current_number, prompt))
        current_number = None
        prompt_parts = []
        collecting_english = False

    for raw_line in source.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if line in SILENT_MARKERS:
            continue

        if CHECKPOINT_RE.match(line):
            collecting_english = False
            continue

        scene_match = SCENE_RE.match(line)
        if scene_match:
            flush()
            current_number = int(scene_match.group(1))
            continue

        en_match = EN_LABEL_RE.match(line)
        if en_match:
            if current_number is None:
                raise FlowBuildError("장면 번호 없이 영어 이미지 프롬프트가 나왔습니다.")
            collecting_english = True
            inline = en_match.group(1).strip()
            if inline:
                prompt_parts.append(inline)
            continue

        if ANY_LABEL_RE.match(line):
            collecting_english = False
            continue

        if collecting_english and line:
            prompt_parts.append(line)

    flush()

    if not scenes:
        raise FlowBuildError("변환할 시각화 장면을 찾지 못했습니다.")

    numbers = [scene.number for scene in scenes]
    expected = list(range(1, len(scenes) + 1))
    if numbers != expected:
        raise FlowBuildError(
            "장면 번호가 1부터 연속되지 않습니다: "
            f"실제 {numbers[:12]}{'...' if len(numbers) > 12 else ''}"
        )

    return scenes


def build_flow_text(scenes: list[Scene]) -> str:
    return "\n\n".join(scene.prompt for scene in scenes) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="시각화 프롬프트에서 장면별 Google Flow 프롬프트를 생성합니다."
    )
    parser.add_argument("input", type=Path, help="UTF-8 시각화 프롬프트 텍스트")
    parser.add_argument("output", type=Path, help="생성할 Flow 프롬프트 텍스트")
    parser.add_argument(
        "--expected-scenes",
        type=int,
        help="예상 장면 수와 다르면 실패합니다.",
    )
    args = parser.parse_args()

    try:
        source = args.input.read_text(encoding="utf-8")
        scenes = parse_visualization(source)
        if args.expected_scenes is not None and len(scenes) != args.expected_scenes:
            raise FlowBuildError(
                f"장면 수 불일치: 예상 {args.expected_scenes}, 실제 {len(scenes)}"
            )
        output = build_flow_text(scenes)
        args.output.write_text(output, encoding="utf-8")
    except (OSError, UnicodeError, FlowBuildError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        "OK: "
        f"Flow {len(scenes)}개 / 장면 사이 빈 줄 {max(0, len(scenes) - 1)}곳 / "
        "CTA·END 제거 / 범용 오류 문구 0개",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
