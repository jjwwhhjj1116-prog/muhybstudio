#!/usr/bin/env python3
"""Build concise, silent image-to-video prompts from finalized visuals.

The source image already owns character design, staging, lighting, and story
facts. This converter adds one restrained camera move, one central physical
action, one environmental response, and one stable end state without adding
audio or new story information.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from build_flow_from_visual import FlowBuildError, Scene, parse_visualization


SCENE_RE = re.compile(r"^\s*\[장면\s+(\d+)\]\s*$")
KO_RE = re.compile(r"^\s*\[한국어 번역\]\s*(.*)$")
DIALOGUE_RE = re.compile(r"\[([^|\]]+)\|[^\]]+\]")
WORD_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)
AUDIO_RE = re.compile(
    r"\b(?:audio|sounds?|voices?|speaks?|shouts?|says?|dialogue|lip[- ]?sync|"
    r"tts|bgm|sfx|music|musical|soundtrack|narration|subtitle|speech bubble)\b",
    re.IGNORECASE,
)
ACTION_RE = re.compile(
    r"\b(?:walks?|runs?|rides?|turns?|raises?|lowers?|holds?|reaches?|draws?|"
    r"cuts?|strikes?|steps?|moves?|approaches?|falls?|kneels?|stands?|sits?|"
    r"opens?|closes?|breaks?|shatters?|collapses?|erupts?|glows?|spreads?|"
    r"flows?|races?|pushes?|pulls?|twists?|slides?|plants?|places?|points?|"
    r"looks?|watches?|examines?|writes?|carries?|guards?|blocks?|redirects?|"
    r"advances?|withdraws?|climbs?|enters?|leaves?|bows?|clasps?|grips?|"
    r"stops?|swings?|trembles?|drifts?|flares?|bends?|rises?|descends?|"
    r"clings?|tends?|converges?|settles?|steadies?|presses?|leans?|returns?|"
    r"gathers?|circles?|releases?|ages?|whitens?|wrinkles?|flickers?)\b",
    re.IGNORECASE,
)
SKIP_CLAUSE_RE = re.compile(
    r"(?:continuity-locked|ink-black|no readable text|not photorealistic|"
    r"physically age\s+\d+|wearing\b|no sword\b|no heroic armor\b)",
    re.IGNORECASE,
)


class VideoBuildError(ValueError):
    """Raised when a generated video prompt violates a locked invariant."""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def korean_lines(source: str) -> dict[int, str]:
    result: dict[int, str] = {}
    current: int | None = None
    for raw in source.splitlines():
        line = raw.strip()
        match = SCENE_RE.match(line)
        if match:
            current = int(match.group(1))
            continue
        translation = KO_RE.match(line)
        if translation and current is not None:
            result[current] = translation.group(1).strip()
    return result


def camera_instruction(image_prompt: str) -> str:
    lowered = image_prompt.lower()
    if "close-up" in lowered:
        return "Use a very slow push-in toward the main depicted subject."
    if "low-angle" in lowered or "action axis" in lowered:
        return "Use controlled forward tracking along the established action axis."
    if "wide" in lowered or "establishing" in lowered:
        return "Use a slight lateral pan across the established scene."
    return "Use a slow push-in toward the established focal point."


def _clean_clause(clause: str) -> str:
    text = re.sub(r"\s+", " ", clause).strip(" ,.;:")
    text = re.sub(
        r"\b(?:dramatic|cinematic|dynamic|intense|solemn|symbolic)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+", " ", text).strip(" ,.;:")
    words = text.split()
    if len(words) > 28:
        text = " ".join(words[:28]).rstrip(" ,.;:")
    return text


def central_action(image_prompt: str) -> str:
    clauses = [_clean_clause(part) for part in image_prompt.split(";")]
    candidates: list[tuple[int, int, str]] = []
    for index, clause in enumerate(clauses):
        if not clause or SKIP_CLAUSE_RE.search(clause) or AUDIO_RE.search(clause):
            continue
        action_count = len(ACTION_RE.findall(clause))
        if action_count:
            candidates.append((action_count, index, clause))

    if candidates:
        _, _, chosen = max(candidates, key=lambda item: (item[0], item[1]))
        return f"Animate only the established central action: {chosen}."

    return (
        "The main depicted figure makes one restrained shift of weight and "
        "steadies the established prop without changing position."
    )


def environment_reaction(image_prompt: str) -> str:
    lowered = image_prompt.lower()
    if any(word in lowered for word in ("river", "water", "current", "reeds", "boat")):
        return "Nearby water, reeds, and loose fabric respond with restrained natural motion."
    if any(word in lowered for word in ("fire", "smoke", "ember", "ash")):
        return "A little smoke, ash, and loose fabric drift around the fixed action."
    if any(word in lowered for word in ("rain", "storm", "wet")):
        return "Rain and wet fabric move lightly while the established footing remains stable."
    if any(word in lowered for word in ("lantern", "flame", "torch")):
        return "Lantern light flickers softly and nearby cloth moves once, then becomes still."
    if any(word in lowered for word in ("star", "celestial", "glow", "particles")):
        return "Cold particles and faint celestial light drift slowly around the fixed subject."
    return "Loose hair and fabric move gently around the otherwise stable composition."


def build_prompt(scene: Scene, korean: str) -> str:
    dialogue = DIALOGUE_RE.search(korean)
    if dialogue:
        actor = dialogue.group(1).strip()
        action = (
            f"{actor} makes one restrained head or hand gesture while holding the "
            "established expression, stance, age, injury state, and prop position."
        )
    else:
        action = central_action(scene.prompt)

    prompt = " ".join(
        [
            camera_instruction(scene.prompt),
            action,
            environment_reaction(scene.prompt),
            (
                "The movement settles on the same composition, with every person, "
                "injury, weapon, ownership detail, wetness state, and prop position preserved."
            ),
            "Keep the motion restrained in the existing Korean dark-fantasy wuxia manhwa look.",
        ]
    )
    prompt = re.sub(r"\s+", " ", prompt).strip()
    validate_prompt(scene.number, prompt)
    return prompt


def validate_prompt(scene_number: int, prompt: str) -> None:
    if AUDIO_RE.search(prompt):
        raise VideoBuildError(f"장면 {scene_number}: 금지된 오디오 표현 감지")
    count = len(WORD_RE.findall(prompt))
    if not 40 <= count <= 120:
        raise VideoBuildError(
            f"장면 {scene_number}: 단어 수 {count}, 허용 범위 40~120"
        )
    if prompt.count("Use ") != 1:
        raise VideoBuildError(f"장면 {scene_number}: 카메라 지시는 정확히 1개여야 함")


def build_video(source: str) -> tuple[list[Scene], list[str]]:
    scenes = parse_visualization(source)
    korean = korean_lines(source)
    outputs = [build_prompt(scene, korean.get(scene.number, "")) for scene in scenes]
    return scenes, outputs


def manifest_data(source: str, scenes: list[Scene], outputs: list[str]) -> dict[str, object]:
    output_text = "\n\n".join(outputs) + "\n"
    return {
        "source_visualization_sha256": _sha256(source),
        "scene_count": len(scenes),
        "video_prompt_count": len(outputs),
        "blank_line_count": max(0, len(outputs) - 1),
        "output_sha256": _sha256(output_text),
        "items": [
            {
                "scene_number": scene.number,
                "source_scene_hash": _sha256(scene.prompt),
                "video_prompt_hash": _sha256(prompt),
            }
            for scene, prompt in zip(scenes, outputs, strict=True)
        ],
        "errors": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="확정 시각화에서 장면별 무음 영상 프롬프트를 생성합니다."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-scenes", type=int)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()

    try:
        source = args.input.read_text(encoding="utf-8")
        scenes, outputs = build_video(source)
        if args.expected_scenes is not None and len(outputs) != args.expected_scenes:
            raise VideoBuildError(
                f"장면 수 불일치: 예상 {args.expected_scenes}, 실제 {len(outputs)}"
            )
        output_text = "\n\n".join(outputs) + "\n"
        args.output.write_text(output_text, encoding="utf-8")
        if args.manifest:
            args.manifest.write_text(
                json.dumps(manifest_data(source, scenes, outputs), ensure_ascii=False, indent=2)
                + "\n",
                encoding="utf-8",
            )
    except (OSError, UnicodeError, FlowBuildError, VideoBuildError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        "OK: "
        f"영상 프롬프트 {len(outputs)}개 / 빈 줄 {max(0, len(outputs) - 1)}곳 / "
        "40~120단어 위반 0개 / 오디오 표현 0개",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
