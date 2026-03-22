from __future__ import annotations

import re
from typing import Any


RUN_ID_RE = re.compile(r"^[A-Fa-f0-9]{32}$")
TASK_ID_RE = re.compile(r"^[0-9]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_string_list(value: Any, *, allow_empty: bool) -> bool:
    if not isinstance(value, list):
        return False
    if not allow_empty and not value:
        return False
    return all(_is_non_empty_string(item) for item in value)


def _is_int_not_bool(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_string(errors: list[str], payload: dict[str, Any], key: str) -> None:
    if not _is_non_empty_string(payload.get(key)):
        errors.append(f"$.{key}: must be non-empty string")


def _validate_common_approval(payload: Any, *, base_path: str) -> list[str]:
    errors: list[str] = []
    known = {
        "soft_gate": bool,
        "required_action": str,
        "status": str,
        "decision": str,
        "reason": str,
        "request_id": str,
        "request_path": str,
        "response_path": str,
    }
    if not isinstance(payload, dict):
        return [f"{base_path}: must be object"]
    for key in payload.keys():
        if key not in known:
            errors.append(f"{base_path}.{key}: unexpected property")
    for key, typ in known.items():
        if key not in payload:
            continue
        value = payload.get(key)
        if typ is bool:
            if not isinstance(value, bool):
                errors.append(f"{base_path}.{key}: must be boolean")
        elif not isinstance(value, str):
            errors.append(f"{base_path}.{key}: must be string")
    return errors


def validate_pipeline_execution_context_without_jsonschema(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["$: payload must be an object"]

    required = {"task_id", "run_id", "status", "failed_step"}
    allowed = required | {
        "schema_version",
        "cmd",
        "date",
        "requested_run_id",
        "delivery_profile",
        "security_profile",
        "paths",
        "git",
        "recovery",
        "marathon",
        "agent_review",
        "llm_review",
        "approval",
    }
    for key in required:
        if key not in payload:
            errors.append(f"$.{key}: missing required property")
    for key in payload.keys():
        if key not in allowed:
            errors.append(f"$.{key}: unexpected property")
    if "cmd" in payload and str(payload.get("cmd") or "") != "sc-review-pipeline":
        errors.append("$.cmd: must equal 'sc-review-pipeline'")
    if "schema_version" in payload and (not isinstance(payload.get("schema_version"), str) or not SEMVER_RE.match(str(payload.get("schema_version") or ""))):
        errors.append("$.schema_version: must match semantic version pattern when present")
    if "date" in payload and (not isinstance(payload.get("date"), str) or not DATE_RE.match(str(payload.get("date") or ""))):
        errors.append("$.date: must match YYYY-MM-DD when present")
    if not isinstance(payload.get("task_id"), str) or not TASK_ID_RE.match(str(payload.get("task_id") or "")):
        errors.append("$.task_id: must be numeric string")
    if "requested_run_id" in payload:
        _require_string(errors, payload, "requested_run_id")
    if not _is_non_empty_string(payload.get("run_id")):
        errors.append("$.run_id: must be non-empty string")
    if str(payload.get("status") or "") not in {"ok", "fail"}:
        errors.append("$.status: must be one of ['ok', 'fail']")
    if "security_profile" in payload and str(payload.get("security_profile") or "") not in {"strict", "host-safe"}:
        errors.append("$.security_profile: must be one of ['strict', 'host-safe'] when present")
    if not isinstance(payload.get("failed_step"), str):
        errors.append("$.failed_step: must be string")
    for key in ("paths", "git", "recovery", "marathon", "agent_review", "llm_review"):
        if key in payload and not isinstance(payload.get(key), dict):
            errors.append(f"$.{key}: must be object when present")
    if "delivery_profile" in payload and not _is_non_empty_string(payload.get("delivery_profile")):
        errors.append("$.delivery_profile: must be non-empty string when present")
    if "approval" in payload:
        errors.extend(_validate_common_approval(payload.get("approval"), base_path="$.approval"))
    return errors


def validate_pipeline_repair_guide_without_jsonschema(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["$: payload must be an object"]

    required = {"status", "recommendations"}
    allowed = required | {"schema_version", "task_id", "summary_status", "failed_step", "approval", "generated_from"}
    for key in required:
        if key not in payload:
            errors.append(f"$.{key}: missing required property")
    for key in payload.keys():
        if key not in allowed:
            errors.append(f"$.{key}: unexpected property")
    if "schema_version" in payload and (not isinstance(payload.get("schema_version"), str) or not SEMVER_RE.match(str(payload.get("schema_version") or ""))):
        errors.append("$.schema_version: must match semantic version pattern when present")
    if str(payload.get("status") or "") not in {"not-needed", "needs-fix"}:
        errors.append("$.status: must be one of ['not-needed', 'needs-fix']")
    if "task_id" in payload and (not isinstance(payload.get("task_id"), str) or not TASK_ID_RE.match(str(payload.get("task_id") or ""))):
        errors.append("$.task_id: must be numeric string when present")
    if "summary_status" in payload and str(payload.get("summary_status") or "") not in {"ok", "fail"}:
        errors.append("$.summary_status: must be one of ['ok', 'fail'] when present")
    if "failed_step" in payload and not isinstance(payload.get("failed_step"), str):
        errors.append("$.failed_step: must be string when present")
    if "approval" in payload:
        errors.extend(_validate_common_approval(payload.get("approval"), base_path="$.approval"))

    recommendations = payload.get("recommendations")
    if not isinstance(recommendations, list):
        errors.append("$.recommendations: must be array")
    else:
        for index, item in enumerate(recommendations):
            base = f"$.recommendations[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{base}: must be object")
                continue
            for key in ("id", "title"):
                if not isinstance(item.get(key), str):
                    errors.append(f"{base}.{key}: must be string")
            if "why" in item and not isinstance(item.get("why"), str):
                errors.append(f"{base}.why: must be string when present")
            for key in ("actions", "commands", "files"):
                if key in item and (not isinstance(item.get(key), list) or not all(isinstance(v, str) for v in item.get(key, []))):
                    errors.append(f"{base}.{key}: must be array of strings when present")

    generated_from = payload.get("generated_from")
    if generated_from is not None:
        if not isinstance(generated_from, dict):
            errors.append("$.generated_from: must be object when present")
        else:
            for key in ("summary_json", "step_log", "step_summary_file"):
                if key in generated_from and not isinstance(generated_from.get(key), str):
                    errors.append(f"$.generated_from.{key}: must be string when present")
    return errors


def validate_pipeline_latest_index_without_jsonschema(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["$: payload must be an object"]
    required = {"task_id", "run_id", "latest_out_dir"}
    allowed = required | {
        "status",
        "date",
        "summary_path",
        "execution_context_path",
        "repair_guide_json_path",
        "repair_guide_md_path",
        "marathon_state_path",
        "run_events_path",
        "harness_capabilities_path",
        "approval_request_path",
        "approval_response_path",
        "agent_review_json_path",
        "agent_review_md_path",
    }
    for key in required:
        if key not in payload:
            errors.append(f"$.{key}: missing required property")
    for key in payload.keys():
        if key not in allowed:
            errors.append(f"$.{key}: unexpected property")
    if not isinstance(payload.get("task_id"), str) or not TASK_ID_RE.match(str(payload.get("task_id") or "")):
        errors.append("$.task_id: must be numeric string")
    if not _is_non_empty_string(payload.get("run_id")):
        errors.append("$.run_id: must be non-empty string")
    if "status" in payload and str(payload.get("status") or "") not in {"ok", "fail", "running", "aborted"}:
        errors.append("$.status: must be one of ['ok', 'fail', 'running', 'aborted'] when present")
    if "date" in payload and (not isinstance(payload.get("date"), str) or not DATE_RE.match(str(payload.get("date") or ""))):
        errors.append("$.date: must match YYYY-MM-DD when present")
    for key in allowed - {"task_id", "run_id", "status", "date"}:
        if key in payload and not isinstance(payload.get(key), str):
            errors.append(f"$.{key}: must be string when present")
    return errors


def validate_local_execution_context_without_jsonschema(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["$: payload must be an object"]
    required = {"cmd", "task_id", "run_id", "status", "failed_step", "artifacts"}
    allowed = required | {"requested_run_id", "delivery_profile", "security_profile"}
    for key in required:
        if key not in payload:
            errors.append(f"$.{key}: missing required property")
    for key in payload.keys():
        if key not in allowed:
            errors.append(f"$.{key}: unexpected property")
    if str(payload.get("cmd") or "") != "local-hard-checks":
        errors.append("$.cmd: must equal 'local-hard-checks'")
    if str(payload.get("task_id") or "") != "repo":
        errors.append("$.task_id: must equal 'repo'")
    for key in ("requested_run_id", "delivery_profile"):
        if key in payload:
            _require_string(errors, payload, key)
    if not _is_non_empty_string(payload.get("run_id")):
        errors.append("$.run_id: must be non-empty string")
    if "security_profile" in payload and str(payload.get("security_profile") or "") not in {"strict", "host-safe"}:
        errors.append("$.security_profile: must be one of ['strict', 'host-safe'] when present")
    if str(payload.get("status") or "") not in {"ok", "fail"}:
        errors.append("$.status: must be one of ['ok', 'fail']")
    if not isinstance(payload.get("failed_step"), str):
        errors.append("$.failed_step: must be string")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("$.artifacts: must be object")
    else:
        for key in ("summary_json", "execution_context_json", "repair_guide_json", "repair_guide_md", "run_events_jsonl", "harness_capabilities_json", "run_id_txt"):
            if not isinstance(artifacts.get(key), str):
                errors.append(f"$.artifacts.{key}: must be string")
    return errors


def validate_local_repair_guide_without_jsonschema(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["$: payload must be an object"]
    if str(payload.get("cmd") or "") != "local-hard-checks":
        errors.append("$.cmd: must equal 'local-hard-checks'")
    if str(payload.get("task_id") or "") != "repo":
        errors.append("$.task_id: must equal 'repo'")
    _require_string(errors, payload, "run_id")
    if str(payload.get("status") or "") not in {"ok", "fail"}:
        errors.append("$.status: must be one of ['ok', 'fail']")
    if not isinstance(payload.get("failed_step"), str):
        errors.append("$.failed_step: must be string")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("$.artifacts: must be object")
    else:
        for key in ("summary_json", "execution_context_json"):
            if not isinstance(artifacts.get(key), str):
                errors.append(f"$.artifacts.{key}: must be string")
    if not _is_string_list(payload.get("next_actions"), allow_empty=False):
        errors.append("$.next_actions: must be non-empty array of non-empty strings")
    if not _is_string_list(payload.get("rerun_command"), allow_empty=False):
        errors.append("$.rerun_command: must be non-empty array of non-empty strings")
    return errors


def validate_local_latest_index_without_jsonschema(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["$: payload must be an object"]
    required = {"cmd", "task_id", "run_id", "out_dir"}
    allowed = required | {"status", "summary_path", "execution_context_path", "repair_guide_json_path", "repair_guide_md_path", "run_events_path"}
    for key in required:
        if key not in payload:
            errors.append(f"$.{key}: missing required property")
    for key in payload.keys():
        if key not in allowed:
            errors.append(f"$.{key}: unexpected property")
    if str(payload.get("cmd") or "") != "local-hard-checks":
        errors.append("$.cmd: must equal 'local-hard-checks'")
    if str(payload.get("task_id") or "") != "repo":
        errors.append("$.task_id: must equal 'repo'")
    _require_string(errors, payload, "run_id")
    if "status" in payload and str(payload.get("status") or "") not in {"ok", "fail", "running"}:
        errors.append("$.status: must be one of ['ok', 'fail', 'running'] when present")
    for key in allowed - {"cmd", "task_id", "run_id", "status"}:
        if key in payload and not isinstance(payload.get(key), str):
            errors.append(f"$.{key}: must be string when present")
    return errors
