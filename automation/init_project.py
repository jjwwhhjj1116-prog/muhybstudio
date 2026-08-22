#!/usr/bin/env python3
"""Create a project directory from the checked-in templates."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("slug")
    parser.add_argument("--title", required=True)
    parser.add_argument("--document-id", required=True)
    args = parser.parse_args()

    target = ROOT / "projects" / args.slug
    if target.exists():
        raise SystemExit(f"project already exists: {target}")

    for rel in [
        "canon", "synopsis", "script/chunks", "script/state",
        "characters/main/images", "visualization/chunks", "visualization/state",
        "flow", "video", "metadata", "reports", "exports",
    ]:
        (target / rel).mkdir(parents=True, exist_ok=True)

    manifest = json.loads((ROOT / "templates/project_manifest.template.json").read_text(encoding="utf-8"))
    manifest["project_id"] = args.slug
    manifest["title"] = args.title
    manifest["google_docs"]["document_id"] = args.document_id
    manifest["google_docs"]["url"] = f"https://docs.google.com/document/d/{args.document_id}/edit"
    (target / "project_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    status = json.loads((ROOT / "templates/stage_status.template.json").read_text(encoding="utf-8"))
    status["project_id"] = args.slug
    (target / "stage_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    shutil.copy2(ROOT / "templates/script_chunk_state.template.json", target / "script/state/chunk_01.state.json")
    shutil.copy2(ROOT / "templates/visual_chunk_state.template.json", target / "visualization/state/visual_chunk_01.state.json")
    (target / "PROJECT_CONTEXT.md").write_text("# 작품 컨텍스트\n\n`stages/01_SYNOPSIS_CONTEXT.md`의 14개 목차를 채운다.\n", encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
