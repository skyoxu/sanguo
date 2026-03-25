#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "scripts" / "python") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "python"))

from inspect_run import inspect_run_artifacts  # noqa: E402
from validate_recovery_docs import extract_repo_paths, is_readme, is_template, parse_fields  # noqa: E402


def _repo_rel(root: Path, path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _resolve_path(root: Path, raw: str) -> Path:
    path = Path(str(raw or "").strip())
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def _today() -> str:
    return date.today().isoformat()


def _default_output_paths(root: Path, task_id: str) -> tuple[Path, Path]:
    slug = f"task-{task_id}" if task_id else "task-unknown"
    base = root / "logs" / "ci" / _today() / "task-resume"
    return base / f"{slug}-resume-summary.json", base / f"{slug}-resume-summary.md"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def _extract_scalar_tokens(value: str) -> list[str]:
    text = str(value or "").strip()
    if not text or text.lower().startswith("n/a"):
        return []
    tokens: list[str] = []
    for chunk in text.split(","):
        item = chunk.strip().strip("`").strip()
        if item:
            tokens.append(item)
    return tokens


def _doc_match_score(*, fields: dict[str, str], task_id: str, run_id: str, latest_rel: str) -> int:
    score = 0
    task_tokens = _extract_scalar_tokens(fields.get("Related task id(s)", ""))
    run_tokens = _extract_scalar_tokens(fields.get("Related run id", ""))
    latest_tokens = [item.replace("\\", "/").lstrip("./") for item in extract_repo_paths(fields.get("Related latest.json", ""))]
    if task_id and task_id in task_tokens:
        score += 100
    if run_id and run_id in run_tokens:
        score += 10
    if latest_rel and latest_rel in latest_tokens:
        score += 1
    return score


def _find_related_docs(root: Path, dir_name: str, *, task_id: str, run_id: str, latest_rel: str) -> list[str]:
    doc_dir = root / dir_name
    if not doc_dir.exists():
        return []
    matches: list[tuple[int, float, str]] = []
    for path in doc_dir.glob("*.md"):
        if is_readme(path) or is_template(path):
            continue
        fields = parse_fields(path)
        score = _doc_match_score(fields=fields, task_id=task_id, run_id=run_id, latest_rel=latest_rel)
        if score <= 0:
            continue
        matches.append((score, path.stat().st_mtime, _repo_rel(root, path)))
    matches.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    return [item[2] for item in matches]


def _load_optional_agent_review(root: Path, out_dir_rel: str) -> dict[str, Any]:
    if not out_dir_rel:
        return {}
    path = _resolve_path(root, f"{out_dir_rel}/agent-review.json")
    if not path.exists():
        return {}
    try:
        payload = _read_json(path)
    except Exception:
        return {}
    payload["_path"] = _repo_rel(root, path)
    return payload


def _active_task_json_path(root: Path, task_id: str) -> Path:
    return root / "logs" / "ci" / "active-tasks" / f"task-{task_id}.active.json"


def _load_active_task(root: Path, task_id: str) -> dict[str, Any]:
    if not task_id:
        return {}
    path = _active_task_json_path(root, task_id)
    if not path.exists():
        return {}
    try:
        payload = _read_json(path)
    except Exception:
        return {}
    payload["_path"] = _repo_rel(root, path)
    return payload


def _fallback_recommendation(inspection: dict[str, Any], task_id: str) -> tuple[str, str, str, list[str]]:
    failure = inspection.get("failure") or {}
    failure_code = str(failure.get("code") or "").strip().lower()
    failed_step = str(inspection.get("failed_step") or "").strip()
    repair_status = str(inspection.get("repair_status") or "").strip().lower()
    signals = [f"failure.code={failure_code or 'unknown'}"]
    if failed_step:
        signals.append(f"failed_step={failed_step}")
    if repair_status:
        signals.append(f"repair_status={repair_status}")
    if failure_code == "ok":
        return (
            "none",
            "inspection",
            "Inspection reported status=ok, so no follow-up action is required before continuing local work.",
            signals,
        )
    if failure_code in {"schema-invalid", "stale-latest", "artifact-missing"}:
        return (
            "rerun",
            "inspection",
            str(failure.get("message") or "Recovery artifacts are unreliable, so rerun the task pipeline from a clean producer run.").strip(),
            signals,
        )
    if failure_code in {"step-failed", "review-needs-fix"} and task_id:
        step_text = failed_step or "the first failing stage"
        return (
            "resume",
            "inspection",
            f"Inspection shows that {step_text} is the current blocking point, so resume is the lowest-cost recovery path after fixing that issue.",
            signals,
        )
    if failure_code == "aborted":
        return (
            "rerun",
            "inspection",
            "The latest task run was intentionally aborted, so restart from a fresh run instead of resuming the frozen artifact set.",
            signals,
        )
    return (
        "inspect",
        "inspection",
        str(failure.get("message") or "Inspect the latest artifacts before choosing resume or fork.").strip(),
        signals,
    )


def _recommendation_from_agent_review(agent_review: dict[str, Any]) -> tuple[str, str, list[str]] | None:
    explain = agent_review.get("explain") if isinstance(agent_review.get("explain"), dict) else {}
    recommended_action = str(explain.get("recommended_action") or agent_review.get("recommended_action") or "").strip().lower()
    if not recommended_action:
        return None
    summary = str(explain.get("summary") or "").strip()
    signals = [f"agent_review.recommended_action={recommended_action}"]
    review_verdict = str(agent_review.get("review_verdict") or "").strip().lower()
    if review_verdict:
        signals.append(f"agent_review.review_verdict={review_verdict}")
    reasons = [str(item).strip() for item in (explain.get("reasons") or []) if str(item).strip()]
    for item in reasons:
        signals.append(f"agent_review.reason={item}")
    return recommended_action, (summary or "Agent review supplied the recovery recommendation."), signals


def _candidate_commands(task_id: str, latest: str) -> dict[str, str]:
    inspect_cmd = ["py", "-3", "scripts/python/inspect_run.py", "--kind", "pipeline"]
    if latest:
        inspect_cmd += ["--latest", latest]
    elif task_id:
        inspect_cmd += ["--task-id", task_id]
    commands = {
        "inspect": " ".join(inspect_cmd),
        "resume": "",
        "fork": "",
        "rerun": "",
    }
    if task_id:
        commands["resume"] = f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id} --resume"
        commands["fork"] = f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id} --fork"
        commands["rerun"] = f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id}"
    return commands


