#!/usr/bin/env python3
"""Create a deterministic manifest and ZIP release for this dashboard bundle."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT.parent / f"{ROOT.name}.zip"
SKIP = {"manifest.json"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def files() -> list[Path]:
    return sorted(
        path for path in ROOT.rglob("*")
        if path.is_file()
        and path.relative_to(ROOT).as_posix() not in SKIP
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    )


def main() -> None:
    entries = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path)
        }
        for path in files()
    ]
    manifest = {
        "package": "manus-wuxia-production-system",
        "version": "1.0.0",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "encoding": "UTF-8",
        "entrypoint": "README_FIRST.md",
        "manusPrompt": "manus/DASHBOARD_BUILD_PROMPT.md",
        "files": entries
    }
    (ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    release_files = files() + [ROOT / "manifest.json"]
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(release_files):
            archive.write(path, arcname=f"{ROOT.name}/{path.relative_to(ROOT).as_posix()}")
    print(OUTPUT)


if __name__ == "__main__":
    main()
