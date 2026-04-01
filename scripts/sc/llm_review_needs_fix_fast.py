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
import time
import uuid
from pathlib import Path
from typing import Any

from _util import ci_dir, repo_root, run_cmd, split_csv, today_str, write_json, write_text


OUT_RE = re.compile(r"\bout=([^\r\n]+)")


def normalize_verdict(value: str | None) -> str:
    raw = (value or "").strip().lower()
    if raw in {"ok", "pass", "passed"}:
        return "OK"
    if raw in {"needs fix", "needs_fix", "need fix", "fail", "failed"}:
        return "Needs Fix"
    return "Unknown"


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


def try_reuse_latest_deterministic_step(
    *,
    task_id: str,
    security_profile: str,
    skip_sc_test: bool,
    planned_cmd: list[str],
    out_dir: Path,
    script_start: float,
    budget_min: int,
) -> dict[str, Any] | None:
    latest_index = repo_root() / "logs" / "ci" / today_str() / f"sc-review-pipeline-task-{task_id}" / "latest.json"
    latest_payload = read_json(latest_index)
    latest_out_dir = Path(str(latest_payload.get("latest_out_dir") or "")).resolve() if str(latest_payload.get("latest_out_dir") or "").strip() else None
    summary_file = Path(str(latest_payload.get("summary_path") or "")).resolve() if str(latest_payload.get("summary_path") or "").strip() else None
    execution_context_file = (
        Path(str(latest_payload.get("execution_context_path") or "")).resolve()
        if str(latest_payload.get("execution_context_path") or "").strip()
        else None
    )
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
    if str(execution_context.get("security_profile") or "").strip().lower() != str(security_profile).strip().lower():
        return None
    if not _git_snapshot_matches(execution_context):
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
                "[needs-fix-fast] reused latest deterministic pipeline artifacts",
                f"task_id={task_id}",
                f"run_id={str(latest_payload.get('run_id') or '').strip()}",
                f"summary_file={summary_file}",
                f"execution_context_file={execution_context_file}",
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
        "reuse_reason": "latest_successful_deterministic_pipeline",
    }


def find_pipeline_step(pipeline_summary_path: Path, step_name: str) -> dict[str, Any]:
    payload = read_json(pipeline_summary_path)
    return find_pipeline_step_dict(payload, step_name)


def elapsed_sec(start_monotonic: float) -> int:
    return int(max(0.0, time.monotonic() - start_monotonic))


def remain_sec(start_monotonic: float, budget_min: int) -> int:
    return int(max(0.0, budget_min * 60 - elapsed_sec(start_monotonic)))


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Fast stop-loss workflow for llm_review Needs Fix.")
    ap.add_argument("--task-id", required=True, help="Task id (for task-scoped runs).")
    ap.add_argument("--security-profile", default="host-safe", help="Security profile (default: host-safe).")
    ap.add_argument(
        "--agents",
        default="code-reviewer,security-auditor,test-automator,semantic-equivalence-auditor",
        help="Comma-separated llm_review agents.",
    )
    ap.add_argument("--review-template", default="scripts/sc/templates/llm_review/bmad-godot-review-template.txt")
    ap.add_argument("--base", default="origin/main", help="Git base for diff-mode full.")
    ap.add_argument("--diff-mode", default="full", help="llm_review diff mode (full/none/committed).")
    ap.add_argument("--max-rounds", type=int, default=2, help="Maximum llm_review rounds (>=1).")
    ap.add_argument(
        "--rerun-failing-only",
        action="store_true",
        help="From round 2, rerun only agents that were Needs Fix in previous round.",
    )
    ap.add_argument("--time-budget-min", type=int, default=45, help="Hard time budget in minutes.")
    ap.add_argument("--llm-timeout-sec", type=int, default=2400, help="llm_review --timeout-sec.")
    ap.add_argument("--agent-timeout-sec", type=int, default=480, help="llm_review --agent-timeout-sec.")
    ap.add_argument("--step-timeout-sec", type=int, default=3600, help="Outer timeout for each subprocess step.")
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


