#!/usr/bin/env python3
"""
Validator for GdUnit (.gd) test file naming and UTF-8 encoding stability.

Why:
  - Prevent "works on my machine" due to BOM/encoding drift.
  - Keep test refs stable: for a task, referenced .gd test files must follow a deterministic name pattern.

Scope:
  - Task scope: validates .gd files referenced by the task views:
      .taskmaster/tasks/tasks_back.json
      .taskmaster/tasks/tasks_gameplay.json
    via:
      - test_refs
      - acceptance items containing "Refs: <path>"
  - Files scope: validates explicitly provided repo-relative paths (CI-friendly).

Rules (strict):
  - File must exist and be repo-relative.
  - File must be valid UTF-8 WITHOUT BOM.
  - Task scope: file name must be: test_task<id>_*.gd
  - Files scope: file name must be: test_<lower_snake_case>.gd

Usage (Windows):
  py -3 scripts/python/check_gd_test_naming_and_encoding.py --task-id 60 --style strict
  py -3 scripts/python/check_gd_test_naming_and_encoding.py --files Tests.Godot/tests/UI/test_task60_example.gd --style strict

Exit codes:
  0 - OK
  1 - Violations found
  2 - Invalid args / unexpected error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


UTF8_BOM = b"\xef\xbb\xbf"


def repo_root() -> Path:
    # scripts/python/* -> repo root
    return Path(__file__).resolve().parents[2]


def read_text_utf8_sig(path: Path) -> str:
    return path.read_bytes().decode("utf-8-sig")


def resolve_repo_path(root: Path, raw: str) -> Path | None:
    s = str(raw or "").strip()
    if not s:
        return None
    p = Path(s)
    if p.is_absolute():
        try:
            _ = p.resolve().relative_to(root.resolve())
            return p.resolve()
        except Exception:
            return None
    pp = (root / p).resolve()
    try:
        _ = pp.relative_to(root.resolve())
    except Exception:
        return None
    return pp


def load_task_gd_refs(*, root: Path, task_id: str) -> List[str]:
    back_path = root / ".taskmaster" / "tasks" / "tasks_back.json"
    gameplay_path = root / ".taskmaster" / "tasks" / "tasks_gameplay.json"
    if not back_path.exists() or not gameplay_path.exists():
        return []

    try:
        back = json.loads(read_text_utf8_sig(back_path))
        gameplay = json.loads(read_text_utf8_sig(gameplay_path))
    except Exception:
        return []

    try:
        tid_int = int(str(task_id))
    except ValueError:
        return []

    refs: List[str] = []
    ref_re = re.compile(r"\bRefs:\s*([^\s]+)")
    for view in (back, gameplay):
        if not isinstance(view, list):
            continue
        for t in view:
            if not isinstance(t, dict):
                continue
            if t.get("taskmaster_id") != tid_int:
                continue
            tr = t.get("test_refs")
            if isinstance(tr, list):
                for r in tr:
                    s = str(r).strip().replace("\\", "/")
                    if s:
                        refs.append(s)
            acceptance = t.get("acceptance")
            if isinstance(acceptance, list):
                for item in acceptance:
                    s = str(item or "")
                    m = ref_re.search(s)
                    if not m:
                        continue
                    r = str(m.group(1)).strip().replace("\\", "/")
                    if r:
                        refs.append(r)

    uniq: List[str] = []
    seen = set()
    for r in refs:
        if not r.lower().endswith(".gd"):
            continue
        if r in seen:
            continue
        seen.add(r)
        uniq.append(r)
    return uniq


def check_gd_file(*, root: Path, task_id: str, rel: str, style: str) -> List[str]:
    errors: List[str] = []
    rp = resolve_repo_path(root, rel)
    if rp is None:
        return [f"{rel}: invalid_path_outside_repo"]
    if not rp.exists():
        return [f"{rel}: missing_file"]

    filename = rp.name
    if style == "strict":
        if task_id:
            expected_prefix = f"test_task{task_id}_"
            if not filename.startswith(expected_prefix) or not filename.lower().endswith(".gd"):
                errors.append(f"{rel}: bad_name (expected prefix: {expected_prefix})")
        else:
            if not re.match(r"^test_[a-z0-9_]+\.gd$", filename):
                errors.append(f"{rel}: bad_name (expected: test_<lower_snake_case>.gd)")

    raw = rp.read_bytes()
    if raw.startswith(UTF8_BOM):
        errors.append(f"{rel}: utf8_bom_present")

    try:
        _ = raw.decode("utf-8")
    except UnicodeDecodeError:
        errors.append(f"{rel}: not_utf8")

    if raw and not raw.endswith(b"\n"):
        errors.append(f"{rel}: missing_final_newline")

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate task-scoped GdUnit (.gd) test naming and UTF-8 encoding.")
    ap.add_argument("--task-id", default=None, help="Task id to validate.")
    ap.add_argument("--files", nargs="*", default=None, help="Explicit repo-relative .gd files to validate (CI-friendly).")
    ap.add_argument("--style", choices=["strict"], default="strict", help="Validation strictness.")
    ap.add_argument("--out", default=None, help="Optional JSON output report path.")
    args = ap.parse_args()

    root = repo_root()
    if args.task_id and args.files is not None:
        print("Error: --task-id and --files are mutually exclusive.", file=sys.stderr)
        return 2

    if args.task_id:
        gd_refs = load_task_gd_refs(root=root, task_id=str(args.task_id))
        scope = f"task-id={args.task_id} (refs .gd only)"
    else:
        raw_files = args.files or []
        gd_refs = [str(x).strip().replace("\\", "/") for x in raw_files if str(x).strip()]
        gd_refs = [x for x in gd_refs if x.lower().endswith(".gd")]
        scope = "explicit files"

    print("Scanning GdUnit (.gd) tests for naming/encoding violations...")
    print(f"Scope: {scope}")
    print(f"Style: {args.style}")
    print()

    report: Dict[str, Any] = {
        "status": "ok",
        "task_id": str(args.task_id) if args.task_id else None,
        "style": args.style,
        "files": [],
        "errors": [],
    }

    if not gd_refs:
        print("[OK] No .gd test refs found for this task.")
        if args.out:
            out_path = resolve_repo_path(root, args.out) or Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0

    all_errors: List[str] = []
    for rel in gd_refs:
        errs = check_gd_file(root=root, task_id=str(args.task_id or ""), rel=rel, style=args.style)
        report["files"].append({"path": rel, "errors": errs})
        all_errors.extend(errs)

    if all_errors:
        report["status"] = "fail"
        report["errors"] = all_errors
        print("[FAIL] GdUnit naming/encoding violations found:\n")
        for e in all_errors:
            print(f"- {e}")
        print()
        print("Fix:")
        print(f"- Ensure files are UTF-8 without BOM and end with a newline")
        print(f"- Rename to: test_task{args.task_id}_<description>.gd and update task refs")
    else:
        print("[OK] All .gd test files pass naming/encoding rules.")

    if args.out:
        out_path = resolve_repo_path(root, args.out) or Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
