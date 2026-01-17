"""
Data JSON version hard gate (ADR-0005).

Rule:
- For any changed JSON file under Data/**, the top-level integer field "version" must exist.
- If the file existed in the base ref, new_version must be > old_version.
- For newly added files, version must be >= 1.

This script is meant to run in CI on main/PR-to-main and write evidence into logs/ci/<YYYY-MM-DD>/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FileCheckResult:
    path: str
    status: str  # ok | fail | skip
    old_version: int | None
    new_version: int | None
    reason: str | None


def _run_git(args: list[str]) -> str:
    p = subprocess.run(
        ["git", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if p.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (rc={p.returncode}): {p.stderr.strip()}"
        )
    return p.stdout


def _resolve_default_base_ref() -> str:
    event = os.environ.get("GITHUB_EVENT_NAME", "").strip().lower()
    if event == "pull_request":
        return "origin/main"
    # Push to main: compare with previous commit by default.
    return "HEAD~1"


def _list_changed_data_json(base_ref: str, head_ref: str) -> list[str]:
    # Use three-dot to compare to merge-base (PR-friendly).
    out = _run_git(["diff", "--name-only", f"{base_ref}...{head_ref}"])
    paths = [p.strip().replace("\\", "/") for p in out.splitlines() if p.strip()]
    return [p for p in paths if p.lower().startswith("data/") and p.lower().endswith(".json")]


def _read_json_at_ref(ref: str, path: str) -> Any:
    try:
        content = _run_git(["show", f"{ref}:{path}"])
    except RuntimeError as e:
        # If the file doesn't exist at ref, git show returns nonzero.
        msg = str(e)
        if "fatal:" in msg and ("exists on disk, but not in" in msg or "Path '" in msg):
            raise
        raise
    return json.loads(content)


def _read_json_worktree(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _get_top_level_int(obj: Any, key: str) -> int | None:
    if not isinstance(obj, dict):
        return None
    v = obj.get(key)
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    return None


def _check_file(base_ref: str, path: str) -> FileCheckResult:
    # Deleted files are not part of "changed files" in worktree, but may appear in diff.
    if not Path(path).exists():
        return FileCheckResult(path=path, status="skip", old_version=None, new_version=None, reason="deleted")

    try:
        new_obj = _read_json_worktree(path)
    except Exception as e:
        return FileCheckResult(path=path, status="fail", old_version=None, new_version=None, reason=f"invalid_json_new: {e}")

    new_version = _get_top_level_int(new_obj, "version")
    if new_version is None or new_version < 1:
        return FileCheckResult(
            path=path,
            status="fail",
            old_version=None,
            new_version=new_version,
            reason='missing_or_invalid_version (require top-level int "version" >= 1)',
        )

    # Old content may not exist (new file).
    try:
        old_obj = _read_json_at_ref(base_ref, path)
        old_version = _get_top_level_int(old_obj, "version")
        if old_version is None:
            return FileCheckResult(
                path=path,
                status="fail",
                old_version=None,
                new_version=new_version,
                reason='missing_old_version (base ref missing top-level int "version")',
            )
        if new_version <= old_version:
            return FileCheckResult(
                path=path,
                status="fail",
                old_version=old_version,
                new_version=new_version,
                reason="version_not_bumped (new_version must be > old_version)",
            )
        return FileCheckResult(path=path, status="ok", old_version=old_version, new_version=new_version, reason=None)
    except RuntimeError:
        # New file in this diff.
        return FileCheckResult(path=path, status="ok", old_version=None, new_version=new_version, reason="new_file")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", dest="base_ref", default=_resolve_default_base_ref())
    ap.add_argument("--head", dest="head_ref", default="HEAD")
    args = ap.parse_args()

    base_ref: str = args.base_ref
    head_ref: str = args.head_ref

    changed = _list_changed_data_json(base_ref, head_ref)

    today = dt.date.today().strftime("%Y-%m-%d")
    out_dir = Path("logs") / "ci" / today
    out_dir.mkdir(parents=True, exist_ok=True)
    log_txt = out_dir / "data-version-gate.log"
    log_json = out_dir / "data-version-gate.json"

    results: list[FileCheckResult] = []
    for path in changed:
        results.append(_check_file(base_ref, path))

    payload = {
        "base_ref": base_ref,
        "head_ref": head_ref,
        "changed_files": changed,
        "results": [
            {
                "path": r.path,
                "status": r.status,
                "old_version": r.old_version,
                "new_version": r.new_version,
                "reason": r.reason,
            }
            for r in results
        ],
        "failures": [r.path for r in results if r.status == "fail"],
    }
    log_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    lines: list[str] = []
    lines.append(f"DATA_VERSION_GATE base={base_ref} head={head_ref}")
    if not changed:
        lines.append("No changed Data/*.json files detected; gate=skip")
    for r in results:
        if r.status == "ok":
            extra = f" old={r.old_version} new={r.new_version}" if r.old_version is not None else f" new={r.new_version}"
            lines.append(f"OK   {r.path}{extra}")
        elif r.status == "skip":
            lines.append(f"SKIP {r.path} reason={r.reason}")
        else:
            lines.append(
                f"FAIL {r.path} old={r.old_version} new={r.new_version} reason={r.reason}"
            )

    log_txt.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))

    return 1 if any(r.status == "fail" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())

