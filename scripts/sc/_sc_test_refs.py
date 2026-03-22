from __future__ import annotations

import json
from pathlib import Path

from _taskmaster_paths import resolve_default_task_triplet_paths
from _util import repo_root


def normalize_task_root_id(task_id: str | None) -> str | None:
    raw = str(task_id or "").strip()
    if not raw:
        return None
    return raw.split(".", 1)[0].strip()


def task_scoped_gdunit_refs(*, task_id: str | None, tests_project: Path) -> list[str]:
    task_root_id = normalize_task_root_id(task_id)
    if not task_root_id:
        return []

    refs: list[str] = []
    seen: set[str] = set()
    _tasks_json, tasks_back_path, tasks_gameplay_path = resolve_default_task_triplet_paths(repo_root())
    view_files = [tasks_back_path, tasks_gameplay_path]
    for view_path in view_files:
        if not view_path.is_file():
            continue
        try:
            data = json.loads(view_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for item in data:
            if not isinstance(item, dict):
                continue
            if str(item.get("taskmaster_id")).strip() != task_root_id:
                continue
            test_refs = item.get("test_refs")
            if not isinstance(test_refs, list):
                continue
            for raw_ref in test_refs:
                if not isinstance(raw_ref, str):
                    continue
                ref = raw_ref.replace("\\", "/").strip()
                if not ref.lower().endswith(".gd"):
                    continue
                rel: str | None = None
                if ref.startswith("Tests.Godot/"):
                    rel = ref[len("Tests.Godot/") :]
                elif ref.startswith("tests/"):
                    rel = ref
                if not rel or not (tests_project / rel).is_file() or rel in seen:
                    continue
                seen.add(rel)
                refs.append(rel)
    return refs


def task_scoped_cs_refs(*, task_id: str | None) -> list[str]:
    task_root_id = normalize_task_root_id(task_id)
    if not task_root_id:
        return []

    refs: list[str] = []
    seen: set[str] = set()
    _tasks_json, tasks_back_path, tasks_gameplay_path = resolve_default_task_triplet_paths(repo_root())
    view_files = [tasks_back_path, tasks_gameplay_path]
    for view_path in view_files:
        if not view_path.is_file():
            continue
        try:
            data = json.loads(view_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for item in data:
            if not isinstance(item, dict):
                continue
            if str(item.get("taskmaster_id")).strip() != task_root_id:
                continue
            test_refs = item.get("test_refs")
            if not isinstance(test_refs, list):
                continue
            for raw_ref in test_refs:
                if not isinstance(raw_ref, str):
                    continue
                ref = raw_ref.replace("\\", "/").strip()
                if not ref.lower().endswith(".cs"):
                    continue
                if not ref.startswith("Game.Core.Tests/"):
                    continue
                if not (repo_root() / ref).is_file() or ref in seen:
                    continue
                seen.add(ref)
                refs.append(ref)
    return refs


def build_dotnet_filter_from_cs_refs(cs_refs: list[str]) -> str:
    clauses: list[str] = []
    seen: set[str] = set()
    for ref in cs_refs:
        stem = Path(ref).stem.strip()
        if not stem:
            continue
        clause = f"FullyQualifiedName~{stem}"
        if clause in seen:
            continue
        seen.add(clause)
        clauses.append(clause)
    return "|".join(clauses)
