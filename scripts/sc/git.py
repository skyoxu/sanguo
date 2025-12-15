#!/usr/bin/env python3
"""
sc-git: Repo-specific git shim with basic safety rails.

Usage (Windows):
  py -3 scripts/sc/git.py status
  py -3 scripts/sc/git.py diff -- --stat
  py -3 scripts/sc/git.py commit --smart-commit --yes
"""

from __future__ import annotations

import argparse
import shlex
from pathlib import Path
from typing import Any

from _taskmaster import resolve_triplet
from _util import ci_dir, repo_root, run_cmd, write_json, write_text


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="sc-git (git shim)")
    ap.add_argument("operation", nargs="?", default="status")
    ap.add_argument("args", nargs=argparse.REMAINDER, help="args for git operation (use -- to separate)")
    ap.add_argument("--smart-commit", action="store_true")
    ap.add_argument("--interactive", action="store_true")
    ap.add_argument("--yes", action="store_true", help="confirm potentially destructive operations")
    ap.add_argument("--task-id", default=None, help="task id; defaults to first status=in-progress in tasks.json")
    ap.add_argument("--task-ref", default=None, help="commit Task ref (e.g. #2.1); defaults to #<task-id>")
    return ap


def is_force_push(op: str, args: list[str]) -> bool:
    if op != "push":
        return False
    force_flags = {"--force", "-f", "--force-with-lease"}
    return any(a in force_flags for a in args)


def requires_yes(op: str, args: list[str]) -> bool:
    if op in {"reset", "clean", "rebase"}:
        return True
    if is_force_push(op, args):
        return True
    return False


def has_commit_message(args: list[str]) -> bool:
    return "-m" in args or "--message" in args


def smart_commit_message() -> str:
    rc, out = run_cmd(["git", "diff", "--cached", "--name-only"], cwd=repo_root(), timeout_sec=30)
    files = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if not files:
        return "chore(repo): update working tree"

    areas = set()
    for f in files:
        f = f.replace("\\", "/")
        if f.startswith("docs/"):
            areas.add("docs")
        elif f.startswith("scripts/"):
            areas.add("scripts")
        elif f.startswith("Game.Core.Tests/") or f.endswith("Tests.cs"):
            areas.add("tests")
        elif f.startswith("Game.Core/Contracts/"):
            areas.add("contracts")
        elif f.startswith("Game.Core/"):
            areas.add("core")
        elif f.startswith("Game.Godot/"):
            areas.add("godot")
        else:
            areas.add("repo")

    scope = ",".join(sorted(areas))
    prefix = "chore"
    if "tests" in areas and len(areas) == 1:
        prefix = "test"
    if "docs" in areas and len(areas) == 1:
        prefix = "docs"
    if "core" in areas and len(areas) == 1:
        prefix = "feat"
    if "contracts" in areas and len(areas) == 1:
        prefix = "feat"

    return f"{prefix}({scope}): update {scope}"


def load_commit_template() -> str:
    # Hardcoded repo convention (per project standard).
    path = repo_root() / ".superclaude" / "commit-template.txt"
    if not path.exists():
        raise FileNotFoundError(f"commit template not found: {path}")
    return path.read_text(encoding="utf-8")


def build_commit_body(max_files: int = 12) -> str:
    rc, out = run_cmd(["git", "diff", "--cached", "--name-only"], cwd=repo_root(), timeout_sec=30)
    files = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if not files:
        return "- No staged files.\n"

    lines = ["- Changes:"]
    for f in files[:max_files]:
        lines.append(f"  - {f}")
    if len(files) > max_files:
        lines.append(f"  - (+{len(files) - max_files} more)")
    lines.append("")
    lines.append("- Rationale: (please amend this commit message to explain why)")
    return "\n".join(lines) + "\n"