def build_resume_payload(
    *,
    repo_root: Path,
    task_id: str,
    latest: str,
    run_id: str,
) -> tuple[int, dict[str, Any]]:
    active_task = _load_active_task(repo_root, task_id)
    if not latest:
        latest = str(((active_task.get("paths") or {}).get("latest_json")) or "").strip()
    if not run_id:
        run_id = str(active_task.get("run_id") or "").strip()
    inspection_rc, inspection = inspect_run_artifacts(
        repo_root=repo_root,
        latest=latest,
        kind="pipeline",
        task_id=task_id,
        run_id=run_id,
    )
    resolved_task_id = str(inspection.get("task_id") or task_id or "").strip()
    resolved_run_id = str(inspection.get("run_id") or run_id or "").strip()
    latest_rel = str(((inspection.get("paths") or {}).get("latest")) or "").strip()
    out_dir_rel = str(((inspection.get("paths") or {}).get("out_dir")) or "").strip()
    active_task = _load_active_task(repo_root, resolved_task_id)
    agent_review = _load_optional_agent_review(repo_root, out_dir_rel)
    agent_review_signal = _recommendation_from_agent_review(agent_review)
    if agent_review_signal is not None:
        recommended_action, recommendation_reason, blocking_signals = agent_review_signal
        recommendation_source = "agent-review"
    else:
        recommended_action, recommendation_source, recommendation_reason, blocking_signals = _fallback_recommendation(inspection, resolved_task_id)
    plans = _find_related_docs(repo_root, "execution-plans", task_id=resolved_task_id, run_id=resolved_run_id, latest_rel=latest_rel)
    logs = _find_related_docs(repo_root, "decision-logs", task_id=resolved_task_id, run_id=resolved_run_id, latest_rel=latest_rel)
    payload: dict[str, Any] = {
        "task_id": resolved_task_id,
        "run_id": resolved_run_id,
        "recommended_action": recommended_action,
        "recommended_action_why": recommendation_reason,
        "decision_basis": recommendation_source,
        "blocking_signals": blocking_signals,
        "recommendation_source": recommendation_source,
        "recommendation_reason": recommendation_reason,
        "candidate_commands": _candidate_commands(resolved_task_id, latest or latest_rel),
        "inspection_exit_code": inspection_rc,
        "inspection": inspection,
        "related_execution_plans": plans,
        "latest_execution_plan": plans[0] if plans else "",
        "related_decision_logs": logs,
        "latest_decision_log": logs[0] if logs else "",
        "agent_review": {
            "path": str(agent_review.get("_path") or ""),
            "review_verdict": str(agent_review.get("review_verdict") or "").strip(),
            "recommended_action": str(((agent_review.get("explain") or {}).get("recommended_action") or agent_review.get("recommended_action") or "")).strip(),
            "summary": str(((agent_review.get("explain") or {}).get("summary") or "")).strip(),
        },
        "active_task": {
            "path": str(active_task.get("_path") or ""),
            "status": str(active_task.get("status") or "").strip(),
            "recommended_action": str(active_task.get("recommended_action") or "").strip(),
            "recommended_action_why": str(active_task.get("recommended_action_why") or "").strip(),
            "latest_json": str(((active_task.get("paths") or {}).get("latest_json")) or "").strip(),
        },
    }
    return inspection_rc, payload


