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
    apply_delivery_profile_defaults,
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
from _util import ci_dir, repo_rel, repo_root, write_json, write_text


_SEMANTIC_AGENT = "semantic-equivalence-auditor"
_DEFERRED_REASON_CODE = "deferred_until_prior_reviewers_clean"


def _prompt_shape_for_agent(
    agent: str,
    *,
    delivery_profile: str | None = None,
    resolved_agents: list[str] | None = None,
    semantic_gate: str | None = None,
) -> dict[str, str]:
    if agent == "semantic-equivalence-auditor":
        return {
            "task_context_mode": "semantic",
            "acceptance_semantic_profile": "semantic",
            "diff_position": "tail",
        }
    normalized_profile = str(delivery_profile or "").strip().lower()
    normalized_gate = str(semantic_gate or "").strip().lower()
    reviewer_set = {str(item).strip() for item in (resolved_agents or []) if str(item).strip()}
    if normalized_profile in {"playable-ea", "fast-ship"} and "semantic-equivalence-auditor" not in reviewer_set and normalized_gate in {"skip", "warn"}:
        return {
            "task_context_mode": "compact",
            "acceptance_semantic_profile": "none",
            "diff_position": "before_acceptance_semantic",
        }
    return {
        "task_context_mode": "compact",
        "acceptance_semantic_profile": "compact",
        "diff_position": "before_acceptance_semantic",
    }


def _compose_prompt(*, blocks: list[str], diff_ctx: str, acceptance_semantic_ctx: str, diff_position: str) -> str:
    rendered = [*blocks]
    if diff_position == "before_acceptance_semantic":
        rendered.append(diff_ctx)
    if acceptance_semantic_ctx:
        rendered.append(acceptance_semantic_ctx)
    if diff_position != "before_acceptance_semantic":
        rendered.append(diff_ctx)
    return "\n\n".join([b for b in rendered if str(b or "").strip()]).strip() + "\n"


def _fit_prompt_context(
    *,
    blocks: list[str],
    diff_ctx: str,
    diff_ctx_summary: str | None,
    acceptance_semantic_ctx: str,
    diff_position: str,
    max_chars: int,
    allow_drop_acceptance_semantic: bool,
) -> tuple[str, dict[str, Any]]:
    prompt = _compose_prompt(
        blocks=blocks,
        diff_ctx=diff_ctx,
        acceptance_semantic_ctx=acceptance_semantic_ctx,
        diff_position=diff_position,
    )
    meta: dict[str, Any] = {
        "diff_mode_used": "full",
        "acceptance_semantic_included": bool(acceptance_semantic_ctx),
        "fallbacks_applied": [],
        "pre_budget_chars": len(prompt),
    }
    if len(prompt) <= max_chars:
        return prompt, meta

    if diff_ctx_summary and diff_ctx_summary != diff_ctx:
        summary_prompt = _compose_prompt(
            blocks=blocks,
            diff_ctx=diff_ctx_summary,
            acceptance_semantic_ctx=acceptance_semantic_ctx,
            diff_position=diff_position,
        )
        if len(summary_prompt) < len(prompt):
            prompt = summary_prompt
            meta["diff_mode_used"] = "summary"
            meta["fallbacks_applied"].append("summary_diff")
            meta["pre_budget_chars"] = len(prompt)

    if len(prompt) > max_chars and allow_drop_acceptance_semantic and acceptance_semantic_ctx:
        reduced_prompt = _compose_prompt(
            blocks=blocks,
            diff_ctx=diff_ctx_summary if meta["diff_mode_used"] == "summary" and diff_ctx_summary else diff_ctx,
            acceptance_semantic_ctx="",
            diff_position=diff_position,
        )
        if len(reduced_prompt) < len(prompt):
            prompt = reduced_prompt
            meta["acceptance_semantic_included"] = False
            meta["fallbacks_applied"].append("drop_acceptance_semantic")
            meta["pre_budget_chars"] = len(prompt)

    return prompt, meta


def _review_result_is_clean(result: ReviewResult | dict[str, Any]) -> bool:
    if isinstance(result, ReviewResult):
        status = str(result.status or "").strip().lower()
        rc = int(result.rc or 0)
        details = result.details if isinstance(result.details, dict) else {}
    else:
        status = str(result.get("status") or "").strip().lower()
        rc = int(result.get("rc") or 0)
        details = result.get("details") if isinstance(result.get("details"), dict) else {}
    verdict = str(details.get("verdict") or "").strip().upper()
    if status != "ok" or rc != 0:
        return False
    return verdict in {"", "OK"}


