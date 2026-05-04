#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail fast on deterministic acceptance gaps before expensive extract runs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


RULES: list[dict[str, Any]] = [
    {
        "id": "task_specific_deterministic_tests_missing",
        "trigger_any": ["task-specific deterministic tests"],
        "require_any": ["task-specific deterministic tests"],
        "message": "Acceptance must explicitly carry task-specific deterministic tests gate language.",
    },
    {
        "id": "split_task_evidence_missing",
        "trigger_any": ["split-task evidence", "implementation is moved to tasks", "split from t"],
        "require_any": ["split-task evidence", "split tasks", "completion evidence", "closure", "not complete"],
        "message": "Split-task evidence or closure language is required when the task is split/moved.",
    },
    {
        "id": "hard_gate_negative_missing",
        "trigger_any": ["hard gate", "hard-gate", "must not advance", "refuse to advance", "not accepted if"],
        "require_any": ["must not advance", "not accepted", "not complete", "fail", "refuse to advance", "cannot advance"],
        "message": "Acceptance must encode the negative hard-gate condition, not only the success path.",
    },
    {
        "id": "registry_tests_missing",
        "trigger_any": ["registry tests"],
        "require_any": ["registry tests"],
        "message": "Acceptance must mention registry-test coverage when the task text requires it.",
    },
    {
        "id": "versioning_hooks_missing",
        "trigger_any": ["versioning hooks", "deprecation metadata"],
        "require_any": ["versioning hooks", "deprecation metadata"],
        "message": "Acceptance must mention explicit versioning/deprecation metadata when task text requires it.",
    },
    {
        "id": "validate_contracts_missing",
        "trigger_any": ["validate_contracts"],
        "require_any": ["validate_contracts"],
        "message": "Acceptance must mention validate_contracts when task text requires contract validation gates.",
    },
    {
        "id": "fixtures_missing",
        "trigger_any": ["representative fixtures", "positive and negative fixtures", "minimal valid and invalid fixtures"],
        "require_any": ["fixture", "fixtures"],
        "message": "Acceptance must explicitly mention fixture coverage when task text requires fixtures.",
    },
    {
        "id": "routing_choke_point_missing",
        "trigger_any": ["routing choke point", "choke point"],
        "require_any": ["routing choke point", "choke point"],
        "message": "Acceptance must preserve routing choke-point semantics when task text requires them.",
    },
    {
        "id": "summary_artifacts_missing",
        "trigger_any": ["summary artifacts"],
        "require_any": ["summary artifacts"],
        "message": "Acceptance must mention summary artifacts when task text requires them.",
    },
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _today() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _default_out_dir(root: Path, task_id: str) -> Path:
    return root / "logs" / "ci" / _today() / f"preflight-acceptance-extract-guard-task-{task_id}"


def _triplet_paths(root: Path) -> tuple[Path, Path, Path]:
    base = root / ".taskmaster" / "tasks"
    if not (base / "tasks.json").exists():
        base = root / "examples" / "taskmaster"
    return base / "tasks.json", base / "tasks_back.json", base / "tasks_gameplay.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_master_tasks(tasks_json: dict[str, Any]) -> list[dict[str, Any]]:
    master = tasks_json.get("master") or {}
    tasks = master.get("tasks") or tasks_json.get("tasks") or []
    return [item for item in tasks if isinstance(item, dict)] if isinstance(tasks, list) else []


def _find_master_task(tasks_json: dict[str, Any], task_id: str) -> dict[str, Any]:
    for task in _iter_master_tasks(tasks_json):
        if str(task.get("id") or "").strip() == str(task_id):
            return task
    raise KeyError(f"Task id not found in tasks.json: {task_id}")


def _find_view_task(items: list[dict[str, Any]], task_id: str) -> dict[str, Any] | None:
    try:
        task_id_int = int(str(task_id))
    except ValueError:
        return None
    for item in items:
        if isinstance(item, dict) and int(item.get("taskmaster_id") or -1) == task_id_int:
            return item
    return None


def _normalize(text: str) -> str:
    return " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split()).strip().lower()


def _contains_any(text: str, needles: list[str]) -> bool:
    hay = _normalize(text)
    return any(_normalize(needle) in hay for needle in needles if str(needle).strip())


def _collect_master_source_blocks(task: dict[str, Any]) -> list[str]:
    blocks: list[str] = []
    for key in ("title", "description", "details", "testStrategy"):
        value = task.get(key)
        if isinstance(value, list):
            blocks.extend(str(item) for item in value if str(item).strip())
        elif str(value or "").strip():
            blocks.append(str(value))
    for subtask in task.get("subtasks") or []:
        if not isinstance(subtask, dict):
            continue
        for key in ("title", "description", "details", "testStrategy"):
            value = subtask.get(key)
            if isinstance(value, list):
                blocks.extend(str(item) for item in value if str(item).strip())
            elif str(value or "").strip():
                blocks.append(str(value))
    return blocks


def _collect_acceptance_views(back: dict[str, Any] | None, gameplay: dict[str, Any] | None) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for view_name, entry in (("back", back), ("gameplay", gameplay)):
        items = entry.get("acceptance") if isinstance(entry, dict) else []
        if isinstance(items, list):
            out[view_name] = [str(item) for item in items if str(item).strip()]
        else:
            out[view_name] = []
    return out


def evaluate_task(*, task_id: str, master: dict[str, Any], back: dict[str, Any] | None, gameplay: dict[str, Any] | None) -> dict[str, Any]:
    source_blocks = _collect_master_source_blocks(master)
    source_text = "\n".join(source_blocks)
    acceptance_by_view = _collect_acceptance_views(back, gameplay)
    acceptance_items = [item for items in acceptance_by_view.values() for item in items]
    acceptance_text = "\n".join(acceptance_items)
    issues: list[dict[str, Any]] = []

    if not acceptance_items:
        issues.append(
            {
                "rule_id": "missing_acceptance",
                "severity": "hard",
                "message": "No acceptance items found in task views.",
            }
        )

    for view_name, items in acceptance_by_view.items():
        if not items:
            issues.append(
                {
                    "rule_id": "missing_acceptance_view",
                    "severity": "hard",
                    "message": f"View '{view_name}' has no acceptance items.",
                }
            )
        for idx, item in enumerate(items, start=1):
            if "refs:" not in _normalize(item):
                issues.append(
                    {
                        "rule_id": "missing_refs",
                        "severity": "hard",
                        "message": f"View '{view_name}' acceptance item {idx} is missing Refs:.",
                    }
                )

    for rule in RULES:
        if not _contains_any(source_text, list(rule.get("trigger_any") or [])):
            continue
        if _contains_any(acceptance_text, list(rule.get("require_any") or [])):
            continue
        issues.append(
            {
                "rule_id": str(rule["id"]),
                "severity": "hard",
                "message": str(rule["message"]),
            }
        )

    issue_ids = [str(item["rule_id"]) for item in issues]
    return {
        "task_id": str(task_id),
        "status": "fail" if issues else "ok",
        "issue_count": len(issues),
        "issue_ids": issue_ids,
        "issues": issues,
        "views_present": [name for name, items in acceptance_by_view.items() if items],
        "acceptance_item_counts": {name: len(items) for name, items in acceptance_by_view.items()},
        "source_block_count": len(source_blocks),
    }


def _write_markdown_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# preflight acceptance extract guard",
        "",
        f"- task_id: {payload.get('task_id')}",
        f"- status: {payload.get('status')}",
        f"- issue_count: {payload.get('issue_count')}",
        "",
    ]
    issues = payload.get("issues") or []
    if issues:
        lines.extend(["## Issues", ""])
        for issue in issues:
            lines.append(f"- {issue.get('rule_id')}: {issue.get('message')}")
    else:
        lines.append("No deterministic preflight issues found.")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail fast on deterministic acceptance gaps before extract.")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--out-dir", default="")
    args = parser.parse_args()

    root = _repo_root()
    tasks_json_path, tasks_back_path, tasks_gameplay_path = _triplet_paths(root)
    tasks_json = _load_json(tasks_json_path)
    back_items = _load_json(tasks_back_path) if tasks_back_path.exists() else []
    gameplay_items = _load_json(tasks_gameplay_path) if tasks_gameplay_path.exists() else []

    task_id = str(args.task_id)
    master = _find_master_task(tasks_json, task_id)
    back = _find_view_task(back_items, task_id) if isinstance(back_items, list) else None
    gameplay = _find_view_task(gameplay_items, task_id) if isinstance(gameplay_items, list) else None

    out_dir = Path(args.out_dir) if str(args.out_dir).strip() else _default_out_dir(root, task_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = evaluate_task(task_id=task_id, master=master, back=back, gameplay=gameplay)
    payload.update(
        {
            "cmd": "preflight-acceptance-extract-guard",
            "out_dir": str(out_dir).replace("\\", "/"),
            "tasks_json_path": str(tasks_json_path).replace("\\", "/"),
            "tasks_back_path": str(tasks_back_path).replace("\\", "/"),
            "tasks_gameplay_path": str(tasks_gameplay_path).replace("\\", "/"),
            "schema_version": "preflight-acceptance-extract-guard.v1",
        }
    )
    (out_dir / "summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_markdown_report(out_dir / "report.md", payload)
    out_label = str(out_dir).replace("\\", "/")
    print(f"SC_ACCEPTANCE_EXTRACT_PREFLIGHT status={payload['status']} out={out_label}")
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
