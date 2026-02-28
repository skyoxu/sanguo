#!/usr/bin/env python3
"""
Runtime helpers for acceptance_check orchestration.
"""

from __future__ import annotations

import argparse
import os
from argparse import Namespace

from _security_profile import normalize_gate_mode, resolve_security_profile, security_gate_defaults


ALLOWED_ONLY_STEPS = {
    "adr",
    "links",
    "subtasks",
    "overlay",
    "contracts",
    "arch",
    "build",
    "security",
    "quality",
    "rules",
    "tests",
    "perf",
    "risk",
}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="sc-acceptance-check (reproducible acceptance gate)")
    ap.add_argument("--self-check", action="store_true", help="Validate args and orchestration wiring only; do not resolve task or run gates.")
    ap.add_argument("--dry-run-plan", action="store_true", help="Resolve task and print planned steps/gate levels without executing checks.")
    ap.add_argument("--task-id", default=None, help="Taskmaster id (e.g. 10 or 10.3). Default: first status=in-progress task.")
    ap.add_argument("--godot-bin", default=None, help="Godot mono console path (or set env GODOT_BIN)")
    ap.add_argument(
        "--out-per-task",
        action="store_true",
        help="Write outputs to logs/ci/<date>/sc-acceptance-check-task-<id>/ to avoid overwriting when running many tasks.",
    )
    ap.add_argument("--perf-p95-ms", type=int, default=None, help="Enable perf hard gate by parsing [PERF] p95_ms from latest logs/ci/**/headless.log. 0 disables.")
    ap.add_argument("--require-perf", action="store_true", help="(legacy) enable perf hard gate using env PERF_P95_THRESHOLD_MS (or default 20ms)")
    ap.add_argument("--strict-adr-status", action="store_true", help="fail if any referenced ADR is not Accepted")
    ap.add_argument("--strict-test-quality", action="store_true", help="fail if deterministic test-quality heuristics report verdict=Needs Fix")
    ap.add_argument("--strict-quality-rules", action="store_true", help="fail if deterministic quality rules report verdict=Needs Fix")
    ap.add_argument("--require-task-test-refs", action="store_true", help="fail if tasks_back/tasks_gameplay test_refs is empty for the resolved task id")
    ap.add_argument("--require-executed-refs", action="store_true", help="fail if acceptance anchors cannot be proven executed in this run (TRX/JUnit evidence)")
    ap.add_argument(
        "--security-profile",
        default=None,
        choices=["strict", "host-safe"],
        help="Security posture profile (default: env SECURITY_PROFILE or host-safe). host-safe keeps host boundary checks hard, lowers anti-tamper defaults.",
    )
    ap.add_argument(
        "--security-path-gate",
        default=None,
        choices=["skip", "warn", "require"],
        help="Hard gate: path safety invariants (static). Default follows --security-profile.",
    )
    ap.add_argument(
        "--security-sql-gate",
        default=None,
        choices=["skip", "warn", "require"],
        help="Hard gate: SQL injection anti-patterns (static). Default follows --security-profile.",
    )
    ap.add_argument(
        "--security-audit-schema-gate",
        default=None,
        choices=["skip", "warn", "require"],
        help="Hard gate: security-audit.jsonl schema keys exist in runtime code (static). Default follows --security-profile.",
    )
    ap.add_argument(
        "--ui-event-json-guards",
        default=None,
        choices=["skip", "warn", "require"],
        help="UI event gate: JSON size/max-depth guards (static). Default follows --security-profile.",
    )
    ap.add_argument(
        "--ui-event-source-verify",
        default=None,
        choices=["skip", "warn", "require"],
        help="UI event gate: if handler has `source`, require it is used (static). Default follows --security-profile.",
    )
    ap.add_argument(
        "--security-audit-evidence",
        default=None,
        choices=["skip", "warn", "require"],
        help="Require runtime evidence of security-audit.jsonl for this run_id (requires tests). Default follows --security-profile.",
    )
    ap.add_argument(
        "--require-headless-e2e",
        action="store_true",
        help="fail when task acceptance refs include .gd tests but this run does not produce headless GdUnit4 artifacts under logs/e2e/<date>/sc-test/",
    )
    ap.add_argument(
        "--subtasks-coverage",
        default="skip",
        choices=["skip", "warn", "require"],
        help="Subtasks coverage gate mode (tasks.json subtasks must be covered by tasks_back/tasks_gameplay acceptance).",
    )
    ap.add_argument("--subtasks-timeout-sec", type=int, default=600, help="Timeout for subtasks coverage LLM gate.")
    ap.add_argument(
        "--only",
        default=None,
        help="Comma-separated step filter (adr,links,subtasks,overlay,contracts,arch,build,security,quality,rules,tests,perf,risk). Default: all.",
    )
    return ap