def _build_agent_execution_plan(agents: list[str]) -> dict[str, Any]:
    ordered_agents = [str(agent).strip() for agent in agents if str(agent).strip()]
    llm_agents = [agent for agent in ordered_agents if agent not in DETERMINISTIC_AGENTS]
    if _SEMANTIC_AGENT not in llm_agents or len(llm_agents) <= 1:
        return {
            "ordered_agents": ordered_agents,
            "primary_agents": ordered_agents,
            "deferred_agents": [],
            "primary_llm_agents": llm_agents,
            "stages": {agent: "primary" for agent in ordered_agents},
            "semantic_deferred": False,
        }

    primary_agents = [agent for agent in ordered_agents if agent != _SEMANTIC_AGENT]
    deferred_agents = [agent for agent in ordered_agents if agent == _SEMANTIC_AGENT]
    return {
        "ordered_agents": [*primary_agents, *deferred_agents],
        "primary_agents": primary_agents,
        "deferred_agents": deferred_agents,
        "primary_llm_agents": [agent for agent in primary_agents if agent not in DETERMINISTIC_AGENTS],
        "stages": {
            agent: ("deferred" if agent == _SEMANTIC_AGENT else "primary")
            for agent in ordered_agents
        },
        "semantic_deferred": True,
    }


def _run_self_check(args: argparse.Namespace) -> int:
    out_dir = ci_dir("sc-llm-review-self-check")
    security_profile = resolve_security_profile(args.security_profile)
    errors = validate_args(args)
    summary = summary_base(mode="self-check", out_dir=out_dir, args=args, security_profile=security_profile, status="fail" if errors else "ok")
    summary["arg_validation"] = {"valid": len(errors) == 0, "errors": errors}
    write_json(out_dir / "summary.json", summary)
    for e in errors:
        print(f"[sc-llm-review] ERROR: {e}")
    print(f"SC_LLM_REVIEW_SELF_CHECK status={summary['status']} out={repo_rel(out_dir)}")
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

    requested_agents = resolve_agents(args.agents, str(args.semantic_gate))
    execution_plan = _build_agent_execution_plan(requested_agents)
    agents = list(execution_plan["ordered_agents"])
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
                "execution_stage": str(execution_plan["stages"].get(agent) or "primary"),
                "activation_condition": "all_prior_reviewers_clean" if agent in set(execution_plan["deferred_agents"]) else "always",
                "prompt_budget_gate": str(args.prompt_budget_gate),
                "prompt_max_chars": int(args.prompt_max_chars),
            }
        )
    summary = summary_base(mode="dry-run-plan", out_dir=out_dir, args=args, security_profile=security_profile, status="ok")
    summary["task_id"] = triplet.task_id if triplet else None
    summary["agents"] = agents
    summary["requested_agents"] = requested_agents
    summary["execution_plan"] = execution_plan
    summary["plan"] = plan
    write_json(out_dir / "summary.json", summary)
    print(f"SC_LLM_REVIEW_DRY_RUN_PLAN status={summary['status']} out={repo_rel(out_dir)}")
    return 0


