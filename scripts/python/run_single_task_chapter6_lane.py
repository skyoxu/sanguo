#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _today() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _default_out_dir(task_id: str) -> Path:
    return _repo_root() / "logs" / "ci" / _today() / f"single-task-chapter6-task-{task_id}"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _load_delivery_profiles() -> dict[str, Any]:
    config_path = Path(__file__).resolve().parents[1] / "sc" / "config" / "delivery_profiles.json"
    return json.loads(config_path.read_text(encoding="utf-8"))


def resolve_profile_policy(
    delivery_profile: str | None,
    *,
    security_profile: str | None = None,
    fix_through: str | None = None,
) -> dict[str, str]:
    config = _load_delivery_profiles()
    profiles = config.get("profiles") if isinstance(config.get("profiles"), dict) else {}
    default_profile = str(config.get("default_profile") or "fast-ship").strip().lower() or "fast-ship"
    resolved_profile = str(delivery_profile or os.environ.get("DELIVERY_PROFILE") or default_profile).strip().lower()
    if resolved_profile not in profiles:
        resolved_profile = default_profile

    profile_payload = profiles.get(resolved_profile) if isinstance(profiles.get(resolved_profile), dict) else {}
    resolved_security = str(security_profile or profile_payload.get("security_profile_default") or "host-safe").strip().lower()
    if resolved_security not in {"host-safe", "strict"}:
        resolved_security = "host-safe"

    default_fix_through = "P0" if resolved_profile == "playable-ea" else "P1"
    resolved_fix_through = str(fix_through or default_fix_through).strip().upper() or default_fix_through
    if resolved_fix_through not in {"P0", "P1", "P2", "P3"}:
        resolved_fix_through = default_fix_through

    return {
        "delivery_profile": resolved_profile,
        "security_profile": resolved_security,
        "fix_through": resolved_fix_through,
        "execution_plan_policy": "warn" if resolved_profile == "playable-ea" else "draft",
        "red_verify": "auto" if resolved_profile == "standard" else "unit",
        "needs_fix_max_rounds": "1",
        "record_residual": "true" if resolved_fix_through in {"P0", "P1"} else "false",
    }


def build_resume_task_cmd(task_id: str) -> list[str]:
    return [
        "py",
        "-3",
        "scripts/python/dev_cli.py",
        "resume-task",
        "--task-id",
        str(task_id),
        "--recommendation-only",
        "--recommendation-format",
        "json",
    ]


def build_chapter6_route_cmd(task_id: str, *, record_residual: bool) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/python/dev_cli.py",
        "chapter6-route",
        "--task-id",
        str(task_id),
        "--recommendation-only",
        "--recommendation-format",
        "json",
    ]
    if record_residual:
        cmd.append("--record-residual")
    return cmd


def build_check_tdd_plan_cmd(task_id: str, *, profile_policy: dict[str, str]) -> list[str]:
    return [
        "py",
        "-3",
        "scripts/sc/check_tdd_execution_plan.py",
        "--task-id",
        str(task_id),
        "--tdd-stage",
        "red-first",
        "--verify",
        str(profile_policy["red_verify"]),
        "--execution-plan-policy",
        str(profile_policy["execution_plan_policy"]),
    ]


def build_red_first_cmd(task_id: str, *, profile_policy: dict[str, str], godot_bin: str) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/sc/llm_generate_tests_from_acceptance_refs.py",
        "--task-id",
        str(task_id),
        "--tdd-stage",
        "red-first",
        "--verify",
        str(profile_policy["red_verify"]),
    ]
    if str(profile_policy["red_verify"]) == "auto" and str(godot_bin).strip():
        cmd += ["--godot-bin", str(godot_bin)]
    return cmd


def build_build_tdd_cmd(task_id: str, *, stage: str, profile_policy: dict[str, str]) -> list[str]:
    return [
        "py",
        "-3",
        "scripts/sc/build.py",
        "tdd",
        "--task-id",
        str(task_id),
        "--stage",
        str(stage),
        "--delivery-profile",
        str(profile_policy["delivery_profile"]),
        "--security-profile",
        str(profile_policy["security_profile"]),
    ]


def build_review_pipeline_cmd(task_id: str, *, profile_policy: dict[str, str], godot_bin: str) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/sc/run_review_pipeline.py",
        "--task-id",
        str(task_id),
        "--delivery-profile",
        str(profile_policy["delivery_profile"]),
        "--security-profile",
        str(profile_policy["security_profile"]),
    ]
    if str(godot_bin).strip():
        cmd += ["--godot-bin", str(godot_bin)]
    return cmd


def build_review_pipeline_fork_cmd(task_id: str, *, profile_policy: dict[str, str], godot_bin: str) -> list[str]:
    return build_review_pipeline_cmd(
        task_id,
        profile_policy=profile_policy,
        godot_bin=godot_bin,
    ) + ["--fork"]


def build_needs_fix_fast_cmd(task_id: str, *, profile_policy: dict[str, str]) -> list[str]:
    return [
        "py",
        "-3",
        "scripts/sc/llm_review_needs_fix_fast.py",
        "--task-id",
        str(task_id),
        "--delivery-profile",
        str(profile_policy["delivery_profile"]),
        "--security-profile",
        str(profile_policy["security_profile"]),
        "--rerun-failing-only",
        "--max-rounds",
        str(profile_policy["needs_fix_max_rounds"]),
    ]


