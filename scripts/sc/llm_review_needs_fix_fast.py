#!/usr/bin/env python3
"""
Fast, bounded workflow to clear llm_review "Needs Fix" with stop-loss.

Windows usage example:
  py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 1
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from _delivery_profile import (
    default_security_profile_for_delivery,
    known_delivery_profiles,
    profile_needs_fix_fast_defaults,
    resolve_delivery_profile,
)
from _llm_review_cli import resolve_agents as resolve_llm_review_agents
from _llm_backend import KNOWN_LLM_BACKENDS, resolve_llm_backend
from _change_scope import classify_change_scope_between_snapshots
from _risk_profile_floor import derive_delivery_profile_floor, requires_security_auditor_for_change_scope
from _util import ci_dir, repo_root, run_cmd, split_csv, write_json, write_text


OUT_RE = re.compile(r"\bout=([^\r\n]+)")
DELIVERY_PROFILE_CHOICES = tuple(sorted(known_delivery_profiles()))
FAST_SHIP_SMALL_DIFF_MAX_CHANGED_PATHS = 4
REVIEWER_ANCHOR_PREFIXES = (
    ".taskmaster/tasks/",
    "docs/architecture/overlays/",
    "docs/adr/",
    "game.core/",
    "game.godot/",
    "game.core.tests/",
    "tests.godot/",
    "scripts/sc/templates/llm_review/",
)
REVIEWER_ANCHOR_EXACT = {
    "workflow.md",
    "workflow.example.md",
    "scripts/sc/llm_review_needs_fix_fast.py",
    "scripts/sc/run_review_pipeline.py",
}
SEMANTIC_TARGET_PREFIXES = (
    ".taskmaster/",
    "examples/taskmaster/",
    "docs/architecture/",
    "docs/adr/",
    "docs/prd/",
    "execution-plans/",
    "decision-logs/",
)
CODE_TARGET_PREFIXES = (
    "game.core/",
    "game.godot/",
    "game.core.tests/",
    "tests.godot/",
    "scripts/sc/",
    "scripts/python/",
)
CODE_TARGET_SUFFIXES = (".cs", ".gd", ".tscn", ".tres", ".csproj", ".sln")
SECURITY_TARGET_TOKENS = ("security", "audit", "whitelist", "tamper")


def normalize_verdict(value: str | None) -> str:
    raw = (value or "").strip().lower()
    if raw in {"ok", "pass", "passed"}:
        return "OK"
    if raw in {"needs fix", "needs_fix", "need fix", "fail", "failed"}:
        return "Needs Fix"
    return "Unknown"


def resolve_configured_agents(raw_agents: str) -> list[str]:
    return [str(agent).strip() for agent in resolve_llm_review_agents(str(raw_agents or "").strip(), "warn") if str(agent).strip()]


def parse_out_dir(stdout: str) -> Path | None:
    for line in reversed(stdout.splitlines()):
        m = OUT_RE.search(line)
        if not m:
            continue
        candidate = m.group(1).strip().strip("\"'").strip()
        if candidate:
            p = Path(candidate)
            if p.exists():
                return p
    return None


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def format_agent_timeout_overrides(overrides: dict[str, int]) -> str:
    return ",".join(f"{agent}={int(seconds)}" for agent, seconds in overrides.items() if int(seconds) > 0)


def _iter_latest_pipeline_indices(task_id: str) -> list[Path]:
    logs_root = repo_root() / "logs" / "ci"
    if not logs_root.exists():
        return []
    return sorted(
        [item for item in logs_root.rglob(f"sc-review-pipeline-task-{task_id}/latest.json") if item.is_file()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )


def resolve_latest_pipeline_payload(task_id: str) -> dict[str, Any]:
    for latest_index in _iter_latest_pipeline_indices(task_id):
        payload = read_json(latest_index)
        if payload:
            return payload
    return {}


def parse_llm_verdicts(summary_path: Path) -> dict[str, str]:
    payload = read_json(summary_path)
    out: dict[str, str] = {}
    for row in payload.get("results", []):
        if not isinstance(row, dict):
            continue
        agent = str(row.get("agent") or "").strip()
        if not agent:
            continue
        details = row.get("details") if isinstance(row.get("details"), dict) else {}
        verdict = normalize_verdict(str(details.get("verdict") or ""))
        out[agent] = verdict
    return out


def _llm_summary_unknown_only(*, llm_step: dict[str, Any]) -> bool:
    summary_file = str(llm_step.get("summary_file") or "").strip()
    if not summary_file:
        rc = int(llm_step.get("rc") or 0)
        status = str(llm_step.get("status") or "").strip().lower()
        return status != "ok" or rc != 0
    summary_path = Path(summary_file)
    if not summary_path.exists():
        rc = int(llm_step.get("rc") or 0)
        status = str(llm_step.get("status") or "").strip().lower()
        return status != "ok" or rc != 0
    payload = read_json(summary_path)
    results = payload.get("results") if isinstance(payload.get("results"), list) else []
    if not results:
        return True
    saw_unknown = False
    for row in results:
        if not isinstance(row, dict):
            continue
        details = row.get("details") if isinstance(row.get("details"), dict) else {}
        verdict = normalize_verdict(str(details.get("verdict") or ""))
        if verdict == "Needs Fix":
            return False
        status = str(row.get("status") or "").strip().lower()
        rc = int(row.get("rc") or 0)
        if verdict == "Unknown" or status != "ok" or rc != 0:
            saw_unknown = True
    step_status = str(llm_step.get("status") or "").strip().lower()
    step_rc = int(llm_step.get("rc") or 0)
    return saw_unknown or step_status != "ok" or step_rc != 0


def _changed_paths_hit_reviewer_anchors(changed_paths: list[str]) -> bool:
    for raw in changed_paths:
        path = str(raw or "").strip().replace("\\", "/").lower()
        if not path:
            continue
        if path in REVIEWER_ANCHOR_EXACT:
            return True
        if any(path.startswith(prefix) for prefix in REVIEWER_ANCHOR_PREFIXES):
            return True
    return False


def current_git_fingerprint() -> dict[str, Any]:
    rc_head, out_head = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_root(), timeout_sec=30)
    rc_status, out_status = run_cmd(["git", "status", "--short"], cwd=repo_root(), timeout_sec=30)
    return {
        "head": out_head.strip() if rc_head == 0 else "",
        "status_short": sorted([line.rstrip() for line in out_status.splitlines() if line.strip()]) if rc_status == 0 else [],
    }


def _step_status(summary: dict[str, Any], step_name: str) -> str:
    step = find_pipeline_step_dict(summary, step_name)
    return str(step.get("status") or "").strip().lower()


def find_pipeline_step_dict(summary_payload: dict[str, Any], step_name: str) -> dict[str, Any]:
    for step in summary_payload.get("steps", []):
        if not isinstance(step, dict):
            continue
        if str(step.get("name") or "").strip() == step_name:
            return step
    return {}


def _git_snapshot_matches(execution_context: dict[str, Any]) -> bool:
    git_info = execution_context.get("git") if isinstance(execution_context.get("git"), dict) else {}
    previous = {
        "head": str(git_info.get("head") or "").strip(),
        "status_short": sorted([str(line).rstrip() for line in (git_info.get("status_short") or []) if str(line).strip()]),
    }
    current = current_git_fingerprint()
    return previous == current


def _resolve_latest_pipeline_files(task_id: str) -> tuple[dict[str, Any], Path | None, Path | None, Path | None]:
    latest_payload = resolve_latest_pipeline_payload(task_id)
    latest_out_dir = Path(str(latest_payload.get("latest_out_dir") or "")).resolve() if str(latest_payload.get("latest_out_dir") or "").strip() else None
    summary_file = Path(str(latest_payload.get("summary_path") or "")).resolve() if str(latest_payload.get("summary_path") or "").strip() else None
    execution_context_file = (
        Path(str(latest_payload.get("execution_context_path") or "")).resolve()
        if str(latest_payload.get("execution_context_path") or "").strip()
        else None
    )
    return latest_payload, latest_out_dir, summary_file, execution_context_file


def _ordered_agent_subset(configured_agents: list[str], candidate_agents: set[str]) -> list[str]:
    return [agent for agent in configured_agents if agent in candidate_agents]


def prefer_targeted_agents_by_change_scope(
    *,
    configured_agents: list[str],
    current_agents: list[str],
    current_source: str,
    change_scope: dict[str, Any] | None,
) -> tuple[list[str], str]:
    if str(current_source or "").strip() != "configured-defaults":
        return list(current_agents), current_source
    scope = change_scope if isinstance(change_scope, dict) else {}
    changed_paths = [str(item or "").strip().replace("\\", "/").lower() for item in list(scope.get("changed_paths") or []) if str(item or "").strip()]
    if not changed_paths:
        return list(current_agents), current_source

    candidate_agents: set[str] = set()
    if any(any(path.startswith(prefix) for prefix in SEMANTIC_TARGET_PREFIXES) for path in changed_paths):
        candidate_agents.add("semantic-equivalence-auditor")
    if any(
        any(path.startswith(prefix) for prefix in CODE_TARGET_PREFIXES)
        or path == "project.godot"
        or path.endswith(CODE_TARGET_SUFFIXES)
        for path in changed_paths
    ):
        candidate_agents.add("code-reviewer")
    if any(any(token in path for token in SECURITY_TARGET_TOKENS) for path in changed_paths) or requires_security_auditor_for_change_scope(scope):
        candidate_agents.add("security-auditor")

    targeted_agents = _ordered_agent_subset(configured_agents, candidate_agents)
    if not targeted_agents:
        return list(current_agents), current_source
    return targeted_agents, "change-scope-targeted"


def _extract_agents_from_agent_review(agent_review_payload: dict[str, Any], configured_agents: list[str]) -> list[str]:
    candidate_agents: set[str] = set()
    findings = agent_review_payload.get("findings")
    if not isinstance(findings, list):
        return []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        category = str(finding.get("category") or "").strip()
        owner_step = str(finding.get("owner_step") or "").strip()
        if category != "llm-review" and owner_step != "sc-llm-review":
            continue
        finding_id = str(finding.get("finding_id") or "").strip()
        for agent in configured_agents:
            if finding_id.startswith(f"llm-{agent}-"):
                candidate_agents.add(agent)
    return _ordered_agent_subset(configured_agents, candidate_agents)


def _extract_agents_from_llm_summary(llm_summary_payload: dict[str, Any], configured_agents: list[str]) -> list[str]:
    candidate_agents: set[str] = set()
    configured_set = set(configured_agents)
    for row in llm_summary_payload.get("results", []):
        if not isinstance(row, dict):
            continue
        agent = str(row.get("agent") or "").strip()
        if not agent or agent not in configured_set:
            continue
        details = row.get("details") if isinstance(row.get("details"), dict) else {}
        verdict = normalize_verdict(str(details.get("verdict") or ""))
        status = str(row.get("status") or "").strip().lower()
        rc = int(row.get("rc") or 0)
        if verdict != "OK" or rc != 0 or status != "ok":
            candidate_agents.add(agent)
    return _ordered_agent_subset(configured_agents, candidate_agents)


def infer_initial_run_agents(task_id: str, configured_agents: list[str]) -> tuple[list[str], str]:
    latest_payload, latest_out_dir, summary_file, _execution_context_file = _resolve_latest_pipeline_files(task_id)
    if not latest_payload or latest_out_dir is None or summary_file is None:
        return list(configured_agents), "configured-defaults"
    agent_review_path = latest_out_dir / "agent-review.json"
    if agent_review_path.exists():
        agent_review_payload = read_json(agent_review_path)
        hit_agents = _extract_agents_from_agent_review(agent_review_payload, configured_agents)
        if hit_agents:
            return hit_agents, "previous-agent-review"
    summary_payload = read_json(summary_file)
    llm_step = find_pipeline_step_dict(summary_payload, "sc-llm-review")
    llm_summary_path = Path(str(llm_step.get("summary_file") or "")).resolve() if str(llm_step.get("summary_file") or "").strip() else None
    if llm_summary_path and llm_summary_path.exists():
        hit_agents = _extract_agents_from_llm_summary(read_json(llm_summary_path), configured_agents)
        if hit_agents:
            return hit_agents, "previous-llm-summary"
    return list(configured_agents), "configured-defaults"


def prefer_precise_llm_summary_agents(
    *,
    task_id: str,
    delivery_profile: str,
    diff_mode: str,
    configured_agents: list[str],
    current_agents: list[str],
    current_source: str,
) -> tuple[list[str], str]:
    if str(delivery_profile or "").strip().lower() not in {"fast-ship", "playable-ea"}:
        return list(current_agents), current_source
    if str(diff_mode or "").strip().lower() != "summary":
        return list(current_agents), current_source
    if not current_agents:
        return list(current_agents), current_source
    _latest_payload, _latest_out_dir, summary_file, _execution_context_file = _resolve_latest_pipeline_files(task_id)
    if summary_file is None or not summary_file.exists():
        return list(current_agents), current_source
    summary_payload = read_json(summary_file)
    llm_step = find_pipeline_step_dict(summary_payload, "sc-llm-review")
    llm_summary_path = Path(str(llm_step.get("summary_file") or "")).resolve() if str(llm_step.get("summary_file") or "").strip() else None
    if llm_summary_path is None or not llm_summary_path.exists():
        return list(current_agents), current_source
    precise_agents = _extract_agents_from_llm_summary(read_json(llm_summary_path), configured_agents)
    precise_subset = [agent for agent in precise_agents if agent in set(current_agents)]
    if not precise_subset:
        return list(current_agents), current_source
    if len(precise_subset) >= len(current_agents):
        return list(current_agents), current_source
    return precise_subset, "previous-llm-summary-precise"


def try_reuse_latest_deterministic_step(
    *,
    task_id: str,
    delivery_profile: str | None = None,
    security_profile: str,
    skip_sc_test: bool,
    planned_cmd: list[str],
    out_dir: Path,
    script_start: float,
    budget_min: int,
) -> dict[str, Any] | None:
    latest_payload, latest_out_dir, summary_file, execution_context_file = _resolve_latest_pipeline_files(task_id)
    if str(latest_payload.get("status") or "").strip().lower() != "ok":
        return None
    if latest_out_dir is None or not latest_out_dir.exists():
        return None
    if summary_file is None or not summary_file.exists():
        return None
    if execution_context_file is None or not execution_context_file.exists():
        return None

    summary = read_json(summary_file)
    execution_context = read_json(execution_context_file)
    if str(summary.get("status") or "").strip().lower() != "ok":
        return None
    if delivery_profile is not None and str(execution_context.get("delivery_profile") or "").strip().lower() != str(delivery_profile).strip().lower():
        return None
    if str(execution_context.get("security_profile") or "").strip().lower() != str(security_profile).strip().lower():
        return None
    current_git = current_git_fingerprint()
    exact_git_match = _git_snapshot_matches(execution_context)
    change_scope = (
        {
            "deterministic_strategy": "reuse-latest",
            "changed_paths": [],
        }
        if exact_git_match
        else classify_change_scope_between_snapshots(
            previous_git=execution_context.get("git") if isinstance(execution_context.get("git"), dict) else {},
            current_git=current_git,
        )
    )
    if not exact_git_match and str(delivery_profile or "").strip().lower() == "standard":
        return None
    if not exact_git_match and str(change_scope.get("deterministic_strategy") or "").strip() != "reuse-latest":
        return None

    acceptance_status = _step_status(summary, "sc-acceptance-check")
    if acceptance_status != "ok":
        return None
    test_status = _step_status(summary, "sc-test")
    if skip_sc_test:
        if test_status not in {"", "ok", "skipped"}:
            return None
    elif test_status != "ok":
        return None

    remaining_before = remain_sec(script_start, budget_min)
    log_file = out_dir / "pipeline-deterministic.log"
    write_text(
        log_file,
        "\n".join(
            [
                "[needs-fix-fast] reused latest deterministic pipeline artifacts"
                if exact_git_match
                else "[needs-fix-fast] reused latest deterministic pipeline artifacts after docs-only delta",
                f"task_id={task_id}",
                f"run_id={str(latest_payload.get('run_id') or '').strip()}",
                f"summary_file={summary_file}",
                f"execution_context_file={execution_context_file}",
                f"change_scope_strategy={str(change_scope.get('deterministic_strategy') or '').strip()}",
                f"changed_paths={json.dumps(change_scope.get('changed_paths') or [], ensure_ascii=False)}",
                f"SC_REVIEW_PIPELINE status=ok out={latest_out_dir}",
            ]
        )
        + "\n",
    )
    return {
        "name": "pipeline-deterministic",
        "status": "reused",
        "rc": 0,
        "duration_sec": 0.0,
        "remaining_before_sec": int(max(0, remaining_before)),
        "remaining_after_sec": int(remain_sec(script_start, budget_min)),
        "cmd": planned_cmd,
        "log_file": str(log_file),
        "reported_out_dir": str(latest_out_dir),
        "summary_file": str(summary_file),
        "reused_run_id": str(latest_payload.get("run_id") or "").strip(),
        "reuse_reason": "latest_successful_deterministic_pipeline"
        if exact_git_match
        else "latest_successful_deterministic_pipeline_docs_only_delta",
    }


def try_skip_when_latest_pipeline_already_clean(
    *,
    task_id: str,
    delivery_profile: str,
    security_profile: str,
    out_dir: Path,
    script_start: float,
    budget_min: int,
) -> dict[str, Any] | None:
    latest_payload = resolve_latest_pipeline_payload(task_id)
    latest_out_dir = Path(str(latest_payload.get("latest_out_dir") or "").strip()) if latest_payload else None
    summary_file = Path(str(latest_payload.get("summary_path") or "").strip()) if latest_payload else None
    execution_context_file = Path(str(latest_payload.get("execution_context_path") or "").strip()) if latest_payload else None
    if not latest_out_dir or not latest_out_dir.exists() or not summary_file or not summary_file.exists() or not execution_context_file or not execution_context_file.exists():
        return None
    summary = read_json(summary_file)
    execution_context = read_json(execution_context_file)
    if not summary or not execution_context:
        return None
    if str(summary.get("status") or "").strip().lower() != "ok":
        return None
    if str(execution_context.get("delivery_profile") or "").strip().lower() != str(delivery_profile).strip().lower():
        return None
    if str(execution_context.get("security_profile") or "").strip().lower() != str(security_profile).strip().lower():
        return None
    if _step_status(summary, "sc-test") != "ok" or _step_status(summary, "sc-acceptance-check") != "ok" or _step_status(summary, "sc-llm-review") != "ok":
        return None
    llm_step = find_pipeline_step_dict(summary, "sc-llm-review")
    llm_summary_path = Path(str(llm_step.get("summary_file") or "")).resolve() if str(llm_step.get("summary_file") or "").strip() else None
    if llm_summary_path is None or not llm_summary_path.exists():
        return None
    verdicts = parse_llm_verdicts(llm_summary_path)
    if not verdicts or any(verdict != "OK" for verdict in verdicts.values()):
        return None

    agent_review = read_json(latest_out_dir / "agent-review.json")
    review_verdict = str(agent_review.get("review_verdict") or "").strip().lower()
    if review_verdict in {"needs-fix", "block"}:
        return None

    current_git = current_git_fingerprint()
    previous_git = execution_context.get("git") if isinstance(execution_context.get("git"), dict) else {}
    previous_status = sorted([str(line).rstrip() for line in (previous_git.get("status_short") or []) if str(line).strip()])
    exact_git_match = str(previous_git.get("head") or "").strip() == str(current_git.get("head") or "").strip() and previous_status == sorted(
        [str(line).rstrip() for line in (current_git.get("status_short") or []) if str(line).strip()]
    )
    change_scope = (
        {"deterministic_strategy": "reuse-latest", "changed_paths": [], "unsafe_paths": []}
        if exact_git_match
        else classify_change_scope_between_snapshots(previous_git=previous_git, current_git=current_git)
    )
    if not exact_git_match and str(change_scope.get("deterministic_strategy") or "").strip() != "reuse-latest":
        return None

    remaining_before = remain_sec(script_start, budget_min)
    log_file = out_dir / "pipeline-clean-skip.log"
    write_text(
        log_file,
        "\n".join(
            [
                "[needs-fix-fast] latest pipeline already clean; skipping rerun"
                if exact_git_match
                else "[needs-fix-fast] latest pipeline already clean after non-task doc delta; skipping rerun",
                f"task_id={task_id}",
                f"run_id={str(latest_payload.get('run_id') or '').strip()}",
                f"summary_file={summary_file}",
                f"execution_context_file={execution_context_file}",
                f"change_scope_strategy={str(change_scope.get('deterministic_strategy') or '').strip()}",
                f"changed_paths={json.dumps(change_scope.get('changed_paths') or [], ensure_ascii=False)}",
                f"SC_NEEDS_FIX_FAST status=ok out={out_dir}",
            ]
        )
        + "\n",
    )
    return {
        "name": "pipeline-clean-skip",
        "status": "reused",
        "rc": 0,
        "duration_sec": 0.0,
        "remaining_before_sec": int(max(0, remaining_before)),
        "remaining_after_sec": int(remain_sec(script_start, budget_min)),
        "cmd": [],
        "log_file": str(log_file),
        "reported_out_dir": str(latest_out_dir),
        "summary_file": str(summary_file),
        "reused_run_id": str(latest_payload.get("run_id") or "").strip(),
        "reuse_reason": "latest_pipeline_already_clean" if exact_git_match else "latest_pipeline_already_clean_docs_only_delta",
        "change_scope": change_scope,
    }


def try_stop_when_latest_llm_unknown_without_anchor_fix(
    *,
    task_id: str,
    delivery_profile: str,
    security_profile: str,
    out_dir: Path,
    script_start: float,
    budget_min: int,
) -> dict[str, Any] | None:
    latest_payload, latest_out_dir, summary_file, execution_context_file = _resolve_latest_pipeline_files(task_id)
    if latest_out_dir is None or summary_file is None or execution_context_file is None:
        return None
    if not latest_out_dir.exists() or not summary_file.exists() or not execution_context_file.exists():
        return None
    summary = read_json(summary_file)
    execution_context = read_json(execution_context_file)
    if not summary or not execution_context:
        return None
    if str(execution_context.get("delivery_profile") or "").strip().lower() != str(delivery_profile).strip().lower():
        return None
    if str(execution_context.get("security_profile") or "").strip().lower() != str(security_profile).strip().lower():
        return None
    if _step_status(summary, "sc-test") != "ok" or _step_status(summary, "sc-acceptance-check") != "ok":
        return None
    llm_step = find_pipeline_step_dict(summary, "sc-llm-review")
    if not llm_step:
        return None
    if not _llm_summary_unknown_only(llm_step=llm_step):
        return None
    current_git = current_git_fingerprint()
    previous_git = execution_context.get("git") if isinstance(execution_context.get("git"), dict) else {}
    previous_status = sorted([str(line).rstrip() for line in (previous_git.get("status_short") or []) if str(line).strip()])
    exact_git_match = str(previous_git.get("head") or "").strip() == str(current_git.get("head") or "").strip() and previous_status == sorted(
        [str(line).rstrip() for line in (current_git.get("status_short") or []) if str(line).strip()]
    )
    change_scope = (
        {"deterministic_strategy": "reuse-latest", "changed_paths": [], "unsafe_paths": []}
        if exact_git_match
        else classify_change_scope_between_snapshots(previous_git=previous_git, current_git=current_git)
    )
    changed_paths = [str(item or "").strip() for item in list(change_scope.get("changed_paths") or []) if str(item or "").strip()]
    if _changed_paths_hit_reviewer_anchors(changed_paths):
        return None
    remaining_before = remain_sec(script_start, budget_min)
    log_file = out_dir / "llm-unknown-stop-loss.log"
    write_text(
        log_file,
        "\n".join(
            [
                "[needs-fix-fast] latest pipeline only reported llm unknown/timeout and current edits do not hit reviewer anchors; stop before rerun",
                f"task_id={task_id}",
                f"run_id={str(latest_payload.get('run_id') or '').strip()}",
                f"summary_file={summary_file}",
                f"execution_context_file={execution_context_file}",
                f"changed_paths={json.dumps(changed_paths, ensure_ascii=False)}",
                "SC_NEEDS_FIX_FAST status=indeterminate",
            ]
        )
        + "\n",
    )
    return {
        "name": "pipeline-llm-unknown-stop-loss",
        "status": "reused",
        "rc": 0,
        "duration_sec": 0.0,
        "remaining_before_sec": int(max(0, remaining_before)),
        "remaining_after_sec": int(remain_sec(script_start, budget_min)),
        "cmd": [],
        "log_file": str(log_file),
        "reported_out_dir": str(latest_out_dir),
        "summary_file": str(summary_file),
        "reused_run_id": str(latest_payload.get("run_id") or "").strip(),
        "reuse_reason": "latest_llm_unknown_without_anchor_fix",
        "change_scope": change_scope,
    }


def resolve_deterministic_execution_plan(
    *,
    task_id: str,
    delivery_profile: str,
    security_profile: str,
    planned_cmd: list[str],
) -> dict[str, Any]:
    latest_payload, _latest_out_dir, summary_file, execution_context_file = _resolve_latest_pipeline_files(task_id)
    if not latest_payload or summary_file is None or execution_context_file is None:
        return {"mode": "full-pipeline", "cmd": list(planned_cmd), "change_scope": {}}
    summary = read_json(summary_file)
    execution_context = read_json(execution_context_file)
    if str(summary.get("status") or "").strip().lower() != "ok":
        return {"mode": "full-pipeline", "cmd": list(planned_cmd), "change_scope": {}}
    if str(execution_context.get("delivery_profile") or "").strip().lower() != str(delivery_profile).strip().lower():
        return {"mode": "full-pipeline", "cmd": list(planned_cmd), "change_scope": {}}
    if str(execution_context.get("security_profile") or "").strip().lower() != str(security_profile).strip().lower():
        return {"mode": "full-pipeline", "cmd": list(planned_cmd), "change_scope": {}}
    if _step_status(summary, "sc-acceptance-check") != "ok":
        return {"mode": "full-pipeline", "cmd": list(planned_cmd), "change_scope": {}}
    change_scope = classify_change_scope_between_snapshots(
        previous_git=execution_context.get("git") if isinstance(execution_context.get("git"), dict) else {},
        current_git=current_git_fingerprint(),
    )
    if str(change_scope.get("deterministic_strategy") or "").strip() != "minimal-acceptance":
        return {"mode": "full-pipeline", "cmd": list(planned_cmd), "change_scope": change_scope}
    if str(delivery_profile or "").strip().lower() == "standard":
        return {"mode": "full-pipeline", "cmd": list(planned_cmd), "change_scope": change_scope}
    only_steps = list(change_scope.get("acceptance_only_steps") or [])
    if not only_steps:
        return {"mode": "full-pipeline", "cmd": list(planned_cmd), "change_scope": change_scope}
    cmd = [
        "py",
        "-3",
        "scripts/sc/acceptance_check.py",
        "--task-id",
        str(task_id),
        "--out-per-task",
        "--delivery-profile",
        str(delivery_profile),
        "--security-profile",
        str(security_profile),
        "--only",
        ",".join(only_steps),
    ]
    return {"mode": "minimal-acceptance", "cmd": cmd, "change_scope": change_scope}


def derive_needs_fix_fast_agent_timeout_overrides(
    *,
    task_id: str,
    delivery_profile: str,
    security_profile: str,
    run_agents: list[str],
    diff_mode: str,
    llm_timeout_sec: int,
    agent_timeout_sec: int,
) -> tuple[dict[str, int], dict[str, Any]]:
    if str(delivery_profile or "").strip().lower() != "fast-ship":
        return {}, {}
    if str(diff_mode or "").strip().lower() != "summary":
        return {}, {}
    if "code-reviewer" not in run_agents:
        return {}, {}

    latest_payload, _latest_out_dir, summary_file, execution_context_file = _resolve_latest_pipeline_files(task_id)
    if not latest_payload or summary_file is None or execution_context_file is None:
        return {}, {}
    summary = read_json(summary_file)
    execution_context = read_json(execution_context_file)
    if not summary or not execution_context:
        return {}, {}
    if str(execution_context.get("delivery_profile") or "").strip().lower() != str(delivery_profile).strip().lower():
        return {}, {}
    if str(execution_context.get("security_profile") or "").strip().lower() != str(security_profile).strip().lower():
        return {}, {}

    current_git = current_git_fingerprint()
    exact_git_match = _git_snapshot_matches(execution_context)
    change_scope = (
        {"deterministic_strategy": "reuse-latest", "changed_paths": [], "unsafe_paths": [], "doc_only_delta": True}
        if exact_git_match
        else classify_change_scope_between_snapshots(
            previous_git=execution_context.get("git") if isinstance(execution_context.get("git"), dict) else {},
            current_git=current_git,
        )
    )
    changed_paths = list(change_scope.get("changed_paths") or [])
    if not exact_git_match:
        if not bool(change_scope.get("doc_only_delta")):
            return {}, {}
        if len(changed_paths) > FAST_SHIP_SMALL_DIFF_MAX_CHANGED_PATHS:
            return {}, {}

    llm_step = find_pipeline_step_dict(summary, "sc-llm-review")
    llm_summary_path = Path(str(llm_step.get("summary_file") or "")).resolve() if llm_step else None
    if llm_summary_path is None or not llm_summary_path.exists():
        return {}, {}
    llm_summary = read_json(llm_summary_path)
    code_reviewer_row = next(
        (
            row
            for row in llm_summary.get("results", [])
            if isinstance(row, dict) and str(row.get("agent") or "").strip() == "code-reviewer"
        ),
        None,
    )
    if not isinstance(code_reviewer_row, dict):
        return {}, {}
    if int(code_reviewer_row.get("rc") or 0) != 124:
        return {}, {}

    escalated_timeout = min(int(llm_timeout_sec), max(int(agent_timeout_sec) * 2, int(agent_timeout_sec) + 120))
    if escalated_timeout <= int(agent_timeout_sec):
        return {}, {}

    overrides = {"code-reviewer": escalated_timeout}
    meta = {
        "reason": "previous_code_reviewer_timeout_small_diff",
        "source_run_id": str(latest_payload.get("run_id") or "").strip(),
        "exact_git_match": bool(exact_git_match),
        "change_scope": change_scope,
    }
    return overrides, meta


def _iter_previous_needs_fix_fast_summaries(task_id: str) -> list[Path]:
    logs_root = repo_root() / "logs" / "ci"
    if not logs_root.exists():
        return []
    return sorted(
        [item for item in logs_root.rglob(f"sc-needs-fix-fast-task-{task_id}/summary.json") if item.is_file()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )


def derive_llm_round_budget_prediction(
    *,
    task_id: str,
    delivery_profile: str,
    security_profile: str,
    run_agents: list[str],
    diff_mode: str,
    llm_timeout_sec: int,
    agent_timeout_sec: int,
    agent_timeout_overrides: dict[str, int],
) -> tuple[int, dict[str, Any]]:
    override_ceiling = max([int(agent_timeout_sec)] + [int(value) for value in agent_timeout_overrides.values() if int(value) > 0])
    predicted_budget_sec = max(int(llm_timeout_sec) + 60, override_ceiling + 120)
    if len(run_agents) > 1:
        predicted_budget_sec += 45 * (len(run_agents) - 1)

    matched_timeout_rounds = 0
    recent_observed_timeout_sec = 0
    recent_sources: list[str] = []
    normalized_agents = {str(agent).strip() for agent in run_agents if str(agent).strip()}
    for summary_path in _iter_previous_needs_fix_fast_summaries(task_id):
        payload = read_json(summary_path)
        args_payload = payload.get("args") if isinstance(payload.get("args"), dict) else {}
        if str(args_payload.get("delivery_profile") or "").strip().lower() != str(delivery_profile).strip().lower():
            continue
        if str(args_payload.get("security_profile") or "").strip().lower() != str(security_profile).strip().lower():
            continue
        if str(args_payload.get("diff_mode") or "").strip().lower() != str(diff_mode).strip().lower():
            continue
        rounds = payload.get("rounds") if isinstance(payload.get("rounds"), list) else []
        timeline = payload.get("timeline") if isinstance(payload.get("timeline"), list) else []
        for round_item in rounds:
            if not isinstance(round_item, dict):
                continue
            if str(round_item.get("failure_kind") or "").strip() != "timeout-no-summary":
                continue
            timeout_agents = {str(agent).strip() for agent in list(round_item.get("timeout_agents") or []) if str(agent).strip()}
            if normalized_agents and timeout_agents and not timeout_agents.intersection(normalized_agents):
                continue
            round_no = int(round_item.get("round") or 0)
            timeline_step = next(
                (
                    row
                    for row in timeline
                    if isinstance(row, dict) and str(row.get("name") or "").strip() == f"pipeline-llm-round-{round_no}"
                ),
                {},
            )
            observed_timeout_sec = int(float(timeline_step.get("duration_sec") or 0))
            if observed_timeout_sec <= 0:
                observed_timeout_sec = int(args_payload.get("llm_timeout_sec") or llm_timeout_sec)
            recent_observed_timeout_sec = max(recent_observed_timeout_sec, observed_timeout_sec)
            matched_timeout_rounds += 1
            recent_sources.append(str(summary_path))
            if matched_timeout_rounds >= 3:
                break
        if matched_timeout_rounds >= 3:
            break

    if recent_observed_timeout_sec > 0:
        predicted_budget_sec = max(predicted_budget_sec, recent_observed_timeout_sec + 60)

    meta = {
        "predicted_budget_sec": int(predicted_budget_sec),
        "matched_timeout_rounds": int(matched_timeout_rounds),
        "recent_observed_timeout_sec": int(recent_observed_timeout_sec),
        "agent_timeout_override_applied": bool(agent_timeout_overrides),
        "recent_timeout_sources": recent_sources,
    }
    return int(predicted_budget_sec), meta


def try_reuse_matching_minimal_acceptance_step(
    *,
    task_id: str,
    delivery_profile: str,
    security_profile: str,
    planned_cmd: list[str],
    out_dir: Path,
    change_scope: dict[str, Any],
    script_start: float,
    budget_min: int,
) -> dict[str, Any] | None:
    target_fingerprint = str(change_scope.get("change_fingerprint") or "").strip()
    if not target_fingerprint:
        return None
    logs_root = repo_root() / "logs" / "ci"
    if not logs_root.exists():
        return None
    current_out_dir = out_dir.resolve()
    candidates = sorted(
        [item for item in logs_root.rglob(f"sc-needs-fix-fast-task-{task_id}/summary.json") if item.is_file()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for summary_path in candidates:
        if summary_path.parent.resolve() == current_out_dir:
            continue
        payload = read_json(summary_path)
        args_payload = payload.get("args") if isinstance(payload.get("args"), dict) else {}
        plan_payload = payload.get("deterministic_plan") if isinstance(payload.get("deterministic_plan"), dict) else {}
        plan_scope = plan_payload.get("change_scope") if isinstance(plan_payload.get("change_scope"), dict) else {}
        if str(plan_payload.get("mode") or "").strip() != "minimal-acceptance":
            continue
        if str(args_payload.get("delivery_profile") or "").strip().lower() != str(delivery_profile).strip().lower():
            continue
        if str(args_payload.get("security_profile") or "").strip().lower() != str(security_profile).strip().lower():
            continue
        if str(plan_scope.get("change_fingerprint") or "").strip() != target_fingerprint:
            continue
        timeline = payload.get("timeline") if isinstance(payload.get("timeline"), list) else []
        deterministic_step = next((row for row in timeline if isinstance(row, dict) and str(row.get("summary_file") or "").strip()), None)
        if not isinstance(deterministic_step, dict):
            continue
        summary_file_raw = str(deterministic_step.get("summary_file") or "").strip()
        reported_out_dir_raw = str(deterministic_step.get("reported_out_dir") or "").strip()
        if not summary_file_raw or not reported_out_dir_raw:
            continue
        summary_file = Path(summary_file_raw)
        reported_out_dir = Path(reported_out_dir_raw)
        if not summary_file.exists() or not reported_out_dir.exists():
            continue
        remaining_before = remain_sec(script_start, budget_min)
        log_file = out_dir / "pipeline-deterministic.log"
        write_text(
            log_file,
            "\n".join(
                [
                    "[needs-fix-fast] reused minimal acceptance subset by change fingerprint",
                    f"task_id={task_id}",
                    f"summary_file={summary_file}",
                    f"source_needs_fix_summary={summary_path}",
                    f"change_fingerprint={target_fingerprint}",
                    f"SC_ACCEPTANCE status=ok out={reported_out_dir}",
                ]
            )
            + "\n",
        )
        return {
            "name": "pipeline-deterministic-minimal-acceptance",
            "status": "reused",
            "rc": 0,
            "duration_sec": 0.0,
            "remaining_before_sec": int(max(0, remaining_before)),
            "remaining_after_sec": int(remain_sec(script_start, budget_min)),
            "cmd": list(planned_cmd),
            "log_file": str(log_file),
            "reported_out_dir": str(reported_out_dir),
            "summary_file": str(summary_file),
            "reuse_reason": "minimal_acceptance_change_fingerprint",
        }
    return None


def find_pipeline_step(pipeline_summary_path: Path, step_name: str) -> dict[str, Any]:
    payload = read_json(pipeline_summary_path)
    return find_pipeline_step_dict(payload, step_name)


def elapsed_sec(start_monotonic: float) -> int:
    return int(max(0.0, time.monotonic() - start_monotonic))


def remain_sec(start_monotonic: float, budget_min: int) -> int:
    return int(max(0.0, budget_min * 60 - elapsed_sec(start_monotonic)))


def cap_targeted_single_agent_timeouts(
    *,
    run_agents: list[str],
    current_source: str,
    llm_timeout_sec: int,
    agent_timeout_sec: int,
    explicit_llm_timeout: bool,
    explicit_agent_timeout: bool,
    final_pass: bool,
) -> tuple[int, int]:
    targeted_sources = {
        "agent-review-targeted",
        "previous-llm-summary-precise",
        "change-scope-targeted",
    }
    if final_pass or len(list(run_agents)) != 1 or str(current_source or "").strip() not in targeted_sources:
        return int(llm_timeout_sec), int(agent_timeout_sec)

    next_llm_timeout = int(llm_timeout_sec)
    next_agent_timeout = int(agent_timeout_sec)
    if not explicit_llm_timeout:
        next_llm_timeout = min(next_llm_timeout, 480)
    if not explicit_agent_timeout:
        next_agent_timeout = min(next_agent_timeout, 180)
    next_agent_timeout = min(next_agent_timeout, next_llm_timeout)
    return max(120, next_llm_timeout), max(60, next_agent_timeout)


def apply_delivery_profile_defaults(args: argparse.Namespace) -> argparse.Namespace:
    delivery_profile = resolve_delivery_profile(getattr(args, "delivery_profile", None))
    defaults = profile_needs_fix_fast_defaults(delivery_profile)
    args.delivery_profile = delivery_profile
    args.llm_backend = resolve_llm_backend(getattr(args, "llm_backend", None))
    if not str(getattr(args, "security_profile", "") or "").strip():
        args.security_profile = default_security_profile_for_delivery(delivery_profile)
    if not str(getattr(args, "agents", "") or "").strip():
        args.agents = str(defaults.get("agents") or "code-reviewer,security-auditor,semantic-equivalence-auditor")
    if not str(getattr(args, "diff_mode", "") or "").strip():
        args.diff_mode = str(defaults.get("diff_mode") or "summary")
    if args.max_rounds is None:
        args.max_rounds = int(defaults.get("max_rounds", 2) or 2)
    if args.rerun_failing_only is None:
        args.rerun_failing_only = bool(defaults.get("rerun_failing_only", True))
    if args.time_budget_min is None:
        args.time_budget_min = int(defaults.get("time_budget_min", 30) or 30)
    if args.llm_timeout_sec is None:
        args.llm_timeout_sec = int(defaults.get("llm_timeout_sec", 900) or 900)
    if args.agent_timeout_sec is None:
        args.agent_timeout_sec = int(defaults.get("agent_timeout_sec", 240) or 240)
    if args.step_timeout_sec is None:
        args.step_timeout_sec = int(defaults.get("step_timeout_sec", 1800) or 1800)
    if args.min_llm_budget_min is None:
        args.min_llm_budget_min = int(defaults.get("min_llm_budget_min", 10) or 10)
    if bool(getattr(args, "final_pass", False)):
        args.agents = "all"
        args.diff_mode = "full"
        args.skip_sc_test = False
    return args


def _apply_risky_change_profile_floor(
    args: argparse.Namespace,
    *,
    explicit_flags: dict[str, bool],
    change_scope: dict[str, Any] | None,
) -> dict[str, Any]:
    decision = derive_delivery_profile_floor(
        delivery_profile=str(args.delivery_profile),
        security_profile=str(args.security_profile),
        change_scope=change_scope,
        explicit_security_profile=bool(explicit_flags.get("security_profile")),
    )
    if not bool(decision.get("applied")):
        return decision

    args.delivery_profile = str(decision.get("delivery_profile") or args.delivery_profile)
    if not bool(explicit_flags.get("security_profile")):
        args.security_profile = str(
            decision.get("security_profile")
            or args.security_profile
            or default_security_profile_for_delivery(str(args.delivery_profile))
        )

    defaults = profile_needs_fix_fast_defaults(str(args.delivery_profile))
    if not bool(explicit_flags.get("agents")):
        args.agents = str(defaults.get("agents") or args.agents)
    if not bool(explicit_flags.get("diff_mode")):
        args.diff_mode = str(defaults.get("diff_mode") or args.diff_mode)
    if not bool(explicit_flags.get("max_rounds")):
        args.max_rounds = int(defaults.get("max_rounds", args.max_rounds) or args.max_rounds)
    if not bool(explicit_flags.get("rerun_failing_only")):
        args.rerun_failing_only = bool(defaults.get("rerun_failing_only", args.rerun_failing_only))
    if not bool(explicit_flags.get("time_budget_min")):
        args.time_budget_min = int(defaults.get("time_budget_min", args.time_budget_min) or args.time_budget_min)
    if not bool(explicit_flags.get("llm_timeout_sec")):
        args.llm_timeout_sec = int(defaults.get("llm_timeout_sec", args.llm_timeout_sec) or args.llm_timeout_sec)
    if not bool(explicit_flags.get("agent_timeout_sec")):
        args.agent_timeout_sec = int(defaults.get("agent_timeout_sec", args.agent_timeout_sec) or args.agent_timeout_sec)
    if not bool(explicit_flags.get("step_timeout_sec")):
        args.step_timeout_sec = int(defaults.get("step_timeout_sec", args.step_timeout_sec) or args.step_timeout_sec)
    if not bool(explicit_flags.get("min_llm_budget_min")):
        args.min_llm_budget_min = int(defaults.get("min_llm_budget_min", args.min_llm_budget_min) or args.min_llm_budget_min)
    return decision


def _build_deterministic_cmd(*, py: str, args: argparse.Namespace) -> list[str]:
    cmd = [
        py,
        "-3",
        "scripts/sc/run_review_pipeline.py",
        "--task-id",
        str(args.task_id),
        "--delivery-profile",
        str(args.delivery_profile),
        "--security-profile",
        str(args.security_profile),
        "--skip-llm-review",
        "--llm-base",
        str(args.base),
        "--llm-diff-mode",
        str(args.diff_mode),
    ]
    if args.skip_sc_test:
        cmd.append("--skip-test")
    return cmd


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Fast stop-loss workflow for llm_review Needs Fix.")
    ap.add_argument("--task-id", required=True, help="Task id (for task-scoped runs).")
    ap.add_argument("--delivery-profile", default=None, choices=DELIVERY_PROFILE_CHOICES, help="Delivery profile (default: env DELIVERY_PROFILE or fast-ship).")
    ap.add_argument("--security-profile", default=None, help="Security profile (default follows delivery profile).")
    ap.add_argument(
        "--agents",
        default=None,
        help="Comma-separated llm_review agents. Default follows delivery profile.",
    )
    ap.add_argument("--review-template", default="scripts/sc/templates/llm_review/bmad-godot-review-template.txt")
    ap.add_argument("--base", default="origin/main", help="Git base for diff-mode full.")
    ap.add_argument("--diff-mode", default=None, help="llm_review diff mode (full/summary/none). Default follows delivery profile.")
    ap.add_argument(
        "--llm-backend",
        default=None,
        choices=KNOWN_LLM_BACKENDS,
        help="llm_review backend transport. Default: env SC_LLM_BACKEND or codex-cli.",
    )
    ap.add_argument("--max-rounds", type=int, default=None, help="Maximum llm_review rounds (>=1). Default follows delivery profile.")
    rerun_group = ap.add_mutually_exclusive_group()
    rerun_group.add_argument(
        "--rerun-failing-only",
        dest="rerun_failing_only",
        action="store_true",
        help="From round 2, rerun only agents that were Needs Fix in previous round.",
    )
    rerun_group.add_argument(
        "--no-rerun-failing-only",
        dest="rerun_failing_only",
        action="store_false",
        help="Always rerun the full reviewer set across rounds.",
    )
    ap.set_defaults(rerun_failing_only=None)
    ap.add_argument("--time-budget-min", type=int, default=None, help="Hard time budget in minutes. Default follows delivery profile.")
    ap.add_argument("--llm-timeout-sec", type=int, default=None, help="llm_review --timeout-sec. Default follows delivery profile.")
    ap.add_argument("--agent-timeout-sec", type=int, default=None, help="llm_review --agent-timeout-sec. Default follows delivery profile.")
    ap.add_argument("--step-timeout-sec", type=int, default=None, help="Outer timeout for each subprocess step. Default follows delivery profile.")
    ap.add_argument("--min-llm-budget-min", type=int, default=None, help="Fail fast when remaining budget is below this floor before a new LLM round. Default follows delivery profile.")
    ap.add_argument("--final-pass", action="store_true", help="Force a full closure pass: no deterministic shortcuts, no reviewer auto-shrink, full reviewer set.")
    ap.add_argument("--skip-sc-test", action="store_true", help="Skip sc-test in deterministic pipeline stage.")
    ap.add_argument("--python", default="py", help="Python launcher command (Windows default: py).")
    return ap


def run_step(
    *,
    name: str,
    cmd: list[str],
    out_dir: Path,
    timeout_sec: int,
    script_start: float,
    budget_min: int,
) -> dict[str, Any]:
    remaining_before = remain_sec(script_start, budget_min)
    if remaining_before <= 0:
        return {
            "name": name,
            "status": "timeout",
            "rc": 124,
            "duration_sec": 0,
            "remaining_before_sec": 0,
            "log_file": "",
            "summary_file": "",
            "reported_out_dir": "",
            "error": "time_budget_exhausted_before_step",
        }

    effective_timeout = min(timeout_sec, remaining_before)
    started = time.monotonic()
    rc, stdout = run_cmd(cmd, cwd=repo_root(), timeout_sec=max(1, effective_timeout))
    duration = round(time.monotonic() - started, 3)

    log_file = out_dir / f"{name}.log"
    write_text(log_file, stdout)

    reported_out_dir = parse_out_dir(stdout)
    summary_file = (reported_out_dir / "summary.json") if reported_out_dir else None
    return {
        "name": name,
        "status": "ok" if rc == 0 else "fail",
        "rc": int(rc),
        "duration_sec": duration,
        "remaining_before_sec": int(remaining_before),
        "remaining_after_sec": int(remain_sec(script_start, budget_min)),
        "cmd": cmd,
        "log_file": str(log_file),
        "reported_out_dir": str(reported_out_dir) if reported_out_dir else "",
        "summary_file": str(summary_file) if summary_file and summary_file.exists() else "",
    }


def copy_llm_round_artifacts(source_dir: Path, out_dir: Path, round_no: int) -> None:
    round_dir = out_dir / f"round-{round_no}"
    round_dir.mkdir(parents=True, exist_ok=True)
    for name in ["summary.json", "review-code-reviewer.md", "review-security-auditor.md", "review-test-automator.md", "review-semantic-equivalence-auditor.md"]:
        src = source_dir / name
        if src.exists():
            shutil.copy2(src, round_dir / name)


def majority_verdict(votes: list[str]) -> str:
    ok = sum(1 for v in votes if v == "OK")
    nf = sum(1 for v in votes if v == "Needs Fix")
    if nf > ok:
        return "Needs Fix"
    if ok > nf:
        return "OK"
    if nf > 0:
        return "Needs Fix"
    return "Unknown"


def _round_needs_fix_signature(round_result: dict[str, Any]) -> list[dict[str, str]]:
    verdicts = round_result.get("verdicts") if isinstance(round_result.get("verdicts"), dict) else {}
    signature: list[dict[str, str]] = []
    for agent in sorted(verdicts.keys()):
        verdict = normalize_verdict(verdicts.get(agent))
        if verdict != "Needs Fix":
            continue
        signature.append({"agent": agent, "verdict": verdict})
    return signature


def _round_verdict(verdicts: dict[str, str], *, rc: int) -> str:
    normalized = {normalize_verdict(str(value or "")) for value in verdicts.values()}
    if "Needs Fix" in normalized:
        return "Needs Fix"
    if rc == 0 and normalized and normalized.issubset({"OK"}):
        return "OK"
    return "Unknown"


def _derive_final_status(*, final_verdicts: dict[str, str], rounds: list[dict[str, Any]]) -> tuple[str, str]:
    final_needs_fix = sorted([agent for agent, verdict in final_verdicts.items() if verdict == "Needs Fix"])
    final_unknown = sorted([agent for agent, verdict in final_verdicts.items() if verdict == "Unknown"])
    if final_needs_fix:
        return "needs-fix", "llm_review_needs_fix_remaining"
    if final_unknown:
        return "indeterminate", "llm_review_verdict_unknown"
    if any(int(round_item.get("rc") or 0) != 0 for round_item in rounds):
        return "indeterminate", "llm_review_round_failed"
    return "ok", "llm_review_clean"


def _run_chapter6_route_preflight(*, task_id: str, out_dir: Path) -> dict[str, Any]:
    latest_payload = resolve_latest_pipeline_payload(task_id)
    latest_out_dir_raw = str(latest_payload.get("latest_out_dir") or "").strip()
    if not latest_out_dir_raw:
        return {}
    latest_out_dir = Path(latest_out_dir_raw)
    agent_review_path = latest_out_dir / "agent-review.json"
    if not agent_review_path.exists():
        return {}

    python_dir = repo_root() / "scripts" / "python"
    if str(python_dir) not in sys.path:
        sys.path.insert(0, str(python_dir))

    from chapter6_route import route_chapter6  # noqa: WPS433

    _rc, payload = route_chapter6(
        repo_root=repo_root(),
        task_id=str(task_id),
        record_residual=True,
    )
    if not isinstance(payload, dict):
        return {}
    write_json(out_dir / "chapter6-route.json", payload)
    return payload


def _build_chapter6_route_step(
    *,
    payload: dict[str, Any],
    script_start: float,
    budget_min: int,
    proceed: bool,
) -> dict[str, Any]:
    preferred_lane = str(payload.get("preferred_lane") or "").strip() or "inspect-first"
    remaining_before = remain_sec(script_start, budget_min)
    return {
        "name": "chapter6-route-preflight",
        "status": "ok" if proceed else "blocked",
        "rc": 0 if proceed else 1,
        "duration_sec": 0.0,
        "remaining_before_sec": int(max(0, remaining_before)),
        "remaining_after_sec": int(remain_sec(script_start, budget_min)),
        "cmd": ["py", "-3", "scripts/python/dev_cli.py", "chapter6-route", "--task-id", str(payload.get("task_id") or ""), "--recommendation-only"],
        "log_file": "",
        "reported_out_dir": "",
        "summary_file": "",
        "preferred_lane": preferred_lane,
        "recommended_command": str(payload.get("recommended_command") or "").strip(),
        "blocked_by": str(payload.get("blocked_by") or "").strip(),
        "repo_noise_classification": str(payload.get("repo_noise_classification") or "").strip(),
        "residual_recording": payload.get("residual_recording") if isinstance(payload.get("residual_recording"), dict) else {},
    }


def _chapter6_route_stop_outcome(payload: dict[str, Any]) -> tuple[str, str, int]:
    preferred_lane = str(payload.get("preferred_lane") or "").strip() or "inspect-first"
    if preferred_lane == "record-residual":
        return "ok", "chapter6_route_recorded_residual", 0
    if preferred_lane == "repo-noise-stop":
        return "indeterminate", "chapter6_route_repo_noise_stop", 1
    if preferred_lane == "fix-deterministic":
        return "indeterminate", "chapter6_route_fix_deterministic_first", 1
    if preferred_lane == "run-6.7":
        return "indeterminate", "chapter6_route_run_6_7_first", 1
    return "indeterminate", "chapter6_route_inspect_first", 1


def _normalized_timeline_phase(name: str) -> str:
    step_name = str(name or "").strip()
    if step_name.startswith("pipeline-llm-round-"):
        return "pipeline-llm-round"
    return step_name


def _build_timeline_bottleneck_summary(*, timeline: list[dict[str, Any]], rounds: list[dict[str, Any]]) -> dict[str, Any]:
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    failure_kind_counts: dict[str, int] = {}
    for item in timeline:
        if not isinstance(item, dict):
            continue
        phase = _normalized_timeline_phase(str(item.get("name") or ""))
        duration_raw = item.get("duration_sec")
        if not phase or not isinstance(duration_raw, (int, float)) or isinstance(duration_raw, bool):
            continue
        duration = round(max(0.0, float(duration_raw)), 3)
        totals[phase] = round(totals.get(phase, 0.0) + duration, 3)
        counts[phase] = counts.get(phase, 0) + 1
    for item in rounds:
        if not isinstance(item, dict):
            continue
        failure_kind = str(item.get("failure_kind") or "").strip()
        if not failure_kind:
            continue
        failure_kind_counts[failure_kind] = failure_kind_counts.get(failure_kind, 0) + 1
    if not totals and not failure_kind_counts:
        return {}
    payload: dict[str, Any] = {
        "round_failure_kind_counts": {
            key: failure_kind_counts[key]
            for key in sorted(failure_kind_counts)
        },
    }
    if totals:
        payload["step_duration_totals"] = {
            key: totals[key]
            for key in sorted(totals)
        }
        payload["step_duration_counts"] = {
            key: counts[key]
            for key in sorted(counts)
        }
        payload["step_duration_avg"] = {
            key: round(totals[key] / max(1, counts.get(key, 1)), 3)
            for key in sorted(totals)
        }
        payload["dominant_cost_phase"] = max(sorted(totals.items()), key=lambda item: (item[1], item[0]))[0]
    return payload


def _derive_summary_recommendation(summary: dict[str, Any]) -> tuple[str, str]:
    status = str(summary.get("status") or "").strip().lower()
    reason = str(summary.get("reason") or "").strip().lower()
    route_preflight = summary.get("route_preflight") if isinstance(summary.get("route_preflight"), dict) else {}
    preferred_lane = str(route_preflight.get("preferred_lane") or "").strip().lower()
    args_payload = summary.get("args") if isinstance(summary.get("args"), dict) else {}
    final_unknown_agents = [str(item).strip() for item in list(summary.get("final_unknown_agents") or []) if str(item).strip()]
    final_needs_fix_agents = [str(item).strip() for item in list(summary.get("final_needs_fix_agents") or []) if str(item).strip()]
    stop_loss = summary.get("stop_loss") if isinstance(summary.get("stop_loss"), dict) else {}

    if reason == "latest_pipeline_already_clean" or status == "ok":
        return "continue", "The latest full pipeline is already clean for the current change scope; no extra 6.8 rerun is needed."
    if reason == "no_anchor_fix_for_previous_llm_unknown":
        return "inspect", "The previous reviewer result was Unknown and this change did not hit the reviewer anchors; inspect the current sidecars before spending more budget."
    if preferred_lane == "inspect-first" or reason == "chapter6_route_inspect_first":
        return "inspect", "Chapter 6 route says inspect first; do not pay for a new 6.8 run until the current evidence is reviewed."
    if preferred_lane == "fix-deterministic" or reason == "chapter6_route_fix_deterministic":
        return "fix-and-resume", "Chapter 6 route says a deterministic issue still blocks progress; fix that root cause before continuing 6.8."
    if preferred_lane == "record-residual" or reason == "chapter6_route_record_residual":
        return "record-residual", "Chapter 6 route says the remaining findings should be recorded as residual debt instead of paying for another 6.8 run."
    if reason == "repeated_needs_fix_no_progress" or bool(stop_loss.get("triggered")):
        return "record-residual", "Repeated Needs Fix rounds made no progress; record the remaining findings instead of looping another 6.8 run."
    if final_unknown_agents:
        if bool(args_payload.get("final_pass")):
            return "inspect", "The final pass still ended with Unknown reviewers; inspect the latest reviewer artifacts before deciding on any further rerun."
        return "final-pass", "Reviewer closure still has Unknown agents; if this is the last task-level cleanup, run one strict final pass next."
    if final_needs_fix_agents:
        return "record-residual", "Concrete Needs Fix findings remain after the narrow closure run; fix them directly or record them as residual debt."
    if status == "indeterminate":
        return "inspect", "The narrow closure run ended indeterminate; inspect route, reviewer, and timeout evidence before rerunning."
    return "inspect", "Inspect the latest narrow closure artifacts before deciding whether to rerun or close the task."


def _write_summary(out_dir: Path, summary: dict[str, Any]) -> None:
    recommended_action, recommended_action_why = _derive_summary_recommendation(summary)
    summary["recommended_action"] = recommended_action
    summary["recommended_action_why"] = recommended_action_why
    write_json(out_dir / "summary.json", summary)


def main() -> int:
    parsed_args = build_parser().parse_args()
    explicit_flags = {
        "security_profile": bool(str(getattr(parsed_args, "security_profile", "") or "").strip()),
        "agents": bool(str(getattr(parsed_args, "agents", "") or "").strip()),
        "diff_mode": bool(str(getattr(parsed_args, "diff_mode", "") or "").strip()),
        "max_rounds": getattr(parsed_args, "max_rounds", None) is not None,
        "rerun_failing_only": getattr(parsed_args, "rerun_failing_only", None) is not None,
        "time_budget_min": getattr(parsed_args, "time_budget_min", None) is not None,
        "llm_timeout_sec": getattr(parsed_args, "llm_timeout_sec", None) is not None,
        "agent_timeout_sec": getattr(parsed_args, "agent_timeout_sec", None) is not None,
        "step_timeout_sec": getattr(parsed_args, "step_timeout_sec", None) is not None,
        "min_llm_budget_min": getattr(parsed_args, "min_llm_budget_min", None) is not None,
    }
    args = apply_delivery_profile_defaults(parsed_args)
    if args.max_rounds < 1:
        print("[needs-fix-fast] ERROR: --max-rounds must be >= 1")
        return 2

    agents = resolve_configured_agents(args.agents)
    if not agents:
        print("[needs-fix-fast] ERROR: --agents resolved to empty list")
        return 2

    script_start = time.monotonic()
    out_dir = ci_dir(f"sc-needs-fix-fast-task-{args.task_id}")
    write_text(out_dir / "run_id.txt", uuid.uuid4().hex + "\n")

    timeline: list[dict[str, Any]] = []
    route_payload: dict[str, Any] = {}
    py = args.python
    clean_skip_step = try_skip_when_latest_pipeline_already_clean(
        task_id=str(args.task_id),
        delivery_profile=str(args.delivery_profile),
        security_profile=str(args.security_profile),
        out_dir=out_dir,
        script_start=script_start,
        budget_min=args.time_budget_min,
    )
    if clean_skip_step is not None:
        summary = {
            "cmd": "sc-needs-fix-fast",
            "task_id": str(args.task_id),
            "status": "ok",
            "reason": "latest_pipeline_already_clean",
            "out_dir": str(out_dir),
            "elapsed_sec": elapsed_sec(script_start),
            "delivery_profile": str(args.delivery_profile),
            "change_scope": clean_skip_step.get("change_scope") if isinstance(clean_skip_step.get("change_scope"), dict) else {},
            "timeline": [clean_skip_step],
            "rounds": [],
            "votes": {agent: [] for agent in agents},
            "final_verdicts": {agent: "OK" for agent in agents},
            "final_needs_fix_agents": [],
            "final_unknown_agents": [],
        }
        _write_summary(out_dir, summary)
        print(f"SC_NEEDS_FIX_FAST status=ok out={out_dir}")
        return 0

    if not bool(args.final_pass):
        stop_loss_step = try_stop_when_latest_llm_unknown_without_anchor_fix(
            task_id=str(args.task_id),
            delivery_profile=str(args.delivery_profile),
            security_profile=str(args.security_profile),
            out_dir=out_dir,
            script_start=script_start,
            budget_min=args.time_budget_min,
        )
        if stop_loss_step is not None:
            summary = {
                "cmd": "sc-needs-fix-fast",
                "task_id": str(args.task_id),
                "status": "indeterminate",
                "reason": "no_anchor_fix_for_previous_llm_unknown",
                "out_dir": str(out_dir),
                "elapsed_sec": elapsed_sec(script_start),
                "delivery_profile": str(args.delivery_profile),
                "change_scope": stop_loss_step.get("change_scope") if isinstance(stop_loss_step.get("change_scope"), dict) else {},
                "timeline": [stop_loss_step],
                "rounds": [],
                "votes": {agent: [] for agent in agents},
                "final_verdicts": {agent: "Unknown" for agent in agents},
                "final_needs_fix_agents": [],
                "final_unknown_agents": list(agents),
            }
            _write_summary(out_dir, summary)
            print(f"SC_NEEDS_FIX_FAST status=indeterminate out={out_dir}")
            return 1
        route_payload = _run_chapter6_route_preflight(task_id=str(args.task_id), out_dir=out_dir)
        if route_payload:
            route_preflight_step = _build_chapter6_route_step(
                payload=route_payload,
                script_start=script_start,
                budget_min=args.time_budget_min,
                proceed=str(route_payload.get("preferred_lane") or "").strip() == "run-6.8",
            )
            timeline.append(route_preflight_step)
            if str(route_payload.get("preferred_lane") or "").strip() != "run-6.8":
                status, reason, exit_code = _chapter6_route_stop_outcome(route_payload)
                residual_recording = route_payload.get("residual_recording") if isinstance(route_payload.get("residual_recording"), dict) else {}
                summary = {
                    "cmd": "sc-needs-fix-fast",
                    "task_id": str(args.task_id),
                    "status": status,
                    "reason": reason,
                    "out_dir": str(out_dir),
                    "elapsed_sec": elapsed_sec(script_start),
                    "delivery_profile": str(args.delivery_profile),
                    "timeline": list(timeline),
                    "rounds": [],
                    "votes": {agent: [] for agent in agents},
                    "final_verdicts": {agent: ("OK" if status == "ok" else "Unknown") for agent in agents},
                    "final_needs_fix_agents": [],
                    "final_unknown_agents": [] if status == "ok" else list(agents),
                    "route_preflight": route_payload,
                    "residual_recording": residual_recording,
                }
                _write_summary(out_dir, summary)
                print(f"SC_NEEDS_FIX_FAST status={status} out={out_dir}")
                return exit_code

    deterministic_cmd = _build_deterministic_cmd(py=py, args=args)
    profile_floor_decision = {
        "applied": False,
        "delivery_profile": str(args.delivery_profile),
        "security_profile": str(args.security_profile),
        "reason": "",
    }
    if bool(args.final_pass):
        deterministic_plan = {"mode": "full-pipeline", "change_scope": {"reason": "final-pass"}, "final_pass": True}
        deterministic_step = None
    else:
        deterministic_plan = resolve_deterministic_execution_plan(
            task_id=str(args.task_id),
            delivery_profile=str(args.delivery_profile),
            security_profile=str(args.security_profile),
            planned_cmd=deterministic_cmd,
        )
        profile_floor_decision = _apply_risky_change_profile_floor(
            args,
            explicit_flags=explicit_flags,
            change_scope=deterministic_plan.get("change_scope") if isinstance(deterministic_plan.get("change_scope"), dict) else {},
        )
        if bool(profile_floor_decision.get("applied")):
            deterministic_cmd = _build_deterministic_cmd(py=py, args=args)
            deterministic_plan = resolve_deterministic_execution_plan(
                task_id=str(args.task_id),
                delivery_profile=str(args.delivery_profile),
                security_profile=str(args.security_profile),
                planned_cmd=deterministic_cmd,
            )
        deterministic_step = try_reuse_latest_deterministic_step(
            task_id=str(args.task_id),
            delivery_profile=str(args.delivery_profile),
            security_profile=str(args.security_profile),
            skip_sc_test=bool(args.skip_sc_test),
            planned_cmd=deterministic_cmd,
            out_dir=out_dir,
            script_start=script_start,
            budget_min=args.time_budget_min,
        )
    if deterministic_step is None:
        minimal_reuse = None
        if (not bool(args.final_pass)) and str(deterministic_plan.get("mode") or "").strip() == "minimal-acceptance":
            minimal_reuse = try_reuse_matching_minimal_acceptance_step(
                task_id=str(args.task_id),
                delivery_profile=str(args.delivery_profile),
                security_profile=str(args.security_profile),
                planned_cmd=list(deterministic_plan.get("cmd") or []),
                out_dir=out_dir,
                change_scope=deterministic_plan.get("change_scope") if isinstance(deterministic_plan.get("change_scope"), dict) else {},
                script_start=script_start,
                budget_min=args.time_budget_min,
            )
        if minimal_reuse is not None:
            deterministic_step = minimal_reuse
            print("[needs-fix-fast] step: reuse minimal acceptance subset by change fingerprint")
        elif str(deterministic_plan.get("mode") or "").strip() == "minimal-acceptance":
            print("[needs-fix-fast] step: run minimal acceptance subset")
            deterministic_step = run_step(
                name="pipeline-deterministic-minimal-acceptance",
                cmd=list(deterministic_plan.get("cmd") or []),
                out_dir=out_dir,
                timeout_sec=args.step_timeout_sec,
                script_start=script_start,
                budget_min=args.time_budget_min,
            )
        else:
            print("[needs-fix-fast] step: run_review_pipeline deterministic gates")
            deterministic_step = run_step(
                name="pipeline-deterministic",
                cmd=deterministic_cmd,
                out_dir=out_dir,
                timeout_sec=args.step_timeout_sec,
                script_start=script_start,
                budget_min=args.time_budget_min,
            )
    else:
        print(f"[needs-fix-fast] step: reuse deterministic pipeline run_id={deterministic_step['reused_run_id']}")
    timeline.append(deterministic_step)
    if deterministic_step["rc"] != 0:
        summary = {
            "cmd": "sc-needs-fix-fast",
            "task_id": str(args.task_id),
            "status": "fail",
            "reason": "deterministic_gate_failed_pipeline",
            "out_dir": str(out_dir),
            "timeline": timeline,
            "elapsed_sec": elapsed_sec(script_start),
        }
        _write_summary(out_dir, summary)
        print(f"SC_NEEDS_FIX_FAST status=fail out={out_dir}")
        return 1

    votes: dict[str, list[str]] = {agent: [] for agent in agents}
    rounds: list[dict[str, Any]] = []
    round_agent_timeout_overrides_history: list[dict[str, Any]] = []
    llm_budget_prediction_history: list[dict[str, Any]] = []
    stop_loss: dict[str, Any] = {"triggered": False}
    if bool(args.final_pass):
        run_agents, initial_agent_source = list(agents), "final-pass"
    else:
        run_agents, initial_agent_source = infer_initial_run_agents(str(args.task_id), list(agents))
        run_agents, initial_agent_source = prefer_precise_llm_summary_agents(
            task_id=str(args.task_id),
            delivery_profile=str(args.delivery_profile),
            diff_mode=str(args.diff_mode),
            configured_agents=list(agents),
            current_agents=list(run_agents),
            current_source=initial_agent_source,
        )
        run_agents, initial_agent_source = prefer_targeted_agents_by_change_scope(
            configured_agents=list(agents),
            current_agents=list(run_agents),
            current_source=initial_agent_source,
            change_scope=deterministic_plan.get("change_scope") if isinstance(deterministic_plan.get("change_scope"), dict) else {},
        )
    participating_agents: set[str] = set(run_agents)
    for round_no in range(1, args.max_rounds + 1):
        if not run_agents:
            break

        remaining = remain_sec(script_start, args.time_budget_min)
        if remaining <= 0:
            break
        if remaining < int(args.min_llm_budget_min) * 60:
            timeline.append(
                {
                    "name": f"pipeline-llm-round-{round_no}",
                    "status": "fail",
                    "rc": 124,
                    "duration_sec": 0,
                    "remaining_before_sec": int(remaining),
                    "remaining_after_sec": int(remaining),
                    "cmd": [],
                    "log_file": "",
                    "reported_out_dir": "",
                    "summary_file": "",
                    "error": "insufficient_llm_budget",
                    "min_llm_budget_min": int(args.min_llm_budget_min),
                }
            )
            if not rounds:
                summary = {
                    "cmd": "sc-needs-fix-fast",
                    "task_id": str(args.task_id),
                    "status": "fail",
                    "reason": "insufficient_llm_budget_before_llm",
                    "out_dir": str(out_dir),
                    "timeline": timeline,
                    "elapsed_sec": elapsed_sec(script_start),
                    "delivery_profile": str(args.delivery_profile),
                }
                _write_summary(out_dir, summary)
                print(f"SC_NEEDS_FIX_FAST status=fail out={out_dir}")
                return 1
            break

        llm_timeout = max(120, min(args.llm_timeout_sec, remaining))
        agent_timeout = max(60, min(args.agent_timeout_sec, llm_timeout))
        llm_timeout, agent_timeout = cap_targeted_single_agent_timeouts(
            run_agents=list(run_agents),
            current_source=initial_agent_source,
            llm_timeout_sec=llm_timeout,
            agent_timeout_sec=agent_timeout,
            explicit_llm_timeout=bool(explicit_flags.get("llm_timeout_sec")),
            explicit_agent_timeout=bool(explicit_flags.get("agent_timeout_sec")),
            final_pass=bool(args.final_pass),
        )
        round_agent_timeout_overrides, round_agent_timeout_meta = derive_needs_fix_fast_agent_timeout_overrides(
            task_id=str(args.task_id),
            delivery_profile=str(args.delivery_profile),
            security_profile=str(args.security_profile),
            run_agents=list(run_agents),
            diff_mode=str(args.diff_mode),
            llm_timeout_sec=llm_timeout,
            agent_timeout_sec=agent_timeout,
        )
        predicted_llm_budget_sec, llm_budget_prediction = derive_llm_round_budget_prediction(
            task_id=str(args.task_id),
            delivery_profile=str(args.delivery_profile),
            security_profile=str(args.security_profile),
            run_agents=list(run_agents),
            diff_mode=str(args.diff_mode),
            llm_timeout_sec=llm_timeout,
            agent_timeout_sec=agent_timeout,
            agent_timeout_overrides=round_agent_timeout_overrides,
        )
        llm_budget_prediction = {
            **llm_budget_prediction,
            "round": round_no,
            "remaining_before_sec": int(remaining),
            "agents": list(run_agents),
        }
        llm_budget_prediction_history.append(llm_budget_prediction)
        if remaining < int(predicted_llm_budget_sec):
            timeline.append(
                {
                    "name": f"pipeline-llm-round-{round_no}",
                    "status": "fail",
                    "rc": 124,
                    "duration_sec": 0,
                    "remaining_before_sec": int(remaining),
                    "remaining_after_sec": int(remaining),
                    "cmd": [],
                    "log_file": "",
                    "reported_out_dir": "",
                    "summary_file": "",
                    "error": "predicted_insufficient_llm_budget",
                    "predicted_budget_sec": int(predicted_llm_budget_sec),
                    "budget_prediction": llm_budget_prediction,
                }
            )
            if not rounds:
                summary = {
                    "cmd": "sc-needs-fix-fast",
                    "task_id": str(args.task_id),
                    "status": "fail",
                    "reason": "insufficient_llm_budget_before_llm",
                    "out_dir": str(out_dir),
                    "timeline": timeline,
                    "elapsed_sec": elapsed_sec(script_start),
                    "delivery_profile": str(args.delivery_profile),
                    "llm_budget_prediction_history": llm_budget_prediction_history,
                }
                _write_summary(out_dir, summary)
                print(f"SC_NEEDS_FIX_FAST status=fail out={out_dir}")
                return 1
            break
        llm_cmd = [
            py,
            "-3",
            "scripts/sc/run_review_pipeline.py",
            "--task-id",
            str(args.task_id),
            "--delivery-profile",
            str(args.delivery_profile),
            "--security-profile",
            str(args.security_profile),
            "--skip-test",
            "--skip-acceptance",
            "--review-template",
            str(args.review_template),
            "--llm-backend",
            str(args.llm_backend),
            "--llm-agents",
            ",".join(run_agents),
            "--llm-diff-mode",
            str(args.diff_mode),
            "--llm-base",
            str(args.base),
            "--llm-timeout-sec",
            str(llm_timeout),
            "--llm-agent-timeout-sec",
            str(agent_timeout),
        ]
        if round_agent_timeout_overrides:
            llm_cmd += ["--llm-agent-timeouts", format_agent_timeout_overrides(round_agent_timeout_overrides)]

        print(f"[needs-fix-fast] step: run_review_pipeline llm round={round_no} agents={','.join(run_agents)}")
        llm_step = run_step(
            name=f"pipeline-llm-round-{round_no}",
            cmd=llm_cmd,
            out_dir=out_dir,
            timeout_sec=min(args.step_timeout_sec, llm_timeout + 60),
            script_start=script_start,
            budget_min=args.time_budget_min,
        )
        timeline.append(llm_step)

        round_result: dict[str, Any] = {
            "round": round_no,
            "round_index": round_no,
            "status": str(llm_step.get("status") or ""),
            "agents": list(run_agents),
            "run_agents": list(run_agents),
            "agent_source": initial_agent_source if round_no == 1 else ("previous-round-needs-fix" if args.rerun_failing_only else "configured-defaults"),
            "rc": llm_step["rc"],
            "remaining_before_sec": int(llm_step.get("remaining_before_sec") or 0),
            "remaining_after_sec": int(llm_step.get("remaining_after_sec") or 0),
            "reported_out_dir": str(llm_step.get("reported_out_dir") or ""),
            "log_file": str(llm_step.get("log_file") or ""),
            "summary_file": "",
            "verdicts": {},
            "needs_fix_agents": [],
            "timeout_agents": [],
        }
        if round_agent_timeout_overrides:
            round_result["agent_timeout_overrides"] = round_agent_timeout_overrides
            round_result["agent_timeout_override_reason"] = round_agent_timeout_meta
            round_agent_timeout_overrides_history.append(
                {
                    "round": round_no,
                    "overrides": round_agent_timeout_overrides,
                    "reason": round_agent_timeout_meta,
                }
            )

        pipeline_summary_file = Path(llm_step["summary_file"]) if llm_step["summary_file"] else None
        llm_child_step: dict[str, Any] = {}
        if pipeline_summary_file and pipeline_summary_file.exists():
            llm_child_step = find_pipeline_step(pipeline_summary_file, "sc-llm-review")
        llm_summary_file = Path(str(llm_child_step.get("summary_file") or "")) if llm_child_step else None
        round_result["summary_file"] = str(llm_summary_file) if (llm_summary_file and llm_summary_file.exists()) else ""

        verdicts: dict[str, str] = {}
        if llm_step["rc"] == 0 and llm_summary_file and llm_summary_file.exists():
            verdicts = parse_llm_verdicts(llm_summary_file)
            if llm_summary_file.parent.exists():
                copy_llm_round_artifacts(llm_summary_file.parent, out_dir, round_no)

        for agent in run_agents:
            verdict = normalize_verdict(verdicts.get(agent))
            votes.setdefault(agent, []).append(verdict)
            round_result["verdicts"][agent] = verdict
        timeout_agents = sorted(
            [
                agent
                for agent in run_agents
                if int(llm_step.get("rc") or 0) == 124 and round_result["verdicts"].get(agent) == "Unknown"
            ]
        )
        round_result["timeout_agents"] = timeout_agents
        if timeout_agents:
            if not round_result["summary_file"]:
                round_result["failure_kind"] = "timeout-no-summary"
        elif int(llm_step.get("rc") or 0) == 124:
            round_result["failure_kind"] = "timeout"

        needs_fix_agents = [a for a, v in round_result["verdicts"].items() if v == "Needs Fix"]
        round_result["needs_fix_agents"] = needs_fix_agents
        round_result["needs_fix_signature"] = _round_needs_fix_signature(round_result)
        round_result["verdict"] = _round_verdict(round_result["verdicts"], rc=int(llm_step.get("rc") or 0))
        rounds.append(round_result)

        if len(rounds) >= 2:
            previous_signature = rounds[-2].get("needs_fix_signature") if isinstance(rounds[-2].get("needs_fix_signature"), list) else []
            current_signature = rounds[-1].get("needs_fix_signature") if isinstance(rounds[-1].get("needs_fix_signature"), list) else []
            if previous_signature and current_signature and previous_signature == current_signature:
                stop_loss = {
                    "triggered": True,
                    "kind": "repeated-needs-fix-signature",
                    "round": round_no,
                    "signature": current_signature,
                }
                break

        if not needs_fix_agents:
            break
        if round_no >= args.max_rounds:
            break
        run_agents = needs_fix_agents if args.rerun_failing_only else list(agents)
        participating_agents.update(run_agents)

    final_verdicts = {
        agent: (majority_verdict(votes.get(agent, [])) if votes.get(agent) else ("OK" if agent not in participating_agents else "Unknown"))
        for agent in agents
    }
    final_needs_fix = sorted([a for a, v in final_verdicts.items() if v == "Needs Fix"])
    final_unknown = sorted([a for a, v in final_verdicts.items() if v == "Unknown"])
    status, reason = _derive_final_status(final_verdicts=final_verdicts, rounds=rounds)
    if bool(stop_loss.get("triggered")) and status == "needs-fix":
        reason = "repeated_needs_fix_no_progress"
    summary = {
        "cmd": "sc-needs-fix-fast",
        "task_id": str(args.task_id),
        "status": status,
        "reason": reason,
        "out_dir": str(out_dir),
        "elapsed_sec": elapsed_sec(script_start),
        "time_budget_min": int(args.time_budget_min),
        "args": {
            "delivery_profile": str(args.delivery_profile),
            "agents": agents,
            "initial_run_agents": list(run_agents if not rounds else rounds[0].get("agents") or []),
            "initial_run_agents_source": initial_agent_source,
            "participating_agents": sorted(participating_agents),
            "max_rounds": int(args.max_rounds),
            "rerun_failing_only": bool(args.rerun_failing_only),
            "security_profile": str(args.security_profile),
            "review_template": str(args.review_template),
            "base": str(args.base),
            "diff_mode": str(args.diff_mode),
            "final_pass": bool(args.final_pass),
            "skip_sc_test": bool(args.skip_sc_test),
            "min_llm_budget_min": int(args.min_llm_budget_min),
        },
        "profile_floor": profile_floor_decision,
        "deterministic_plan": deterministic_plan,
        "route_preflight": route_payload if not bool(args.final_pass) else {},
        "agent_timeout_override_history": round_agent_timeout_overrides_history,
        "llm_budget_prediction_history": llm_budget_prediction_history,
        "timeline": timeline,
        "rounds": rounds,
        "stop_loss": stop_loss,
        "votes": votes,
        "final_verdicts": final_verdicts,
        "final_needs_fix_agents": final_needs_fix,
        "final_unknown_agents": final_unknown,
    }
    summary.update(_build_timeline_bottleneck_summary(timeline=timeline, rounds=rounds))
    _write_summary(out_dir, summary)

    if status == "ok":
        print(f"SC_NEEDS_FIX_FAST status=ok out={out_dir}")
        return 0

    print(f"SC_NEEDS_FIX_FAST status={status} out={out_dir}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