def main() -> int:
    args = apply_delivery_profile_defaults(build_parser().parse_args())
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
    requested_agents = resolve_agents(args.agents, str(args.semantic_gate or "skip").strip().lower())
    execution_plan = _build_agent_execution_plan(requested_agents)
    agents = list(execution_plan["ordered_agents"])
    per_agent_overrides = parse_agent_timeout_overrides(args.agent_timeouts)
    total_timeout_sec = int(args.timeout_sec)
    per_agent_timeout_sec = int(args.agent_timeout_sec)

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

    acceptance_semantic_cache: dict[str, tuple[str, dict[str, Any] | None]] = {}
    diff_ctx = build_diff_context(args)
    diff_ctx_summary: str | None = None

    results: list[ReviewResult] = []
    hard_fail = False
    had_warnings = False
    prompt_truncated_agents: list[str] = []
    deadline_ts = time.monotonic() + total_timeout_sec

    for agent in agents:
        execution_stage = str(execution_plan["stages"].get(agent) or "primary")
        if execution_stage == "deferred":
            blocked_by_agents = [result.agent for result in results if not _review_result_is_clean(result)]
            if blocked_by_agents:
                results.append(
                    ReviewResult(
                        agent=agent,
                        status="skipped",
                        rc=0,
                        details={
                            "execution_stage": execution_stage,
                            "reason_code": _DEFERRED_REASON_CODE,
                            "blocked_by_agents": blocked_by_agents,
                            "note": "Deferred reviewer skipped because prior reviewers are not yet clean.",
                        },
                    )
                )
                continue
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
                    details={"execution_stage": execution_stage, "note": "Skipped due to total timeout budget exhausted.", "total_timeout_sec": total_timeout_sec, "agent_timeout_sec": per_agent_overrides.get(agent, per_agent_timeout_sec)},
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
                    details={"execution_stage": execution_stage, "claude_agents_root": str(claude_agents_root), "agent_prompt_source": agent_prompt(agent, claude_agents_root=claude_agents_root, skip_agent_files=bool(args.skip_agent_prompts))[1].get("agent_prompt_source"), "security_profile": security_profile_payload(security_profile), **(det.get("details") or {}), "note": "Deterministic mapping: generated from sc-acceptance-check artifacts."},
                )
            )
            continue

        base_prompt, prompt_meta = agent_prompt(agent, claude_agents_root=claude_agents_root, skip_agent_files=bool(args.skip_agent_prompts))
        prompt_shape = _prompt_shape_for_agent(
            agent,
            delivery_profile=str(getattr(args, "delivery_profile", "") or ""),
            resolved_agents=list(execution_plan["primary_llm_agents"]) if execution_stage == "primary" and bool(execution_plan["semantic_deferred"]) else agents,
            semantic_gate=str(args.semantic_gate or "skip").strip().lower(),
        )
        ctx = build_task_context(triplet, mode=prompt_shape["task_context_mode"])
        acceptance_semantic_ctx = ""
        acceptance_semantic_meta: dict[str, Any] | None = None
        acceptance_semantic_profile = prompt_shape["acceptance_semantic_profile"]
        if triplet and acceptance_semantic_profile != "none" and not bool(args.no_acceptance_semantic):
            if acceptance_semantic_profile not in acceptance_semantic_cache:
                try:
                    acceptance_semantic_cache[acceptance_semantic_profile] = build_acceptance_semantic_context(
                        triplet,
                        profile=acceptance_semantic_profile,
                    )
                except Exception:  # noqa: BLE001
                    acceptance_semantic_cache[acceptance_semantic_profile] = ("", {"status": "error", "profile": acceptance_semantic_profile})
            acceptance_semantic_ctx, acceptance_semantic_meta = acceptance_semantic_cache[acceptance_semantic_profile]
        task_requirements_blob = "\n".join([ctx, acceptance_ctx, acceptance_semantic_ctx, review_template])
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
        if str(args.diff_mode or "").strip().lower() == "full" and diff_ctx_summary is None:
            diff_args = argparse.Namespace(**vars(args))
            diff_args.diff_mode = "summary"
            diff_ctx_summary = build_diff_context(diff_args)
        prompt, prompt_fit_meta = _fit_prompt_context(
            blocks=blocks,
            diff_ctx=diff_ctx,
            diff_ctx_summary=diff_ctx_summary,
            acceptance_semantic_ctx=acceptance_semantic_ctx,
            diff_position=prompt_shape["diff_position"],
            max_chars=int(args.prompt_max_chars),
            allow_drop_acceptance_semantic=(agent != "semantic-equivalence-auditor"),
        )
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
                    details={"execution_stage": execution_stage, "trace": str(trace_path.relative_to(repo_root())).replace("\\", "/"), "claude_agents_root": str(claude_agents_root), "agent_prompt_source": prompt_meta.get("agent_prompt_source"), "security_profile": security_profile_payload(security_profile), "prompt_budget": budget_meta, "prompt_shape": {**prompt_shape, **prompt_fit_meta}, "acceptance_semantic_meta": acceptance_semantic_meta, "note": "--prompts-only: LLM execution skipped."},
                )
            )
            write_text(trace_path, "--prompts-only: LLM execution skipped.\n")
            continue

        agent_cap = per_agent_overrides.get(agent, per_agent_timeout_sec)
        remaining_before_sec = max(0, int(remaining))
        effective_timeout = max(1, int(agent_cap))
        rc, trace_out, cmd = run_codex_exec(
            backend=str(args.llm_backend),
            prompt=prompt_used,
            output_last_message=output_path,
            timeout_sec=effective_timeout,
            codex_configs=codex_configs,
        )
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
        semantic_agent = _SEMANTIC_AGENT
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
                details={"execution_stage": execution_stage, "trace": str(trace_path.relative_to(repo_root())).replace("\\", "/"), "claude_agents_root": str(claude_agents_root), "agent_prompt_source": prompt_meta.get("agent_prompt_source"), "security_profile": security_profile_payload(security_profile), "total_timeout_sec": total_timeout_sec, "agent_timeout_sec": effective_timeout, "remaining_before_sec": remaining_before_sec, "prompt_budget": budget_meta, "prompt_shape": {**prompt_shape, **prompt_fit_meta}, "acceptance_semantic_meta": acceptance_semantic_meta, "verdict": verdict, "verdict_normalization": verdict_normalization, "note": "This step is best-effort. Use --strict to make it a hard gate."},
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
            "requested_agents": requested_agents,
            "execution_plan": execution_plan,
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
    print(f"SC_LLM_REVIEW status={summary['status']} out={repo_rel(out_dir)}")
    return 0 if summary["status"] in ("ok", "warn") else 1
