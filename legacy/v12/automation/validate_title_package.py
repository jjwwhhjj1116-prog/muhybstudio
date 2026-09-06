#!/usr/bin/env python3
"""Validate a Korean wuxia YouTube title/description package."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REQUIRED_TYPES = ["의문형", "직설형", "숫자·역전형"]
CATEGORY_TERMS = ("무협", "애니", "다크 판타지", "웹툰")
BRIDGE_TERMS = (
    "무협",
    "애니",
    "다크 판타지",
    "복수",
    "검객",
    "후계자",
    "가문",
    "스승",
    "검진",
)
INTERNAL_MARKERS = ("[URL]", "잠정", "게시 전", "내부 검수", "placeholder")


def load_package(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("package root must be an object")
    return value


def validate(package: dict) -> list[str]:
    errors: list[str] = []
    titles = package.get("titles")
    if not isinstance(titles, list) or len(titles) != 3:
        return ["titles must contain exactly three entries"]

    actual_types = [item.get("type") for item in titles if isinstance(item, dict)]
    if actual_types != REQUIRED_TYPES:
        errors.append(f"title types must be in this order: {', '.join(REQUIRED_TYPES)}")

    title_texts: list[str] = []
    for index, item in enumerate(titles, start=1):
        if not isinstance(item, dict):
            errors.append(f"title {index} must be an object")
            continue
        title = str(item.get("text", "")).strip()
        title_texts.append(title)
        if not 15 <= len(title) <= 100:
            errors.append(f"title {index} length must be 15-100 characters (got {len(title)})")
        if not any(term in title for term in CATEGORY_TERMS):
            errors.append(f"title {index} needs one truthful category bridge")
        if "\n" in title or re.search(r"[!?]{2,}", title):
            errors.append(f"title {index} contains noisy punctuation or a newline")

    if len(set(title_texts)) != len(title_texts):
        errors.append("all three titles must be unique")
    if title_texts and "?" not in title_texts[0]:
        errors.append("the 의문형 title must contain ?")
    if len(title_texts) >= 3 and not re.search(r"\d", title_texts[2]):
        errors.append("the 숫자·역전형 title must contain a real number")

    description = str(package.get("description", "")).strip()
    first_lines = [line.strip() for line in description.splitlines() if line.strip()][:2]
    opening = " ".join(first_lines)
    bridge_count = sum(term in opening for term in BRIDGE_TERMS)
    if len(first_lines) < 2:
        errors.append("description needs two non-empty opening lines")
    if bridge_count < 3:
        errors.append("the first two description lines need at least three natural bridge terms")
    for marker in INTERNAL_MARKERS:
        if marker.lower() in description.lower():
            errors.append(f"description contains an internal or placeholder marker: {marker}")

    hashtags = package.get("hashtags")
    if not isinstance(hashtags, list) or not 5 <= len(hashtags) <= 8:
        errors.append("hashtags must contain 5-8 entries")
    elif len(set(hashtags)) != len(hashtags):
        errors.append("hashtags must be unique")
    elif any(not isinstance(tag, str) or not tag.startswith("#") for tag in hashtags):
        errors.append("every hashtag must be a string beginning with #")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_package.py PACKAGE.json", file=sys.stderr)
        return 2
    try:
        package = load_package(Path(sys.argv[1]))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    errors = validate(package)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: package passed title, description, and hashtag checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
