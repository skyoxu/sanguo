#!/usr/bin/env python3
"""
CLI and runtime config helpers for llm_review.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from _delivery_profile import known_delivery_profiles, profile_llm_review_defaults, resolve_delivery_profile
from _deterministic_review import DETERMINISTIC_AGENTS
from _llm_backend import KNOWN_LLM_BACKENDS, inspect_llm_backend, resolve_llm_backend
from _llm_review_acceptance import truncate
from _security_profile import security_profile_payload
from _util import repo_rel, split_csv, today_str


DELIVERY_PROFILE_CHOICES = tuple(sorted(known_delivery_profiles()))


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="sc-llm-review (optional local LLM review)")
    ap.add_argument("--self-check", action="store_true", help="Validate args and plan only; do not execute LLM calls.")
    ap.add_argument("--dry-run-plan", action="store_true", help="Resolve task + agents and write execution plan without LLM calls.")
    ap.add_argument("--task-id", default=None, help="Taskmaster id to include as review context (optional)")
    ap.add_argument(
        "--delivery-profile",
        default=None,
        choices=DELIVERY_PROFILE_CHOICES,
        help="Delivery profile (default: env DELIVERY_PROFILE or fast-ship).",
    )
    ap.add_argument("--review-profile", default="default", choices=["default", "bmad-godot"], help="Inject a structured review template into prompts.")
    ap.add_argument("--review-template", default="", help="Optional template file path (relative to repo root). Overrides --review-profile.")
    ap.add_argument("--no-acceptance-semantic", action="store_true", help="Do not inject acceptance anchors + referenced test excerpts into prompts.")
    ap.add_argument("--prompts-only", action="store_true", help="Write prompts to logs/ and skip LLM execution.")
    ap.add_argument(
        "--llm-backend",
        default=None,
        choices=KNOWN_LLM_BACKENDS,
        help="LLM transport backend. Default: env SC_LLM_BACKEND or codex-cli.",
    )
    ap.add_argument("--agents", default="", help="Comma-separated agent list. Empty=default 3. Special: all|full.")
    ap.add_argument("--diff-mode", default="full", choices=["full", "summary", "none"], help="How much diff to include in prompts.")
    ap.add_argument("--base", default="main", help="Base branch for diff review.")
    ap.add_argument("--uncommitted", action="store_true", help="Review staged/unstaged/untracked changes.")
    ap.add_argument("--commit", default=None, help="Review a single commit SHA.")
    ap.add_argument("--auto-commit", action="store_true", help="Auto-select latest commit referencing task id. Requires --task-id.")
    ap.add_argument("--timeout-sec", type=int, default=900, help="Total timeout budget for whole run (seconds).")
    ap.add_argument("--agent-timeout-sec", type=int, default=300, help="Per-agent timeout cap (seconds).")
    ap.add_argument("--agent-timeouts", default="", help="Per-agent override map: agent=seconds,agent=seconds")
    ap.add_argument("--semantic-gate", default="skip", choices=["skip", "warn", "require"], help="Semantic equivalence gate mode.")
    ap.add_argument("--strict", action="store_true", help="Fail if any agent cannot produce output.")
    ap.add_argument("--model-reasoning-effort", default="low", choices=["low", "medium", "high"], help="Codex config override.")
    ap.add_argument("--threat-model", default=None, help="singleplayer|modded|networked")
    ap.add_argument("--security-profile", default=None, choices=["strict", "host-safe"], help="Security review profile hint.")
    ap.add_argument("--claude-agents-root", default=None, help="Claude agents root path.")
    ap.add_argument("--skip-agent-prompts", action="store_true", help="Skip loading external agent prompt files.")
    ap.add_argument("--prompt-max-chars", type=int, default=32000, help="Max prompt chars per agent before truncation.")
    ap.add_argument(
        "--prompt-budget-gate",
        default="warn",
        choices=["skip", "warn", "require"],
        help="How to treat prompt truncation: skip|warn|require",
    )
    return ap


def apply_delivery_profile_defaults(args: argparse.Namespace) -> argparse.Namespace:
    delivery_profile = resolve_delivery_profile(getattr(args, "delivery_profile", None))
    defaults = profile_llm_review_defaults(delivery_profile)
    args.delivery_profile = delivery_profile
    args.llm_backend = resolve_llm_backend(getattr(args, "llm_backend", None))
    explicit_agents = bool(str(getattr(args, "agents", "") or "").strip())
    setattr(args, "_agents_explicit", explicit_agents)

    if not explicit_agents:
        args.agents = str(defaults.get("agents") or "")
    if str(getattr(args, "diff_mode", "") or "").strip() == "full":
        args.diff_mode = str(defaults.get("diff_mode") or args.diff_mode)
    if int(getattr(args, "timeout_sec", 0) or 0) == 900:
        args.timeout_sec = int(defaults.get("timeout_sec", args.timeout_sec) or args.timeout_sec)
    if int(getattr(args, "agent_timeout_sec", 0) or 0) == 300:
        args.agent_timeout_sec = int(defaults.get("agent_timeout_sec", args.agent_timeout_sec) or args.agent_timeout_sec)
    if str(getattr(args, "semantic_gate", "") or "").strip() == "skip":
        args.semantic_gate = str(defaults.get("semantic_gate") or args.semantic_gate)
    if not bool(getattr(args, "strict", False)):
        args.strict = bool(defaults.get("strict", False))
    if str(getattr(args, "model_reasoning_effort", "") or "").strip() == "low":
        args.model_reasoning_effort = str(defaults.get("model_reasoning_effort") or args.model_reasoning_effort)
    if str(getattr(args, "prompt_budget_gate", "") or "").strip() == "warn":
        args.prompt_budget_gate = str(defaults.get("prompt_budget_gate") or args.prompt_budget_gate)
    return args


def parse_agent_timeout_overrides(raw: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in split_csv(raw):
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
            out[k] = sec
    return out


def resolve_agents(raw: str, semantic_gate: str) -> list[str]:
    default_agents = ["architect-reviewer", "code-reviewer", "security-auditor"]
    all_agents = [*DETERMINISTIC_AGENTS, "architect-reviewer", "code-reviewer", "security-auditor", "test-automator"]
    raw_text = str(raw or "").strip()
    agents_raw = raw_text.lower()
    explicit_agents = bool(raw_text) and agents_raw not in {"all", "full", "6"}
    agents = all_agents if agents_raw in {"all", "full", "6"} else (split_csv(raw_text) or default_agents)
    semantic_agent = "semantic-equivalence-auditor"
    if semantic_gate != "skip" and semantic_agent not in agents and not explicit_agents:
        agents = [*agents, semantic_agent]
    return agents


def validate_args(args: argparse.Namespace) -> list[str]:
    errors: list[str] = []
    if args.uncommitted and args.commit:
        errors.append("--uncommitted and --commit are mutually exclusive.")
    if args.auto_commit and (args.uncommitted or args.commit):
        errors.append("--auto-commit is mutually exclusive with --uncommitted/--commit.")
    if args.auto_commit and not str(args.task_id or "").strip():
        errors.append("--auto-commit requires --task-id.")
    if int(args.timeout_sec) <= 0:
        errors.append("--timeout-sec must be > 0.")
    if int(args.agent_timeout_sec) <= 0:
        errors.append("--agent-timeout-sec must be > 0.")
    if int(args.prompt_max_chars) <= 0:
        errors.append("--prompt-max-chars must be > 0.")
    explicit_agents = bool(getattr(args, "_agents_explicit", False))
    if str(getattr(args, "semantic_gate", "") or "").strip().lower() == "require" and explicit_agents:
        resolved_agents = resolve_agents(str(getattr(args, "agents", "") or ""), "skip")
        if "semantic-equivalence-auditor" not in resolved_agents:
            errors.append("--semantic-gate require needs semantic-equivalence-auditor in explicit --agents.")
    requires_backend_ready = not any(
        (
            bool(getattr(args, "self_check", False)),
            bool(getattr(args, "dry_run_plan", False)),
            bool(getattr(args, "prompts_only", False)),
        )
    )
    backend_info = inspect_llm_backend(getattr(args, "llm_backend", None))
    setattr(args, "_llm_backend_info", backend_info)
    if requires_backend_ready:
        errors.extend(str(item) for item in list(backend_info.get("blocking_errors") or []))
    return errors


def summary_base(*, mode: str, out_dir: Path, args: argparse.Namespace, security_profile: str, status: str) -> dict[str, Any]:
    backend_info = getattr(args, "_llm_backend_info", None)
    if not isinstance(backend_info, dict):
        backend_info = inspect_llm_backend(getattr(args, "llm_backend", None))
    return {
        "schema_version": "1.0.0",
        "cmd": "sc-llm-review",
        "date": today_str(),
        "mode": mode,
        "status": status,
        "out_dir": repo_rel(out_dir),
        "strict": bool(args.strict),
        "llm_backend": dict(backend_info),
        "security_profile": security_profile_payload(security_profile),
        "prompt_budget": {
            "max_chars": int(args.prompt_max_chars),
            "gate": str(args.prompt_budget_gate),
        },
    }


def apply_prompt_budget(prompt: str, *, max_chars: int) -> tuple[str, dict[str, Any]]:
    original_chars = len(prompt)
    if original_chars <= max_chars:
        return prompt, {"original_chars": original_chars, "final_chars": original_chars, "max_chars": max_chars, "truncated": False}
    truncated_prompt = truncate(prompt, max_chars=max_chars)
    return truncated_prompt, {"original_chars": original_chars, "final_chars": len(truncated_prompt), "max_chars": max_chars, "truncated": True}
