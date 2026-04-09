from __future__ import annotations

from typing import Any


def classify_run_failure(
    *,
    latest_status: str,
    summary_status: str,
    repair_status: str,
    failed_step: str,
    validation_errors: list[str],
    missing_artifacts: list[str],
    stale_latest: bool,
    incomplete_run: bool,
) -> dict[str, Any]:
    if validation_errors:
        return {
            "code": "schema-invalid",
            "message": "One or more run artifacts failed schema validation.",
            "severity": "hard",
        }
    if stale_latest:
        return {
            "code": "stale-latest",
            "message": "The latest pointer resolves to missing or moved run artifacts.",
            "severity": "hard",
        }
    if missing_artifacts:
        return {
            "code": "artifact-missing",
            "message": "One or more required sidecars are missing.",
            "severity": "hard",
        }
    if incomplete_run:
        return {
            "code": "artifact-incomplete",
            "message": "The latest pointer reports ok, but the producer run has no run_completed event yet.",
            "severity": "hard",
        }
    if latest_status == "aborted":
        return {
            "code": "aborted",
            "message": "The run was intentionally aborted.",
            "severity": "soft",
        }
    if summary_status == "fail":
        step_text = failed_step or "unknown-step"
        return {
            "code": "step-failed",
            "message": f"The producer pipeline failed at {step_text}.",
            "severity": "soft",
        }
    if repair_status == "needs-fix":
        return {
            "code": "review-needs-fix",
            "message": "The run completed but follow-up repair work is still required.",
            "severity": "soft",
        }
    return {
        "code": "ok",
        "message": "The run artifacts are valid and no blocking follow-up is required.",
        "severity": "none",
    }
