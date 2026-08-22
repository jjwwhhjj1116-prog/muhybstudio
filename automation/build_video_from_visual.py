#!/usr/bin/env python3
"""Build concise, silent motion prompts from finalized visualization prompts."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from build_flow_from_visual import parse_visualization


SCENE_RE = re.compile(r"^\s*\[장면\s+(\d+)\]\s*$")
KO_RE = re.compile(r"^\s*\[한국어 번역\]\s*(.*)$")
DIALOGUE_RE = re.compile(r'^\[([^|\]]+)\|[^\]]+\]')
PREFIX = (
    "Korean dark-fantasy martial-arts action manhwa webtoon style, "
    "hand-drawn illustration, ink line art with digital coloring, NOT photorealistic, "
    "NOT 3D render, NOT photograph, Masterpiece, ultra-detailed, premium anime key-visual "
    "quality, cel-shaded digital painting with ink brush texture, rich ink-wash rendering "
    "with dramatic lighting, floating particles and embers, flowing hair and fabric with "
    "natural physics,"
)
ACTION_WORDS = re.compile(
    r"\b(?:walks?|runs?|rides?|turns?|raises?|lowers?|holds?|reaches?|draws?|cuts?|"
    r"strikes?|steps?|moves?|approaches?|falls?|kneels?|stands?|sits?|opens?|closes?|"
    r"breaks?|shatters?|collapses?|erupts?|glows?|spreads?|flows?|races?|pushes?|pulls?|"
    r"twists?|slides?|plants?|places?|points?|looks?|watches?|examines?|writes?|carries?|"
    r"guards?|blocks?|redirects?|advances?|withdraws?|climbs?|enters?|leaves?|bows?|"
    r"clasps?|grips?|stops?|swings?|trembles?|drifts?|flares?|bends?|rises?|descends?)\b",
    re.IGNORECASE,
)
DISALLOWED = re.compile(
    r"\b(?:camera|audio|sounds?|voice|speaks?|shouts?|says?|dialogue|lip[- ]?sync|tts|bgm|"
    r"subtitle|speech bubble|composition|shot|frame|framing|format|portrait|close-up|wide view)\b",
    re.IGNORECASE,
)


def korean_lines(source: str) -> dict[int, str]:
    result: dict[int, str] = {}
    current: int | None = None
    for raw in source.splitlines():
        line = raw.strip()
        m = SCENE_RE.match(line)
        if m:
            current = int(m.group(1))
            continue
        k = KO_RE.match(line)
        if k and current is not None:
            result[current] = k.group(1).strip()
    return result


def concise_action(prompt: str) -> str:
    text = prompt
    if text.startswith(PREFIX):
        text = text[len(PREFIX):].lstrip(" ,")
    text = re.split(r",\s*1365x768\b", text, maxsplit=1)[0]
    clauses = [re.sub(r"\s+", " ", c).strip(" .;:") for c in text.split(",")]
    candidates = [
        c for c in clauses
        if c and ACTION_WORDS.search(c) and not DISALLOWED.search(c) and len(c.split()) <= 26
    ]
    action = candidates[-1] if candidates else "hair and clothing drift gently while the depicted pose remains stable"
    action = re.sub(r"\b(?:dramatic|cinematic|dynamic|intense|solemn|symbolic)\b", "", action, flags=re.I)
    action = re.sub(r"\s+", " ", action).strip(" .;:")
    if len(action.split()) > 16:
        action = " ".join(action.split()[:16])
    return action


def build_video(source: str) -> str:
    scenes = parse_visualization(source)
    ko = korean_lines(source)
    outputs: list[str] = []
    for scene in scenes:
        dialogue = DIALOGUE_RE.match(ko.get(scene.number, ""))
        if dialogue:
            actor = dialogue.group(1)
            line = f"Subtle natural movement only: {actor} makes one small head or hand gesture, with gentle hair and clothing motion."
        else:
            action = concise_action(scene.prompt)
            line = f"Subtle natural movement only: {action}."
        if DISALLOWED.search(line):
            raise ValueError(f"장면 {scene.number}: 금지된 오디오·카메라 표현 감지")
        outputs.append(line)
    return "\n\n".join(outputs) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-scenes", type=int)
    args = parser.parse_args()
    source = args.input.read_text(encoding="utf-8")
    output = build_video(source)
    count = len(output.strip().split("\n\n"))
    if args.expected_scenes is not None and count != args.expected_scenes:
        raise SystemExit(f"ERROR: 장면 수 불일치: 예상 {args.expected_scenes}, 실제 {count}")
    args.output.write_text(output, encoding="utf-8")
    print(f"OK: 영상 프롬프트 {count}개 / 장면 사이 빈 줄 {max(0, count-1)}곳 / 오디오·카메라·TTS 표현 0개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
