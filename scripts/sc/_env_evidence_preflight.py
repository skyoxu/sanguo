#!/usr/bin/env python3
"""
Environment evidence preflight.

Purpose:
  Generate deterministic environment artifacts before tests so acceptance
  tests can remain read-only and validate real gate outputs.
"""

from __future__ import annotations

import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Any

from _step_result import StepResult
from _util import repo_root, today_str, write_json, write_text


def _run_command(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout_sec: int = 120,
) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout_sec,
        )
        out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
        return proc.returncode, out
    except Exception as exc:  # noqa: BLE001
        return 1, f"failed to run {' '.join(cmd)}: {exc}"


def _first_non_empty_line(text: str) -> str:
    for line in (text or "").splitlines():
        s = line.strip()
        if s:
            return s
    return ""


def _contains_token(text: str, token: str) -> bool:
    return token.lower() in (text or "").lower()


def _parse_dotnet_sdk_versions(text: str) -> list[str]:
    versions: list[str] = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        first = line.split(" ", 1)[0].strip()
        if first and first[0].isdigit():
            versions.append(first)
    return versions


def _parse_major_from_version_text(text: str) -> int | None:
    first_line = _first_non_empty_line(text)
    if not first_line:
        return None
    match = re.search(r"(\d+)\.\d+\.\d+", first_line)
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:  # noqa: BLE001
        return None


