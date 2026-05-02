#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from _chapter7_profile import (
    default_story_ids,
    layer_for_bucket,
    load_chapter7_profile,
    owner_for_prefix,
    priority_for_bucket,
    source_label_for_prefix,
    task_creation_config,
    view_id_for_prefix,
    view_priority_for_bucket,
)


TASKS_JSON = Path(".taskmaster/tasks/tasks.json")
TASKS_BACK = Path(".taskmaster/tasks/tasks_back.json")
TASKS_GAMEPLAY = Path(".taskmaster/tasks/tasks_gameplay.json")
UI_CANDIDATES = Path("docs/gdd/ui-gdd-flow.candidates.json")
DEFAULT_OVERLAY_ROOT = Path("docs/architecture/overlays")
DEFAULT_CHAPTER7_PROFILE_PATH = Path("docs/workflows/chapter7-profile.json")
DEFAULT_STORY_ID_BACK = ""
DEFAULT_STORY_ID_GAMEPLAY = ""
DEFAULT_REPO_LABEL = ""


def _resolve_path(value: str | Path) -> Path:
    return value if isinstance(value, Path) else Path(value)


def _normalize_rel_path(path: Path) -> str:
    return path.as_posix().lstrip('./')


def _resolve_repo_path(repo_root: Path, value: Path) -> Path:
    return value if value.is_absolute() else (repo_root / value)