def render_commit_message(
    *,
    subject: str,
    body: str,
    task_ref: str,
    adr_refs: list[str],
    overlay_file: str | None,
) -> str:
    if not adr_refs:
        raise ValueError("Missing ADR refs for commit message (expected at least 1).")

    tpl = load_commit_template()
    msg = tpl.replace("<type>(<scope>): <description>", subject)
    msg = msg.replace("<body>", body.rstrip() + "\n")
    msg = msg.replace("{{task_id}}", task_ref)
    msg = msg.replace("{{adr_refs}}", ", ".join(adr_refs))
    msg = msg.replace("{{overlay_file}}", overlay_file or "")
    return msg


def main() -> int:
    args = build_parser().parse_args()

    op = args.operation
    extra = list(args.args)
    if extra and extra[0] == "--":
        extra = extra[1:]

    # argparse.REMAINDER captures everything after operation, so wrapper flags placed
    # after the operation would otherwise be passed through to git (and fail).
    # We only support these wrapper flags post-operation for the commit workflow
    # to match the documented usage.
    smart_commit = bool(args.smart_commit)
    interactive = bool(args.interactive)
    yes = bool(args.yes)
    task_id = args.task_id
    task_ref = args.task_ref

    def pop_flag(flag: str) -> bool:
        nonlocal extra
        if flag in extra:
            extra = [a for a in extra if a != flag]
            return True
        return False

    def pop_option(opt: str) -> str | None:
        nonlocal extra
        if opt not in extra:
            return None
        i = extra.index(opt)
        if i + 1 >= len(extra):
            return None
        value = extra[i + 1]
        extra = extra[:i] + extra[i + 2 :]
        return value

    if op == "commit":
        if pop_flag("--smart-commit"):
            smart_commit = True
        if pop_flag("--interactive"):
            interactive = True
        if pop_flag("--yes"):
            yes = True

        v = pop_option("--task-id")
        if v is not None:
            task_id = v
        v = pop_option("--task-ref")
        if v is not None:
            task_ref = v

    if requires_yes(op, extra) and not yes:
        print(f"[sc-git] ERROR: operation '{op}' requires --yes for confirmation.")
        return 2

    git_args = ["git", op] + extra
    notes = []

    if op == "commit" and smart_commit and not has_commit_message(extra):
        triplet = resolve_triplet(task_id=task_id)
        task_ref = task_ref or f"#{triplet.task_id}"
        subject = smart_commit_message()
        body = build_commit_body()
        commit_msg = render_commit_message(
            subject=subject,
            body=body,
            task_ref=task_ref,
            adr_refs=triplet.adr_refs(),
            overlay_file=triplet.overlay(),
        )

        out_dir = ci_dir("sc-git")
        msg_path = out_dir / "commit-message.txt"
        write_text(msg_path, commit_msg)

        git_args = ["git", "commit", "-F", str(msg_path)] + extra
        notes.append(
            {
                "smart_commit_subject": subject,
                "task_id": triplet.task_id,
                "task_ref": task_ref,
                "adr_refs": triplet.adr_refs(),
                "overlay": triplet.overlay(),
                "message_file": str(msg_path),
            }
        )

    out_dir = ci_dir("sc-git")
    rc, out = run_cmd(git_args, cwd=repo_root(), timeout_sec=300)

    # Log output
    safe_op = "".join(ch for ch in op if ch.isalnum() or ch in ("-", "_"))[:32]
    log_path = out_dir / f"{safe_op}.log"
    write_text(log_path, out)

    summary: dict[str, Any] = {
        "cmd": "sc-git",
        "operation": op,
        "args": extra,
        "interactive": interactive,
        "rc": rc,
        "log": str(log_path),
        "notes": notes,
    }
    write_json(out_dir / "summary.json", summary)

    printable = " ".join(shlex.quote(a) for a in git_args)
    print(f"SC_GIT rc={rc} op={op} cmd={printable} out={out_dir}")
    return 0 if rc == 0 else rc


if __name__ == "__main__":
    raise SystemExit(main())
