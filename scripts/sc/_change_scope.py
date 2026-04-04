from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from _util import repo_root, run_cmd


_STATUS_PREFIX_RE = re.compile(r"^[ MARCUD?!]{1,2}\s+")

_SAFE_ROOTS = (
    "docs/",
    ".taskmaster/",
    "examples/taskmaster/",
    "execution-plans/",
    "decision-logs/",
)
_SAFE_FILES = {
    "AGENTS.md",
    "README.md",
    "DELIVERY_PROFILE.md",
    "workflow.md",
    "workflow.example.md",
}
_TASK_SEMANTIC_ROOTS = (
    ".taskmaster/",
    "examples/taskmaster/",
    "docs/architecture/",
    "docs/adr/",
    "docs/prd/",
)


def _normalize_path(value: str) -> str:
    normalized = str(value or "").strip().strip("\"'").replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _status_paths(status_short: list[str] | tuple[str, ...] | None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for line in status_short or []:
        entry = _STATUS_PREFIX_RE.sub("", str(line or "").strip(), count=1)
        if not entry:
            continue
        parts = [entry]
        if " -> " in entry:
            parts = [part for part in entry.split(" -> ") if part.strip()]
        for part in parts:
            normalized = _normalize_path(part)
            if normalized and normalized not in seen:
                seen.add(normalized)
                out.append(normalized)
    return out


def _is_safe_path(path: str) -> bool:
    normalized = _normalize_path(path)
    if not normalized:
        return False
    if normalized in _SAFE_FILES:
        return True
    return any(normalized.startswith(prefix) for prefix in _SAFE_ROOTS)


def _is_task_semantic_path(path: str) -> bool:
    normalized = _normalize_path(path)
    return any(normalized.startswith(prefix) for prefix in _TASK_SEMANTIC_ROOTS)


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        normalized = str(value or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


def _acceptance_only_steps(changed_paths: list[str]) -> list[str]:
    steps = ["adr", "links", "overlay"]
    if any(path.startswith(".taskmaster/") or path.startswith("examples/taskmaster/") for path in changed_paths):
        steps.append("subtasks")
    return _dedupe_preserve_order(steps)


def _fingerprint_payload(
    *,
    previous_head: str,
    current_head: str,
    changed_paths: list[str],
    acceptance_only_steps: list[str],
) -> str:
    payload = {
        "previous_head": str(previous_head or "").strip(),
        "current_head": str(current_head or "").strip(),
        "changed_paths": list(changed_paths),
        "acceptance_only_steps": list(acceptance_only_steps),
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def classify_change_scope(
    *,
    previous_head: str,
    previous_status_short: list[str] | tuple[str, ...] | None,
    current_head: str,
    current_status_short: list[str] | tuple[str, ...] | None,
    diff_paths: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    changed_paths = _dedupe_preserve_order(
        _status_paths(previous_status_short)
        + _status_paths(current_status_short)
        + [_normalize_path(path) for path in (diff_paths or []) if _normalize_path(path)]
    )
    unsafe_paths = [path for path in changed_paths if not _is_safe_path(path)]
    task_semantic_paths = [path for path in changed_paths if _is_task_semantic_path(path)]

    deterministic_strategy = "full-pipeline"
    sc_test_reuse_allowed = False
    acceptance_only_steps: list[str] = []
    if changed_paths and not unsafe_paths:
        sc_test_reuse_allowed = True
        if task_semantic_paths:
            deterministic_strategy = "minimal-acceptance"
            acceptance_only_steps = _acceptance_only_steps(changed_paths)
        else:
            deterministic_strategy = "reuse-latest"

    return {
        "previous_head": str(previous_head or "").strip(),
        "current_head": str(current_head or "").strip(),
        "changed_paths": changed_paths,
        "unsafe_paths": unsafe_paths,
        "task_semantic_paths": task_semantic_paths,
        "doc_only_delta": bool(changed_paths) and not bool(unsafe_paths),
        "sc_test_reuse_allowed": sc_test_reuse_allowed,
        "deterministic_strategy": deterministic_strategy,
        "acceptance_only_steps": acceptance_only_steps,
        "change_fingerprint": _fingerprint_payload(
            previous_head=previous_head,
            current_head=current_head,
            changed_paths=changed_paths,
            acceptance_only_steps=acceptance_only_steps,
        ),
    }


def _git_diff_paths(previous_head: str, current_head: str) -> tuple[list[str], str | None]:
    prev = str(previous_head or "").strip()
    cur = str(current_head or "").strip()
    if not prev or not cur or prev == cur:
        return [], None
    rc, out = run_cmd(["git", "diff", "--name-only", f"{prev}..{cur}"], cwd=repo_root(), timeout_sec=60)
    if rc != 0:
        return [], f"git_diff_failed:{prev}..{cur}"
    return [_normalize_path(line) for line in out.splitlines() if _normalize_path(line)], None


def classify_change_scope_between_snapshots(*, previous_git: dict[str, Any] | None, current_git: dict[str, Any] | None) -> dict[str, Any]:
    previous = previous_git if isinstance(previous_git, dict) else {}
    current = current_git if isinstance(current_git, dict) else {}
    diff_paths, diff_error = _git_diff_paths(
        str(previous.get("head") or "").strip(),
        str(current.get("head") or "").strip(),
    )
    payload = classify_change_scope(
        previous_head=str(previous.get("head") or "").strip(),
        previous_status_short=list(previous.get("status_short") or []),
        current_head=str(current.get("head") or "").strip(),
        current_status_short=list(current.get("status_short") or []),
        diff_paths=diff_paths,
    )
    if diff_error:
        payload["unsafe_paths"] = _dedupe_preserve_order(list(payload.get("unsafe_paths") or []) + [diff_error])
        payload["sc_test_reuse_allowed"] = False
        payload["deterministic_strategy"] = "full-pipeline"
    return payload
