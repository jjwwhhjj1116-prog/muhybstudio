#!/usr/bin/env python3
"""Validate public workflow documents and templates; not fiction or media quality."""
from __future__ import annotations

import hashlib
import json
import py_compile
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def files() -> list[str]:
    result = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard", "-z"], capture_output=True)
    if result.returncode:
        raise ValueError("cannot enumerate Git files")
    return sorted(set(x.decode("utf-8") for x in result.stdout.split(b"\0") if x))


def validate_shape(value: object, schema: dict, at: str = "root") -> list[str]:
    """Check the schema features used by our two initializer templates, not all JSON Schema."""
    errors = []
    types = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool, "null": type(None)}
    expected = schema.get("type")
    if expected:
        expected = [expected] if isinstance(expected, str) else expected
        matches = any(isinstance(value, types[t]) and not (t in {"integer", "number"} and isinstance(value, bool)) for t in expected)
        if not matches:
            return [f"{at}: type mismatch"]
    if "const" in schema and value != schema["const"]:
        errors.append(f"{at}: wrong constant")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{at}: unexpected enum")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{at}: missing {key}")
        for key, child in schema.get("properties", {}).items():
            if key in value:
                errors.extend(validate_shape(value[key], child, at + "." + key))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{at}: below minimum")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            errors.append(f"{at}: below exclusive minimum")
    if isinstance(value, (str, list)):
        length_key = "minLength" if isinstance(value, str) else "minItems"
        if len(value) < schema.get(length_key, 0):
            errors.append(f"{at}: too short")
    if isinstance(value, list):
        if schema.get("uniqueItems") and len({json.dumps(x, sort_keys=True) for x in value}) != len(value):
            errors.append(f"{at}: duplicate items")
        for i, child in enumerate(value):
            errors.extend(validate_shape(child, schema.get("items", {}), f"{at}[{i}]"))
    return errors


def main() -> int:
    errors = []
    try:
        paths = files()
        version = json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))
        mapping = json.loads((ROOT / "migrations/v13.json").read_text(encoding="utf-8"))
        if version.get("version") != "3.0.0" or version.get("writer_policy") != "V12_RESTORED" or version.get("format") != "episodic-animation":
            errors.append("wrong workflow version/format")
        if len(mapping) != 37 or len({x['previous'] for x in mapping}) != 37:
            errors.append("migration must cover 37 distinct old entries")
        for restored in version.get("writer_restored_files", []):
            path = ROOT / restored["path"]
            if not path.is_file() or hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != restored["sha256"]:
                errors.append("restored writer source changed: " + restored["path"])
        if len(version.get("writer_restored_files", [])) != 5:
            errors.append("five original writer documents must be pinned")
        required = version["active_policy"] + ["AGENTS.md", "workflow/12_THREE_PC_SYNC.md", "coordination/STATUS.md"]
        required += [d for row in mapping for d in [row['previous'], *row['current']]]
        for rel in required:
            if not (ROOT / rel).is_file():
                errors.append(f"missing: {rel}")
        for rel in paths:
            p = ROOT / rel
            if not p.is_file():
                continue
            if (rel.startswith("projects/") and rel != "projects/_template/README.md") or re.search(r"(^|/)(\.env(\..*)?|credentials[^/]*|token[^/]*)$", rel, re.I) or p.suffix.lower() in {".mp4", ".mp3", ".wav", ".zip"}:
                errors.append(f"private/generated file in public candidate: {rel}")
            if p.suffix == ".json":
                json.loads(p.read_text(encoding="utf-8"))
            if p.suffix in {".md", ".json", ".py", ".yml"}:
                content = p.read_text(encoding="utf-8")
                # Conservative accidental secret/path/story leak check, not a security guarantee.
                if re.search(r"(?:gh[pousr]_[A-Za-z0-9]{24,}|sk-proj-[A-Za-z0-9_-]{24,}|C:[\\/]Users[\\/])", content):
                    errors.append(f"possible credential or private absolute path: {rel}")
                if any(name in content for name in ["혈월" + "동심록", "윤" + "태강", "연" + "소화"]):
                    errors.append(f"private project content: {rel}")
                if p.suffix == ".md":
                    for link in re.findall(r"\]\(([^)]+)\)", content):
                        if "://" in link or link.startswith("#"):
                            continue
                        target = (p.parent / link.split("#")[0]).resolve()
                        if not target.exists():
                            errors.append(f"broken link: {rel} -> {link}")
        for template, schema in [("project_manifest", "project_manifest"), ("script_chunk_state", "chunk_state")]:
            data = json.loads((ROOT / f"templates/{template}.template.json").read_text(encoding="utf-8"))
            spec = json.loads((ROOT / f"schemas/{schema}.schema.json").read_text(encoding="utf-8"))
            errors.extend(validate_shape(data, spec, template))
        status = json.loads((ROOT / "templates/stage_status.template.json").read_text(encoding="utf-8"))
        for step in ["05_VOICE_ALIGNMENT", "07_FLOW_IMAGES", "08_FLOW_VIDEOS", "10_EDIT_RENDER"]:
            if step not in status['stages']:
                errors.append(f"missing runtime stage: {step}")
        with tempfile.TemporaryDirectory() as temp:
            for index, p in enumerate((ROOT / "automation").glob("*.py")):
                py_compile.compile(str(p), cfile=str(Path(temp) / f"{index}.pyc"), doraise=True)
    except (ValueError, KeyError, OSError, py_compile.PyCompileError) as exc:
        errors.append(str(exc))
    print(json.dumps({"ok": not errors, "scope": "public workflow structure and template checks; not prose or media QA", "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
