#!/usr/bin/env python3
"""
Deterministic hard gate for C# test naming and structure conventions.

Checks:
  - file name: PascalCase + Tests.cs
  - class name: PascalCase and matches file stem
  - test method names: ShouldX_WhenY
  - helper method names: PascalCase
  - local variables: camelCase
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _bootstrap_imports() -> None:
    root = Path(__file__).resolve().parents[2]
    python_dir = root / "scripts" / "python"
    sc_dir = root / "scripts" / "sc"
    for candidate in (python_dir, sc_dir):
        text = str(candidate)
        if text not in sys.path:
            sys.path.insert(0, text)


_bootstrap_imports()

from _csharp_test_conventions import validate_csharp_test_file  # noqa: E402
from _taskmaster_paths import resolve_default_task_triplet_paths  # noqa: E402


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _find_view_task(view: list[dict], task_id: str) -> dict | None:
    try:
        tid_int = int(str(task_id))
    except ValueError:
        return None
    for item in view:
        if isinstance(item, dict) and item.get("taskmaster_id") == tid_int:
            return item
    return None


def load_task_triplet_metadata(*, root: Path, task_id: str) -> tuple[dict, dict | None, dict | None]:
    tasks_json_path, back_path, gameplay_path = resolve_default_task_triplet_paths(root)
    master = {}
    back = None
    gameplay = None

    if tasks_json_path.is_file():
        obj = load_json(tasks_json_path)
        tasks = ((obj.get("master") or {}).get("tasks") or []) if isinstance(obj, dict) else []
        for item in tasks:
            if isinstance(item, dict) and str(item.get("id")) == str(task_id):
                master = item
                break

    if back_path.is_file():
        obj = load_json(back_path)
        if isinstance(obj, list):
            back = _find_view_task(obj, task_id)

    if gameplay_path.is_file():
        obj = load_json(gameplay_path)
        if isinstance(obj, list):
            gameplay = _find_view_task(obj, task_id)

    return master, back, gameplay


def _collect_raw_task_cs_refs(*, root: Path, task_id: str) -> list[str]:
    master, back, gameplay = load_task_triplet_metadata(root=root, task_id=task_id)
    refs: list[str] = []
    for block in (master, back or {}, gameplay or {}):
        raw = block.get("test_refs")
        if not isinstance(raw, list):
            continue
        for item in raw:
            ref = str(item or "").strip().replace("\\", "/")
            if ref.startswith("Game.Core.Tests/") and ref.endswith(".cs") and ref not in refs:
                refs.append(ref)
    return refs


def task_requires_csharp_tests(*, root: Path, task_id: str) -> tuple[bool, list[str]]:
    master, back, gameplay = load_task_triplet_metadata(root=root, task_id=task_id)
    reasons: list[str] = []

    for block in (master, back or {}, gameplay or {}):
        contract_refs = block.get("contractRefs")
        if isinstance(contract_refs, list) and any(str(item or "").strip() for item in contract_refs):
            reasons.append("contract_refs_present")
            break

    text_blobs: list[str] = []
    for block in (master, back or {}, gameplay or {}):
        for key in ("title", "details", "testStrategy"):
            value = block.get(key)
            if isinstance(value, str) and value.strip():
                text_blobs.append(value)
        for key in ("test_strategy", "acceptance"):
            value = block.get(key)
            if isinstance(value, list):
                text_blobs.extend(str(item or "").strip() for item in value if str(item or "").strip())

    lower_blob = "\n".join(text_blobs).lower()
    if "xunit" in lower_blob:
        reasons.append("mentions_xunit")
    if "game.core" in lower_blob:
        reasons.append("mentions_game_core")
    if "c#" in lower_blob or "csharp" in lower_blob:
        reasons.append("mentions_csharp")
    if "scripts/core" in lower_blob or "game.core/contracts" in lower_blob:
        reasons.append("mentions_core_paths")

    raw_cs_refs = _collect_raw_task_cs_refs(root=root, task_id=task_id)
    if raw_cs_refs:
        reasons.append("test_refs_include_cs")

    deduped: list[str] = []
    for item in reasons:
        if item not in deduped:
            deduped.append(item)
    return bool(deduped), deduped


def load_task_csharp_test_refs(*, root: Path, task_id: str) -> list[Path]:
    refs = _collect_raw_task_cs_refs(root=root, task_id=str(task_id).split(".", 1)[0].strip())
    files: list[Path] = []
    for ref in refs:
        path = root / ref
        if path.is_file():
            files.append(path)
    return files


def load_all_csharp_test_files(*, root: Path) -> list[Path]:
    test_dir = root / "Game.Core.Tests"
    if not test_dir.is_dir():
        return []
    return sorted(p for p in test_dir.rglob("*Tests.cs") if p.is_file())


def scan_files(files: list[Path], *, root: Path) -> list[dict]:
    violations: list[dict] = []
    for path in files:
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as exc:
            violations.append(
                {
                    "file": str(path.relative_to(root)).replace("\\", "/"),
                    "line": 1,
                    "rule": "read_error",
                    "message": f"failed to read file: {exc}",
                }
            )
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        for item in validate_csharp_test_file(ref=rel, content=content):
            violations.append({"file": rel, **item})
    return violations


def main() -> int:
    ap = argparse.ArgumentParser(description="Check C# test naming and structure conventions.")
    ap.add_argument("--task-id", default=None, help="If set, only scan task-scoped C# test_refs.")
    args = ap.parse_args()

    root = repo_root()
    if args.task_id:
        task_id = str(args.task_id).split(".", 1)[0]
        raw_cs_refs = _collect_raw_task_cs_refs(root=root, task_id=task_id)
        files = load_task_csharp_test_refs(root=root, task_id=task_id)
        scope = f"task-id={task_id} (task-scoped .cs test_refs)"
    else:
        files = load_all_csharp_test_files(root=root)
        scope = "all Game.Core.Tests/**/*.cs"

    print("Scanning C# test conventions...")
    print(f"Scope: {scope}")
    print()

    if args.task_id:
        required, reasons = task_requires_csharp_tests(root=root, task_id=task_id)
        if required and not raw_cs_refs:
            print("[FAIL] Task requires C# tests but task metadata has no .cs test_refs")
            print(f"Reasons: {', '.join(reasons)}")
            return 1
        if required and raw_cs_refs and not files:
            print("[FAIL] Task requires C# tests but none of the .cs test_refs exist on disk")
            print(f"Reasons: {', '.join(reasons)}")
            for ref in raw_cs_refs:
                print(f"Missing: {ref}")
            return 1

    if not files:
        print("[OK] No C# test files matched this scope")
        return 0

    violations = scan_files(files, root=root)
    if not violations:
        print("[OK] All scanned C# test files satisfy deterministic conventions")
        return 0

    print("[FAIL] C# test convention violations found:")
    print()
    for item in violations:
        print(f"{item['file']}:{item['line']} [{item['rule']}] {item['message']}")
    print()
    print(f"Total violations: {len(violations)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