def build_local_hard_checks_preflight_cmd(*, profile_policy: dict[str, str]) -> list[str]:
    return [
        "py",
        "-3",
        "scripts/python/dev_cli.py",
        "run-local-hard-checks-preflight",
        "--delivery-profile",
        str(profile_policy["delivery_profile"]),
    ]


def build_local_hard_checks_cmd(*, profile_policy: dict[str, str], godot_bin: str) -> list[str]:
    cmd = [
        "py",
        "-3",
        "scripts/python/dev_cli.py",
        "run-local-hard-checks",
        "--delivery-profile",
        str(profile_policy["delivery_profile"]),
    ]
    if str(godot_bin).strip():
        cmd += ["--godot-bin", str(godot_bin)]
    return cmd


def build_inspect_local_hard_checks_cmd() -> list[str]:
    return [
        "py",
        "-3",
        "scripts/python/dev_cli.py",
        "inspect-run",
        "--kind",
        "local-hard-checks",
        "--recommendation-only",
        "--recommendation-format",
        "json",
    ]


def _route_lane(route_payload: dict[str, Any] | None) -> str:
    return str((route_payload or {}).get("preferred_lane") or "").strip().lower() or "inspect-first"


def _route_next_action(route_payload: dict[str, Any] | None) -> str:
    return _normalize_action((route_payload or {}).get("chapter6_next_action"))


def _route_run_id(route_payload: dict[str, Any] | None) -> str:
    return str((route_payload or {}).get("run_id") or "").strip().lower()


def _route_latest_reason(route_payload: dict[str, Any] | None) -> str:
    return str((route_payload or {}).get("latest_reason") or "").strip().lower()


def _route_blocked_by(route_payload: dict[str, Any] | None) -> str:
    return str((route_payload or {}).get("blocked_by") or "").strip().lower()


def _route_run_type(route_payload: dict[str, Any] | None) -> str:
    return str((route_payload or {}).get("latest_run_type") or (route_payload or {}).get("run_type") or "").strip().lower()


def _route_forbidden_commands(route_payload: dict[str, Any] | None) -> list[str]:
    route = route_payload or {}
    raw = route.get("forbidden_commands")
    items: list[str] = []
    if isinstance(raw, str):
        items = [segment.strip() for segment in raw.split("|")]
    elif isinstance(raw, list):
        items = [str(item).strip() for item in raw]
    return [item for item in items if item and item.lower() != "none"]


def _initial_route_has_recovery_signal(route_payload: dict[str, Any] | None) -> bool:
    route = route_payload or {}
    return bool(
        _route_run_id(route) not in {"", "n/a"}
        or _route_latest_reason(route) not in {"", "n/a", "none"}
        or _route_blocked_by(route) not in {"", "n/a", "none"}
        or bool(_route_forbidden_commands(route))
    )


def _route_stop_reason(route_payload: dict[str, Any] | None) -> str:
    if not _initial_route_has_recovery_signal(route_payload):
        return ""
    blocked_by = _route_blocked_by(route_payload)
    latest_reason = _route_latest_reason(route_payload)
    latest_run_type = _route_run_type(route_payload)
    lane = _route_lane(route_payload)
    next_action = _route_next_action(route_payload)

    if blocked_by == "artifact_integrity" or latest_reason == "planned_only_incomplete" or latest_run_type == "planned-only":
        return "artifact-integrity"
    if blocked_by in {"approval_pending", "approval_invalid"}:
        return blocked_by
    if blocked_by == "approval_approved" and next_action not in {"fork", "continue"}:
        return blocked_by
    # `chapter6_next_action=inspect` is a generic safety fallback. When the route lane
    # already converged to a stricter action under `recent_failure_summary`, trust the lane.
    if blocked_by == "recent_failure_summary" and lane in {
        "run-6.7",
        "fix-deterministic",
        "repo-noise-stop",
        "record-residual",
    }:
        return lane
    if blocked_by == "recent_failure_summary" and lane == "run-6.8":
        return ""
    if next_action == "continue":
        return ""
    if next_action == "needs-fix-fast":
        # Explicit Chapter 6 hint allows narrow closure even when preferred_lane falls back to inspect-first.
        return ""
    if next_action == "fix-and-resume":
        return "fix-deterministic"
    if next_action in {"pause", "fork", "resume", "inspect", "rerun"}:
        return next_action
    if lane in {"run-6.7", "repo-noise-stop", "fix-deterministic", "inspect-first", "record-residual"}:
        return lane
    return ""


def _route_is_blocking(route_payload: dict[str, Any] | None) -> bool:
    return bool(_route_stop_reason(route_payload))


def _route_requires_needs_fix(route_payload: dict[str, Any] | None) -> bool:
    next_action = _route_next_action(route_payload)
    if next_action == "needs-fix-fast":
        return True
    if next_action in {"pause", "fork", "resume", "rerun", "fix-and-resume"}:
        return False
    if _route_lane(route_payload) == "run-6.8":
        return True
    if next_action in {"continue", "inspect"}:
        return False
    return False


