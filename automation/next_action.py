#!/usr/bin/env python3
"""Report the first incomplete V13 stage; does not execute it."""
import argparse
import json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage_status", type=Path)
    args = parser.parse_args()
    data = json.loads(args.stage_status.read_text(encoding="utf-8"))
    if data.get("schema_version") != "3.0":
        raise SystemExit("Old stage status requires explicit migration to V13")
    template = json.loads((Path(__file__).resolve().parents[1] / "templates/stage_status.template.json").read_text(encoding="utf-8"))
    if set(data["stages"]) != set(template["stages"]):
        raise SystemExit("Stage set does not match V13 template")
    for name in template["stages"]:
        item = data["stages"][name]
        if item["status"] != "ACCEPTED":
            print(json.dumps({"stage": name, "status": item["status"], "next_unit": item.get("next_unit")}, ensure_ascii=False))
            return 0
    print("ALL_STAGES_ACCEPTED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
