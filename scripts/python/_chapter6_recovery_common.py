#!/usr/bin/env python3
from __future__ import annotations

from typing import Any


def chapter6_stop_loss_note(chapter6_hints: dict[str, Any], latest_summary_signals: dict[str, Any]) -> str:
    blocked_by = str(chapter6_hints.get("blocked_by") or "").strip().lower()
    reason = str(latest_summary_signals.get("reason") or "").strip()
    artifact_integrity_kind = str(latest_summary_signals.get("artifact_integrity_kind") or "").strip().lower()
    if not blocked_by and reason.startswith("rerun_blocked:deterministic_green_llm_not_clean"):
        blocked_by = "rerun_guard"
    elif not blocked_by and reason.startswith("rerun_blocked:repeat_deterministic_failure"):
        blocked_by = "rerun_guard"
    elif not blocked_by and (
        reason.startswith("rerun_blocked:dirty_worktree_unsafe_paths_ceiling")
        or reason.startswith("rerun_blocked:dirty_worktree_changed_paths_ceiling")
        or reason.startswith("rerun_blocked:profile_drift_change_scope_ceiling")
    ):
        blocked_by = "rerun_guard"
    elif not blocked_by and (reason == "planned_only_incomplete" or artifact_integrity_kind == "planned_only_incomplete"):
        blocked_by = "artifact_integrity"
    if blocked_by == "rerun_guard":
        if reason.startswith("rerun_blocked:deterministic_green_llm_not_clean"):
            return "Deterministic evidence is already green; do not pay for another full 6.7. Continue with 6.8 or needs-fix-fast."
        if reason.startswith("rerun_blocked:repeat_deterministic_failure"):
            return "Recent deterministic failures already repeated with the same fingerprint; inspect and fix the root cause before rerunning 6.7."
        if (
            reason.startswith("rerun_blocked:dirty_worktree_unsafe_paths_ceiling")
            or reason.startswith("rerun_blocked:dirty_worktree_changed_paths_ceiling")
            or reason.startswith("rerun_blocked:profile_drift_change_scope_ceiling")
        ):
            return "Current changes exceed the standard Chapter 6 safe scope; shrink the dirty worktree or inspect/reset the drift before paying for another full 6.7."
        return "A rerun guard is active; check the latest diagnostics before paying for another full rerun."
    if blocked_by == "llm_retry_stop_loss":
        return "This run already stopped after the first costly llm timeout; continue with the narrow llm-only closure path instead of reopening deterministic steps."
    if blocked_by == "sc_test_retry_stop_loss":
        return "The pipeline already proved the unit root cause and stopped the same-run retry; fix the unit issue first, then start a fresh run."
    if blocked_by == "waste_signals":
        return "Unit failure was already known before more expensive engine-lane work continued; fix the unit/root cause before paying that cost again."
    if blocked_by == "recent_failure_summary":
        return "Recent runs already repeat the same failure family; inspect the repeated fingerprint and fix the root cause before rerunning 6.7."
    if blocked_by == "artifact_integrity":
        if reason == "planned_only_incomplete" or artifact_integrity_kind == "planned_only_incomplete":
            return "The latest bundle is a planned-only terminal run, not a real completed producer run; inspect it only for evidence and start a fresh real run before reopening Chapter 6."
        return "The latest recovery bundle is incomplete or stale; inspect the evidence only, then start a fresh real run instead of resuming from this pointer."
    return ""