def _stringify_cmd(cmd: list[str]) -> str:
    return " ".join(str(item).strip() for item in list(cmd) if str(item).strip())


def _normalize_cmd_text(text: str) -> str:
    return " ".join(str(text or "").strip().split())


def _contains_ordered_subsequence(haystack: list[str], needle: list[str]) -> bool:
    if not needle:
        return False
    index = 0
    for token in haystack:
        if token == needle[index]:
            index += 1
            if index == len(needle):
                return True
    return False


def _command_is_forbidden(route_payload: dict[str, Any] | None, cmd: list[str]) -> bool:
    cmd_text = _normalize_cmd_text(_stringify_cmd(cmd))
    cmd_tokens = [str(item).strip() for item in list(cmd) if str(item).strip()]
    forbidden = _route_forbidden_commands(route_payload)
    if not cmd_text:
        return False
    for item in forbidden:
        forbidden_text = _normalize_cmd_text(item)
        if not forbidden_text:
            continue
        if cmd_text == forbidden_text or cmd_text.startswith(f"{forbidden_text} "):
            return True
        forbidden_tokens = [token for token in forbidden_text.split(" ") if token]
        if _contains_ordered_subsequence(cmd_tokens, forbidden_tokens):
            return True
    return False


def _normalize_action(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-")


def _normalize_action_list(raw: Any) -> list[str]:
    items: list[str] = []
    if isinstance(raw, list):
        items = [str(item).strip() for item in raw]
    elif isinstance(raw, str):
        text = str(raw).strip()
        if text:
            if "|" in text:
                items = [segment.strip() for segment in text.split("|")]
            elif "," in text:
                items = [segment.strip() for segment in text.split(",")]
            elif text.lower() not in {"none", "n/a"}:
                items = [text]
    return [value for value in (_normalize_action(item) for item in items) if value and value not in {"none", "n/a"}]


def _extract_approval(resume_payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = resume_payload if isinstance(resume_payload, dict) else {}
    nested = payload.get("approval") if isinstance(payload.get("approval"), dict) else {}
    required_action = _normalize_action(nested.get("required_action") or payload.get("approval_required_action"))
    status = _normalize_action(nested.get("status") or payload.get("approval_status")) or "not-needed"
    allowed_actions = _normalize_action_list(
        nested.get("allowed_actions")
        if nested.get("allowed_actions") is not None
        else payload.get("approval_allowed_actions")
    )
    blocked_actions = _normalize_action_list(
        nested.get("blocked_actions")
        if nested.get("blocked_actions") is not None
        else payload.get("approval_blocked_actions")
    )
    return {
        "required_action": required_action,
        "status": status,
        "allowed_actions": allowed_actions,
        "blocked_actions": blocked_actions,
    }


def _merge_initial_route_with_resume(route_payload: dict[str, Any] | None, resume_payload: dict[str, Any] | None) -> dict[str, Any]:
    route = dict(route_payload or {})
    resume = resume_payload if isinstance(resume_payload, dict) else {}
    if _normalize_action(route.get("chapter6_next_action")) in {"", "n/a"}:
        route_next_action = _normalize_action(resume.get("chapter6_next_action"))
        if route_next_action not in {"", "n/a"}:
            route["chapter6_next_action"] = route_next_action
    if _route_blocked_by(route) in {"", "n/a", "none"}:
        blocked_by = str(resume.get("blocked_by") or "").strip().lower()
        if blocked_by not in {"", "n/a", "none"}:
            route["blocked_by"] = blocked_by
    if _route_latest_reason(route) in {"", "n/a", "none"}:
        latest_reason = str(resume.get("latest_reason") or "").strip().lower()
        if latest_reason not in {"", "n/a", "none"}:
            route["latest_reason"] = latest_reason
    if _route_run_id(route) in {"", "n/a"}:
        run_id = str(resume.get("run_id") or "").strip()
        if run_id and run_id.lower() not in {"n/a", "none"}:
            route["run_id"] = run_id
    if not _route_forbidden_commands(route):
        forbidden_commands = resume.get("forbidden_commands")
        if isinstance(forbidden_commands, str) and forbidden_commands.strip():
            route["forbidden_commands"] = forbidden_commands
        elif isinstance(forbidden_commands, list):
            route["forbidden_commands"] = [str(item).strip() for item in forbidden_commands if str(item).strip()]
    return route


def _approval_stop_reason(resume_payload: dict[str, Any] | None, *, desired_action: str) -> str:
    approval = _extract_approval(resume_payload)
    required_action = str(approval.get("required_action") or "")
    if required_action != "fork":
        return ""
    status = str(approval.get("status") or "not-needed")
    allowed_actions = {item for item in list(approval.get("allowed_actions") or []) if item}
    desired = _normalize_action(desired_action) or "resume"
    if desired == "needs-fix-fast":
        desired = "resume"
    if status == "pending":
        return "approval_pending"
    if status == "approved":
        if allowed_actions and "fork" not in allowed_actions:
            return "approval_approved"
        return ""
    if status in {"invalid", "mismatched"}:
        return "approval_invalid"
    if status == "denied" and allowed_actions and desired not in allowed_actions:
        return "approval_denied"
    return ""


def _no_increment_stop_reason(resume_payload: dict[str, Any] | None, route_payload: dict[str, Any] | None) -> str:
    payload = resume_payload if isinstance(resume_payload, dict) else {}
    run_event_summary = payload.get("run_event_summary") if isinstance(payload.get("run_event_summary"), dict) else {}
    turn_count = int(run_event_summary.get("turn_count") or 0)
    if turn_count < 2:
        return ""
    if list(run_event_summary.get("new_reviewers") or []):
        return ""
    if list(run_event_summary.get("new_sidecars") or []):
        return ""
    if bool(run_event_summary.get("approval_changed")):
        return ""
    recommended_action = _normalize_action(payload.get("recommended_action"))
    latest_reason = _route_latest_reason(route_payload)
    preferred_lane = _route_lane(route_payload)
    reviewer_only_lane = recommended_action == "needs-fix-fast" or _route_requires_needs_fix(route_payload)
    reviewer_only_reason = latest_reason.startswith("rerun_blocked:repeat_review_needs_fix") or latest_reason.startswith(
        "rerun_blocked:deterministic_green_llm_not_clean"
    )
    if reviewer_only_lane or reviewer_only_reason or preferred_lane == "run-6.8":
        return "record-residual"
    return ""


def _decide_phase(
    route_payload: dict[str, Any] | None,
    *,
    allow_needs_fix: bool,
    resume_payload: dict[str, Any] | None = None,
) -> dict[str, str]:
    approval_stop_reason = _approval_stop_reason(resume_payload, desired_action="resume")
    if approval_stop_reason:
        return {
            "action": "blocked",
            "stop_reason": approval_stop_reason,
        }
    stop_reason = _route_stop_reason(route_payload)
    if stop_reason == "fork":
        return {
            "action": "fork",
            "stop_reason": "fork",
        }
    if stop_reason:
        return {
            "action": "blocked",
            "stop_reason": stop_reason,
        }
    no_increment_stop_reason = _no_increment_stop_reason(resume_payload, route_payload)
    if no_increment_stop_reason:
        return {
            "action": "blocked",
            "stop_reason": no_increment_stop_reason,
        }
    if _route_next_action(route_payload) == "continue":
        return {
            "action": "complete",
            "stop_reason": "continue",
        }
    if allow_needs_fix and _route_requires_needs_fix(route_payload):
        return {
            "action": "needs-fix-fast",
            "stop_reason": "",
        }
    return {
        "action": "continue",
        "stop_reason": "",
    }


def build_orchestration_decision(
    *,
    initial_route: dict[str, Any],
    post_review_route: dict[str, Any],
    final_route: dict[str, Any],
    resume_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_initial_route = _merge_initial_route_with_resume(initial_route, resume_payload)
    initial_phase = _decide_phase(resolved_initial_route, allow_needs_fix=True, resume_payload=resume_payload)
    if initial_phase["action"] == "continue" and not _initial_route_has_recovery_signal(resolved_initial_route):
        initial_phase = {
            "action": "full-path",
            "stop_reason": "",
        }

    post_review_phase = _decide_phase(post_review_route, allow_needs_fix=True)
    final_phase = _decide_phase(final_route, allow_needs_fix=True)
    return {
        "initial_phase": initial_phase,
        "post_review_phase": post_review_phase,
        "final_phase": final_phase,
    }


def _build_step(name: str, cmd: list[str]) -> dict[str, Any]:
    return {"name": name, "cmd": list(cmd)}


def build_execution_plan(
    *,
    task_id: str,
    godot_bin: str,
    profile_policy: dict[str, str],
    initial_route: dict[str, Any],
    post_review_route: dict[str, Any],
    final_route: dict[str, Any],
    resume_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record_residual = str(profile_policy.get("record_residual") or "").strip().lower() == "true"
    decision = build_orchestration_decision(
        initial_route=initial_route,
        post_review_route=post_review_route,
        final_route=final_route,
        resume_payload=resume_payload,
    )
    steps: list[dict[str, Any]] = [
        _build_step("resume-task", build_resume_task_cmd(task_id)),
        _build_step("chapter6-route-initial", build_chapter6_route_cmd(task_id, record_residual=record_residual)),
    ]
    if decision["initial_phase"]["action"] == "blocked":
        return {
            "status": "blocked",
            "stop_reason": str(decision["initial_phase"]["stop_reason"] or ""),
            "steps": steps,
        }
    if decision["initial_phase"]["action"] == "complete":
        return {
            "status": "complete",
            "stop_reason": str(decision["initial_phase"]["stop_reason"] or "continue"),
            "steps": steps,
        }
    if decision["initial_phase"]["action"] == "fork":
        steps.extend(
            [
                _build_step("review-pipeline-fork", build_review_pipeline_fork_cmd(task_id, profile_policy=profile_policy, godot_bin=godot_bin)),
                _build_step("chapter6-route-post-review", build_chapter6_route_cmd(task_id, record_residual=record_residual)),
            ]
        )
        if decision["post_review_phase"]["action"] == "needs-fix-fast":
            steps.extend(
                [
                    _build_step("needs-fix-fast", build_needs_fix_fast_cmd(task_id, profile_policy=profile_policy)),
                    _build_step("chapter6-route-post-needs-fix", build_chapter6_route_cmd(task_id, record_residual=record_residual)),
                ]
            )
            if decision["final_phase"]["action"] == "blocked":
                return {
                    "status": "blocked",
                    "stop_reason": str(decision["final_phase"]["stop_reason"] or ""),
                    "steps": steps,
                }
        elif decision["post_review_phase"]["action"] == "blocked":
            return {
                "status": "blocked",
                "stop_reason": str(decision["post_review_phase"]["stop_reason"] or ""),
                "steps": steps,
            }
        steps.extend(
            [
                _build_step("local-hard-checks-preflight", build_local_hard_checks_preflight_cmd(profile_policy=profile_policy)),
                _build_step("local-hard-checks", build_local_hard_checks_cmd(profile_policy=profile_policy, godot_bin=godot_bin)),
                _build_step("inspect-local-hard-checks", build_inspect_local_hard_checks_cmd()),
            ]
        )
        return {
            "status": "planned",
            "stop_reason": "",
            "steps": steps,
        }

    if decision["initial_phase"]["action"] == "needs-fix-fast":
        steps.extend(
            [
                _build_step("needs-fix-fast", build_needs_fix_fast_cmd(task_id, profile_policy=profile_policy)),
                _build_step("chapter6-route-post-needs-fix", build_chapter6_route_cmd(task_id, record_residual=record_residual)),
            ]
        )
        if decision["final_phase"]["action"] == "continue":
            steps.extend(
                [
                    _build_step("local-hard-checks-preflight", build_local_hard_checks_preflight_cmd(profile_policy=profile_policy)),
                    _build_step("local-hard-checks", build_local_hard_checks_cmd(profile_policy=profile_policy, godot_bin=godot_bin)),
                    _build_step("inspect-local-hard-checks", build_inspect_local_hard_checks_cmd()),
                ]
            )
        return {
            "status": "planned",
            "stop_reason": "",
            "steps": steps,
        }

    steps.extend(
        [
            _build_step("check-tdd-plan", build_check_tdd_plan_cmd(task_id, profile_policy=profile_policy)),
            _build_step("red-first", build_red_first_cmd(task_id, profile_policy=profile_policy, godot_bin=godot_bin)),
            _build_step("green", build_build_tdd_cmd(task_id, stage="green", profile_policy=profile_policy)),
            _build_step("refactor", build_build_tdd_cmd(task_id, stage="refactor", profile_policy=profile_policy)),
            _build_step("review-pipeline", build_review_pipeline_cmd(task_id, profile_policy=profile_policy, godot_bin=godot_bin)),
            _build_step("chapter6-route-post-review", build_chapter6_route_cmd(task_id, record_residual=record_residual)),
        ]
    )

    if decision["post_review_phase"]["action"] == "needs-fix-fast":
        steps.extend(
            [
                _build_step("needs-fix-fast", build_needs_fix_fast_cmd(task_id, profile_policy=profile_policy)),
                _build_step("chapter6-route-post-needs-fix", build_chapter6_route_cmd(task_id, record_residual=record_residual)),
            ]
        )
        if decision["final_phase"]["action"] == "blocked":
            return {
                "status": "blocked",
                "stop_reason": str(decision["final_phase"]["stop_reason"] or ""),
                "steps": steps,
            }
    else:
        if decision["post_review_phase"]["action"] == "blocked":
            return {
                "status": "blocked",
                "stop_reason": str(decision["post_review_phase"]["stop_reason"] or ""),
                "steps": steps,
            }

    steps.extend(
        [
            _build_step("local-hard-checks-preflight", build_local_hard_checks_preflight_cmd(profile_policy=profile_policy)),
            _build_step("local-hard-checks", build_local_hard_checks_cmd(profile_policy=profile_policy, godot_bin=godot_bin)),
            _build_step("inspect-local-hard-checks", build_inspect_local_hard_checks_cmd()),
        ]
    )
    return {
        "status": "planned",
        "stop_reason": "",
        "steps": steps,
    }


def _run_cmd(cmd: list[str], *, cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    return int(proc.returncode), proc.stdout or "", proc.stderr or ""


def _write_step_log(out_dir: Path, *, name: str, cmd: list[str], stdout: str, stderr: str, rc: int) -> str:
    log_path = out_dir / f"{name}.log"
    log_path.write_text(
        "\n".join(
            [
                f"cmd: {' '.join(cmd)}",
                f"rc: {int(rc)}",
                "--- stdout ---",
                stdout,
                "--- stderr ---",
                stderr,
            ]
        ).rstrip()
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return str(log_path).replace("\\", "/")


def _parse_json_stdout(stdout: str) -> dict[str, Any]:
    text = str(stdout or "")
    if not text.strip():
        return {}
    decoder = json.JSONDecoder()
    start = text.find("{")
    if start < 0:
        return {}
    while start >= 0:
        try:
            payload, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            start = text.find("{", start + 1)
            continue
        if isinstance(payload, dict):
            return payload
        start = text.find("{", start + 1)
    return {}


def _run_json_step(out_dir: Path, *, name: str, cmd: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    rc, stdout, stderr = _run_cmd(cmd, cwd=_repo_root())
    log_path = _write_step_log(out_dir, name=name, cmd=cmd, stdout=stdout, stderr=stderr, rc=rc)
    step = {
        "name": name,
        "cmd": list(cmd),
        "rc": rc,
        "stdout_tail": stdout.strip().splitlines()[-1] if stdout.strip() else "",
        "stderr_tail": stderr.strip().splitlines()[-1] if stderr.strip() else "",
        "log": log_path,
    }
    payload = _parse_json_stdout(stdout)
    return step, payload


def _is_no_latest_index_error(step: dict[str, Any] | None) -> bool:
    payload = step if isinstance(step, dict) else {}
    stdout_tail = str(payload.get("stdout_tail") or "").strip().lower()
    stderr_tail = str(payload.get("stderr_tail") or "").strip().lower()
    markers = (
        "no latest run index found",
        "failed to build task resume summary",
        "failed to route chapter6 recovery",
    )
    text = f"{stdout_tail}\n{stderr_tail}"
    return any(marker in text for marker in markers)


def _run_plain_step(out_dir: Path, *, name: str, cmd: list[str]) -> dict[str, Any]:
    rc, stdout, stderr = _run_cmd(cmd, cwd=_repo_root())
    log_path = _write_step_log(out_dir, name=name, cmd=cmd, stdout=stdout, stderr=stderr, rc=rc)
    return {
        "name": name,
        "cmd": list(cmd),
        "rc": rc,
        "stdout_tail": stdout.strip().splitlines()[-1] if stdout.strip() else "",
        "stderr_tail": stderr.strip().splitlines()[-1] if stderr.strip() else "",
        "log": log_path,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Chapter 6 single-task orchestrator.")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--godot-bin", default=str(os.environ.get("GODOT_BIN") or ""))
    parser.add_argument("--delivery-profile", default=str(os.environ.get("DELIVERY_PROFILE") or "fast-ship"))
    parser.add_argument("--security-profile", default="")
    parser.add_argument("--fix-through", default="")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--self-check", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    task_id = str(args.task_id).strip()
    out_dir = Path(str(args.out_dir).strip()) if str(args.out_dir).strip() else _default_out_dir(task_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    profile_policy = resolve_profile_policy(
        str(args.delivery_profile),
        security_profile=str(args.security_profile),
        fix_through=str(args.fix_through),
    )

    if bool(args.self_check):
        placeholder_route = {
            "preferred_lane": "inspect-first",
            "run_id": "n/a",
            "latest_reason": "n/a",
            "blocked_by": "n/a",
        }
        plan = build_execution_plan(
            task_id=task_id,
            godot_bin=str(args.godot_bin),
            profile_policy=profile_policy,
            initial_route=placeholder_route,
            post_review_route={"preferred_lane": "inspect-first"},
            final_route={"preferred_lane": "inspect-first"},
            resume_payload={},
        )
        payload = {
            "cmd": "run-single-task-chapter6",
            "task_id": task_id,
            "status": "ok",
            "profile_policy": profile_policy,
            "plan_status": plan["status"],
            "steps": plan["steps"],
            "out_dir": str(out_dir).replace("\\", "/"),
        }
        _write_json(out_dir / "summary.json", payload)
        print(
            "SINGLE_TASK_CHAPTER6_SELF_CHECK "
            f"status=ok task={task_id} profile={profile_policy['delivery_profile']} "
            f"out={str((out_dir / 'summary.json')).replace('\\', '/')}"
        )
        return 0

    summary: dict[str, Any] = {
        "cmd": "run-single-task-chapter6",
        "task_id": task_id,
        "status": "running",
        "profile_policy": profile_policy,
        "out_dir": str(out_dir).replace("\\", "/"),
        "steps": [],
        "stop_reason": "",
    }

    resume_step, resume_payload = _run_json_step(out_dir, name="resume-task", cmd=build_resume_task_cmd(task_id))
    summary["steps"].append(resume_step)
    summary["resume"] = resume_payload
    resume_missing_latest = int(resume_step["rc"]) != 0 and _is_no_latest_index_error(resume_step)
    if int(resume_step["rc"]) != 0 and not resume_missing_latest:
        summary["status"] = "fail"
        summary["stop_reason"] = "resume-task"
        _write_json(out_dir / "summary.json", summary)
        print(f"SINGLE_TASK_CHAPTER6 status=fail task={task_id} stop=resume-task")
        return 1
    if resume_missing_latest:
        resume_payload = {}
        summary["resume_recovery_mode"] = "fresh-start-no-latest"

    record_residual = str(profile_policy["record_residual"]).strip().lower() == "true"
    initial_route_step, initial_route = _run_json_step(
        out_dir,
        name="chapter6-route-initial",
        cmd=build_chapter6_route_cmd(task_id, record_residual=record_residual),
    )
    summary["steps"].append(initial_route_step)
    summary["initial_route"] = initial_route
    initial_route_missing_latest = int(initial_route_step["rc"]) != 0 and _is_no_latest_index_error(initial_route_step)
    if int(initial_route_step["rc"]) != 0 and not initial_route_missing_latest:
        summary["status"] = "fail"
        summary["stop_reason"] = "chapter6-route-initial"
        _write_json(out_dir / "summary.json", summary)
        print(f"SINGLE_TASK_CHAPTER6 status=fail task={task_id} stop=chapter6-route-initial")
        return 1
    if initial_route_missing_latest:
        if not resume_missing_latest:
            summary["status"] = "fail"
            summary["stop_reason"] = "chapter6-route-initial"
            _write_json(out_dir / "summary.json", summary)
            print(f"SINGLE_TASK_CHAPTER6 status=fail task={task_id} stop=chapter6-route-initial")
            return 1
        initial_route = {
            "preferred_lane": "inspect-first",
            "run_id": "n/a",
            "latest_reason": "n/a",
            "blocked_by": "n/a",
        }
        summary["initial_route"] = initial_route
        summary["route_recovery_mode"] = "fresh-start-no-latest"

    plan = build_execution_plan(
        task_id=task_id,
        godot_bin=str(args.godot_bin),
        profile_policy=profile_policy,
        initial_route=initial_route,
        post_review_route={"preferred_lane": "inspect-first"},
        final_route={"preferred_lane": "inspect-first"},
        resume_payload=resume_payload,
    )
    summary["planned_steps"] = [step["name"] for step in plan["steps"]]
    if plan["status"] == "blocked":
        summary["status"] = "blocked"
        summary["stop_reason"] = str(plan["stop_reason"])
        _write_json(out_dir / "summary.json", summary)
        print(f"SINGLE_TASK_CHAPTER6 status=blocked task={task_id} stop={plan['stop_reason']}")
        return 1
    if plan["status"] == "complete":
        summary["status"] = "complete"
        summary["stop_reason"] = str(plan["stop_reason"] or "continue")
        _write_json(out_dir / "summary.json", summary)
        print(f"SINGLE_TASK_CHAPTER6 status=complete task={task_id} stop={summary['stop_reason']}")
        return 0

    post_review_route: dict[str, Any] = {}
    final_route: dict[str, Any] = {}

    def _run_required(name: str, cmd: list[str]) -> bool:
        route_payload: dict[str, Any] | None = None
        if name in {"check-tdd-plan", "red-first", "green", "refactor", "review-pipeline", "review-pipeline-fork"}:
            route_payload = initial_route
        elif name in {"local-hard-checks-preflight", "local-hard-checks"}:
            route_payload = final_route if isinstance(final_route, dict) and final_route else post_review_route
        if _command_is_forbidden(route_payload, cmd):
            summary["status"] = "blocked"
            summary["stop_reason"] = f"forbidden-command:{name}"
            _write_json(out_dir / "summary.json", summary)
            print(f"SINGLE_TASK_CHAPTER6 status=blocked task={task_id} stop={summary['stop_reason']}")
            return False
        step = _run_plain_step(out_dir, name=name, cmd=cmd)
        summary["steps"].append(step)
        if int(step["rc"]) != 0:
            summary["status"] = "fail"
            summary["stop_reason"] = name
            _write_json(out_dir / "summary.json", summary)
            print(f"SINGLE_TASK_CHAPTER6 status=fail task={task_id} stop={name}")
            return False
        return True

    def _run_route(name: str) -> dict[str, Any] | None:
        step, payload = _run_json_step(
            out_dir,
            name=name,
            cmd=build_chapter6_route_cmd(task_id, record_residual=record_residual),
        )
        summary["steps"].append(step)
        summary[name.replace("-", "_")] = payload
        if int(step["rc"]) != 0:
            summary["status"] = "fail"
            summary["stop_reason"] = name
            _write_json(out_dir / "summary.json", summary)
            print(f"SINGLE_TASK_CHAPTER6 status=fail task={task_id} stop={name}")
            return None
        return payload

    decision = build_orchestration_decision(
        initial_route=initial_route,
        post_review_route={},
        final_route={},
        resume_payload=resume_payload,
    )
    if decision["initial_phase"]["action"] == "fork":
        if not _run_required(
            "review-pipeline-fork",
            build_review_pipeline_fork_cmd(task_id, profile_policy=profile_policy, godot_bin=str(args.godot_bin)),
        ):
            return 1
        post_review_route = _run_route("chapter6-route-post-review")
        if post_review_route is None:
            return 1
        post_review_decision = build_orchestration_decision(
            initial_route=initial_route,
            post_review_route=post_review_route,
            final_route={},
            resume_payload=resume_payload,
        )
        if post_review_decision["post_review_phase"]["action"] == "blocked":
            summary["status"] = "blocked"
            summary["stop_reason"] = str(post_review_decision["post_review_phase"]["stop_reason"] or "")
            _write_json(out_dir / "summary.json", summary)
            print(f"SINGLE_TASK_CHAPTER6 status=blocked task={task_id} stop={summary['stop_reason']}")
            return 1
        if post_review_decision["post_review_phase"]["action"] == "needs-fix-fast":
            if not _run_required("needs-fix-fast", build_needs_fix_fast_cmd(task_id, profile_policy=profile_policy)):
                return 1
            final_route = _run_route("chapter6-route-post-needs-fix")
            if final_route is None:
                return 1
            final_decision = build_orchestration_decision(
                initial_route=initial_route,
                post_review_route=post_review_route,
                final_route=final_route,
                resume_payload=resume_payload,
            )
            if final_decision["final_phase"]["action"] in {"blocked", "needs-fix-fast"}:
                summary["status"] = "blocked"
                summary["stop_reason"] = str(final_decision["final_phase"]["stop_reason"] or _route_lane(final_route))
                _write_json(out_dir / "summary.json", summary)
                print(f"SINGLE_TASK_CHAPTER6 status=blocked task={task_id} stop={summary['stop_reason']}")
                return 1
    elif decision["initial_phase"]["action"] == "needs-fix-fast":
        if not _run_required("needs-fix-fast", build_needs_fix_fast_cmd(task_id, profile_policy=profile_policy)):
            return 1
        final_route = _run_route("chapter6-route-post-needs-fix")
        if final_route is None:
            return 1
        final_decision = build_orchestration_decision(
            initial_route=initial_route,
            post_review_route={},
            final_route=final_route,
            resume_payload=resume_payload,
        )
        if final_decision["final_phase"]["action"] in {"blocked", "needs-fix-fast"}:
            summary["status"] = "blocked"
            summary["stop_reason"] = str(final_decision["final_phase"]["stop_reason"] or _route_lane(final_route))
            _write_json(out_dir / "summary.json", summary)
            print(f"SINGLE_TASK_CHAPTER6 status=blocked task={task_id} stop={summary['stop_reason']}")
            return 1
    else:
        full_path_steps = [
            ("check-tdd-plan", build_check_tdd_plan_cmd(task_id, profile_policy=profile_policy)),
            ("red-first", build_red_first_cmd(task_id, profile_policy=profile_policy, godot_bin=str(args.godot_bin))),
            ("green", build_build_tdd_cmd(task_id, stage="green", profile_policy=profile_policy)),
            ("refactor", build_build_tdd_cmd(task_id, stage="refactor", profile_policy=profile_policy)),
            ("review-pipeline", build_review_pipeline_cmd(task_id, profile_policy=profile_policy, godot_bin=str(args.godot_bin))),
        ]
        for name, cmd in full_path_steps:
            if not _run_required(name, cmd):
                return 1
        post_review_route = _run_route("chapter6-route-post-review")
        if post_review_route is None:
            return 1
        post_review_decision = build_orchestration_decision(
            initial_route=initial_route,
            post_review_route=post_review_route,
            final_route={},
            resume_payload=resume_payload,
        )
        if post_review_decision["post_review_phase"]["action"] == "blocked":
            summary["status"] = "blocked"
            summary["stop_reason"] = str(post_review_decision["post_review_phase"]["stop_reason"] or "")
            _write_json(out_dir / "summary.json", summary)
            print(f"SINGLE_TASK_CHAPTER6 status=blocked task={task_id} stop={summary['stop_reason']}")
            return 1
        if post_review_decision["post_review_phase"]["action"] == "needs-fix-fast":
            if not _run_required("needs-fix-fast", build_needs_fix_fast_cmd(task_id, profile_policy=profile_policy)):
                return 1
            final_route = _run_route("chapter6-route-post-needs-fix")
            if final_route is None:
                return 1
            final_decision = build_orchestration_decision(
                initial_route=initial_route,
                post_review_route=post_review_route,
                final_route=final_route,
                resume_payload=resume_payload,
            )
            if final_decision["final_phase"]["action"] in {"blocked", "needs-fix-fast"}:
                summary["status"] = "blocked"
                summary["stop_reason"] = str(final_decision["final_phase"]["stop_reason"] or _route_lane(final_route))
                _write_json(out_dir / "summary.json", summary)
                print(f"SINGLE_TASK_CHAPTER6 status=blocked task={task_id} stop={summary['stop_reason']}")
                return 1

    if not _run_required("local-hard-checks-preflight", build_local_hard_checks_preflight_cmd(profile_policy=profile_policy)):
        return 1
    if not _run_required("local-hard-checks", build_local_hard_checks_cmd(profile_policy=profile_policy, godot_bin=str(args.godot_bin))):
        return 1
    inspect_step, inspect_payload = _run_json_step(out_dir, name="inspect-local-hard-checks", cmd=build_inspect_local_hard_checks_cmd())
    summary["steps"].append(inspect_step)
    summary["inspect_local_hard_checks"] = inspect_payload
    if int(inspect_step["rc"]) != 0:
        summary["status"] = "fail"
        summary["stop_reason"] = "inspect-local-hard-checks"
        _write_json(out_dir / "summary.json", summary)
        print(f"SINGLE_TASK_CHAPTER6 status=fail task={task_id} stop=inspect-local-hard-checks")
        return 1

    summary["status"] = "ok"
    _write_json(out_dir / "summary.json", summary)
    print(f"SINGLE_TASK_CHAPTER6 status=ok task={task_id} out={str((out_dir / 'summary.json')).replace('\\', '/')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