def _render_markdown(payload: dict[str, Any]) -> str:
    inspection = payload.get("inspection") or {}
    failure = inspection.get("failure") or {}
    paths = inspection.get("paths") or {}
    commands = payload.get("candidate_commands") or {}
    def _line(key: str, value: str) -> str:
        return f"- {key}: {value}"
    lines = [
        "# Task Resume Summary",
        "",
        _line("Task id", f"`{payload.get('task_id')}`" if payload.get("task_id") else "n/a"),
        _line("Run id", f"`{payload.get('run_id')}`" if payload.get("run_id") else "n/a"),
        _line("Recommended action", str(payload.get("recommended_action") or "none")),
        _line("Recommended action why", str(payload.get("recommended_action_why") or "n/a")),
        _line("Decision basis", str(payload.get("decision_basis") or "inspection")),
        _line("Recommendation source", str(payload.get("recommendation_source") or "inspection")),
        _line("Recommendation reason", str(payload.get("recommendation_reason") or "n/a")),
        _line("Inspection status", str(inspection.get("status") or "unknown")),
        _line("Failure code", str(failure.get("code") or "unknown")),
        _line("Latest pointer", f"`{paths.get('latest')}`" if paths.get("latest") else "n/a"),
        _line("Pipeline out dir", f"`{paths.get('out_dir')}`" if paths.get("out_dir") else "n/a"),
        _line("Latest execution plan", f"`{payload.get('latest_execution_plan')}`" if payload.get("latest_execution_plan") else "none"),
        _line("Latest decision log", f"`{payload.get('latest_decision_log')}`" if payload.get("latest_decision_log") else "none"),
        _line("Inspect command", f"`{commands.get('inspect')}`" if commands.get("inspect") else "n/a"),
        _line("Resume command", f"`{commands.get('resume')}`" if commands.get("resume") else "n/a"),
        _line("Fork command", f"`{commands.get('fork')}`" if commands.get("fork") else "n/a"),
        _line("Rerun command", f"`{commands.get('rerun')}`" if commands.get("rerun") else "n/a"),
    ]
    agent_review = payload.get("agent_review") or {}
    active_task = payload.get("active_task") or {}
    if agent_review.get("path"):
        lines.extend(
            [
                _line("Agent review", f"`{agent_review.get('path')}`"),
                _line("Agent review verdict", str(agent_review.get("review_verdict") or "unknown")),
                _line("Agent review summary", str(agent_review.get("summary") or "n/a")),
            ]
        )
    if active_task.get("path"):
        lines.extend(
            [
                _line("Active task summary", f"`{active_task.get('path')}`"),
                _line("Active task status", str(active_task.get("status") or "unknown")),
                _line("Active task recommendation", str(active_task.get("recommended_action") or "n/a")),
            ]
        )
    related_plans = payload.get("related_execution_plans") or []
    related_logs = payload.get("related_decision_logs") or []
    blocking_signals = payload.get("blocking_signals") or []
    lines.append(_line("Blocking signals", ", ".join(f"`{item}`" for item in blocking_signals) if blocking_signals else "none"))
    lines.append(_line("Related execution plans", ", ".join(f"`{item}`" for item in related_plans) if related_plans else "none"))
    lines.append(_line("Related decision logs", ", ".join(f"`{item}`" for item in related_logs) if related_logs else "none"))
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a task-scoped recovery summary from the latest pipeline artifacts.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--task-id", default="", help="Taskmaster task id.")
    parser.add_argument("--run-id", default="", help="Optional run id filter.")
    parser.add_argument("--latest", default="", help="Optional latest.json path.")
    parser.add_argument("--out-json", default="", help="Optional output JSON path.")
    parser.add_argument("--out-md", default="", help="Optional output Markdown path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    task_id = str(args.task_id or "").strip()
    latest = str(args.latest or "").strip()
    if not task_id and not latest:
        print("ERROR: pass --task-id or --latest", file=sys.stderr)
        return 2
    root = Path(str(args.repo_root or REPO_ROOT)).resolve()
    try:
        _, payload = build_resume_payload(
            repo_root=root,
            task_id=task_id,
            latest=latest,
            run_id=str(args.run_id or "").strip(),
        )
    except Exception as exc:
        print(f"ERROR: failed to build task resume summary: {exc}", file=sys.stderr)
        return 2

    out_json, out_md = _default_output_paths(root, str(payload.get("task_id") or task_id or "unknown"))
    if str(args.out_json or "").strip():
        out_json = _resolve_path(root, str(args.out_json or "").strip())
    if str(args.out_md or "").strip():
        out_md = _resolve_path(root, str(args.out_md or "").strip())
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    out_md.write_text(_render_markdown(payload), encoding="utf-8", newline="\n")
    print(f"TASK_RESUME status=ok out_json={_repo_rel(root, out_json)} out_md={_repo_rel(root, out_md)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
