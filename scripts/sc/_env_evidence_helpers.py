#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


_EXCLUDED_LOCK_DIR_NAMES = {
    ".git",
    ".godot",
    "bin",
    "obj",
    "logs",
    "node_modules",
}


def run_command(
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
    except Exception as exc:
        return 1, f"failed to run {' '.join(cmd)}: {exc}"


def first_non_empty_line(text: str) -> str:
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def contains_token(text: str, token: str) -> bool:
    return token.lower() in (text or "").lower()


def parse_dotnet_sdk_versions(text: str) -> list[str]:
    versions: list[str] = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        first = line.split(" ", 1)[0].strip()
        if first and first[0].isdigit():
            versions.append(first)
    return versions


def parse_major_from_version_text(text: str) -> int | None:
    first_line = first_non_empty_line(text)
    if not first_line:
        return None
    match = re.search(r"(\d+)\.\d+\.\d+", first_line)
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def write_utf8_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def strict_utf8_read(path: Path) -> tuple[bool, str]:
    try:
        path.read_bytes().decode("utf-8", errors="strict")
        return True, ""
    except Exception as exc:
        return False, str(exc)


def rel(root: Path, path: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def discover_packages_lock_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for path in root.rglob("packages.lock.json"):
        if not path.is_file():
            continue
        try:
            rel_path = path.relative_to(root)
        except ValueError:
            continue
        if any(part in _EXCLUDED_LOCK_DIR_NAMES for part in rel_path.parts[:-1]):
            continue
        found.append(path)
    return sorted(found, key=lambda p: (len(p.relative_to(root).parts), rel(root, p).lower()))


def normalize_task_id(task_id: str | int | None) -> str:
    raw = str(task_id or "").strip()
    if not raw:
        return "1"
    if raw.isdigit():
        return str(int(raw))
    return re.sub(r"[^0-9A-Za-z_-]+", "-", raw)


def task_json_filename(task_id: str) -> str:
    if task_id.isdigit():
        return f"task-{int(task_id):04d}.json"
    return f"task-{task_id}.json"


def build_utf8_checked_files(*, task_json_rel: str, checklist_rel: str, date: str, errors: list[str]) -> list[str]:
    files = [
        task_json_rel,
        f"logs/ci/{date}/env-evidence/godot-bin-env.txt",
        f"logs/ci/{date}/env-evidence/godot-version.txt",
        f"logs/ci/{date}/env-evidence/godot-bin-version.txt",
        f"logs/ci/{date}/env-evidence/dotnet-version.txt",
        f"logs/ci/{date}/env-evidence/dotnet-sdks.txt",
        f"logs/ci/{date}/env-evidence/dotnet-restore.txt",
        f"logs/ci/{date}/env-evidence/packages-lock-exists.txt",
        f"logs/ci/{date}/env-evidence/windows-only-check.txt",
    ]
    if checklist_rel:
        files.insert(1, checklist_rel)
    else:
        errors.append("missing_acceptance_checklist")
    return files
