#!/usr/bin/env python3
"""Support helpers for local hard checks protocol artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from dev_cli_builders import (
    build_gate_bundle_hard_cmd,
    build_run_dotnet_cmd,
    build_run_gdunit_hard_cmd,
    build_smoke_strict_cmd,
)

try:
    from _sidecar_schema import validate_harness_capabilities_payload
    from _util import repo_root, today_str, write_json, write_text
except ImportError:
    import sys

    _SC_DIR = Path(__file__).resolve().parents[1] / "sc"
    if str(_SC_DIR) not in sys.path:
        sys.path.insert(0, str(_SC_DIR))
    from _sidecar_schema import validate_harness_capabilities_payload
    from _util import repo_root, today_str, write_json, write_text


CMD_NAME = "local-hard-checks"
TASK_SCOPE = "repo"
SCHEMA_VERSION = "1.0.0"
PROTOCOL_VERSION = "1.0.0"
SUPPORTED_SIDECARS = [
    "summary.json",
    "execution-context.json",
    "repair-guide.json",
    "repair-guide.md",
    "run-events.jsonl",
    "harness-capabilities.json",
    "run_id.txt",
]
SUPPORTED_RECOVERY_ACTIONS = [
    "rerun",
    "inspect-failed-step",
]


def default_out_dir(run_id: str) -> Path:
    return repo_root() / "logs" / "ci" / today_str() / f"{CMD_NAME}-{run_id}"


def latest_index_path(out_dir: Path) -> Path:
    return out_dir.parent / f"{CMD_NAME}-latest.json"


def build_harness_capabilities(
    *,
    run_id: str,
    delivery_profile: str,
    security_profile: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "cmd": CMD_NAME,
        "task_id": TASK_SCOPE,
        "run_id": str(run_id).strip(),
        "delivery_profile": str(delivery_profile).strip(),
        "security_profile": str(security_profile).strip(),
        "supported_sidecars": list(SUPPORTED_SIDECARS),
        "supported_recovery_actions": list(SUPPORTED_RECOVERY_ACTIONS),
        "approval_contract_supported": False,
    }
    validate_harness_capabilities_payload(payload)
    return payload


def write_step_log(path: Path, *, cmd: list[str], rc: int, status: str, artifacts: dict[str, Any] | None = None) -> None:
    payload = {
        "cmd": list(cmd),
        "rc": int(rc),
        "status": str(status),
        "artifacts": dict(artifacts or {}),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_step_plan(
    *,
    delivery_profile: str,
    task_files: list[str],
    out_dir: Path,
    run_id: str,
    solution: str,
    configuration: str,
    godot_bin: str,
    timeout_sec: int,
) -> list[dict[str, Any]]:
    unit_dir = repo_root() / "logs" / "unit" / today_str()
    steps: list[dict[str, Any]] = [
        {
            "name": "project-health-scan",
            "cmd": ["py", "-3", "scripts/python/project_health_scan.py", "--repo-root", "."],
            "artifacts": {
                "reported_out_dir": str((repo_root() / "logs" / "ci" / "project-health")).replace("\\", "/"),
                "summary_file": str((repo_root() / "logs" / "ci" / "project-health" / "latest.json")).replace(
                    "\\",
                    "/",
                ),
            },
        },
        {
            "name": "gate-bundle-hard",
            "cmd": build_gate_bundle_hard_cmd(
                delivery_profile=delivery_profile,
                task_files=task_files,
                out_dir=str(out_dir),
                run_id=run_id,
            ),
            "artifacts": {
                "reported_out_dir": str(out_dir / "hard").replace("\\", "/"),
                "summary_file": str(out_dir / "hard" / "summary.json").replace("\\", "/"),
            },
        },
        {
            "name": "run-dotnet",
            "cmd": build_run_dotnet_cmd(solution=solution, configuration=configuration),
            "artifacts": {
                "reported_out_dir": str(unit_dir).replace("\\", "/"),
                "summary_file": str(unit_dir / "summary.json").replace("\\", "/"),
            },
        },
    ]
    if godot_bin:
        gdunit_dir = repo_root() / "logs" / "e2e" / "dev-cli" / "local-hard-checks-gdunit-hard"
        smoke_root = repo_root() / "logs" / "ci" / today_str() / "smoke"
        steps.extend(
            [
                {
                    "name": "gdunit-hard",
                    "cmd": build_run_gdunit_hard_cmd(
                        godot_bin=godot_bin,
                        report_dir="logs/e2e/dev-cli/local-hard-checks-gdunit-hard",
                    ),
                    "artifacts": {
                        "reported_out_dir": str(gdunit_dir).replace("\\", "/"),
                    },
                },
                {
                    "name": "smoke-strict",
                    "cmd": build_smoke_strict_cmd(godot_bin=godot_bin, timeout_sec=timeout_sec),
                    "artifacts": {
                        "reported_out_dir": str(smoke_root).replace("\\", "/"),
                    },
                },
            ]
        )
    return steps


def build_execution_context(
    *,
    out_dir: Path,
    run_id: str,
    requested_run_id: str,
    delivery_profile: str,
    security_profile: str,
    status: str,
    failed_step: str,
) -> dict[str, Any]:
    return {
        "cmd": CMD_NAME,
        "task_id": TASK_SCOPE,
        "requested_run_id": requested_run_id,
        "run_id": run_id,
        "delivery_profile": delivery_profile,
        "security_profile": security_profile,
        "status": status,
        "failed_step": failed_step,
        "artifacts": {
            "summary_json": str(out_dir / "summary.json").replace("\\", "/"),
            "execution_context_json": str(out_dir / "execution-context.json").replace("\\", "/"),
            "repair_guide_json": str(out_dir / "repair-guide.json").replace("\\", "/"),
            "repair_guide_md": str(out_dir / "repair-guide.md").replace("\\", "/"),
            "run_events_jsonl": str(out_dir / "run-events.jsonl").replace("\\", "/"),
            "harness_capabilities_json": str(out_dir / "harness-capabilities.json").replace("\\", "/"),
            "run_id_txt": str(out_dir / "run_id.txt").replace("\\", "/"),
        },
    }


def build_repair_guide(
    *,
    out_dir: Path,
    requested_run_id: str,
    run_id: str,
    status: str,
    failed_step: str,
    godot_bin: str,
) -> dict[str, Any]:
    rerun_cmd = ["py", "-3", "scripts/python/dev_cli.py", "run-local-hard-checks"]
    if godot_bin:
        rerun_cmd += ["--godot-bin", godot_bin]
    if requested_run_id:
        rerun_cmd += ["--run-id", requested_run_id]
    return {
        "cmd": CMD_NAME,
        "task_id": TASK_SCOPE,
        "run_id": run_id,
        "status": status,
        "failed_step": failed_step,
        "artifacts": {
            "summary_json": str(out_dir / "summary.json").replace("\\", "/"),
            "execution_context_json": str(out_dir / "execution-context.json").replace("\\", "/"),
        },
        "next_actions": [
            "Open summary.json and inspect the first failing step.",
            "Open the failing step log and then inspect the referenced artifact directory.",
            "Re-run the command after fixing the first failing step.",
        ],
        "rerun_command": rerun_cmd,
    }


def render_repair_guide_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Local Hard Checks Repair Guide",
        "",
        f"- status: `{payload.get('status', '')}`",
        f"- failed_step: `{payload.get('failed_step', '') or 'none'}`",
        "",
        "## Next Actions",
        "",
    ]
    for item in payload.get("next_actions", []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Re-run",
            "",
            "```powershell",
            " ".join(str(x) for x in payload.get("rerun_command", [])),
            "```",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_latest_index(*, out_dir: Path, run_id: str, status: str) -> None:
    payload = {
        "cmd": CMD_NAME,
        "task_id": TASK_SCOPE,
        "run_id": run_id,
        "status": status,
        "out_dir": str(out_dir).replace("\\", "/"),
        "summary_path": str(out_dir / "summary.json").replace("\\", "/"),
        "execution_context_path": str(out_dir / "execution-context.json").replace("\\", "/"),
        "repair_guide_json_path": str(out_dir / "repair-guide.json").replace("\\", "/"),
        "repair_guide_md_path": str(out_dir / "repair-guide.md").replace("\\", "/"),
        "run_events_path": str(out_dir / "run-events.jsonl").replace("\\", "/"),
    }
    write_json(latest_index_path(out_dir), payload)


def persist_sidecars(
    *,
    out_dir: Path,
    run_id: str,
    summary: dict[str, Any],
    execution_context: dict[str, Any],
    repair_guide: dict[str, Any],
    validate_summary: Callable[[dict[str, Any]], None],
    summary_schema_error: type[Exception],
) -> bool:
    schema_error_log = out_dir / "summary-schema-validation-error.log"
    invalid_summary_path = out_dir / "summary.invalid.json"
    try:
        validate_summary(summary)
    except summary_schema_error as exc:
        write_text(schema_error_log, f"{exc}\n")
        write_json(invalid_summary_path, summary)
        write_latest_index(out_dir=out_dir, run_id=run_id, status="fail")
        print(f"[local-hard-checks] ERROR: summary schema validation failed. details={schema_error_log}")
        return False

    if schema_error_log.exists():
        schema_error_log.unlink(missing_ok=True)
    if invalid_summary_path.exists():
        invalid_summary_path.unlink(missing_ok=True)

    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "execution-context.json", execution_context)
    write_json(out_dir / "repair-guide.json", repair_guide)
    write_text(out_dir / "repair-guide.md", render_repair_guide_markdown(repair_guide))
    write_latest_index(out_dir=out_dir, run_id=run_id, status=str(summary["status"]))
    return True
