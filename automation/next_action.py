#!/usr/bin/env python3
"""Report the next executable stage or chunk from stage_status.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ORDER = [
    "00_PROJECT_INIT", "01_SYNOPSIS_CONTEXT", "02_SCRIPT", "03_SCRIPT_AUDIT",
    "04_CHARACTER_CLASSIFICATION", "05_CHARACTER_SHEETS", "06_CHARACTER_IMAGES",
    "07_VISUAL_PREPROCESS", "08_VISUALIZATION", "09_VISUAL_AUDIT", "10_FLOW",
    "11_VIDEO", "12_METADATA", "13_RELEASE",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage_status")
    args = parser.parse_args()
    data = json.loads(Path(args.stage_status).read_text(encoding="utf-8"))
    stages = data["stages"]

    for stage in ORDER:
        state = stages[stage]
        status = state["status"]
        if status != "APPROVED":
            if stage in {"02_SCRIPT", "08_VISUALIZATION"}:
                print(f"{stage}: unit {state.get('next_unit', 1)}; status={status}")
            else:
                print(f"{stage}: status={status}")
            return 0

    print("ALL_STAGES_APPROVED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
