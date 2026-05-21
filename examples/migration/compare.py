"""Compare Go and Python migration script outputs.

Normalizes known serialization differences (HTML entity escaping,
$schema: null, input: null, timestamp precision) before diffing.
Writes DIFF_REPORT.md when semantic differences are found.
"""

from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
GO_DIR = SCRIPT_DIR / "01_audit_hub_go"
PY_DIR = SCRIPT_DIR / "01_audit_hub_python"
EXPECTED_FILES = ["prd.md", "requirements.json", "test_spec.json", "tasks.json", "architecture.md"]
REPORT_PATH = SCRIPT_DIR / "DIFF_REPORT.md"


def strip_null_keys(obj: Any, keys: set[str]) -> Any:
    """Recursively remove dict keys whose value is None."""
    if isinstance(obj, dict):
        return {k: strip_null_keys(v, keys) for k, v in obj.items() if not (k in keys and v is None)}
    if isinstance(obj, list):
        return [strip_null_keys(item, keys) for item in obj]
    return obj


def normalize_json(text: str) -> list[str]:
    data = json.loads(text)
    data = strip_null_keys(data, {"$schema", "input"})
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False).splitlines(keepends=True)


def normalize_md(text: str) -> list[str]:
    lines = text.splitlines(keepends=True)
    return [line for line in lines if not line.startswith("updated_at:")]


def normalize(path: Path) -> list[str]:
    text = path.read_text()
    if path.suffix == ".json":
        return normalize_json(text)
    return normalize_md(text)


def main() -> int:
    missing = []
    if not GO_DIR.is_dir():
        missing.append(str(GO_DIR))
    if not PY_DIR.is_dir():
        missing.append(str(PY_DIR))
    if missing:
        print(f"Missing output directories: {', '.join(missing)}", file=sys.stderr)
        print("Run `make run-go run-python` first.", file=sys.stderr)
        return 1

    diffs: dict[str, list[str]] = {}

    for filename in EXPECTED_FILES:
        go_path = GO_DIR / filename
        py_path = PY_DIR / filename
        if not go_path.exists() or not py_path.exists():
            diffs[filename] = [f"File missing: go={go_path.exists()}, python={py_path.exists()}\n"]
            continue

        go_lines = normalize(go_path)
        py_lines = normalize(py_path)

        diff = list(difflib.unified_diff(go_lines, py_lines, fromfile=f"go/{filename}", tofile=f"python/{filename}"))
        if diff:
            diffs[filename] = diff

    if not diffs:
        print("All outputs identical (after normalization)")
        if REPORT_PATH.exists():
            REPORT_PATH.unlink()
        return 0

    report_lines = ["# Diff Report: Go vs Python Migration Output\n\n"]
    for filename, diff_lines in diffs.items():
        report_lines.append(f"## {filename}\n\n")
        report_lines.append("```diff\n")
        report_lines.extend(diff_lines)
        if not diff_lines[-1].endswith("\n"):
            report_lines.append("\n")
        report_lines.append("```\n\n")

    REPORT_PATH.write_text("".join(report_lines))

    count = len(diffs)
    print(f"FAIL: {count} file(s) differ — see {REPORT_PATH.name}")
    for filename in diffs:
        print(f"  - {filename}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