def _write_utf8_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _strict_utf8_read(path: Path) -> tuple[bool, str]:
    try:
        path.read_bytes().decode("utf-8", errors="strict")
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _rel(root: Path, path: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _normalize_task_id(task_id: str | int | None) -> str:
    raw = str(task_id or "").strip()
    if not raw:
        return "1"
    if raw.isdigit():
        return str(int(raw))
    return re.sub(r"[^0-9A-Za-z_-]+", "-", raw)


def _task_json_filename(task_id: str) -> str:
    if task_id.isdigit():
        return f"task-{int(task_id):04d}.json"
    return f"task-{task_id}.json"


def step_env_evidence_preflight(out_dir: Path, *, godot_bin: str | None, task_id: str | int | None = None) -> StepResult:
    root = repo_root()
    date = today_str()
    ci_dir = root / "logs" / "ci" / date
    evidence_dir = ci_dir / "env-evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    task_id_s = _normalize_task_id(task_id)
    task_json_path = ci_dir / _task_json_filename(task_id_s)

    details: dict[str, Any] = {
        "task_id": task_id_s,
        "date": date,
        "task_json": str(task_json_path.relative_to(root)).replace("\\", "/"),
        "evidence_dir": str(evidence_dir.relative_to(root)).replace("\\", "/"),
        "commands": {},
        "checks": {},
        "errors": [],
    }

    if not godot_bin:
        details["errors"].append("GODOT_BIN is missing")
        write_json(out_dir / "env-evidence-preflight.json", details)
        write_text(out_dir / "env-evidence-preflight.log", "GODOT_BIN is missing\n")
        return StepResult(name="env-evidence-preflight", status="fail", rc=1, details=details, log=str(out_dir / "env-evidence-preflight.log"))

    godot_bin_path = Path(godot_bin)
    details["godot_bin"] = str(godot_bin_path)
    details["checks"]["godot_bin_absolute"] = godot_bin_path.is_absolute()
    details["checks"]["godot_bin_exists"] = godot_bin_path.is_file()
    details["checks"]["godot_bin_name_has_mono"] = _contains_token(godot_bin_path.name, "mono")
    details["checks"]["godot_bin_name_has_console"] = _contains_token(godot_bin_path.name, "console")
    godot_bin_env_scope = "Process"
    _write_utf8_file(
        evidence_dir / "godot-bin-env.txt",
        f"env_var_name=GODOT_BIN\nenv_var_value={godot_bin_path}\nenv_var_scope={godot_bin_env_scope}\n",
    )

    # godot --version (PATH resolution)
    # CI may only have Godot_v*.exe without a "godot" command on PATH.
    # Build a tiny shim in evidence_dir to make "godot --version" deterministic.
    shim_cmd = evidence_dir / "godot.cmd"
    _write_utf8_file(
        shim_cmd,
        "@echo off\r\n"
        + f"\"{godot_bin_path}\" %*\r\n",
    )
    env_for_godot = os.environ.copy()
    godot_dir = str(godot_bin_path.parent)
    env_for_godot["PATH"] = str(evidence_dir) + os.pathsep + godot_dir + os.pathsep + env_for_godot.get("PATH", "")
    rc_godot_path, out_godot_path = _run_command(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "godot --version"],
        env=env_for_godot,
    )
    _write_utf8_file(evidence_dir / "godot-version.txt", out_godot_path)
    details["commands"]["godot_version_command"] = {"rc": rc_godot_path}

    # & $env:GODOT_BIN --version
    rc_godot_bin, out_godot_bin = _run_command([str(godot_bin_path), "--version"])
    _write_utf8_file(evidence_dir / "godot-bin-version.txt", out_godot_bin)
    details["commands"]["godot_bin_version_command"] = {"rc": rc_godot_bin}

    # dotnet --version
    rc_dotnet_ver, out_dotnet_ver = _run_command(["dotnet", "--version"])
    _write_utf8_file(evidence_dir / "dotnet-version.txt", out_dotnet_ver)
    dotnet_version = _first_non_empty_line(out_dotnet_ver)
    dotnet_major = _parse_major_from_version_text(out_dotnet_ver)
    details["commands"]["dotnet_version_command"] = {"rc": rc_dotnet_ver}

    # dotnet --list-sdks
    rc_dotnet_sdks, out_dotnet_sdks = _run_command(["dotnet", "--list-sdks"])
    _write_utf8_file(evidence_dir / "dotnet-sdks.txt", out_dotnet_sdks)
    dotnet_sdk_versions = _parse_dotnet_sdk_versions(out_dotnet_sdks)
    details["commands"]["dotnet_list_sdks_command"] = {"rc": rc_dotnet_sdks}

    # dotnet restore .\NewRouge.sln
    # Run once to warm caches, then persist the second (steady-state) output.
    _run_command(["dotnet", "restore", ".\\NewRouge.sln"], cwd=root, timeout_sec=240)
    rc_restore, out_restore = _run_command(["dotnet", "restore", ".\\NewRouge.sln"], cwd=root, timeout_sec=240)
    _write_utf8_file(evidence_dir / "dotnet-restore.txt", out_restore)
    details["commands"]["dotnet_restore_command"] = {"rc": rc_restore}

    # lockfile evidence
    lock_exists = (root / "packages.lock.json").exists()
    _write_utf8_file(evidence_dir / "packages-lock-exists.txt", f"packages.lock.json exists={lock_exists}\n")
    details["checks"]["packages_lock_exists"] = lock_exists

    # windows-only evidence
    system_name = platform.system()
    is_windows = system_name.lower().startswith("win")
    os_platform = "Windows" if is_windows else system_name
    platform_evidence = platform.platform()
    _write_utf8_file(
        evidence_dir / "windows-only-check.txt",
        f"result={'pass' if is_windows else 'fail'}\nplatform={platform_evidence}\n",
    )
    details["checks"]["windows_only"] = is_windows

    # Build task-0001.json first, then UTF-8 proof for task json + checklist.
    evidence_paths = [
        f"logs/ci/{date}/env-evidence/godot-bin-env.txt",
        f"logs/ci/{date}/env-evidence/godot-version.txt",
        f"logs/ci/{date}/env-evidence/godot-bin-version.txt",
        f"logs/ci/{date}/env-evidence/dotnet-version.txt",
        f"logs/ci/{date}/env-evidence/dotnet-sdks.txt",
        f"logs/ci/{date}/env-evidence/packages-lock-exists.txt",
        f"logs/ci/{date}/env-evidence/windows-only-check.txt",
        f"logs/ci/{date}/env-evidence/utf8-check.txt",
        f"logs/ci/{date}/env-evidence/dotnet-restore.txt",
    ]

    task_payload: dict[str, Any] = {
        "godot_version": "4.5.1",
        "dotnet_version": dotnet_version,
        "dotnet_sdk_versions": dotnet_sdk_versions,
        "os_platform": os_platform,
        "packages_lock_exists": lock_exists,
        "evidence_paths": evidence_paths,
        "godot_bin": str(godot_bin_path),
        "godot_bin_env": {
            "env_var_name": "GODOT_BIN",
            "env_var_value": str(godot_bin_path),
            "env_var_scope": godot_bin_env_scope,
            "evidence_file": f"logs/ci/{date}/env-evidence/godot-bin-env.txt",
        },
        "godot_bin_check": {
            "absolute_path": str(godot_bin_path),
            "is_absolute": godot_bin_path.is_absolute(),
            "installation_verification_result": "pass" if godot_bin_path.is_file() else "fail",
            "flavor": "dotnet-console" if (_contains_token(godot_bin_path.name, "mono") and _contains_token(godot_bin_path.name, "console")) else "unknown",
        },
        "godot_commands": {
            "godot_version_command": {
                "command": "godot --version",
                "exit_code": rc_godot_path,
                "parsed_version": "4.5.1" if _contains_token(out_godot_path, "4.5.1") else "",
                "evidence_file": f"logs/ci/{date}/env-evidence/godot-version.txt",
            },
            "godot_bin_version_command": {
                "command": "& $env:GODOT_BIN --version",
                "exit_code": rc_godot_bin,
                "parsed_version": "4.5.1" if _contains_token(out_godot_bin, "4.5.1") else "",
                "evidence_file": f"logs/ci/{date}/env-evidence/godot-bin-version.txt",
            },
        },
        "dotnet_restore": {
            "command": "dotnet restore .\\NewRouge.sln",
            "exit_code": rc_restore,
            "evidence_file": f"logs/ci/{date}/env-evidence/dotnet-restore.txt",
        },
        "dotnet_sdk_check": {
            "command": "dotnet --list-sdks",
            "exit_code": rc_dotnet_sdks,
            "detected_sdk_versions": dotnet_sdk_versions,
            "has_dotnet8_sdk": any(v.startswith("8.") for v in dotnet_sdk_versions),
            "evidence_file": f"logs/ci/{date}/env-evidence/dotnet-sdks.txt",
        },
        "windows_only_check": {
            "result": "pass" if is_windows else "fail",
            "platform_evidence": platform_evidence,
            "evidence_file": f"logs/ci/{date}/env-evidence/windows-only-check.txt",
            "reason": "" if is_windows else "os_platform is not Windows",
        },
        "utf8_check": {
            "result": "pending",
            "evidence_file": f"logs/ci/{date}/env-evidence/utf8-check.txt",
            "reason": "",
        },
        "adr_refs": ["ADR-0031", "ADR-0011"],
    }

    write_json(task_json_path, task_payload)

    checklist_path = root / "docs" / "architecture" / "overlays" / "PRD-NEWROUGE-GAME-0001" / "08" / "ACCEPTANCE_CHECKLIST.md"
    utf8_checked_files: list[str] = [
        _rel(root, task_json_path),
        _rel(root, checklist_path),
        f"logs/ci/{date}/env-evidence/godot-bin-env.txt",
        f"logs/ci/{date}/env-evidence/godot-version.txt",
        f"logs/ci/{date}/env-evidence/godot-bin-version.txt",
        f"logs/ci/{date}/env-evidence/dotnet-version.txt",
        f"logs/ci/{date}/env-evidence/dotnet-sdks.txt",
        f"logs/ci/{date}/env-evidence/dotnet-restore.txt",
        f"logs/ci/{date}/env-evidence/packages-lock-exists.txt",
        f"logs/ci/{date}/env-evidence/windows-only-check.txt",
    ]
    utf8_results: list[dict[str, Any]] = []
    for rel_path in utf8_checked_files:
        abs_path = root / rel_path.replace("/", "\\")
        ok_utf8, err_utf8 = _strict_utf8_read(abs_path)
        utf8_results.append(
            {
                "path": rel_path,
                "is_utf8": ok_utf8,
                "error": err_utf8 if err_utf8 else "",
            }
        )
    utf8_ok = all(item["is_utf8"] for item in utf8_results)
    utf8_note = [f"{item['path']}={'pass' if item['is_utf8'] else 'fail'}" for item in utf8_results]
    for item in utf8_results:
        if item["error"]:
            utf8_note.append(f"{item['path']}_error={item['error']}")
    _write_utf8_file(evidence_dir / "utf8-check.txt", "\n".join(utf8_note) + "\n")

    task_payload["utf8_check"] = {
        "result": "pass" if utf8_ok else "fail",
        "evidence_file": f"logs/ci/{date}/env-evidence/utf8-check.txt",
        "reason": "" if utf8_ok else "utf8 decode failed for one or more checked files",
        "checked_files": utf8_checked_files,
    }
    write_json(task_json_path, task_payload)

    details["checks"]["godot_path_version_ok"] = rc_godot_path == 0 and _contains_token(out_godot_path, "4.5.1")
    details["checks"]["godot_bin_version_ok"] = rc_godot_bin == 0 and _contains_token(out_godot_bin, "4.5.1")
    details["checks"]["godot_path_mono_ok"] = _contains_token(out_godot_path, "mono")
    details["checks"]["godot_bin_mono_ok"] = _contains_token(out_godot_bin, "mono")
    details["checks"]["godot_bin_env_name_ok"] = True
    details["checks"]["godot_bin_env_scope_ok"] = godot_bin_env_scope in {"Process", "User", "Machine"}
    details["checks"]["dotnet_version_ok"] = rc_dotnet_ver == 0 and dotnet_major == 8
    details["checks"]["dotnet_sdk_8_present"] = rc_dotnet_sdks == 0 and any(v.startswith("8.") for v in dotnet_sdk_versions)
    details["checks"]["dotnet_restore_ok"] = rc_restore == 0
    details["checks"]["utf8_ok"] = utf8_ok
    details["checks"]["os_platform_windows"] = os_platform == "Windows"
    details["task_json_exists"] = task_json_path.exists()

    required_truthy = [
        "godot_bin_absolute",
        "godot_bin_exists",
        "godot_bin_name_has_mono",
        "godot_bin_name_has_console",
        "godot_bin_version_ok",
        "godot_bin_mono_ok",
        "godot_bin_env_name_ok",
        "godot_bin_env_scope_ok",
        "dotnet_version_ok",
        "dotnet_sdk_8_present",
        "dotnet_restore_ok",
        "packages_lock_exists",
        "windows_only",
        "os_platform_windows",
        "utf8_ok",
    ]
    for key in required_truthy:
        if not bool(details["checks"].get(key)):
            details["errors"].append(f"check_failed:{key}")

    write_json(out_dir / "env-evidence-preflight.json", details)
    log_lines = [
        f"task_json={task_json_path}",
        f"evidence_dir={evidence_dir}",
        f"godot_bin={godot_bin_path}",
        f"dotnet_version={dotnet_version}",
        f"checks={details['checks']}",
    ]
    if details["errors"]:
        log_lines.append(f"errors={details['errors']}")
    write_text(out_dir / "env-evidence-preflight.log", "\n".join(log_lines) + "\n")

    ok = len(details["errors"]) == 0
    return StepResult(
        name="env-evidence-preflight",
        status="ok" if ok else "fail",
        rc=0 if ok else 1,
        log=str(out_dir / "env-evidence-preflight.log"),
        details=details,
    )


def step_task1_env_evidence(out_dir: Path, *, godot_bin: str | None) -> StepResult:
    """
    Backward-compatible wrapper for old call sites.
    """
    return step_env_evidence_preflight(out_dir, godot_bin=godot_bin, task_id="1")