def parse_only_steps(value: str | None) -> set[str] | None:
    if not value:
        return None
    parts = {x.strip() for x in str(value).split(",") if x.strip()}
    return parts or None


def normalize_subtasks_mode(value: str | None) -> str:
    mode = str(value or "skip").strip().lower()
    return mode if mode in ("skip", "warn", "require") else "skip"


def resolve_security_modes(args: Namespace) -> tuple[str, dict[str, str]]:
    profile = resolve_security_profile(args.security_profile)
    defaults = security_gate_defaults(profile)
    modes = {
        "path": normalize_gate_mode(args.security_path_gate, defaults["path"]),
        "sql": normalize_gate_mode(args.security_sql_gate, defaults["sql"]),
        "audit_schema": normalize_gate_mode(args.security_audit_schema_gate, defaults["audit_schema"]),
        "ui_event_json_guards": normalize_gate_mode(args.ui_event_json_guards, defaults["ui_event_json_guards"]),
        "ui_event_source_verify": normalize_gate_mode(args.ui_event_source_verify, defaults["ui_event_source_verify"]),
        "audit_evidence": normalize_gate_mode(args.security_audit_evidence, defaults["audit_evidence"]),
    }
    return profile, modes


def compute_perf_p95_ms(*, perf_p95_ms: int | None, require_perf: bool) -> int:
    env_v = os.environ.get("PERF_P95_THRESHOLD_MS")
    env_p95 = int(env_v) if (env_v and env_v.isdigit()) else None
    if perf_p95_ms is not None:
        return max(0, int(perf_p95_ms))
    if env_p95 is not None:
        return env_p95
    return 20 if require_perf else 0


def validate_arg_conflicts(
    *,
    only_steps: set[str] | None,
    subtasks_mode: str,
    require_headless_e2e: bool,
    require_executed_refs: bool,
    audit_evidence_mode: str,
) -> list[str]:
    errors: list[str] = []
    if only_steps is None:
        return errors

    unknown = sorted(x for x in only_steps if x not in ALLOWED_ONLY_STEPS)
    if unknown:
        errors.append(f"unknown --only keys: {','.join(unknown)}")

    has_tests = "tests" in only_steps
    has_subtasks = "subtasks" in only_steps

    if require_headless_e2e and not has_tests:
        errors.append("conflict: --require-headless-e2e requires 'tests' in --only (or remove --only)")
    if require_executed_refs and not has_tests:
        errors.append("conflict: --require-executed-refs requires 'tests' in --only (or remove --only)")
    if audit_evidence_mode == "require" and not has_tests:
        errors.append("conflict: --security-audit-evidence require requires 'tests' in --only (or remove --only)")
    if subtasks_mode in ("warn", "require") and not has_subtasks:
        errors.append("conflict: --subtasks-coverage warn|require needs 'subtasks' in --only (or remove --only)")

    return errors


def should_mark_hard_failure(*, step_name: str, status: str, subtasks_mode: str) -> bool:
    if status != "fail":
        return False
    if step_name == "security-soft":
        return False
    if step_name == "subtasks-coverage" and subtasks_mode != "require":
        return False
    return True