def _repo_relative_path(repo_root: Path, path: Path) -> str:
    try:
        return _normalize_rel_path(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return _normalize_rel_path(path)


def _resolve_overlay_dir(repo_root: Path, overlay_root: Path) -> Path:
    resolved = _resolve_repo_path(repo_root, overlay_root)
    if resolved.name == "08" and (resolved / "overlay-manifest.json").exists():
        return resolved
    manifests = sorted(resolved.glob("*/08/overlay-manifest.json"))
    if manifests:
        return manifests[0].parent
    return resolved


def _overlay_refs_from_root(repo_root: Path, overlay_root: Path) -> list[str]:
    manifest = overlay_root / "overlay-manifest.json"
    if manifest.exists():
        payload = _read_json(manifest)
        files = payload.get("files", {}) if isinstance(payload, dict) else {}
        refs = [
            overlay_root / value
            for value in files.values()
            if isinstance(value, str) and value.strip()
        ]
        return [_repo_relative_path(repo_root, item) for item in refs]
    refs = [overlay_root / "_index.md", overlay_root / "ACCEPTANCE_CHECKLIST.md"]
    return [_repo_relative_path(repo_root, item) for item in refs]


def _overlay_index_from_root(repo_root: Path, overlay_root: Path) -> str:
    return _repo_relative_path(repo_root, overlay_root / '_index.md')


def _repo_label_from_tasks_json(tasks_json_path: Path) -> str:
    stem = tasks_json_path.stem.lower()
    if stem == 'tasks':
        return 'taskmaster'
    return stem.replace('_', '-').replace('.', '-') or DEFAULT_REPO_LABEL


def _today() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _load_master_tasks(repo_root: Path, tasks_json_path: Path) -> list[dict[str, Any]]:
    payload = _read_json(_resolve_repo_path(repo_root, tasks_json_path))
    tasks = payload.get("master", {}).get("tasks", []) if isinstance(payload, dict) else []
    if not isinstance(tasks, list):
        raise ValueError("tasks.json master.tasks must be a list")
    return tasks


def _load_view_tasks(repo_root: Path, rel: Path) -> list[dict[str, Any]]:
    payload = _read_json(_resolve_repo_path(repo_root, rel))
    if not isinstance(payload, list):
        raise ValueError(f"{rel} must be a list")
    return payload


def _max_master_id(master_tasks: list[dict[str, Any]]) -> int:
    values = [int(item.get("id", 0)) for item in master_tasks if isinstance(item.get("id"), int)]
    return max(values or [0])


def _existing_chapter7_task_ids(master_tasks: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in master_tasks:
        if not isinstance(item, dict):
            continue
        details = str(item.get("details") or "")
        title = str(item.get("title") or "")
        marker = "Chapter7 Candidate:"
        if marker in details:
            candidate = details.split(marker, 1)[1].splitlines()[0].strip()
            if candidate and isinstance(item.get("id"), int):
                result[candidate] = int(item["id"])
        elif title.startswith("Wire UI: ") and isinstance(item.get("id"), int):
            result[title.removeprefix("Wire UI: ").strip()] = int(item["id"])
    return result


def _priority_for_bucket(bucket: str) -> str:
    raise RuntimeError("use priority_for_bucket(profile, bucket)")


def _view_priority(master_priority: str) -> str:
    raise RuntimeError("use view_priority_for_bucket(profile, bucket)")


def _layer_for_bucket(bucket: str) -> str:
    raise RuntimeError("use layer_for_bucket(profile, bucket)")


def _merge_refs(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in values:
        value = str(item).strip()
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _acceptance(candidate: dict[str, Any], test_refs: list[str]) -> list[str]:
    refs = " ".join(test_refs) if test_refs else "docs/gdd/ui-gdd-flow.md"
    screen_group = str(candidate.get("screen_group") or "Chapter 7 UI slice")
    ui_entry = str(candidate.get("ui_entry") or "UI surface")
    player_action = str(candidate.get("player_action") or "the player action").strip()
    system_response = str(candidate.get("system_response") or "the expected system response").strip()
    empty_state = str(candidate.get("empty_state") or "the documented empty state").strip()
    failure_state = str(candidate.get("failure_state") or "the documented failure state").strip()
    completion_result = str(candidate.get("completion_result") or "the documented completion result").strip()
    artifact_targets = _merge_refs(list(candidate.get("validation_artifact_targets") or []))
    requirement_ids = _merge_refs(list(candidate.get("requirement_ids") or []))
    scope_ids = [int(item) for item in candidate.get("scope_task_ids") or [] if isinstance(item, int)]
    scope_refs = str(candidate.get("scope_task_refs") or ", ".join(f"T{item:02d}" for item in scope_ids)).strip()
    has_xunit = any(ref.startswith("Game.Core.Tests/") for ref in test_refs)
    has_gdunit = any(ref.startswith("Tests.Godot/") for ref in test_refs)
    framework_clause = "applicable GdUnit and xUnit evidence"
    if has_xunit and has_gdunit:
        framework_clause = "both referenced GdUnit and xUnit suites"
    elif has_xunit:
        framework_clause = "the referenced xUnit suite and an explicit GdUnit N/A record when no GdUnit case applies"
    elif has_gdunit:
        framework_clause = "the referenced GdUnit suite and an explicit xUnit N/A record when no xUnit case applies"
    artifact_clause = (
        f" and must produce validation evidence at {', '.join(artifact_targets)}"
        if artifact_targets
        else ""
    )
    acceptance = [
        f"{screen_group} is implemented as a concrete Chapter 7 UI wiring slice using {ui_entry}, and the player action is visible end-to-end: {player_action}. Refs: {refs}",
        f"{screen_group} selects or creates the suggested standalone surfaces from docs/gdd/ui-gdd-flow.candidates.json before implementation is accepted. Refs: {refs}",
        f"{screen_group} renders the candidate system response from runtime events: {system_response}. Refs: {refs}",
        f"{screen_group} exposes the candidate empty-state rules without relying on logs-only evidence: {empty_state}. Refs: {refs}",
        f"{screen_group} exposes the candidate failure-state rules without relying on logs-only evidence: {failure_state}. Refs: {refs}",
        f"{screen_group} satisfies the completion result, keeps deterministic domain state behind existing contracts, adds no unrelated gameplay behavior{artifact_clause}: {completion_result}. Refs: {refs}",
    ]
    failure_lower = failure_state.lower()
    if "paused or stopped" in failure_lower and "state remains unchanged" not in failure_lower:
        acceptance.append(
            f"{screen_group} must assert that when _Process/_PhysicsProcess updates are paused or stopped, cycle progression does not advance and runtime phase/timer state remains unchanged. Refs: {refs}"
        )
    if requirement_ids:
        acceptance.append(
            f"{screen_group} acceptance must explicitly map every listed Requirement ID ({', '.join(requirement_ids)}) to concrete behavior, test evidence, or artifact evidence; missing any Requirement ID mapping fails acceptance. Refs: {refs}"
        )
    if scope_refs:
        acceptance.append(
            f"{screen_group} acceptance must explicitly map implementation and verification evidence to each scope item ({scope_refs}); missing any scope mapping fails acceptance, and out-of-scope gameplay changes do not count toward completion. Refs: {refs}"
        )
    acceptance.append(
        f"{screen_group} validation must include {framework_clause}, and Chapter 7 artifact evidence must record auditable pass/fail outcomes for each framework; when one framework has no applicable case, acceptance must explicitly record that framework as N/A with rationale instead of omitting it. Refs: {refs}"
    )
    return acceptance


def _master_task(task_id: int, candidate: dict[str, Any], *, ui_candidates_path: Path, overlay_index: str, profile: dict[str, Any]) -> dict[str, Any]:
    screen_group = str(candidate.get("screen_group") or f"Chapter 7 Slice {task_id}")
    bucket = str(candidate.get("bucket") or "ui")
    test_refs = _merge_refs(list(candidate.get("test_refs") or []))
    requirement_ids = _merge_refs(list(candidate.get("requirement_ids") or []))
    artifact_targets = _merge_refs(list(candidate.get("validation_artifact_targets") or []))
    standalone_surfaces = _merge_refs(list(candidate.get("suggested_standalone_surfaces") or []))
    scope_ids = [int(item) for item in candidate.get("scope_task_ids") or [] if isinstance(item, int)]
    contract_boundary = str(candidate.get("contract_boundary") or "keeps deterministic domain state behind existing contracts, adds no unrelated gameplay behavior").strip()
    priority = priority_for_bucket(profile, bucket)
    details = "\n".join(
        [
            f"Chapter7 Candidate: {screen_group}",
            f"Source: {_normalize_rel_path(ui_candidates_path)}",
            f"Scope: {candidate.get('scope_task_refs') or ', '.join(f'T{item:02d}' for item in scope_ids)}",
            f"UI entry: {candidate.get('ui_entry') or 'TBD'}",
            f"Candidate type: {candidate.get('candidate_type') or 'task-shaped UI wiring spec'}",
            f"Suggested standalone surfaces: {', '.join(standalone_surfaces) if standalone_surfaces else 'n/a'}",
            f"Player action: {candidate.get('player_action') or 'TBD'}",
            f"System response: {candidate.get('system_response') or 'TBD'}",
            f"Empty state: {candidate.get('empty_state') or 'TBD'}",
            f"Failure state: {candidate.get('failure_state') or 'TBD'}",
            f"Completion result: {candidate.get('completion_result') or 'TBD'}",
            f"Contract boundary: {contract_boundary}",
            f"Requirement IDs: {', '.join(requirement_ids) if requirement_ids else 'n/a'}",
            f"Validation artifact targets: {', '.join(artifact_targets) if artifact_targets else 'n/a'}",
        ]
    )
    return {
        "id": task_id,
        "title": f"Wire UI: {screen_group}",
        "description": f"Create the Chapter 7 UI wiring slice for {screen_group} from docs/gdd/ui-gdd-flow.candidates.json.",
        "details": details,
        "testStrategy": "Validate the UI slice with the referenced GdUnit/xUnit tests and Chapter 7 artifact evidence.",
        "priority": priority,
        "dependencies": scope_ids,
        "status": "pending",
        "subtasks": [],
        "overlay": overlay_index,
        "adrRefs": [],
        "archRefs": [],
    }


def _view_task(*, prefix: str, task_id: int, candidate: dict[str, Any], owner: str, story_id: str, source_label: str, repo_label: str, overlay_refs: list[str], ui_candidates_path: Path, profile: dict[str, Any]) -> dict[str, Any]:
    screen_group = str(candidate.get("screen_group") or f"Chapter 7 Slice {task_id}")
    bucket = str(candidate.get("bucket") or "ui")
    test_refs = _merge_refs(list(candidate.get("test_refs") or []))
    contract_refs = _merge_refs(list(candidate.get("contract_refs") or []))
    scope_ids = [int(item) for item in candidate.get("scope_task_ids") or [] if isinstance(item, int)]
    depends_on = [view_id_for_prefix(profile, prefix, item) for item in scope_ids]
    priority = view_priority_for_bucket(profile, bucket)
    creation = task_creation_config(profile)
    return {
        "id": view_id_for_prefix(profile, prefix, task_id),
        "story_id": story_id,
        "owner": owner,
        "depends_on": depends_on,
        "taskmaster_exported": prefix == "GM",
        "taskmaster_id": task_id,
        "title": f"Wire UI: {screen_group}",
        "description": f"Create the Chapter 7 UI wiring slice for {screen_group} from docs/gdd/ui-gdd-flow.candidates.json.",
        "status": "pending",
        "priority": priority,
        "layer": layer_for_bucket(profile, bucket),
        "adr_refs": list(creation.get("adr_refs") or []),
        "chapter_refs": list(creation.get("chapter_refs") or []),
        "overlay_refs": overlay_refs,
        "labels": [source_label, repo_label, *(list(creation.get("base_labels") or [])), bucket],
        "test_refs": test_refs,
        "acceptance": _acceptance(candidate, test_refs),
        "contractRefs": contract_refs,
        "ui_wiring_candidate": {
            "source": _normalize_rel_path(ui_candidates_path),
            "screen_group": screen_group,
            "scope_task_ids": scope_ids,
            "ui_entry": candidate.get("ui_entry") or "",
        },
    }


def _replace_task_by_id(tasks: list[dict[str, Any]], task_id: int, replacement: dict[str, Any]) -> bool:
    for index, item in enumerate(tasks):
        if isinstance(item, dict) and item.get("id") == task_id:
            current_status = item.get("status")
            if current_status:
                replacement["status"] = current_status
            tasks[index] = replacement
            return True
    return False


def _replace_view_task_by_taskmaster_id(
    tasks: list[dict[str, Any]],
    task_id: int,
    replacement: dict[str, Any],
) -> bool:
    for index, item in enumerate(tasks):
        if isinstance(item, dict) and item.get("taskmaster_id") == task_id:
            current_status = item.get("status")
            if current_status:
                replacement["status"] = current_status
            tasks[index] = replacement
            return True
    return False


def create_tasks(
    *,
    repo_root: Path,
    dry_run: bool = False,
    tasks_json_path: Path = TASKS_JSON,
    tasks_back_path: Path = TASKS_BACK,
    tasks_gameplay_path: Path = TASKS_GAMEPLAY,
    ui_candidates_path: Path = UI_CANDIDATES,
    overlay_root_path: Path = DEFAULT_OVERLAY_ROOT,
    chapter7_profile_path: Path | None = None,
    repo_label: str = DEFAULT_REPO_LABEL,
    back_story_id: str = DEFAULT_STORY_ID_BACK,
    gameplay_story_id: str = DEFAULT_STORY_ID_GAMEPLAY,
) -> tuple[int, dict[str, Any]]:
    tasks_json_path = _resolve_path(tasks_json_path)
    tasks_back_path = _resolve_path(tasks_back_path)
    tasks_gameplay_path = _resolve_path(tasks_gameplay_path)
    ui_candidates_path = _resolve_path(ui_candidates_path)
    overlay_root_path = _resolve_path(overlay_root_path)
    chapter7_profile_path = _resolve_path(chapter7_profile_path) if chapter7_profile_path else None
    sidecar_path = ui_candidates_path if ui_candidates_path.is_absolute() else (repo_root / ui_candidates_path)
    overlay_root = _resolve_overlay_dir(repo_root, overlay_root_path)
    overlay_refs = _overlay_refs_from_root(repo_root, overlay_root)
    overlay_index = _overlay_index_from_root(repo_root, overlay_root)
    profile = load_chapter7_profile(repo_root=repo_root, profile_path=chapter7_profile_path)
    creation = task_creation_config(profile)
    effective_repo_label = (repo_label or '').strip() or _repo_label_from_tasks_json(tasks_json_path)
    effective_back_story_id = (back_story_id or '').strip()
    effective_gameplay_story_id = (gameplay_story_id or '').strip()
    if not effective_back_story_id or not effective_gameplay_story_id:
        inferred_back_story_id, inferred_gameplay_story_id = default_story_ids(profile, effective_repo_label)
        if not effective_back_story_id:
            effective_back_story_id = inferred_back_story_id
        if not effective_gameplay_story_id:
            effective_gameplay_story_id = inferred_gameplay_story_id
    if not sidecar_path.exists():
        payload = {
            "action": "create-chapter7-tasks-from-ui-candidates",
            "status": "fail",
            "reason": "missing_candidate_sidecar",
            "source": _normalize_rel_path(ui_candidates_path),
        }
        return 1, payload

    sidecar = _read_json(sidecar_path)
    candidates = sidecar.get("candidates", []) if isinstance(sidecar, dict) else []
    if not isinstance(candidates, list):
        raise ValueError("ui-gdd-flow.candidates.json candidates must be a list")

    resolved_tasks_json_path = tasks_json_path if tasks_json_path.is_absolute() else (repo_root / tasks_json_path)
    tasks_payload = _read_json(resolved_tasks_json_path)
    master = tasks_payload.setdefault("master", {})
    master_tasks = master.setdefault("tasks", [])
    if not isinstance(master_tasks, list):
        raise ValueError("tasks.json master.tasks must be a list")

    back_tasks = _load_view_tasks(repo_root, tasks_back_path)
    gameplay_tasks = _load_view_tasks(repo_root, tasks_gameplay_path)
    existing_by_candidate = _existing_chapter7_task_ids(master_tasks)
    next_id = _max_master_id(master_tasks) + 1
    created_task_ids: list[int] = []
    existing_task_ids: list[int] = []
    updated_task_ids: list[int] = []

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        screen_group = str(candidate.get("screen_group") or "").strip()
        if not screen_group:
            continue
        existing_id = existing_by_candidate.get(screen_group)
        if existing_id is not None:
            existing_task_ids.append(existing_id)
            master_task = _master_task(existing_id, candidate, ui_candidates_path=ui_candidates_path, overlay_index=overlay_index, profile=profile)
            master_task["adrRefs"] = list(creation.get("adr_refs") or [])
            master_task["archRefs"] = list(creation.get("chapter_refs") or [])
            master_task["priority"] = priority_for_bucket(profile, str(candidate.get("bucket") or "ui"))
            _replace_task_by_id(master_tasks, existing_id, master_task)
            _replace_view_task_by_taskmaster_id(
                back_tasks,
                existing_id,
                _view_task(
                    prefix="NG",
                    task_id=existing_id,
                    candidate=candidate,
                    owner=owner_for_prefix(profile, "NG"),
                    story_id=effective_back_story_id,
                    source_label=source_label_for_prefix(profile, "NG"),
                    repo_label=effective_repo_label,
                    overlay_refs=overlay_refs,
                    ui_candidates_path=ui_candidates_path,
                    profile=profile,
                ),
            )
            _replace_view_task_by_taskmaster_id(
                gameplay_tasks,
                existing_id,
                _view_task(
                    prefix="GM",
                    task_id=existing_id,
                    candidate=candidate,
                    owner=owner_for_prefix(profile, "GM"),
                    story_id=effective_gameplay_story_id,
                    source_label=source_label_for_prefix(profile, "GM"),
                    repo_label=effective_repo_label,
                    overlay_refs=overlay_refs,
                    ui_candidates_path=ui_candidates_path,
                    profile=profile,
                ),
            )
            updated_task_ids.append(existing_id)
            continue
        task_id = next_id
        next_id += 1
        master_task = _master_task(task_id, candidate, ui_candidates_path=ui_candidates_path, overlay_index=overlay_index, profile=profile)
        master_task["adrRefs"] = list(creation.get("adr_refs") or [])
        master_task["archRefs"] = list(creation.get("chapter_refs") or [])
        master_task["priority"] = priority_for_bucket(profile, str(candidate.get("bucket") or "ui"))
        master_tasks.append(master_task)
        back_tasks.append(
            _view_task(
                prefix="NG",
                task_id=task_id,
                candidate=candidate,
                owner=owner_for_prefix(profile, "NG"),
                story_id=effective_back_story_id,
                source_label=source_label_for_prefix(profile, "NG"),
                repo_label=effective_repo_label,
                overlay_refs=overlay_refs,
                ui_candidates_path=ui_candidates_path,
                profile=profile,
            )
        )
        gameplay_tasks.append(
            _view_task(
                prefix="GM",
                task_id=task_id,
                candidate=candidate,
                owner=owner_for_prefix(profile, "GM"),
                story_id=effective_gameplay_story_id,
                source_label=source_label_for_prefix(profile, "GM"),
                repo_label=effective_repo_label,
                overlay_refs=overlay_refs,
                ui_candidates_path=ui_candidates_path,
                profile=profile,
            )
        )
        created_task_ids.append(task_id)
        existing_by_candidate[screen_group] = task_id

    payload = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "action": "create-chapter7-tasks-from-ui-candidates",
        "status": "ok",
        "source": _normalize_rel_path(ui_candidates_path),
        "dry_run": dry_run,
        "candidate_count": len(candidates),
        "created_count": len(created_task_ids),
        "created_task_ids": created_task_ids,
        "existing_task_ids": existing_task_ids,
        "updated_count": len(updated_task_ids),
        "updated_task_ids": updated_task_ids,
        "tasks_json": _normalize_rel_path(tasks_json_path),
        "tasks_back": _normalize_rel_path(tasks_back_path),
        "tasks_gameplay": _normalize_rel_path(tasks_gameplay_path),
        "overlay_root": _normalize_rel_path(overlay_root_path),
        "resolved_overlay_root": _normalize_rel_path(overlay_root),
        "chapter7_profile_path": profile.get("_loaded_profile_path") or "",
        "repo_label": effective_repo_label,
        "back_story_id": effective_back_story_id,
        "gameplay_story_id": effective_gameplay_story_id,
    }
    if not dry_run:
        _write_json(resolved_tasks_json_path, tasks_payload)
        _write_json(tasks_back_path if tasks_back_path.is_absolute() else (repo_root / tasks_back_path), back_tasks)
        _write_json(tasks_gameplay_path if tasks_gameplay_path.is_absolute() else (repo_root / tasks_gameplay_path), gameplay_tasks)
    return 0, payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create Taskmaster triplet tasks from Chapter 7 UI GDD candidates.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--tasks-json-path", default=str(TASKS_JSON))
    parser.add_argument("--tasks-back-path", default=str(TASKS_BACK))
    parser.add_argument("--tasks-gameplay-path", default=str(TASKS_GAMEPLAY))
    parser.add_argument("--ui-candidates-path", default=str(UI_CANDIDATES))
    parser.add_argument("--overlay-root-path", default=str(DEFAULT_OVERLAY_ROOT))
    parser.add_argument("--chapter7-profile-path", default="")
    parser.add_argument("--repo-label", default="")
    parser.add_argument("--back-story-id", default="")
    parser.add_argument("--gameplay-story-id", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out-json", default="")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    rc, payload = create_tasks(
        repo_root=repo_root,
        dry_run=bool(args.dry_run),
        tasks_json_path=Path(args.tasks_json_path),
        tasks_back_path=Path(args.tasks_back_path),
        tasks_gameplay_path=Path(args.tasks_gameplay_path),
        ui_candidates_path=Path(args.ui_candidates_path),
        overlay_root_path=Path(args.overlay_root_path),
        chapter7_profile_path=Path(args.chapter7_profile_path) if args.chapter7_profile_path else None,
        repo_label=args.repo_label,
        back_story_id=args.back_story_id,
        gameplay_story_id=args.gameplay_story_id,
    )
    out = Path(args.out_json) if args.out_json else (
        repo_root / "logs" / "ci" / _today() / "chapter7-ui-task-creation" / "summary.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(
        "CHAPTER7_CREATE_TASKS "
        f"status={payload['status']} created={payload.get('created_count', 0)} out={str(out).replace('\\\\', '/')}"
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
