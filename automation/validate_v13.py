#!/usr/bin/env python3
"""Validate public workflow documents and templates; not fiction or media quality."""
from __future__ import annotations

import hashlib
import json
import math
import py_compile
import re
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def files() -> list[str]:
    result = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard", "-z"], capture_output=True)
    if result.returncode:
        raise ValueError("cannot enumerate Git files")
    return sorted(set(x.decode("utf-8") for x in result.stdout.split(b"\0") if x))


def validate_shape(value: object, schema: dict, at: str = "root") -> list[str]:
    """Check the schema features used by initializer templates, not all JSON Schema."""
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
    for constraint in schema.get("allOf", []):
        errors.extend(validate_shape(value, constraint, at))
    if "if" in schema:
        branch = "else" if validate_shape(value, schema["if"], at) else "then"
        if branch in schema:
            errors.extend(validate_shape(value, schema[branch], at))
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{at}: missing {key}")
        for key, child in schema.get("properties", {}).items():
            if key in value:
                errors.extend(validate_shape(value[key], child, at + "." + key))
        if schema.get("additionalProperties") is False:
            for key in set(value) - set(schema.get("properties", {})):
                errors.append(f"{at}: unexpected property {key}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):
            errors.append(f"{at}: non-finite number")
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{at}: below minimum")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            errors.append(f"{at}: below exclusive minimum")
    if isinstance(value, (str, list)):
        length_key = "minLength" if isinstance(value, str) else "minItems"
        if len(value) < schema.get(length_key, 0):
            errors.append(f"{at}: too short")
    if isinstance(value, str) and "pattern" in schema and not re.search(schema["pattern"], value):
        errors.append(f"{at}: pattern mismatch")
    if isinstance(value, list):
        if schema.get("uniqueItems") and len({json.dumps(x, sort_keys=True) for x in value}) != len(value):
            errors.append(f"{at}: duplicate items")
        for i, child in enumerate(value):
            errors.extend(validate_shape(child, schema.get("items", {}), f"{at}[{i}]"))
    return errors


def validate_manifest(manifest: object, stage_status: object = None) -> list[str]:
    """Validate a manifest without migrating a legacy project or inventing a chunk plan."""
    spec = json.loads((ROOT / "schemas/project_manifest.schema.json").read_text(encoding="utf-8"))
    errors = validate_shape(manifest, spec, "manifest")
    if errors:
        return errors
    targets = manifest["targets"]
    if targets["script_chunks"] is None and stage_status is not None:
        script_stage = None
        if isinstance(stage_status, dict) and isinstance(stage_status.get("stages"), dict):
            script_stage = stage_status["stages"].get("02_SCRIPT")
        if not isinstance(script_stage, dict) or script_stage.get("status") != "NOT_STARTED":
            errors.append("manifest.targets.script_chunks: null is allowed only while the script stage is NOT_STARTED")
    if manifest["workflow_version"] == "3.1.0":
        if targets["episode_count"] * targets["story_parts_per_episode"] != targets["story_part_count"]:
            errors.append("manifest.targets: public episode count and internal story part allocation disagree")
        if targets["episode_target_minutes"] * 60 < targets["episode_min_runtime_seconds"]:
            errors.append("manifest.targets: planned episode target is shorter than the minimum runtime")
    return errors


def validate_release_plan(plan: object, manifest: object = None) -> list[str]:
    """Validate allocation and externally stated runtimes; never measure/read media."""
    spec = json.loads((ROOT / "schemas/release_plan.schema.json").read_text(encoding="utf-8"))
    errors = validate_shape(plan, spec, "release_plan")
    if errors:
        return errors
    count, parts, per_episode = (plan[key] for key in ("public_episode_count", "story_part_count", "story_parts_per_episode"))
    if count * per_episode != parts:
        errors.append("release_plan: internal story parts cannot be used as the public episode count")
    if len(plan["episodes"]) != count:
        errors.append("release_plan: missing or extra public episodes")
    if plan["episode_target_minutes"] * 60 < plan["episode_min_runtime_seconds"]:
        errors.append("release_plan: target runtime is shorter than the planned minimum")
    owned = []
    for index, episode in enumerate(plan["episodes"], 1):
        if episode["episode_number"] != index or episode["episode_id"] != f"EP{index:02d}":
            errors.append(f"release_plan.episodes[{index - 1}]: public episode ID/order mismatch")
        expected_parts = list(range((index - 1) * per_episode + 1, index * per_episode + 1))
        if episode["story_part_ids"] != expected_parts:
            errors.append(f"release_plan.episodes[{index - 1}]: wrong internal parts or part order")
        owned.extend(episode["story_part_ids"])
        minimum = episode["planned_min_runtime_seconds"]
        if minimum != plan["episode_min_runtime_seconds"]:
            errors.append(f"release_plan.episodes[{index - 1}]: planned minimum differs from the project minimum")
        runtime = episode["runtime_seconds"]
        if runtime is not None and runtime < minimum:
            errors.append(f"release_plan.episodes[{index - 1}]: stated runtime is below the planned minimum")
        if runtime is not None:
            evidence = episode.get("runtime_evidence")
            if not isinstance(evidence, str) or not evidence.strip():
                errors.append(f"release_plan.episodes[{index - 1}]: stated runtime requires runtime_evidence")
            else:
                portable = evidence.replace("\\", "/")
                path = PurePosixPath(portable)
                if path.is_absolute() or ".." in path.parts or not path.parts or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", portable) or any(ord(char) < 32 for char in evidence):
                    errors.append(f"release_plan.episodes[{index - 1}]: runtime_evidence must be a private project-relative file/report path")
    if owned != list(range(1, parts + 1)):
        errors.append("release_plan: omitted, repeated, reordered or out-of-range internal parts")
    if manifest is not None:
        manifest_errors = validate_manifest(manifest)
        if manifest_errors:
            errors.extend(manifest_errors)
        else:
            pairs = {
                "public_episode_count": "episode_count",
                "story_part_count": "story_part_count",
                "story_parts_per_episode": "story_parts_per_episode",
                "episode_target_minutes": "episode_target_minutes",
                "episode_min_runtime_seconds": "episode_min_runtime_seconds",
            }
            if plan["project_id"] != manifest["project_id"] or plan["workflow_version"] != manifest["workflow_version"]:
                errors.append("release_plan: project/workflow does not match the manifest; explicit planning is required")
            for plan_key, target_key in pairs.items():
                if plan[plan_key] != manifest["targets"].get(target_key):
                    errors.append(f"release_plan.{plan_key}: differs from manifest.targets.{target_key}")
    return errors


def validate_defaults(version: dict, manifest: dict, plan: dict, status: dict, chunk: dict) -> list[str]:
    """Catch inconsistent new-project defaults while leaving existing manifests alone."""
    errors = validate_manifest(manifest, status) + validate_release_plan(plan, manifest)
    expected = {
        "default_episode_count": ("episode_count", 4),
        "default_episode_target_minutes": ("episode_target_minutes", 60),
        "default_episode_min_runtime_seconds": ("episode_min_runtime_seconds", 3600),
        "default_story_part_count": ("story_part_count", 16),
        "default_story_parts_per_episode": ("story_parts_per_episode", 4),
        "default_script_chunks": ("script_chunks", None),
        "script_chunk_subdivision": ("allow_subchunks", True),
    }
    for version_key, (target_key, wanted) in expected.items():
        if version_key not in version or version[version_key] != wanted or manifest["targets"].get(target_key) != wanted:
            errors.append(f"new-project default mismatch: {version_key}/targets.{target_key}")
    if manifest.get("workflow_version") != version.get("version") or status.get("workflow_version") != version.get("version"):
        errors.append("initializer template workflow versions differ from VERSION.json")
    if manifest.get("video", {}).get("model") != version.get("video_model") or version.get("video_model") != "Veo 3.1 - Lite":
        errors.append("initializer/default video model mismatch")
    if manifest["targets"].get("script_plan_status") != "NOT_STARTED" or chunk.get("status") != "NOT_STARTED" or chunk.get("of") is not None:
        errors.append("new project must not invent a technical chunk count before planning")
    if plan.get("status") != "NOT_STARTED" or any(episode.get("runtime_seconds") is not None for episode in plan.get("episodes", [])):
        errors.append("new release plan cannot assert an actual measured runtime")
    return errors


def main() -> int:
    errors = []
    try:
        paths = files()
        version = json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))
        mapping = json.loads((ROOT / "migrations/v13.json").read_text(encoding="utf-8"))
        if version.get("version") != "3.1.0" or version.get("writer_policy") != "NARRATIVE_POINT_HOOKS_2026_09" or version.get("format") != "episodic-animation":
            errors.append("wrong workflow version/format")
        if len(mapping) != 37 or len({x['previous'] for x in mapping}) != 37:
            errors.append("migration must cover 37 distinct old entries")
        for restored in version.get("writer_restored_files", []):
            path = ROOT / restored["path"]
            if not path.is_file() or hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != restored["sha256"]:
                errors.append("archived writer source changed: " + restored["path"])
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
        for template, schema in [("project_manifest", "project_manifest"), ("script_chunk_state", "chunk_state"), ("release_plan", "release_plan")]:
            data = json.loads((ROOT / f"templates/{template}.template.json").read_text(encoding="utf-8"))
            spec = json.loads((ROOT / f"schemas/{schema}.schema.json").read_text(encoding="utf-8"))
            errors.extend(validate_shape(data, spec, template))
        status = json.loads((ROOT / "templates/stage_status.template.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "templates/project_manifest.template.json").read_text(encoding="utf-8"))
        release_plan = json.loads((ROOT / "templates/release_plan.template.json").read_text(encoding="utf-8"))
        chunk = json.loads((ROOT / "templates/script_chunk_state.template.json").read_text(encoding="utf-8"))
        errors.extend(validate_defaults(version, manifest, release_plan, status, chunk))
        if "policy/07_SYNOPSIS_AND_RELEASE_PLAN.md" not in version["active_policy"]:
            errors.append("synopsis/release planning policy is not active")
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
