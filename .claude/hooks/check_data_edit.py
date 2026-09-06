#!/usr/bin/env python3
"""PostToolUse hook: validate the ledger whenever anything under data/ is edited.

A malformed ledger row does not raise an error anywhere -- it just makes the
published balance wrong. Remembering to run tools/doctor.py is exactly the kind
of thing that gets forgotten, so this runs it automatically and hands the
findings back to Claude by exiting 2.
"""

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def edited_path(payload):
    tool_input = payload.get("tool_input") or {}
    return tool_input.get("file_path") or tool_input.get("notebook_path") or ""


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    raw = edited_path(payload)
    if not raw:
        return 0
    try:
        edited = pathlib.Path(raw).resolve()
    except (OSError, ValueError):
        return 0
    if ROOT / "data" not in edited.parents:
        return 0

    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "doctor.py"), "--quiet"],
        cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return 0

    findings = (result.stdout + result.stderr).strip()
    print("tools/doctor.py rejected the ledger. Fix these before committing:\n"
          f"{findings}", file=sys.stderr)
    return 2                      # exit 2 feeds stderr back to Claude


if __name__ == "__main__":
    sys.exit(main())
