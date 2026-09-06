#!/usr/bin/env python3
"""Initialize a private local V13 project without story facts or remote creation."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def save(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def create_project(project_root: Path, slug: str, title: str) -> Path:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", slug):
        raise ValueError("slug must contain only letters, digits, underscore or hyphen")
    if not title.strip():
        raise ValueError("title is required")
    parent = project_root.resolve()
    target = (parent / slug).resolve()
    if target.parent != parent or target == ROOT or ROOT in target.parents:
        raise ValueError("private project must be outside the public workflow checkout")
    if target.exists():
        raise ValueError("project already exists; nothing overwritten")
    manifest = json.loads((ROOT / "templates/project_manifest.template.json").read_text(encoding="utf-8"))
    status = json.loads((ROOT / "templates/stage_status.template.json").read_text(encoding="utf-8"))
    checkpoint = json.loads((ROOT / "templates/memory_checkpoint.template.json").read_text(encoding="utf-8"))
    revision = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True)
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True)
    # A dirty checkout has no commit that reproduces all templates.
    manifest.update(project_id=slug, title=title.strip(),
                    workflow_git_sha=revision.stdout.strip() if revision.returncode == 0 and dirty.returncode == 0 and not dirty.stdout.strip() else None)
    status["project_id"] = checkpoint["project_id"] = slug
    target.mkdir(parents=True, exist_ok=False)
    for folder in ["canon", "synopsis", "script/chunks", "script/state", "memory", "characters",
                   "shots", "keyframes", "jobs", "voice", "edit", "metadata", "reports", "exports"]:
        (target / folder).mkdir(parents=True, exist_ok=True)
    save(target / "project_manifest.json", manifest)
    save(target / "stage_status.json", status)
    save(target / "memory/checkpoint.json", checkpoint)
    for name in ["canon", "state", "knowledge", "relationships", "threads", "issues"]:
        save(target / f"memory/{name}.json", {"schema_version": "3.0", "project_id": slug, "items": []})
    (target / "memory/events.jsonl").write_text("", encoding="utf-8")
    (target / "PROJECT_CONTEXT.md").write_text("# 작품 정본\n\n아직 작품 사실을 등록하지 않았다. 원문 근거와 확정 여부를 확인해 기록한다.\n", encoding="utf-8")
    (target / "README.md").write_text("# 비공개 로컬 프로젝트\n\n공개 워크플로우 저장소에 넣지 않는다. 원격과 미디어 동기화는 아직 설정하지 않았다.\n", encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("--title", required=True)
    parser.add_argument("--project-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(create_project(args.project_root, args.slug, args.title))
        return 0
    except (ValueError, OSError) as exc:
        print(f"Initialization failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
