from __future__ import annotations

import re
from typing import Any

from _summary_schema_local_hard_checks import validate_local_hard_checks_without_jsonschema as _validate_local_hard_checks_impl

RUN_ID_RE = re.compile(r"^([A-Fa-f0-9]{32}|[A-Za-z0-9][A-Za-z0-9._:-]{2,127})$")
TASK_ID_RE = re.compile(r"^[0-9]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

PIPELINE_STEP_NAMES = {"sc-test", "sc-acceptance-check", "sc-llm-review", "sc-build-tdd-refactor-preflight"}
PIPELINE_STEP_STATUS = {"ok", "fail", "skipped", "planned"}
PIPELINE_SUMMARY_STATUS = {"ok", "fail"}
PIPELINE_REUSE_MODE = {"none", "full-clean-reuse", "deterministic-only-reuse", "sc-test-reuse", "mixed-reuse"}

SC_TEST_TYPES = {"unit", "integration", "e2e", "all"}
SC_TEST_STEP_STATUS = {"ok", "fail", "skipped"}

SC_ACCEPTANCE_MODES = {"self-check", "dry-run-plan", "run"}
SC_ACCEPTANCE_STATUS = {"ok", "fail"}
SC_ACCEPTANCE_SUBTASKS_MODE = {"skip", "warn", "require"}
GATE_MODE = {"skip", "warn", "require"}
def _is_int_not_bool(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
def _is_optional_int_not_bool(value: Any) -> bool:
    return value is None or _is_int_not_bool(value)
def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
def _is_string_list(value: Any, *, allow_empty: bool) -> bool:
    if not isinstance(value, list):
        return False
    if not allow_empty and len(value) == 0:
        return False
    return all(_is_non_empty_string(x) for x in value)
def _validate_gate_mode_map(value: Any, *, base_path: str) -> list[str]:
    errors: list[str] = []
    required = {
        "path",
        "sql",
        "audit_schema",
        "ui_event_json_guards",
        "ui_event_source_verify",
        "audit_evidence",
    }
    if not isinstance(value, dict):
        return [f"{base_path}: must be object"]
    for key in required:
        if key not in value:
            errors.append(f"{base_path}.{key}: missing required property")
    for key in value.keys():
        if key not in required:
            errors.append(f"{base_path}.{key}: unexpected property")
    for key in required:
        gate_value = value.get(key)
        if not isinstance(gate_value, str) or gate_value not in GATE_MODE:
            errors.append(f"{base_path}.{key}: must be one of {sorted(GATE_MODE)}")
    return errors
def validate_pipeline_without_jsonschema(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["$: summary payload must be an object"]

    required = {
        "cmd",
        "task_id",
        "requested_run_id",
        "run_id",
        "allow_overwrite",
        "force_new_run_id",
        "status",
        "steps",
        "started_at_utc",
        "finished_at_utc",
        "elapsed_sec",
        "run_type",
        "reason",
        "reuse_mode",
    }
    allowed = required | {"diagnostics"}
    for key in required:
        if key not in payload:
            errors.append(f"$.{key}: missing required property")
    for key in payload.keys():
        if key not in allowed:
            errors.append(f"$.{key}: unexpected property")

    if payload.get("cmd") != "sc-review-pipeline":
        errors.append("$.cmd: must equal 'sc-review-pipeline'")

    task_id = payload.get("task_id")
    if not isinstance(task_id, str) or not TASK_ID_RE.match(task_id):
        errors.append("$.task_id: must be numeric string")

    requested_run_id = payload.get("requested_run_id")
    if not isinstance(requested_run_id, str) or not requested_run_id.strip():
        errors.append("$.requested_run_id: must be non-empty string")

    run_id = payload.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID_RE.match(run_id):
        errors.append("$.run_id: must match /^[A-Fa-f0-9]{32}$/")

    for key in ("allow_overwrite", "force_new_run_id"):
        if not isinstance(payload.get(key), bool):
            errors.append(f"$.{key}: must be boolean")

    status = payload.get("status")
    if not isinstance(status, str) or status not in PIPELINE_SUMMARY_STATUS:
        errors.append("$.status: must be one of ['ok', 'fail']")
    if not _is_non_empty_string(payload.get("started_at_utc")):
        errors.append("$.started_at_utc: must be non-empty string")
    if not isinstance(payload.get("finished_at_utc"), str):
        errors.append("$.finished_at_utc: must be string")
    if not _is_int_not_bool(payload.get("elapsed_sec")) or int(payload.get("elapsed_sec") or 0) < 0:
        errors.append("$.elapsed_sec: must be integer >= 0")
    if str(payload.get("run_type") or "") not in {"planned-only", "preflight-only", "llm-only", "deterministic-only", "full"}:
        errors.append("$.run_type: must be a known pipeline run type")
    if not _is_non_empty_string(payload.get("reason")):
        errors.append("$.reason: must be non-empty string")
    reuse_mode = payload.get("reuse_mode")
    if not isinstance(reuse_mode, str) or reuse_mode not in PIPELINE_REUSE_MODE:
        errors.append(f"$.reuse_mode: must be one of {sorted(PIPELINE_REUSE_MODE)}")
    if "diagnostics" in payload and not isinstance(payload.get("diagnostics"), dict):
        errors.append("$.diagnostics: must be object when present")

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
        for key in ("name", "cmd", "rc", "status"):
            if key not in step:
                errors.append(f"{base}.{key}: missing required property")
        for key in step.keys():
            if key not in step_allowed:
                errors.append(f"{base}.{key}: unexpected property")

        name = step.get("name")
        if not isinstance(name, str) or name not in PIPELINE_STEP_NAMES:
            errors.append(f"{base}.name: must be one of {sorted(PIPELINE_STEP_NAMES)}")

        cmd = step.get("cmd")
        if not _is_string_list(cmd, allow_empty=False):
            errors.append(f"{base}.cmd: must be non-empty array of non-empty strings")

        rc = step.get("rc")
        if not _is_int_not_bool(rc):
            errors.append(f"{base}.rc: must be integer")

        step_status = step.get("status")
        if not isinstance(step_status, str) or step_status not in PIPELINE_STEP_STATUS:
            errors.append(f"{base}.status: must be one of {sorted(PIPELINE_STEP_STATUS)}")

        for opt in ("log", "reported_out_dir", "summary_file"):
            if opt in step and not isinstance(step.get(opt), str):
                errors.append(f"{base}.{opt}: must be string when present")

        if step_status in {"ok", "fail"} and "log" not in step:
            errors.append(f"{base}.log: required when status is ok/fail")

    return errors


def validate_sc_test_without_jsonschema(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["$: summary payload must be an object"]

    required = {"cmd", "run_id", "type", "solution", "configuration", "status", "steps"}
    allowed = required | {"task_id"}

    for key in required:
        if key not in payload:
            errors.append(f"$.{key}: missing required property")
    for key in payload.keys():
        if key not in allowed:
            errors.append(f"$.{key}: unexpected property")

    if payload.get("cmd") != "sc-test":
        errors.append("$.cmd: must equal 'sc-test'")
    if not isinstance(payload.get("run_id"), str) or not RUN_ID_RE.match(payload.get("run_id")):
        errors.append("$.run_id: must match /^[A-Fa-f0-9]{32}$/")

    task_id = payload.get("task_id")
    if task_id is not None and (not isinstance(task_id, str) or not task_id.strip() or not TASK_ID_RE.match(task_id)):
        errors.append("$.task_id: must be numeric string when present")

    test_type = payload.get("type")
    if not isinstance(test_type, str) or test_type not in SC_TEST_TYPES:
        errors.append(f"$.type: must be one of {sorted(SC_TEST_TYPES)}")
    if not _is_non_empty_string(payload.get("solution")):
        errors.append("$.solution: must be non-empty string")
    if not _is_non_empty_string(payload.get("configuration")):
        errors.append("$.configuration: must be non-empty string")

    status = payload.get("status")
    if not isinstance(status, str) or status not in SC_ACCEPTANCE_STATUS:
        errors.append("$.status: must be one of ['ok', 'fail']")

    steps = payload.get("steps")
    if not isinstance(steps, list):
        errors.append("$.steps: must be array")
        return errors

    step_allowed = {"name", "status", "rc", "cmd", "log", "artifacts_dir", "report_dir", "reason", "error"}
    for index, step in enumerate(steps):
        base = f"$.steps[{index}]"
        if not isinstance(step, dict):
            errors.append(f"{base}: must be object")
            continue
        for key in ("name", "status"):
            if key not in step:
                errors.append(f"{base}.{key}: missing required property")
        for key in step.keys():
            if key not in step_allowed:
                errors.append(f"{base}.{key}: unexpected property")

        if not _is_non_empty_string(step.get("name")):
            errors.append(f"{base}.name: must be non-empty string")

        step_status = step.get("status")
        if not isinstance(step_status, str) or step_status not in SC_TEST_STEP_STATUS:
            errors.append(f"{base}.status: must be one of {sorted(SC_TEST_STEP_STATUS)}")

        if "rc" in step and not _is_int_not_bool(step.get("rc")):
            errors.append(f"{base}.rc: must be integer when present")
        if "cmd" in step and not _is_string_list(step.get("cmd"), allow_empty=True):
            errors.append(f"{base}.cmd: must be array of non-empty strings when present")

        for key in ("log", "artifacts_dir", "report_dir", "reason", "error"):
            if key in step and not isinstance(step.get(key), str):
                errors.append(f"{base}.{key}: must be string when present")

        if step_status in {"ok", "fail"}:
            if "rc" not in step:
                errors.append(f"{base}.rc: required when status is ok/fail")
            if "log" not in step:
                errors.append(f"{base}.log: required when status is ok/fail")

    return errors


def validate_sc_acceptance_without_jsonschema(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["$: summary payload must be an object"]

    required = {
        "schema_version",
        "cmd",
        "mode",
        "date",
        "only",
        "status",
        "out_dir",
        "subtasks_coverage_mode",
        "security_profile",
        "security_modes",
        "arg_validation",
    }
    allowed = required | {"run_id", "task_id", "title", "steps", "task_requirements", "metrics", "risk_summary", "step_plan"}
    for key in required:
        if key not in payload:
            errors.append(f"$.{key}: missing required property")
    for key in payload.keys():
        if key not in allowed:
            errors.append(f"$.{key}: unexpected property")

    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, str) or not SEMVER_RE.match(schema_version):
        errors.append("$.schema_version: must match semantic version pattern")
    if payload.get("cmd") != "sc-acceptance-check":
        errors.append("$.cmd: must equal 'sc-acceptance-check'")

    mode = payload.get("mode")
    if not isinstance(mode, str) or mode not in SC_ACCEPTANCE_MODES:
        errors.append(f"$.mode: must be one of {sorted(SC_ACCEPTANCE_MODES)}")

    date_value = payload.get("date")
    if not isinstance(date_value, str) or not DATE_RE.match(date_value):
        errors.append("$.date: must match YYYY-MM-DD")

    if payload.get("only") is not None and not isinstance(payload.get("only"), str):
        errors.append("$.only: must be string or null")

    status = payload.get("status")
    if not isinstance(status, str) or status not in SC_ACCEPTANCE_STATUS:
        errors.append("$.status: must be one of ['ok', 'fail']")
    if not isinstance(payload.get("out_dir"), str):
        errors.append("$.out_dir: must be string")

    subtasks_mode = payload.get("subtasks_coverage_mode")
    if not isinstance(subtasks_mode, str) or subtasks_mode not in SC_ACCEPTANCE_SUBTASKS_MODE:
        errors.append(f"$.subtasks_coverage_mode: must be one of {sorted(SC_ACCEPTANCE_SUBTASKS_MODE)}")

    security_profile = payload.get("security_profile")
    if not isinstance(security_profile, dict):
        errors.append("$.security_profile: must be object")
    else:
        required_security_profile = {"profile", "gate_defaults"}
        for key in required_security_profile:
            if key not in security_profile:
                errors.append(f"$.security_profile.{key}: missing required property")
        for key in security_profile.keys():
            if key not in required_security_profile:
                errors.append(f"$.security_profile.{key}: unexpected property")
        profile = security_profile.get("profile")
        if not isinstance(profile, str) or profile not in {"strict", "host-safe"}:
            errors.append("$.security_profile.profile: must be 'strict' or 'host-safe'")
        errors.extend(_validate_gate_mode_map(security_profile.get("gate_defaults"), base_path="$.security_profile.gate_defaults"))

    errors.extend(_validate_gate_mode_map(payload.get("security_modes"), base_path="$.security_modes"))

    arg_validation = payload.get("arg_validation")
    if not isinstance(arg_validation, dict):
        errors.append("$.arg_validation: must be object")
    else:
        required_arg_validation = {"errors", "valid"}
        for key in required_arg_validation:
            if key not in arg_validation:
                errors.append(f"$.arg_validation.{key}: missing required property")
        for key in arg_validation.keys():
            if key not in required_arg_validation:
                errors.append(f"$.arg_validation.{key}: unexpected property")
        if not isinstance(arg_validation.get("errors"), list) or not all(isinstance(x, str) for x in arg_validation.get("errors", [])):
            errors.append("$.arg_validation.errors: must be array of strings")
        if not isinstance(arg_validation.get("valid"), bool):
            errors.append("$.arg_validation.valid: must be boolean")

    if "run_id" in payload and (not isinstance(payload.get("run_id"), str) or not RUN_ID_RE.match(payload.get("run_id"))):
        errors.append("$.run_id: must match /^[A-Fa-f0-9]{32}$/ when present")
    if "task_id" in payload and (not isinstance(payload.get("task_id"), str) or not TASK_ID_RE.match(payload.get("task_id"))):
        errors.append("$.task_id: must be numeric string when present")
    if "title" in payload and not isinstance(payload.get("title"), str):
        errors.append("$.title: must be string when present")
    if "risk_summary" in payload and not isinstance(payload.get("risk_summary"), str):
        errors.append("$.risk_summary: must be string when present")
    if "metrics" in payload and not isinstance(payload.get("metrics"), dict):
        errors.append("$.metrics: must be object when present")

    if "task_requirements" in payload:
        req = payload.get("task_requirements")
        if not isinstance(req, dict):
            errors.append("$.task_requirements: must be object when present")
        else:
            required_req = {"has_gd_refs", "requires_env_evidence_preflight"}
            for key in required_req:
                if key not in req:
                    errors.append(f"$.task_requirements.{key}: missing required property")
                elif not isinstance(req.get(key), bool):
                    errors.append(f"$.task_requirements.{key}: must be boolean")
            for key in req.keys():
                if key not in required_req:
                    errors.append(f"$.task_requirements.{key}: unexpected property")

    if "step_plan" in payload:
        step_plan = payload.get("step_plan")
        if not isinstance(step_plan, list) or not all(isinstance(x, dict) for x in step_plan):
            errors.append("$.step_plan: must be array of objects when present")

    if "steps" in payload:
        steps = payload.get("steps")
        if not isinstance(steps, list):
            errors.append("$.steps: must be array when present")
        else:
            allowed_step = {"name", "status", "rc", "cmd", "log", "details"}
            for index, step in enumerate(steps):
                base = f"$.steps[{index}]"
                if not isinstance(step, dict):
                    errors.append(f"{base}: must be object")
                    continue
                for key in ("name", "status"):
                    if key not in step:
                        errors.append(f"{base}.{key}: missing required property")
                for key in step.keys():
                    if key not in allowed_step:
                        errors.append(f"{base}.{key}: unexpected property")
                if not _is_non_empty_string(step.get("name")):
                    errors.append(f"{base}.name: must be non-empty string")
                step_status = step.get("status")
                if not isinstance(step_status, str) or step_status not in {"ok", "fail", "skipped"}:
                    errors.append(f"{base}.status: must be one of ['ok', 'fail', 'skipped']")
                if "rc" in step and not _is_optional_int_not_bool(step.get("rc")):
                    errors.append(f"{base}.rc: must be integer or null when present")
                if "cmd" in step and step.get("cmd") is not None and not _is_string_list(step.get("cmd"), allow_empty=True):
                    errors.append(f"{base}.cmd: must be array of non-empty strings when present")
                if "log" in step and step.get("log") is not None and not isinstance(step.get("log"), str):
                    errors.append(f"{base}.log: must be string when present")
                if "details" in step and step.get("details") is not None and not isinstance(step.get("details"), dict):
                    errors.append(f"{base}.details: must be object when present")
                if step_status in {"ok", "fail"} and "rc" not in step:
                    errors.append(f"{base}.rc: required when status is ok/fail")

    if mode == "run":
        for key in ("run_id", "task_id", "title", "steps"):
            if key not in payload:
                errors.append(f"$.{key}: required when mode=run")
    elif mode == "dry-run-plan":
        for key in ("run_id", "task_id", "title", "task_requirements", "step_plan"):
            if key not in payload:
                errors.append(f"$.{key}: required when mode=dry-run-plan")

    return errors


def validate_local_hard_checks_without_jsonschema(payload: dict[str, Any]) -> list[str]:
    return _validate_local_hard_checks_impl(
        payload,
        is_non_empty_string=_is_non_empty_string,
        is_string_list=_is_string_list,
        is_int_not_bool=_is_int_not_bool,
    )
