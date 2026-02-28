#!/usr/bin/env python3
"""
Engine for sc-llm-review.
"""

from __future__ import annotations

import argparse
import time
from typing import Any

from _acceptance_artifacts import build_acceptance_evidence
from _deterministic_review import DETERMINISTIC_AGENTS, build_deterministic_review
from _llm_review_acceptance import build_acceptance_semantic_context, read_text, strip_emoji, truncate
from _llm_review_cli import (
    apply_prompt_budget,
    build_parser,
    parse_agent_timeout_overrides,
    resolve_agents,
    summary_base,
    validate_args,
)
from _llm_review_exec import auto_resolve_commit_for_task, build_diff_context, run_codex_exec
from _llm_review_models import ReviewResult
from _llm_review_prompting import (
    agent_prompt,
    build_task_context,
    build_threat_model_context,
    normalize_host_safe_needs_fix,
    parse_verdict,
    resolve_claude_agents_root,
    resolve_threat_model,
)
from _security_profile import build_security_profile_context, resolve_security_profile, security_profile_payload
from _taskmaster import resolve_triplet
from _util import ci_dir, repo_root, write_json, write_text


def _run_self_check(args: argparse.Namespace) -> int:
    out_dir = ci_dir("sc-llm-review-self-check")
    security_profile = resolve_security_profile(args.security_profile)
    errors = validate_args(args)
    summary = summary_base(mode="self-check", out_dir=out_dir, args=args, security_profile=security_profile, status="fail" if errors else "ok")
    summary["arg_validation"] = {"valid": len(errors) == 0, "errors": errors}
    write_json(out_dir / "summary.json", summary)
    for e in errors:
        print(f"[sc-llm-review] ERROR: {e}")
    print(f"SC_LLM_REVIEW_SELF_CHECK status={summary['status']} out={out_dir}")
    return 0 if not errors else 2