def main() -> int:
    args = build_parser().parse_args()
    if args.max_rounds < 1:
        print("[needs-fix-fast] ERROR: --max-rounds must be >= 1")
        return 2

    agents = split_csv(args.agents)
    if not agents:
        print("[needs-fix-fast] ERROR: --agents resolved to empty list")
        return 2

    script_start = time.monotonic()
    out_dir = ci_dir(f"sc-needs-fix-fast-task-{args.task_id}")
    write_text(out_dir / "run_id.txt", uuid.uuid4().hex + "\n")

    timeline: list[dict[str, Any]] = []
    py = args.python

    deterministic_cmd = [
        py,
        "-3",
        "scripts/sc/run_review_pipeline.py",
        "--task-id",
        str(args.task_id),
        "--security-profile",
        str(args.security_profile),
        "--skip-llm-review",
        "--llm-base",
        str(args.base),
        "--llm-diff-mode",
        str(args.diff_mode),
    ]
    if args.skip_sc_test:
        deterministic_cmd.append("--skip-test")
    deterministic_step = try_reuse_latest_deterministic_step(
        task_id=str(args.task_id),
        security_profile=str(args.security_profile),
        skip_sc_test=bool(args.skip_sc_test),
        planned_cmd=deterministic_cmd,
        out_dir=out_dir,
        script_start=script_start,
        budget_min=args.time_budget_min,
    )
    if deterministic_step is None:
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
        write_json(out_dir / "summary.json", summary)
        print(f"SC_NEEDS_FIX_FAST status=fail out={out_dir}")
        return 1

    votes: dict[str, list[str]] = {agent: [] for agent in agents}
    rounds: list[dict[str, Any]] = []
    run_agents = list(agents)
    for round_no in range(1, args.max_rounds + 1):
        if not run_agents:
            break

        remaining = remain_sec(script_start, args.time_budget_min)
        if remaining <= 0:
            break

        llm_timeout = max(120, min(args.llm_timeout_sec, remaining))
        agent_timeout = max(60, min(args.agent_timeout_sec, llm_timeout))
        llm_cmd = [
            py,
            "-3",
            "scripts/sc/run_review_pipeline.py",
            "--task-id",
            str(args.task_id),
            "--security-profile",
            str(args.security_profile),
            "--skip-test",
            "--skip-acceptance",
            "--review-template",
            str(args.review_template),
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
            "agents": run_agents,
            "rc": llm_step["rc"],
            "summary_file": "",
            "verdicts": {},
            "needs_fix_agents": [],
        }

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

        needs_fix_agents = [a for a, v in round_result["verdicts"].items() if v == "Needs Fix"]
        round_result["needs_fix_agents"] = needs_fix_agents
        rounds.append(round_result)

        if not needs_fix_agents:
            break
        if round_no >= args.max_rounds:
            break
        run_agents = needs_fix_agents if args.rerun_failing_only else list(agents)

    final_verdicts = {agent: majority_verdict(votes.get(agent, [])) for agent in agents}
    final_needs_fix = sorted([a for a, v in final_verdicts.items() if v == "Needs Fix"])
    status = "ok" if not final_needs_fix else "needs-fix"
    summary = {
        "cmd": "sc-needs-fix-fast",
        "task_id": str(args.task_id),
        "status": status,
        "out_dir": str(out_dir),
        "elapsed_sec": elapsed_sec(script_start),
        "time_budget_min": int(args.time_budget_min),
        "args": {
            "agents": agents,
            "max_rounds": int(args.max_rounds),
            "rerun_failing_only": bool(args.rerun_failing_only),
            "security_profile": str(args.security_profile),
            "review_template": str(args.review_template),
            "base": str(args.base),
            "diff_mode": str(args.diff_mode),
            "skip_sc_test": bool(args.skip_sc_test),
        },
        "timeline": timeline,
        "rounds": rounds,
        "votes": votes,
        "final_verdicts": final_verdicts,
        "final_needs_fix_agents": final_needs_fix,
    }
    write_json(out_dir / "summary.json", summary)

    if status == "ok":
        print(f"SC_NEEDS_FIX_FAST status=ok out={out_dir}")
        return 0

    print(f"SC_NEEDS_FIX_FAST status=needs-fix out={out_dir}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
