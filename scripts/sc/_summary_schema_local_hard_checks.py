from __future__ import annotations

from typing import Any


LOCAL_HARD_CHECKS_STEP_NAMES = {"project-health-scan", "gate-bundle-hard", "run-dotnet", "gdunit-hard", "smoke-strict"}
LOCAL_HARD_CHECKS_STATUS = {"ok", "fail"}


def validate_local_hard_checks_without_jsonschema(
    payload: dict[str, Any],
    *,
    is_non_empty_string,
    is_string_list,
    is_int_not_bool,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["$: summary payload must be an object"]

    required = {
        "schema_version",
        "protocol_version",
        "cmd",
        "task_id",
        "requested_run_id",
        "run_id",
        "delivery_profile",
        "security_profile",
        "status",
        "failed_step",
        "started_at",
        "finished_at",
        "out_dir",
        "steps",
    }
    allowed = required

    for key in required:
        if key not in payload:
            errors.append(f"$.{key}: missing required property")
    for key in payload.keys():
        if key not in allowed:
            errors.append(f"$.{key}: unexpected property")

    for key in (
        "schema_version",
        "protocol_version",
        "requested_run_id",
        "run_id",
        "delivery_profile",
        "started_at",
        "finished_at",
        "out_dir",
    ):
        if not is_non_empty_string(payload.get(key)):
            errors.append(f"$.{key}: must be non-empty string")

    if payload.get("cmd") != "local-hard-checks":
        errors.append("$.cmd: must equal 'local-hard-checks'")

    task_id = payload.get("task_id")
    if not isinstance(task_id, str) or task_id != "repo":
        errors.append("$.task_id: must equal 'repo'")

    security_profile = payload.get("security_profile")
    if not isinstance(security_profile, str) or security_profile not in {"strict", "host-safe"}:
        errors.append("$.security_profile: must be one of ['host-safe', 'strict']")

    status = payload.get("status")
    if not isinstance(status, str) or status not in LOCAL_HARD_CHECKS_STATUS:
        errors.append("$.status: must be one of ['ok', 'fail']")

    failed_step = payload.get("failed_step")
    if not isinstance(failed_step, str):
        errors.append("$.failed_step: must be string")

    steps = payload.get("steps")
    if not isinstance(steps, list):
        errors.append("$.steps: must be array")
        return errors

    step_allowed = {"name", "cmd", "rc", "status", "log", "reported_out_dir", "summary_file"}
    for index, step in enumerate(steps):
        base = f"$.steps[{index}]"
        if not isinstance(step, dict):
            errors.append(f"{base}: must be object")
            continue
        for key in ("name", "cmd", "rc", "status", "log"):
            if key not in step:
                errors.append(f"{base}.{key}: missing required property")
        for key in step.keys():
            if key not in step_allowed:
                errors.append(f"{base}.{key}: unexpected property")

        name = step.get("name")
        if not isinstance(name, str) or name not in LOCAL_HARD_CHECKS_STEP_NAMES:
            errors.append(f"{base}.name: must be one of {sorted(LOCAL_HARD_CHECKS_STEP_NAMES)}")

        cmd = step.get("cmd")
        if not is_string_list(cmd, allow_empty=False):
            errors.append(f"{base}.cmd: must be non-empty array of non-empty strings")

        if not is_int_not_bool(step.get("rc")):
            errors.append(f"{base}.rc: must be integer")

        step_status = step.get("status")
        if not isinstance(step_status, str) or step_status not in LOCAL_HARD_CHECKS_STATUS:
            errors.append(f"{base}.status: must be one of ['ok', 'fail']")

        if not isinstance(step.get("log"), str):
            errors.append(f"{base}.log: must be string")

        for key in ("reported_out_dir", "summary_file"):
            if key in step and not isinstance(step.get(key), str):
                errors.append(f"{base}.{key}: must be string when present")

        if name == "project-health-scan":
            reported_out_dir = step.get("reported_out_dir")
            summary_file = step.get("summary_file")
            if not isinstance(reported_out_dir, str) or not reported_out_dir.replace("\\", "/").endswith("logs/ci/project-health"):
                errors.append(f"{base}.reported_out_dir: must end with logs/ci/project-health")
            if not isinstance(summary_file, str) or not summary_file.replace("\\", "/").endswith(
                "logs/ci/project-health/project-health-scan.latest.json"
            ):
                errors.append(f"{base}.summary_file: must end with logs/ci/project-health/project-health-scan.latest.json")

    return errors
