#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

from _artifact_schema import ArtifactSchemaError, validate_pipeline_latest_index_payload

HEX_FALLBACK = "n/a (git head unavailable from current repository state)"
BRANCH_FALLBACK = "n/a (git branch unavailable from current repository state)"


@dataclass(frozen=True)
class RecoveryLinks:
    task_ids: str
    run_id: str
    latest_json: str
    pipeline_artifacts: str
    recovery_command: str


def repo_root() -> Path:
    return REPO_ROOT


def iso_today() -> str:
    return date.today().isoformat()


def slugify_title(title: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", str(title or "").strip().lower())
    base = re.sub(r"-{2,}", "-", base).strip("-")
    return base or "untitled"


def _git_capture(root: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
        )
    except OSError:
        return ""
    if proc.returncode != 0:
        return ""
    return str(proc.stdout or "").strip()


def resolve_git_branch(root: Path) -> str:
    branch = _git_capture(root, "branch", "--show-current")
    return branch or BRANCH_FALLBACK


def resolve_git_head(root: Path) -> str:
    head = _git_capture(root, "rev-parse", "HEAD")
    return head or HEX_FALLBACK


def format_repo_path(root: Path, path: Path | None) -> str:
    if path is None:
        return ""
    try:
        rel = path.resolve().relative_to(root.resolve())
        return rel.as_posix()
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def format_path_list(root: Path, values: Sequence[str | Path]) -> str:
    rendered: list[str] = []
    for item in values:
        if isinstance(item, Path):
            value = format_repo_path(root, item)
        else:
            value = str(item or "").strip().replace("\\", "/")
        if value:
            rendered.append(f"`{value}`")
    return ", ".join(rendered) if rendered else "none yet"


def _load_latest_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    try:
        validate_pipeline_latest_index_payload(payload)
    except ArtifactSchemaError:
        return {}
    return payload


def newest_latest_json(root: Path, task_id: str) -> Path | None:
    task = str(task_id or "").strip()
    if not task:
        return None
    candidates = sorted(
        (root / "logs" / "ci").glob(f"*/sc-review-pipeline-task-{task}/latest.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def infer_recovery_links(
    *,
    root: Path,
    task_id: str = "",
    run_id: str = "",
    latest_json: str = "",
) -> RecoveryLinks:
    task = str(task_id or "").strip()
    latest_path: Path | None = None
    if str(latest_json or "").strip():
        candidate = Path(str(latest_json).strip())
        latest_path = candidate if candidate.is_absolute() else root / candidate
        if not latest_path.exists():
            latest_path = None
    if latest_path is None and task:
        latest_path = newest_latest_json(root, task)

    payload = _load_latest_json(latest_path) if latest_path is not None else {}
    resolved_task = task or str(payload.get("task_id") or "").strip()
    resolved_run = str(run_id or payload.get("run_id") or "").strip()
    latest_field = (
        f"`{format_repo_path(root, latest_path)}`"
        if latest_path is not None and latest_path.exists()
        else "n/a (no task-scoped latest.json pointer resolved yet)"
    )

    pipeline_dir: Path | None = None
    latest_out_dir = str(payload.get("latest_out_dir") or "").strip()
    if latest_out_dir:
        candidate = Path(latest_out_dir)
        pipeline_dir = candidate if candidate.is_absolute() else root / candidate
        if not pipeline_dir.exists():
            pipeline_dir = None
    if pipeline_dir is None and resolved_task and resolved_run:
        matches = sorted(
            (root / "logs" / "ci").glob(f"*/sc-review-pipeline-task-{resolved_task}-{resolved_run}"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        pipeline_dir = matches[0] if matches else None

    task_field = f"`{resolved_task}`" if resolved_task else "n/a (no Taskmaster task id linked yet)"
    run_field = f"`{resolved_run}`" if resolved_run else "n/a (no pipeline run id linked yet)"
    artifacts_field = (
        f"`{format_repo_path(root, pipeline_dir)}`"
        if pipeline_dir is not None and pipeline_dir.exists()
        else "n/a (no pipeline artifact directory resolved yet)"
    )
    recovery_command = (
        f"`py -3 scripts/sc/run_review_pipeline.py --task-id {resolved_task} --resume`"
        if resolved_task
        else "n/a (no task-scoped recovery command recorded yet)"
    )
    return RecoveryLinks(
        task_ids=task_field,
        run_id=run_field,
        latest_json=latest_field,
        pipeline_artifacts=artifacts_field,
        recovery_command=recovery_command,
    )


def unique_output_path(base_path: Path) -> Path:
    if not base_path.exists():
        return base_path
    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent
    counter = 2
    while True:
        candidate = parent / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def ensure_output_path(root: Path, path_value: str | None, default_dir: str, title: str) -> Path:
    if str(path_value or "").strip():
        candidate = Path(str(path_value).strip())
        path = candidate if candidate.is_absolute() else root / candidate
    else:
        path = root / default_dir / f"{iso_today()}-{slugify_title(title)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    return unique_output_path(path)


def _render_fields(pairs: Sequence[tuple[str, str]]) -> str:
    lines = []
    for key, value in pairs:
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


def build_execution_plan_markdown(
    *,
    root: Path,
    title: str,
    status: str,
    goal: str,
    scope: str,
    current_step: str,
    stop_loss: str,
    next_action: str,
    exit_criteria: str,
    related_adrs: Sequence[str],
    related_decision_logs: Sequence[str],
    links: RecoveryLinks,
    branch: str,
    git_head: str,
) -> str:
    body = _render_fields(
        [
            ("Title", title),
            ("Status", status),
            ("Branch", branch),
            ("Git Head", git_head),
            ("Goal", goal),
            ("Scope", scope),
            ("Current step", current_step),
            ("Last completed step", "n/a (new execution plan scaffold; no completed step recorded yet)"),
            ("Stop-loss", stop_loss),
            ("Next action", next_action),
            ("Recovery command", links.recovery_command),
            ("Open questions", "none recorded yet"),
            ("Exit criteria", exit_criteria),
            ("Related ADRs", format_path_list(root, list(related_adrs)) if related_adrs else "none yet"),
            ("Related decision logs", format_path_list(root, list(related_decision_logs)) if related_decision_logs else "none yet"),
            ("Related task id(s)", links.task_ids),
            ("Related run id", links.run_id),
            ("Related latest.json", links.latest_json),
            ("Related pipeline artifacts", links.pipeline_artifacts),
        ]
    )
    return f"# {title}\n\n{body}"


def build_decision_log_markdown(
    *,
    root: Path,
    title: str,
    status: str,
    why_now: str,
    context: str,
    decision: str,
    consequences: str,
    recovery_impact: str,
    validation: str,
    supersedes: str,
    superseded_by: str,
    related_adrs: Sequence[str],
    related_execution_plans: Sequence[str],
    links: RecoveryLinks,
    branch: str,
    git_head: str,
) -> str:
    body = _render_fields(
        [
            ("Title", title),
            ("Date", iso_today()),
            ("Status", status),
            ("Supersedes", supersedes),
            ("Superseded by", superseded_by),
            ("Branch", branch),
            ("Git Head", git_head),
            ("Why now", why_now),
            ("Context", context),
            ("Decision", decision),
            ("Consequences", consequences),
            ("Recovery impact", recovery_impact),
            ("Validation", validation),
            ("Related ADRs", format_path_list(root, list(related_adrs)) if related_adrs else "none yet"),
            ("Related execution plans", format_path_list(root, list(related_execution_plans)) if related_execution_plans else "none yet"),
            ("Related task id(s)", links.task_ids),
            ("Related run id", links.run_id),
            ("Related latest.json", links.latest_json),
            ("Related pipeline artifacts", links.pipeline_artifacts),
        ]
    )
    return f"# {title}\n\n{body}"


def write_markdown(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8", newline="\n")
    return path


def record_chapter6_residual_followup(
    *,
    root: Path,
    task_id: str,
    run_id: str,
    latest_json: str,
    findings_summary: str,
    recommended_command: str,
    related_adrs: Sequence[str] | None = None,
) -> dict[str, str]:
    links = infer_recovery_links(root=root, task_id=task_id, run_id=run_id, latest_json=latest_json)
    branch = resolve_git_branch(root)
    git_head = resolve_git_head(root)

    decision_title = f"task-{task_id}-chapter6-residual-needs-fix"
    decision_path = ensure_output_path(root, "", "decision-logs", decision_title)
    decision_content = build_decision_log_markdown(
        root=root,
        title=decision_title,
        status="accepted",
        why_now="Chapter 6 routing determined that another immediate 6.8 rerun would not be cost-effective.",
        context=f"Remaining findings are low priority reviewer items after deterministic evidence was already sufficient. {findings_summary}",
        decision="Record the residual Needs Fix items and stop the current fast-ship closure loop until a later change hits the same reviewer anchors.",
        consequences="The task keeps explicit follow-up evidence instead of paying for another same-shape 6.8 rerun.",
        recovery_impact="Recovery should prefer the recorded follow-up plan over reopening 6.7 or repeating 6.8 without fresh anchor hits.",
        validation=recommended_command or "Re-run chapter6-route after new anchor-hitting changes land.",
        supersedes="none",
        superseded_by="none",
        related_adrs=list(related_adrs or []),
        related_execution_plans=[],
        links=links,
        branch=branch,
        git_head=git_head,
    )
    write_markdown(decision_path, decision_content)

    plan_title = f"task-{task_id}-chapter6-residual-followup"
    plan_path = ensure_output_path(root, "", "execution-plans", plan_title)
    plan_content = build_execution_plan_markdown(
        root=root,
        title=plan_title,
        status="active",
        goal=f"Close the recorded residual reviewer findings for Task {task_id}.",
        scope=findings_summary,
        current_step="Residual Needs Fix recorded; wait for a change that hits the previous reviewer anchors before paying for another 6.8.",
        stop_loss="Do not reopen 6.7 without a fresh deterministic failure. Do not rerun 6.8 when current edits do not hit the recorded reviewer anchors.",
        next_action=recommended_command or "Re-run chapter6-route after fresh anchor-hitting edits.",
        exit_criteria="Either the recorded findings are cleared by a targeted 6.8 pass, or a later run supersedes this residual record.",
        related_adrs=list(related_adrs or []),
        related_decision_logs=[decision_path.relative_to(root).as_posix()],
        links=links,
        branch=branch,
        git_head=git_head,
    )
    write_markdown(plan_path, plan_content)

    return {
        "decision_log_path": decision_path.relative_to(root).as_posix(),
        "execution_plan_path": plan_path.relative_to(root).as_posix(),
    }


def add_common_recovery_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--task-id", default="", help="Optional Taskmaster task id.")
    parser.add_argument("--run-id", default="", help="Optional pipeline run id.")
    parser.add_argument("--latest-json", default="", help="Optional path to an existing latest.json pointer.")
    parser.add_argument("--output", default="", help="Optional output markdown path.")
