#!/usr/bin/env python3
"""
sc-llm-review: Optional LLM review runner (local only).

This script approximates the "6 subagents" style review used in Claude Code by
invoking `codex exec` with role-specific prompts and saving outputs to:
  logs/ci/<YYYY-MM-DD>/sc-llm-review/

Stop-loss design:
  - Default is soft: failures/empty outputs become "skipped" (summary=warn).
  - Use --strict to fail the run when an agent cannot produce output.

Deterministic mapping:
  Two agents are mapped to sc-acceptance-check artifacts (no LLM call):
    - adr-compliance-checker
    - performance-slo-validator
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _acceptance_artifacts import build_acceptance_evidence
from _deterministic_review import DETERMINISTIC_AGENTS, build_deterministic_review
from _taskmaster import TaskmasterTriplet, resolve_triplet
from _util import ci_dir, repo_root, run_cmd, split_csv, today_str, write_json, write_text


@dataclass(frozen=True)
class ReviewResult:
    agent: str
    status: str  # ok|fail|skipped
    rc: int | None = None
    cmd: list[str] | None = None
    output: str | None = None
    prompt_path: str | None = None
    output_path: str | None = None
    details: dict[str, Any] | None = None


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _truncate(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def _build_task_context(triplet: TaskmasterTriplet | None) -> str:
    if not triplet:
        return ""
    title = str(triplet.master.get("title") or "").strip()
    adr = ", ".join(triplet.adr_refs()) or "(none)"
    ch = ", ".join(triplet.arch_refs()) or "(none)"
    overlay = triplet.overlay() or "(none)"
    master_details = _truncate(str(triplet.master.get("details") or ""), max_chars=2_000)
    back_details = _truncate(str((triplet.back or {}).get("details") or ""), max_chars=2_000)
    gameplay_details = _truncate(str((triplet.gameplay or {}).get("details") or ""), max_chars=2_000)
    return "\n".join(
        [
            "Task Context:",
            f"- id: {triplet.task_id}",
            f"- title: {title}",
            f"- adrRefs: {adr}",
            f"- archRefs: {ch}",
            f"- overlay: {overlay}",
            "",
            "Task Details (truncated):",
            f"- master.details: {master_details or '(empty)'}",
            f"- tasks_back.details: {back_details or '(empty)'}",
            f"- tasks_gameplay.details: {gameplay_details or '(empty)'}",
        ]
    )

def _resolve_threat_model(value: str | None) -> str:
    s = str(value or "").strip().lower()
    if not s:
        s = str(os.environ.get("SC_THREAT_MODEL") or "").strip().lower()
    return s if s in {"singleplayer", "modded", "networked"} else "singleplayer"


def _build_threat_model_context(threat_model: str) -> str:
    if threat_model == "networked":
        note = "Assume network features may exist or be added soon; prioritize boundary checks, rate limits, and allowlists."
    elif threat_model == "modded":
        note = "Assume mods/plugins may exist; prioritize trust boundaries, input validation, and stop-loss logging."
    else:
        note = "Single-player/offline default; prioritize deterministic correctness, resource limits, and avoid over-hardening."
    return "\n".join(
        [
            "Threat Model:",
            f"- mode: {threat_model}",
            f"- guidance: {note}",
        ]
    )


def _load_optional_agent_prompt(rel_path: str) -> str | None:
    p = repo_root() / rel_path
    if p.is_file():
        return _read_text(p)
    return None


def _default_agent_prompt(agent: str) -> str:
    return "\n".join(
        [
            f"Role: {agent}",
            "",
            "Review the changes and output a concise Markdown report with:",
            "- P0/P1/P2/P3 findings (if any)",
            "- specific file paths + what to change",
            "- a short 'Verdict: OK | Needs Fix' line at the end",
            "",
            "Avoid speculative claims. Focus on evidence in the diff.",
        ]
    )


def _resolve_claude_agents_root(value: str | None) -> Path:
    if value and str(value).strip():
        return Path(str(value).strip())
    env = os.environ.get("CLAUDE_AGENTS_ROOT")
    if env and env.strip():
        return Path(env.strip())
    return Path.home() / ".claude" / "agents"


def _load_agent_prompt_blob(agent: str, *, claude_agents_root: Path) -> tuple[str | None, Path | None]:
    root = repo_root()
    project_specific = {
        "adr-compliance-checker": root / ".claude" / "agents" / "adr-compliance-checker.md",
        "performance-slo-validator": root / ".claude" / "agents" / "performance-slo-validator.md",
    }
    lst97_agents = {"architect-reviewer", "code-reviewer", "security-auditor", "test-automator"}

    candidates: list[Path] = []
    if agent in project_specific:
        candidates.append(project_specific[agent])
        candidates.append(claude_agents_root / f"{agent}.md")
    elif agent in lst97_agents:
        candidates.append(root / ".claude" / "agents" / "lst97" / f"{agent}.md")
        candidates.append(claude_agents_root / "lst97" / f"{agent}.md")
    else:
        candidates.append(root / ".claude" / "agents" / f"{agent}.md")
        candidates.append(claude_agents_root / f"{agent}.md")

    for p in candidates:
        if p.is_file():
            return _read_text(p), p
    return None, None


def _agent_prompt(agent: str, *, claude_agents_root: Path) -> tuple[str, dict[str, Any]]:
    project_specific = {
        "adr-compliance-checker": ".claude/agents/adr-compliance-checker.md",
        "performance-slo-validator": ".claude/agents/performance-slo-validator.md",
    }
    base = _default_agent_prompt(agent)
    extra, source = _load_agent_prompt_blob(agent, claude_agents_root=claude_agents_root)
    if not extra or not source:
        extra = _load_optional_agent_prompt(project_specific.get(agent, ""))
        if not extra:
            return base, {"agent_prompt_source": None}
        extra_trim = _truncate(extra, max_chars=6_000)
        return "\n\n".join([base, "Project agent prompt (truncated):", extra_trim]), {"agent_prompt_source": project_specific.get(agent)}

    try:
        rel = str(source.relative_to(repo_root())).replace("\\", "/")
    except Exception:
        rel = str(source)

    extra_trim = _truncate(extra, max_chars=6_000)
    header = f"Agent prompt source: {rel}"
    return "\n\n".join([base, header, extra_trim]), {"agent_prompt_source": rel}


def _git_capture(args: list[str], *, timeout_sec: int) -> tuple[int, str]:
    return run_cmd(args, cwd=repo_root(), timeout_sec=timeout_sec)

def _auto_resolve_commit_for_task(task_id: str) -> str | None:
    task_id = str(task_id).strip()
    if not task_id:
        return None
    candidates = [
        f"Task [{task_id}]",
        f"Task [{task_id}]:",
        f"Task {task_id}:",
        f"Task {task_id} ",
        f"#{task_id}",
    ]
    for needle in candidates:
        rc, out = _git_capture(["git", "log", "--format=%H", "-n", "1", "--fixed-strings", "--grep", needle], timeout_sec=30)
        if rc != 0:
            continue
        sha = (out.strip().splitlines() or [""])[0].strip()
        if sha:
            return sha
    return None


def _build_diff_context(args: argparse.Namespace) -> str:
    if args.uncommitted:
        rc1, unstaged = _git_capture(["git", "diff", "--no-color"], timeout_sec=60)
        rc2, staged = _git_capture(["git", "diff", "--no-color", "--staged"], timeout_sec=60)
        rc3, untracked = _git_capture(["git", "ls-files", "--others", "--exclude-standard"], timeout_sec=30)
        if rc1 != 0 or rc2 != 0 or rc3 != 0:
            return _truncate("\n".join([unstaged, staged, untracked]), max_chars=40_000)
        blocks: list[str] = []
        if staged.strip():
            blocks.append("## Staged diff\n```diff\n" + staged.strip() + "\n```")
        if unstaged.strip():
            blocks.append("## Unstaged diff\n```diff\n" + unstaged.strip() + "\n```")
        if untracked.strip():
            blocks.append("## Untracked files\n```\n" + untracked.strip() + "\n```")
        return "\n\n".join(blocks) if blocks else "## Diff\n(no changes detected)\n"

    if args.commit:
        _rc, out = _git_capture(["git", "show", "--no-color", args.commit], timeout_sec=60)
        return "## Commit diff\n```diff\n" + _truncate(out.strip(), max_chars=60_000) + "\n```"

    base = args.base
    _rc, out = _git_capture(["git", "diff", "--no-color", f"{base}...HEAD"], timeout_sec=60)
    return f"## Diff vs {base}\n```diff\n" + _truncate(out.strip(), max_chars=60_000) + "\n```"


def _run_codex_exec(*, prompt: str, output_last_message: Path, timeout_sec: int) -> tuple[int, str, list[str]]:
    exe = shutil.which("codex")
    if not exe:
        return 127, "codex executable not found in PATH\n", ["codex"]

    cmd = [
        exe,
        "exec",
        "-s",
        "read-only",
        "-C",
        str(repo_root()),
        "--output-last-message",
        str(output_last_message),
        "-",
    ]
    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            encoding="utf-8",
            errors="ignore",
            cwd=str(repo_root()),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return 124, "codex exec timeout\n", cmd
    except Exception as exc:  # noqa: BLE001
        return 1, f"codex exec failed to start: {exc}\n", cmd
    return proc.returncode or 0, proc.stdout or "", cmd


def main() -> int:
    ap = argparse.ArgumentParser(description="sc-llm-review (optional local LLM review)")
    ap.add_argument("--task-id", default=None, help="Taskmaster id to include as review context (optional)")
    ap.add_argument(
        "--agents",
        default="",
        help="Comma-separated agent list. Empty = default 3 agents (architect-reviewer,code-reviewer,security-auditor). "
        "Special values: all|full to run the full suite.",
    )
    ap.add_argument("--base", default="main", help="Base branch for diff review (default: main)")
    ap.add_argument("--uncommitted", action="store_true", help="Review staged/unstaged/untracked changes")
    ap.add_argument("--commit", default=None, help="Review a single commit SHA")
    ap.add_argument(
        "--auto-commit",
        action="store_true",
        help="Auto-select the latest commit referencing the task id (looks for 'Task [<id>]' in commit messages). Requires --task-id.",
    )
    ap.add_argument(
        "--timeout-sec",
        type=int,
        default=900,
        help="Total timeout budget for the whole run (seconds). Use --agent-timeout-sec for per-agent cap.",
    )
    ap.add_argument("--agent-timeout-sec", type=int, default=300, help="Per-agent timeout cap (seconds).")
    ap.add_argument(
        "--agent-timeouts",
        default="",
        help="Optional per-agent override map: agent=seconds,agent=seconds (e.g. code-reviewer=600,security-auditor=450).",
    )
    ap.add_argument("--strict", action="store_true", help="Fail if any agent cannot produce output (default: soft)")
    ap.add_argument(
        "--threat-model",
        default=None,
        help="Threat model hint for review prompts: singleplayer|modded|networked (default: env SC_THREAT_MODEL or singleplayer).",
    )
    ap.add_argument(
        "--claude-agents-root",
        default=None,
        help="Claude agents root (default: env CLAUDE_AGENTS_ROOT or $env:USERPROFILE\\.claude\\agents). Used to load lst97 agent prompts.",
    )
    args = ap.parse_args()

    if args.uncommitted and args.commit:
        print("[sc-llm-review] ERROR: --uncommitted and --commit are mutually exclusive.")
        return 2
    if args.auto_commit and (args.uncommitted or args.commit):
        print("[sc-llm-review] ERROR: --auto-commit is mutually exclusive with --uncommitted/--commit.")
        return 2

    triplet = None
    if args.task_id:
        try:
            triplet = resolve_triplet(task_id=str(args.task_id).split(".", 1)[0])
        except Exception as exc:  # noqa: BLE001
            print(f"[sc-llm-review] ERROR: failed to resolve task: {exc}")
            return 2

    if args.auto_commit:
        if not triplet:
            print("[sc-llm-review] ERROR: --auto-commit requires --task-id.")
            return 2
        sha = _auto_resolve_commit_for_task(triplet.task_id)
        if not sha:
            print(f"[sc-llm-review] ERROR: failed to auto-resolve commit for Task {triplet.task_id}. Use --commit <sha>.")
            return 2
        args.commit = sha

    out_dir = ci_dir("sc-llm-review")
    claude_agents_root = _resolve_claude_agents_root(args.claude_agents_root)
    default_agents = [
        "architect-reviewer",
        "code-reviewer",
        "security-auditor",
    ]
    all_agents = [
        "adr-compliance-checker",
        "performance-slo-validator",
        "architect-reviewer",
        "code-reviewer",
        "security-auditor",
        "test-automator",
    ]
    agents_raw = str(args.agents or "").strip()
    if agents_raw.lower() in {"all", "full", "6"}:
        agents = all_agents
    else:
        agents = split_csv(args.agents) or default_agents

    total_timeout_sec = int(args.timeout_sec)
    if total_timeout_sec <= 0:
        print("[sc-llm-review] ERROR: --timeout-sec must be > 0.")
        return 2
    per_agent_timeout_sec = int(args.agent_timeout_sec)
    if per_agent_timeout_sec <= 0:
        print("[sc-llm-review] ERROR: --agent-timeout-sec must be > 0.")
        return 2

    per_agent_overrides: dict[str, int] = {}
    for item in split_csv(args.agent_timeouts):
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k or not v:
            continue
        try:
            sec = int(v)
        except ValueError:
            continue
        if sec > 0:
            per_agent_overrides[k] = sec

    ctx = _build_task_context(triplet)
    threat_model = _resolve_threat_model(args.threat_model)
    threat_ctx = _build_threat_model_context(threat_model)
    acceptance_ctx = ""
    acceptance_meta: dict[str, Any] | None = None
    if triplet:
        acceptance_ctx, acceptance_meta = build_acceptance_evidence(task_id=triplet.task_id)
    diff_ctx = _build_diff_context(args)

    results: list[ReviewResult] = []
    hard_fail = False
    had_warnings = False
    start_ts = time.monotonic()
    deadline_ts = start_ts + total_timeout_sec

    for agent in agents:
        remaining = int(deadline_ts - time.monotonic())
        if remaining <= 0:
            status = "fail" if args.strict else "skipped"
            if status != "ok":
                had_warnings = True
            if status == "fail":
                hard_fail = True
            results.append(
                ReviewResult(
                    agent=agent,
                    status=status,
                    rc=124,
                    cmd=None,
                    prompt_path=None,
                    output_path=None,
                    details={
                        "note": "Skipped due to total timeout budget exhausted.",
                        "total_timeout_sec": total_timeout_sec,
                        "agent_timeout_sec": per_agent_overrides.get(agent, per_agent_timeout_sec),
                    },
                )
            )
            continue

        if agent in DETERMINISTIC_AGENTS:
            det = build_deterministic_review(agent=agent, out_dir=out_dir, task_id=triplet.task_id if triplet else None)
            verdict = (det.get("details") or {}).get("verdict")
            if det.get("status") != "ok" or verdict not in {None, "OK"}:
                had_warnings = True
            if det.get("status") == "fail":
                hard_fail = True
            results.append(
                ReviewResult(
                    agent=agent,
                    status=str(det.get("status")),
                    rc=det.get("rc"),
                    cmd=det.get("cmd"),
                    prompt_path=det.get("prompt_path"),
                    output_path=det.get("output_path"),
                    details={
                        "claude_agents_root": str(claude_agents_root),
                        "agent_prompt_source": _agent_prompt(agent, claude_agents_root=claude_agents_root)[1].get("agent_prompt_source"),
                        **(det.get("details") or {}),
                        "note": "Deterministic mapping: generated from sc-acceptance-check artifacts.",
                    },
                )
            )
            continue

        agent_prompt, prompt_meta = _agent_prompt(agent, claude_agents_root=claude_agents_root)
        blocks = [agent_prompt]
        if ctx:
            blocks.append(ctx)
        if threat_ctx:
            blocks.append(threat_ctx)
        if acceptance_ctx:
            blocks.append(acceptance_ctx)
        blocks.append(diff_ctx)
        prompt = "\n\n".join(blocks).strip() + "\n"
        prompt_path = out_dir / f"prompt-{agent}.md"
        output_path = out_dir / f"review-{agent}.md"
        trace_path = out_dir / f"trace-{agent}.log"
        write_text(prompt_path, prompt)

        agent_cap = per_agent_overrides.get(agent, per_agent_timeout_sec)
        effective_timeout = max(1, min(int(agent_cap), int(remaining)))
        rc, trace_out, cmd = _run_codex_exec(prompt=prompt, output_last_message=output_path, timeout_sec=effective_timeout)
        write_text(trace_path, trace_out)

        last_msg = ""
        if output_path.is_file():
            last_msg = output_path.read_text(encoding="utf-8", errors="ignore")

        status = "ok" if (rc == 0 and last_msg.strip()) else ("fail" if args.strict else "skipped")
        if status != "ok":
            had_warnings = True
        if status == "fail":
            hard_fail = True
        results.append(
            ReviewResult(
                agent=agent,
                status=status,
                rc=rc,
                cmd=cmd,
                prompt_path=str(prompt_path.relative_to(repo_root())).replace("\\", "/"),
                output_path=str(output_path.relative_to(repo_root())).replace("\\", "/"),
                details={
                    "trace": str(trace_path.relative_to(repo_root())).replace("\\", "/"),
                    "claude_agents_root": str(claude_agents_root),
                    "agent_prompt_source": prompt_meta.get("agent_prompt_source"),
                    "total_timeout_sec": total_timeout_sec,
                    "agent_timeout_sec": effective_timeout,
                    "note": "This step is best-effort. Use --strict to make it a hard gate.",
                },
            )
        )

    summary = {
        "cmd": "sc-llm-review",
        "date": today_str(),
        "mode": "uncommitted" if args.uncommitted else ("commit" if args.commit else "base"),
        "base": args.base,
        "commit": args.commit,
        "task_id": triplet.task_id if triplet else None,
        "strict": bool(args.strict),
        "threat_model": threat_model,
        "acceptance_meta": acceptance_meta,
        "status": "fail" if hard_fail else ("warn" if had_warnings else "ok"),
        "results": [r.__dict__ for r in results],
        "out_dir": str(out_dir),
    }
    write_json(out_dir / "summary.json", summary)

    print(f"SC_LLM_REVIEW status={summary['status']} out={out_dir}")
    return 0 if summary["status"] in ("ok", "warn") else 1


if __name__ == "__main__":
    raise SystemExit(main())
