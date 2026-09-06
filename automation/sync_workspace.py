#!/usr/bin/env python3
"""Fetch and inspect shared workflow state; start only fast-forwards clean main."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

EXPECTED = "https://github.com/jjwwhhjj1116-prog/muhybstudio.git"


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], text=True,
                            encoding="utf-8", capture_output=True)
    if result.returncode:
        raise RuntimeError(f"git {args[0]} failed (exit {result.returncode}); inspect Git locally")
    return result.stdout.strip()


def canonical_remote(value: str) -> str:
    if value.startswith("git@github.com:"):
        value = "https://github.com/" + value.split(":", 1)[1]
    return value.removesuffix(".git").rstrip("/")


def inspect(repo: Path, expected: str = EXPECTED) -> dict:
    if canonical_remote(git(repo, "remote", "get-url", "origin")) != canonical_remote(expected):
        raise RuntimeError("origin is not the expected workflow repository; no fetch performed")
    git(repo, "fetch", "--prune", "origin")
    branch = git(repo, "branch", "--show-current")
    counts = git(repo, "rev-list", "--left-right", "--count", "HEAD...origin/main").split()
    return {"branch": branch, "dirty": bool(git(repo, "status", "--porcelain")),
            "ahead": int(counts[0]), "behind": int(counts[1]),
            "head": git(repo, "rev-parse", "HEAD"),
            "remote_main": git(repo, "rev-parse", "origin/main")}


def start(repo: Path, expected: str = EXPECTED) -> dict:
    state = inspect(repo, expected)
    if state["branch"] != "main" or state["dirty"] or state["ahead"]:
        raise RuntimeError("start requires clean main without local-only commits; preserve work and reconcile first")
    git(repo, "merge", "--ff-only", "origin/main")
    state.update(head=git(repo, "rev-parse", "HEAD"), behind=0)
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["check", "start"])
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    try:
        result = start(repo) if args.action == "start" else inspect(repo)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except RuntimeError as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
