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


def _first_failed_step(summary_payload: dict[str, Any] | None) -> str:
    summary = summary_payload if isinstance(summary_payload, dict) else {}
    steps = summary.get("steps") if isinstance(summary.get("steps"), list) else []
    return next(
        (
            str(step.get("name") or "").strip()
            for step in steps
            if isinstance(step, dict) and str(step.get("status") or "").strip().lower() == "fail"
        ),
        "",
    )


def classify_producer_failure(
    *,
    summary_payload: dict[str, Any] | None,
    repair_payload: dict[str, Any] | None = None,
    latest_status: str = "",
    run_completed: bool | None = None,
) -> dict[str, Any]:
    summary = summary_payload if isinstance(summary_payload, dict) else {}
    repair = repair_payload if isinstance(repair_payload, dict) else {}
    normalized_latest_status = str(latest_status or "").strip().lower()
    summary_status = str(summary.get("status") or normalized_latest_status or "fail").strip().lower()
    repair_status = str(repair.get("status") or "").strip().lower()
    run_type = str(summary.get("run_type") or "").strip().lower()
    finished_at_utc = str(summary.get("finished_at_utc") or "").strip()
    incomplete_run = False
    if normalized_latest_status == "running":
        incomplete_run = True
    elif run_type == "planned-only" and (bool(finished_at_utc) or run_completed is True):
        incomplete_run = True
    elif run_completed is False and normalized_latest_status == "ok":
        incomplete_run = True
    return classify_run_failure(
        latest_status=normalized_latest_status or summary_status,
        summary_status=summary_status,
        repair_status=repair_status,
        failed_step=_first_failed_step(summary),
        validation_errors=[],
        missing_artifacts=[],
        stale_latest=False,
        incomplete_run=incomplete_run,
    )


def derive_producer_failure_kind(
    *,
    summary_payload: dict[str, Any] | None,
    repair_payload: dict[str, Any] | None = None,
    latest_status: str = "",
    run_completed: bool | None = None,
) -> str:
    return str(
        classify_producer_failure(
            summary_payload=summary_payload,
            repair_payload=repair_payload,
            latest_status=latest_status,
            run_completed=run_completed,
        ).get("code")
        or "ok"
    ).strip()