def _run_dry_plan(args: argparse.Namespace) -> int:
    security_profile = resolve_security_profile(args.security_profile)
    errors = validate_args(args)
    if errors:
        for e in errors:
            print(f"[sc-llm-review] ERROR: {e}")
        return 2

    triplet = None
    if args.task_id:
        try:
            triplet = resolve_triplet(task_id=str(args.task_id).split(".", 1)[0])
        except Exception as exc:  # noqa: BLE001
            print(f"[sc-llm-review] ERROR: failed to resolve task: {exc}")
            return 2

    agents = resolve_agents(args.agents, str(args.semantic_gate))
    overrides = parse_agent_timeout_overrides(args.agent_timeouts)
    per_agent_timeout_sec = int(args.agent_timeout_sec)
    out_dir = ci_dir(f"sc-llm-review-dry-plan-task-{triplet.task_id}") if triplet else ci_dir("sc-llm-review-dry-plan")
    plan = []
    for agent in agents:
        plan.append(
            {
                "agent": agent,
                "deterministic": agent in DETERMINISTIC_AGENTS,
                "timeout_sec": overrides.get(agent, per_agent_timeout_sec),
                "will_execute_llm": (not bool(args.prompts_only)) and agent not in DETERMINISTIC_AGENTS,
                "prompt_budget_gate": str(args.prompt_budget_gate),
                "prompt_max_chars": int(args.prompt_max_chars),
            }
        )
    summary = summary_base(mode="dry-run-plan", out_dir=out_dir, args=args, security_profile=security_profile, status="ok")
    summary["task_id"] = triplet.task_id if triplet else None
    summary["agents"] = agents
    summary["plan"] = plan
    write_json(out_dir / "summary.json", summary)
    print(f"SC_LLM_REVIEW_DRY_RUN_PLAN status={summary['status']} out={out_dir}")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    if bool(args.self_check):
        return _run_self_check(args)
    if bool(args.dry_run_plan):
        return _run_dry_plan(args)

    errors = validate_args(args)
    if errors:
        for e in errors:
            print(f"[sc-llm-review] ERROR: {e}")
        return 2

    triplet = None
    if args.task_id:
        try:
            triplet = resolve_triplet(task_id=str(args.task_id).split(".", 1)[0])
        except Exception as exc:  # noqa: BLE001
            print(f"[sc-llm-review] ERROR: failed to resolve task: {exc}")
            return 2

    if args.auto_commit:
        sha = auto_resolve_commit_for_task(triplet.task_id if triplet else "")
        if not sha:
            print("[sc-llm-review] ERROR: failed to auto-resolve commit. Use --commit <sha>.")
            return 2
        args.commit = sha

    codex_configs: list[str] = []
    if str(args.model_reasoning_effort or "").strip():
        codex_configs.append(f'model_reasoning_effort="{str(args.model_reasoning_effort).strip()}"')

    out_dir = ci_dir(f"sc-llm-review-task-{triplet.task_id}") if triplet else ci_dir("sc-llm-review")
    claude_agents_root = resolve_claude_agents_root(args.claude_agents_root)
    security_profile = resolve_security_profile(args.security_profile)
    agents = resolve_agents(args.agents, str(args.semantic_gate or "skip").strip().lower())
    per_agent_overrides = parse_agent_timeout_overrides(args.agent_timeouts)
    total_timeout_sec = int(args.timeout_sec)
    per_agent_timeout_sec = int(args.agent_timeout_sec)

    ctx = build_task_context(triplet)
    threat_model = resolve_threat_model(args.threat_model)
    threat_ctx = build_threat_model_context(threat_model)
    security_ctx = build_security_profile_context(security_profile)
    acceptance_ctx = ""
    acceptance_meta: dict[str, Any] | None = None
    if triplet:
        acceptance_ctx, acceptance_meta = build_acceptance_evidence(task_id=triplet.task_id)

    review_template = ""
    template_meta: dict[str, Any] = {"review_profile": str(args.review_profile)}
    template_path_arg = str(args.review_template or "").strip()
    if template_path_arg:
        p = repo_root() / template_path_arg
        if p.is_file():
            review_template = truncate(strip_emoji(read_text(p)), max_chars=8_000)
            template_meta["review_template_source"] = template_path_arg.replace("\\", "/")
        else:
            template_meta["review_template_source"] = None
            template_meta["review_template_error"] = f"missing:{template_path_arg}"
    elif str(args.review_profile).strip().lower() == "bmad-godot":
        p = repo_root() / "scripts/sc/templates/llm_review/bmad-godot-review-template.txt"
        if p.is_file():
            review_template = truncate(strip_emoji(read_text(p)), max_chars=8_000)
            template_meta["review_template_source"] = str(p.relative_to(repo_root())).replace("\\", "/")
        else:
            template_meta["review_template_source"] = None
            template_meta["review_template_error"] = "missing:built_in_bmad_godot_template"

    if str(args.semantic_gate).lower() == "require":
        acc_status = str((acceptance_meta or {}).get("acceptance_status") or "").strip().lower()
        if acc_status and acc_status != "ok":
            print("[sc-llm-review] ERROR: --semantic-gate require needs sc-acceptance-check status=ok.")
            return 1

    acceptance_semantic_ctx = ""
    acceptance_semantic_meta: dict[str, Any] | None = None
    if triplet and not bool(args.no_acceptance_semantic):
        try:
            acceptance_semantic_ctx, acceptance_semantic_meta = build_acceptance_semantic_context(triplet)
        except Exception:  # noqa: BLE001
            acceptance_semantic_ctx, acceptance_semantic_meta = "", {"status": "error"}
    diff_ctx = build_diff_context(args)
    task_requirements_blob = "\n".join([ctx, acceptance_ctx, acceptance_semantic_ctx, review_template])

    results: list[ReviewResult] = []
    hard_fail = False
    had_warnings = False
    prompt_truncated_agents: list[str] = []
    deadline_ts = time.monotonic() + total_timeout_sec

    for agent in agents:
        remaining = int(deadline_ts - time.monotonic())
        if remaining <= 0:
            status = "fail" if args.strict else "skipped"
            had_warnings = True
            if status == "fail":
                hard_fail = True
            results.append(
                ReviewResult(
                    agent=agent,
                    status=status,
                    rc=124,
                    details={"note": "Skipped due to total timeout budget exhausted.", "total_timeout_sec": total_timeout_sec, "agent_timeout_sec": per_agent_overrides.get(agent, per_agent_timeout_sec)},
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
                    details={"claude_agents_root": str(claude_agents_root), "agent_prompt_source": agent_prompt(agent, claude_agents_root=claude_agents_root, skip_agent_files=bool(args.skip_agent_prompts))[1].get("agent_prompt_source"), "security_profile": security_profile_payload(security_profile), **(det.get("details") or {}), "note": "Deterministic mapping: generated from sc-acceptance-check artifacts."},
                )
            )
            continue

        base_prompt, prompt_meta = agent_prompt(agent, claude_agents_root=claude_agents_root, skip_agent_files=bool(args.skip_agent_prompts))
        blocks = [base_prompt]
        if review_template:
            blocks.append("## Structured Review Template\n" + review_template.strip() + "\n")
        if ctx:
            blocks.append(ctx)
        if threat_ctx:
            blocks.append(threat_ctx)
        if security_ctx:
            blocks.append(security_ctx)
        if acceptance_ctx:
            blocks.append(acceptance_ctx)
        if acceptance_semantic_ctx:
            blocks.append(acceptance_semantic_ctx)
        blocks.append(diff_ctx)
        prompt = "\n\n".join(blocks).strip() + "\n"
        prompt_used, budget_meta = apply_prompt_budget(prompt, max_chars=int(args.prompt_max_chars))
        if bool(budget_meta.get("truncated")):
            prompt_truncated_agents.append(agent)
            if str(args.prompt_budget_gate) in {"warn", "require"}:
                had_warnings = True
            if str(args.prompt_budget_gate) == "require":
                hard_fail = True

        prompt_path = out_dir / f"prompt-{agent}.md"
        output_path = out_dir / f"review-{agent}.md"
        trace_path = out_dir / f"trace-{agent}.log"
        write_text(prompt_path, prompt_used)

        if bool(args.prompts_only):
            had_warnings = True
            results.append(
                ReviewResult(
                    agent=agent,
                    status="skipped",
                    prompt_path=str(prompt_path.relative_to(repo_root())).replace("\\", "/"),
                    details={"trace": str(trace_path.relative_to(repo_root())).replace("\\", "/"), "claude_agents_root": str(claude_agents_root), "agent_prompt_source": prompt_meta.get("agent_prompt_source"), "security_profile": security_profile_payload(security_profile), "prompt_budget": budget_meta, "note": "--prompts-only: LLM execution skipped."},
                )
            )
            write_text(trace_path, "--prompts-only: LLM execution skipped.\n")
            continue

        agent_cap = per_agent_overrides.get(agent, per_agent_timeout_sec)
        effective_timeout = max(1, min(int(agent_cap), int(remaining)))
        rc, trace_out, cmd = run_codex_exec(prompt=prompt_used, output_last_message=output_path, timeout_sec=effective_timeout, codex_configs=codex_configs)
        write_text(trace_path, trace_out)

        last_msg = ""
        if output_path.is_file():
            last_msg = output_path.read_text(encoding="utf-8", errors="ignore")
            write_text(output_path, last_msg)

        status = "ok" if (rc == 0 and last_msg.strip()) else ("fail" if args.strict else "skipped")
        if status != "ok":
            had_warnings = True
        if status == "fail":
            hard_fail = True

        semantic_gate = str(args.semantic_gate or "skip").strip().lower()
        semantic_agent = "semantic-equivalence-auditor"
        verdict = parse_verdict(last_msg)
        verdict_normalization: dict[str, Any] | None = None
        if last_msg and agent != semantic_agent:
            normalized_msg, normalized_verdict, verdict_normalization = normalize_host_safe_needs_fix(
                agent=agent,
                text=last_msg,
                security_profile=security_profile,
                task_requirements_blob=task_requirements_blob,
            )
            if normalized_msg != last_msg:
                last_msg = normalized_msg
                write_text(output_path, last_msg)
            if normalized_verdict:
                verdict = normalized_verdict
        if agent == semantic_agent:
            if semantic_gate == "warn" and verdict != "OK":
                had_warnings = True
            if semantic_gate == "require" and verdict != "OK":
                had_warnings = True
                hard_fail = True

        results.append(
            ReviewResult(
                agent=agent,
                status=status,
                rc=rc,
                cmd=cmd,
                prompt_path=str(prompt_path.relative_to(repo_root())).replace("\\", "/"),
                output_path=str(output_path.relative_to(repo_root())).replace("\\", "/"),
                details={"trace": str(trace_path.relative_to(repo_root())).replace("\\", "/"), "claude_agents_root": str(claude_agents_root), "agent_prompt_source": prompt_meta.get("agent_prompt_source"), "security_profile": security_profile_payload(security_profile), "total_timeout_sec": total_timeout_sec, "agent_timeout_sec": effective_timeout, "prompt_budget": budget_meta, "verdict": verdict, "verdict_normalization": verdict_normalization, "note": "This step is best-effort. Use --strict to make it a hard gate."},
            )
        )

    summary = summary_base(
        mode="uncommitted" if args.uncommitted else ("commit" if args.commit else "base"),
        out_dir=out_dir,
        args=args,
        security_profile=security_profile,
        status="fail" if hard_fail else ("warn" if had_warnings else "ok"),
    )
    summary.update(
        {
            "base": args.base,
            "commit": args.commit,
            "task_id": triplet.task_id if triplet else None,
            "threat_model": threat_model,
            "template_meta": template_meta,
            "acceptance_meta": acceptance_meta,
            "acceptance_semantic_meta": acceptance_semantic_meta,
            "results": [r.__dict__ for r in results],
            "prompt_budget": {
                "max_chars": int(args.prompt_max_chars),
                "gate": str(args.prompt_budget_gate),
                "truncated_count": len(prompt_truncated_agents),
                "truncated_agents": prompt_truncated_agents,
            },
        }
    )
    write_json(out_dir / "summary.json", summary)
    print(f"SC_LLM_REVIEW status={summary['status']} out={out_dir}")
    return 0 if summary["status"] in ("ok", "warn") else 1
