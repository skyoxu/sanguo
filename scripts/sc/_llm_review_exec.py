#!/usr/bin/env python3
"""
Git diff and codex execution helpers for llm_review.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from _llm_review_acceptance import truncate
from _util import repo_root, run_cmd


def git_capture(args: list[str], *, timeout_sec: int) -> tuple[int, str]:
    return run_cmd(args, cwd=repo_root(), timeout_sec=timeout_sec)


def auto_resolve_commit_for_task(task_id: str) -> str | None:
    task_id = str(task_id).strip()
    if not task_id:
        return None
    candidates = [
        f"Task [{task_id}]",
        f"Task [{task_id}]:",
        f"Task {task_id}:",
        f"Task {task_id} ",
        f"#{task_id}",
    ]
    for needle in candidates:
        rc, out = git_capture(["git", "log", "--format=%H", "-n", "1", "--fixed-strings", "--grep", needle], timeout_sec=30)
        if rc != 0:
            continue
        sha = (out.strip().splitlines() or [""])[0].strip()
        if sha:
            return sha
    return None


def build_diff_context(args: argparse.Namespace) -> str:
    mode = str(getattr(args, "diff_mode", "full") or "full").strip().lower()
    if mode not in {"full", "summary", "none"}:
        mode = "full"
    if mode == "none":
        return "## Diff\n(skipped: --diff-mode none)\n"

    def _name_only(title: str, cmd: list[str]) -> str:
        rc, out = git_capture(cmd, timeout_sec=60)
        body = out.strip()
        if rc != 0:
            body = "(failed to capture)"
        body = truncate(body, max_chars=20_000)
        return f"{title}\n```\n{body}\n```"

    if args.uncommitted:
        if mode == "summary":
            blocks: list[str] = []
            blocks.append(_name_only("## Staged files", ["git", "diff", "--name-only", "--staged"]))
            blocks.append(_name_only("## Unstaged files", ["git", "diff", "--name-only"]))
            _rc3, untracked = git_capture(["git", "ls-files", "--others", "--exclude-standard"], timeout_sec=30)
            if untracked.strip():
                blocks.append("## Untracked files\n```\n" + truncate(untracked.strip(), max_chars=20_000) + "\n```")
            return "\n\n".join(blocks)

        rc1, unstaged = git_capture(["git", "diff", "--no-color"], timeout_sec=60)
        rc2, staged = git_capture(["git", "diff", "--no-color", "--staged"], timeout_sec=60)
        rc3, untracked = git_capture(["git", "ls-files", "--others", "--exclude-standard"], timeout_sec=30)
        if rc1 != 0 or rc2 != 0 or rc3 != 0:
            return truncate("\n".join([unstaged, staged, untracked]), max_chars=40_000)
        blocks: list[str] = []
        if staged.strip():
            blocks.append("## Staged diff\n```diff\n" + staged.strip() + "\n```")
        if unstaged.strip():
            blocks.append("## Unstaged diff\n```diff\n" + unstaged.strip() + "\n```")
        if untracked.strip():
            blocks.append("## Untracked files\n```\n" + untracked.strip() + "\n```")
        return "\n\n".join(blocks) if blocks else "## Diff\n(no changes detected)\n"

    if args.commit:
        if mode == "summary":
            return _name_only("## Commit files", ["git", "show", "--name-only", "--pretty=format:", args.commit])
        _rc, out = git_capture(["git", "show", "--no-color", args.commit], timeout_sec=60)
        return "## Commit diff\n```diff\n" + truncate(out.strip(), max_chars=60_000) + "\n```"

    base = args.base
    if mode == "summary":
        return _name_only(f"## Files changed vs {base}", ["git", "diff", "--name-only", f"{base}...HEAD"])
    _rc, out = git_capture(["git", "diff", "--no-color", f"{base}...HEAD"], timeout_sec=60)
    return f"## Diff vs {base}\n```diff\n" + truncate(out.strip(), max_chars=60_000) + "\n```"


def run_codex_exec(
    *,
    prompt: str,
    output_last_message: Path,
    timeout_sec: int,
    codex_configs: list[str] | None = None,
) -> tuple[int, str, list[str]]:
    exe = shutil.which("codex")
    if not exe:
        return 127, "codex executable not found in PATH\n", ["codex"]

    extra_config = [c for c in (codex_configs or []) if str(c).strip()]
    extra_config_args: list[str] = []
    for c in extra_config:
        extra_config_args.extend(["-c", str(c)])

    cmd = [
        exe,
        "exec",
        *extra_config_args,
        "-s",
        "read-only",
        "-C",
        str(repo_root()),
        "--output-last-message",
        str(output_last_message),
        "-",
    ]
    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            encoding="utf-8",
            errors="ignore",
            cwd=str(repo_root()),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return 124, "codex exec timeout\n", cmd
    except Exception as exc:  # noqa: BLE001
        return 1, f"codex exec failed to start: {exc}\n", cmd
    return proc.returncode or 0, proc.stdout or "", cmd
