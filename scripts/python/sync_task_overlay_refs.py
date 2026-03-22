#!/usr/bin/env python3
"""Sync overlay refs for Taskmaster triplet in a template-safe way.

Highlights:
- Works with both `.taskmaster/tasks` and `examples/taskmaster` (fallback).
- Supports explicit `--prd-id` or auto-detect from tasks/overlays.
- Supports `--write` (requested workflow style) and dry-run by default.
- Uses overlay manifest when present; otherwise infers page files from folder.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


OVERLAY_PRD_RE = re.compile(r"^docs/architecture/overlays/([^/]+)/08(?:/|$)")
VALID_PRD_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
MANIFEST_FILE_NAME = "overlay-manifest.json"
MANIFEST_KEYS = ("index", "feature", "contracts", "testing", "observability", "acceptance")
TRIPLET_FILES = ("tasks.json", "tasks_back.json", "tasks_gameplay.json")


@dataclass(frozen=True)
class OverlayPaths:
    prd_id: str
    base: str
    manifest: str | None
    index: str
    feature: str | None
    contracts: str | None
    testing: str | None
    observability: str | None
    acceptance: str


@dataclass(frozen=True)
class FileSyncResult:
    file: str
    total_tasks: int
    changed_tasks: int
    changed_ids: list[str]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _today() -> str:
    return dt.date.today().isoformat()


def _to_posix(path: str) -> str:
    return path.replace("\\", "/")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _validate_prd_id(prd_id: str) -> str:
    value = prd_id.strip()
    if not value:
        raise ValueError("Empty PRD id is not allowed.")
    if not VALID_PRD_ID_RE.fullmatch(value):
        raise ValueError(f"Invalid PRD id '{prd_id}'. Allowed chars: [A-Za-z0-9._-].")
    return value


def _resolve_tasks_dir(root: Path, requested: str | None) -> Path:
    if requested and str(requested).strip():
        path = (root / requested).resolve()
        return path
    for rel in (".taskmaster/tasks", "examples/taskmaster"):
        candidate = root / rel
        if all((candidate / name).exists() for name in TRIPLET_FILES):
            return candidate
    return (root / ".taskmaster" / "tasks").resolve()


def _normalize_refs(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def _extract_prd_ids_from_values(values: list[str]) -> set[str]:
    found: set[str] = set()
    for value in values:
        candidate = _to_posix(str(value).strip())
        match = OVERLAY_PRD_RE.match(candidate)
        if match:
            found.add(match.group(1))
    return found


def _extract_prd_ids_from_master_tasks(payload: Any) -> set[str]:
    found: set[str] = set()
    if not isinstance(payload, dict):
        return found
    master = payload.get("master")
    if not isinstance(master, dict):
        return found
    tasks = master.get("tasks")
    if not isinstance(tasks, list):
        return found
    for task in tasks:
        if not isinstance(task, dict):
            continue
        overlay = str(task.get("overlay", "")).strip()
        found.update(_extract_prd_ids_from_values([overlay]))
    return found


def _extract_prd_ids_from_view_tasks(payload: Any) -> set[str]:
    found: set[str] = set()
    if not isinstance(payload, list):
        return found
    for task in payload:
        if not isinstance(task, dict):
            continue
        refs = _normalize_refs(task.get("overlay_refs"))
        found.update(_extract_prd_ids_from_values(refs))
    return found


def _auto_detect_prd_id(root: Path, tasks_dir: Path) -> str:
    task_candidates: set[str] = set()
    task_files = [tasks_dir / "tasks.json", tasks_dir / "tasks_back.json", tasks_dir / "tasks_gameplay.json"]
    for file_path in task_files:
        if not file_path.exists():
            continue
        payload = _load_json(file_path)
        if file_path.name == "tasks.json":
            task_candidates.update(_extract_prd_ids_from_master_tasks(payload))
        else:
            task_candidates.update(_extract_prd_ids_from_view_tasks(payload))

    if len(task_candidates) == 1:
        return next(iter(task_candidates))
    if len(task_candidates) > 1:
        ordered = sorted(task_candidates)
        raise ValueError(f"Auto-detect found multiple PRD IDs in task files: {ordered}. Use --prd-id.")

    overlays_root = root / "docs" / "architecture" / "overlays"
    fs_candidates: list[str] = []
    if overlays_root.exists():
        for folder in overlays_root.iterdir():
            if not folder.is_dir() or folder.name.startswith("_"):
                continue
            if (folder / "08").exists():
                fs_candidates.append(folder.name)

    if len(fs_candidates) == 1:
        return fs_candidates[0]
    if len(fs_candidates) > 1:
        ordered = sorted(fs_candidates)
        raise ValueError(f"Auto-detect found multiple PRD IDs in overlays: {ordered}. Use --prd-id.")
    raise ValueError("Cannot auto-detect PRD ID. Use --prd-id.")


def _resolve_prd_id(root: Path, tasks_dir: Path, explicit_prd_id: str | None) -> str:
    if explicit_prd_id and explicit_prd_id.strip():
        return _validate_prd_id(explicit_prd_id)
    return _auto_detect_prd_id(root, tasks_dir)


def _resolve_overlay_file(base: str, value: object) -> str:
    raw = _to_posix(str(value).strip())
    if not raw:
        raise ValueError("Overlay manifest contains empty path value.")
    if raw.startswith("docs/"):
        return raw
    return f"{base}/{raw.lstrip('./')}"


def _pick_first_matching(files: list[str], prefixes: tuple[str, ...], fallback: str | None = None) -> str | None:
    for name in files:
        lower = name.lower()
        if lower.endswith(".md") and lower.startswith(prefixes):
            return name
    return fallback


def _load_overlay_paths_from_folder(root: Path, prd_id: str) -> OverlayPaths:
    safe_prd_id = _validate_prd_id(prd_id)
    base = f"docs/architecture/overlays/{safe_prd_id}/08"
    folder = root / base
    if not folder.exists():
        raise ValueError(f"Missing overlay directory: {base}")

    all_files = [p.name for p in folder.iterdir() if p.is_file()]
    all_files.sort()

    index = "_index.md"
    acceptance = "ACCEPTANCE_CHECKLIST.md"
    if index not in all_files:
        raise ValueError(f"Missing required overlay file: {base}/{index}")
    if acceptance not in all_files:
        raise ValueError(f"Missing required overlay file: {base}/{acceptance}")

    feature = _pick_first_matching(all_files, ("08-feature-slice",))
    contracts = _pick_first_matching(all_files, ("08-contracts",))
    testing = _pick_first_matching(all_files, ("08-testing",))
    observability = _pick_first_matching(all_files, ("08-observability",))

    return OverlayPaths(
        prd_id=safe_prd_id,
        base=base,
        manifest=None,
        index=f"{base}/{index}",
        feature=f"{base}/{feature}" if feature else None,
        contracts=f"{base}/{contracts}" if contracts else None,
        testing=f"{base}/{testing}" if testing else None,
        observability=f"{base}/{observability}" if observability else None,
        acceptance=f"{base}/{acceptance}",
    )


def _load_overlay_paths_from_manifest(root: Path, prd_id: str) -> OverlayPaths:
    safe_prd_id = _validate_prd_id(prd_id)
    base = f"docs/architecture/overlays/{safe_prd_id}/08"
    manifest = f"{base}/{MANIFEST_FILE_NAME}"
    manifest_path = root / manifest
    if not manifest_path.exists():
        return _load_overlay_paths_from_folder(root, prd_id)

    payload = _load_json(manifest_path)
    if not isinstance(payload, dict):
        raise ValueError(f"Overlay manifest must be object: {manifest}")

    manifest_prd_id = str(payload.get("prd_id", "")).strip()
    if manifest_prd_id and manifest_prd_id != safe_prd_id:
        raise ValueError(f"Manifest prd_id mismatch: expected '{safe_prd_id}', got '{manifest_prd_id}'.")

    files = payload.get("files")
    if not isinstance(files, dict):
        raise ValueError(f"Overlay manifest missing 'files' object: {manifest}")

    missing = [key for key in MANIFEST_KEYS if key not in files]
    if missing:
        raise ValueError(f"Overlay manifest missing keys {missing}: {manifest}")

    return OverlayPaths(
        prd_id=safe_prd_id,
        base=base,
        manifest=manifest,
        index=_resolve_overlay_file(base, files["index"]),
        feature=_resolve_overlay_file(base, files["feature"]),
        contracts=_resolve_overlay_file(base, files["contracts"]),
        testing=_resolve_overlay_file(base, files["testing"]),
        observability=_resolve_overlay_file(base, files["observability"]),
        acceptance=_resolve_overlay_file(base, files["acceptance"]),
    )


def _ensure_overlay_files_exist(root: Path, paths: OverlayPaths) -> list[str]:
    required = [paths.index, paths.acceptance]
    optional = [paths.feature, paths.contracts, paths.testing, paths.observability]
    for maybe in optional:
        if maybe:
            required.append(maybe)
    if paths.manifest:
        required.append(paths.manifest)
    return [rel for rel in required if not (root / rel).exists()]


def _refs_for_task(paths: OverlayPaths) -> list[str]:
    ordered = [
        paths.index,
        paths.feature,
        paths.contracts,
        paths.testing,
        paths.observability,
        paths.acceptance,
    ]
    seen: set[str] = set()
    out: list[str] = []
    for item in ordered:
        if not item:
            continue
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def sync_master(tasks_json_path: Path, paths: OverlayPaths) -> tuple[dict[str, Any], FileSyncResult]:
    payload = _load_json(tasks_json_path)
    master = payload.get("master")
    if not isinstance(master, dict):
        raise ValueError("tasks.json missing top-level 'master' object.")
    tasks = master.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("tasks.json missing 'master.tasks' list.")

    changed_ids: list[str] = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("id", "")).strip()
        expected = paths.index
        current = str(task.get("overlay", "")).strip()
        if current != expected:
            task["overlay"] = expected
            changed_ids.append(task_id or "?")

    return payload, FileSyncResult(
        file=str(tasks_json_path),
        total_tasks=len(tasks),
        changed_tasks=len(changed_ids),
        changed_ids=changed_ids,
    )


def sync_view(view_path: Path, paths: OverlayPaths) -> tuple[list[dict[str, Any]], FileSyncResult]:
    tasks = _load_json(view_path)
    if not isinstance(tasks, list):
        raise ValueError(f"{view_path.name} must be a JSON array.")

    changed_ids: list[str] = []
    expected = _refs_for_task(paths)
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("id", "")).strip()
        current = _normalize_refs(task.get("overlay_refs"))
        if current != expected:
            task["overlay_refs"] = expected
            changed_ids.append(task_id or str(task.get("taskmaster_id", "?")))

    return tasks, FileSyncResult(
        file=str(view_path),
        total_tasks=len(tasks),
        changed_tasks=len(changed_ids),
        changed_ids=changed_ids,
    )


def _write_summary(
    root: Path,
    dry_run: bool,
    status: str,
    reason: str | None,
    paths: OverlayPaths | None,
    results: list[FileSyncResult],
    missing: list[str],
    tasks_dir: Path,
) -> Path:
    out_dir = root / "logs" / "ci" / _today() / "task-overlays"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "sync-overlay-refs-summary.json"
    summary = {
        "action": "sync-task-overlay-refs",
        "dry_run": dry_run,
        "status": status,
        "reason": reason,
        "tasks_dir": _to_posix(str(tasks_dir.relative_to(root) if tasks_dir.is_relative_to(root) else tasks_dir)),
        "prd_id": paths.prd_id if paths else None,
        "overlay_base": paths.base if paths else None,
        "manifest": paths.manifest if paths else None,
        "missing_overlay_files": missing,
        "files": [
            {
                "file": _to_posix(item.file),
                "total_tasks": item.total_tasks,
                "changed_tasks": item.changed_tasks,
                "changed_ids": item.changed_ids,
            }
            for item in results
        ],
    }
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize Taskmaster overlay mappings (master/back/gameplay).")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Apply changes to tasks.json/tasks_back.json/tasks_gameplay.json (default is dry-run).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Explicit dry-run mode (same as default).")
    parser.add_argument(
        "--prd-id",
        type=str,
        default="",
        help="PRD id in docs/architecture/overlays/<PRD-ID>. Auto-detect if omitted.",
    )
    parser.add_argument(
        "--tasks-dir",
        type=str,
        default="",
        help="Taskmaster tasks directory. Auto-resolve .taskmaster/tasks then examples/taskmaster when omitted.",
    )
    args = parser.parse_args()

    if args.write and args.dry_run:
        raise SystemExit("Cannot use --write and --dry-run together.")

    root = _repo_root()
    tasks_dir = _resolve_tasks_dir(root, args.tasks_dir)
    tasks_json_path = tasks_dir / "tasks.json"
    tasks_back_path = tasks_dir / "tasks_back.json"
    tasks_gameplay_path = tasks_dir / "tasks_gameplay.json"

    missing_tasks = [p for p in (tasks_json_path, tasks_back_path, tasks_gameplay_path) if not p.exists()]
    if missing_tasks:
        reason = "missing-task-triplet"
        summary_path = _write_summary(
            root=root,
            dry_run=True,
            status="fail",
            reason=reason,
            paths=None,
            results=[],
            missing=[_to_posix(str(p)) for p in missing_tasks],
            tasks_dir=tasks_dir,
        )
        print(f"SYNC_TASK_OVERLAY_REFS status=fail reason={reason} summary={summary_path.as_posix()}")
        for miss in missing_tasks:
            print(f"- missing task file: {miss}")
        return 2

    try:
        prd_id = _resolve_prd_id(root, tasks_dir, args.prd_id)
        paths = _load_overlay_paths_from_manifest(root, prd_id)
    except ValueError as error:
        summary_path = _write_summary(root, True, "fail", str(error), None, [], [], tasks_dir)
        print(f"SYNC_TASK_OVERLAY_REFS status=fail reason={error} summary={summary_path.as_posix()}")
        return 2

    missing = _ensure_overlay_files_exist(root, paths)
    if missing:
        summary_path = _write_summary(root, True, "fail", "missing-overlay-files", paths, [], missing, tasks_dir)
        print(f"SYNC_TASK_OVERLAY_REFS status=fail missing={len(missing)} summary={summary_path.as_posix()}")
        for rel in missing:
            print(f"- missing overlay file: {rel}")
        return 2

    master_payload, master_result = sync_master(tasks_json_path, paths)
    back_payload, back_result = sync_view(tasks_back_path, paths)
    gameplay_payload, gameplay_result = sync_view(tasks_gameplay_path, paths)
    results = [master_result, back_result, gameplay_result]

    do_write = bool(args.write)
    if do_write:
        _write_json(tasks_json_path, master_payload)
        _write_json(tasks_back_path, back_payload)
        _write_json(tasks_gameplay_path, gameplay_payload)

    status = "ok" if do_write else "dry-run"
    summary_path = _write_summary(root, not do_write, status, None, paths, results, [], tasks_dir)
    total_changed = sum(item.changed_tasks for item in results)
    print(
        "SYNC_TASK_OVERLAY_REFS "
        f"status={status} total_changed={total_changed} summary={summary_path.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

