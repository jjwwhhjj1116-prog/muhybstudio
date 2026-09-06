#!/usr/bin/env python3
"""Archive only committed Git files after public validation, never the working tree."""
import argparse
import subprocess
from pathlib import Path
from validate_v13 import main as validate

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if output.exists():
        raise SystemExit("Output exists; choose a new path")
    if output == root or root in output.parents:
        raise SystemExit("Write the archive outside the public checkout")
    status = subprocess.run(["git", "-C", str(root), "status", "--porcelain"], capture_output=True, text=True, check=True)
    if status.stdout.strip():
        raise SystemExit("Commit reviewed changes before making a release")
    if validate():
        return 1
    subprocess.run(["git", "-C", str(root), "archive", "--format=zip", "--output", str(output), "HEAD"], check=True)
    print(output)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
