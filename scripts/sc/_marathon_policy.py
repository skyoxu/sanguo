from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from _util import repo_root, run_cmd


def _parse_iso(value: str) -> dt.datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return dt.datetime.fromisoformat(raw)
    except ValueError:
        return None


def _coerce_diff_stats(stats: dict[str, Any] | None) -> dict[str, int]:
    payload = stats if isinstance(stats, dict) else {}
    return {
        "files_changed": max(0, int(payload.get("files_changed") or 0)),
        "untracked_files": max(0, int(payload.get("untracked_files") or 0)),
        "lines_added": max(0, int(payload.get("lines_added") or 0)),
        "lines_deleted": max(0, int(payload.get("lines_deleted") or 0)),
        "total_lines": max(0, int(payload.get("total_lines") or 0)),
    }


def _coerce_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({str(item).strip() for item in value if str(item).strip()})


def _category_for_path(path_text: str) -> str:
    path = path_text.replace("\\", "/").strip("/")
    lower = path.lower()
    if not lower:
        return "other"
    if lower.startswith(".github/"):
        return "ci"
    if lower.startswith(".taskmaster/") or lower.startswith("examples/taskmaster/"):
        return "tasking"
    if lower.startswith("execution-plans/") or lower.startswith("decision-logs/"):
        return "tasking"
    if lower.startswith("docs/") or lower in {"agents.md", "readme.md", "delivery_profile.md", "claude.md"}:
        return "docs"
    if lower.startswith("scripts/"):
        return "scripts"
    if lower.startswith("game.core/contracts/"):
        return "core-contracts"
    if lower.startswith("game.core.tests/"):
        return "core-tests"
    if lower.startswith("game.core/"):
        return "core"
    if lower.startswith("tests.godot/") or lower.startswith("game.godot.tests/"):
        return "godot-tests"
    if lower.startswith("game.godot/") or lower.startswith("scripts/") or lower.startswith("scenes/") or lower.startswith("assets/"):
        return "godot-runtime"
    if lower.endswith(".sln") or lower.endswith(".csproj") or lower in {"directory.build.props", "packages.lock.json"}:
        return "solution"
    if lower in {"project.godot", "export_presets.cfg", "icon.svg", "icon.svg.import"}:
        return "godot-runtime"
    return "other"


def _axes_for_categories(categories: list[str]) -> list[str]:
    axes: set[str] = set()
    for category in categories:
        if category in {"docs", "ci", "tasking"}:
            axes.add("governance")
        if category in {"scripts", "core", "godot-runtime", "solution"}:
            axes.add("implementation")
        if category == "core-contracts":
            axes.add("contracts")
        if category in {"core-tests", "godot-tests"}:
            axes.add("tests")
        if category == "ci":
            axes.add("ci")
        if category == "tasking":
            axes.add("tasking")
    return sorted(axes)


def _enrich_diff_stats(payload: dict[str, Any], *, tracked_paths: list[str], untracked_paths: list[str]) -> dict[str, Any]:
    categories = sorted({_category_for_path(path) for path in [*tracked_paths, *untracked_paths] if str(path).strip()})
    payload["categories"] = categories
    payload["categories_count"] = len(categories)
    payload["axes"] = _axes_for_categories(categories)
    return payload


def capture_diff_stats(*, cwd: Path | None = None, timeout_sec: int = 30) -> dict[str, int]:
    root = cwd or repo_root()
    rc_diff, out_diff = run_cmd(["git", "diff", "--numstat", "HEAD"], cwd=root, timeout_sec=timeout_sec)
    rc_untracked, out_untracked = run_cmd(["git", "ls-files", "--others", "--exclude-standard"], cwd=root, timeout_sec=timeout_sec)
    if rc_diff != 0 and rc_untracked != 0:
        return _coerce_diff_stats(None)
    files_changed = 0
    lines_added = 0
    lines_deleted = 0
    tracked_paths: list[str] = []
    if rc_diff == 0:
        for line in out_diff.splitlines():
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            path = parts[2].strip()
            if path:
                tracked_paths.append(path)
            added_raw, deleted_raw = parts[0].strip(), parts[1].strip()
            if added_raw == "-" or deleted_raw == "-":
                continue
            try:
                added = max(0, int(added_raw))
                deleted = max(0, int(deleted_raw))
            except ValueError:
                continue
            lines_added += added
            lines_deleted += deleted
            files_changed += 1
    untracked_files = 0
    untracked_paths: list[str] = []
    if rc_untracked == 0:
        untracked_paths = [line.strip() for line in out_untracked.splitlines() if line.strip()]
        untracked_files = len(untracked_paths)
    payload: dict[str, Any] = {
        "files_changed": files_changed,
        "untracked_files": untracked_files,
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
        "total_lines": lines_added + lines_deleted,
    }
    return _enrich_diff_stats(payload, tracked_paths=tracked_paths, untracked_paths=untracked_paths)


def refresh_diff_stats(
    state: dict[str, Any],
    *,
    snapshot: dict[str, Any] | None = None,
    cwd: Path | None = None,
    timeout_sec: int = 30,
) -> dict[str, Any]:
    current_raw = snapshot or capture_diff_stats(cwd=cwd, timeout_sec=timeout_sec)
    current = {**_coerce_diff_stats(current_raw), "categories": _coerce_text_list((current_raw or {}).get("categories")), "axes": _coerce_text_list((current_raw or {}).get("axes"))}
    raw = state.get("diff_stats")
    diff_stats = raw if isinstance(raw, dict) else {}
    baseline_raw = diff_stats.get("baseline") if isinstance(diff_stats, dict) else {}
    baseline = {**_coerce_diff_stats(baseline_raw), "categories": _coerce_text_list((baseline_raw or {}).get("categories")), "axes": _coerce_text_list((baseline_raw or {}).get("axes"))}
    if baseline["total_lines"] == 0 and baseline["files_changed"] == 0 and baseline["untracked_files"] == 0:
        baseline = dict(current)
    current_categories = _coerce_text_list(current.get("categories"))
    baseline_categories = _coerce_text_list(baseline.get("categories"))
    current_axes = _coerce_text_list(current.get("axes"))
    baseline_axes = _coerce_text_list(baseline.get("axes"))
    growth: dict[str, Any] = {
        "files_changed": max(0, current["files_changed"] - baseline["files_changed"]),
        "untracked_files": max(0, current["untracked_files"] - baseline["untracked_files"]),
        "lines_added": max(0, current["lines_added"] - baseline["lines_added"]),
        "lines_deleted": max(0, current["lines_deleted"] - baseline["lines_deleted"]),
        "total_lines": max(0, current["total_lines"] - baseline["total_lines"]),
        "new_categories": [item for item in current_categories if item not in baseline_categories],
        "new_axes": [item for item in current_axes if item not in baseline_axes],
    }
    state["diff_stats"] = {"baseline": baseline, "current": current, "growth": growth}
    return state


def remaining_wall_time_sec(state: dict[str, Any], *, now: dt.datetime | None = None) -> int | None:
    max_wall_time_sec = max(0, int(state.get("max_wall_time_sec") or 0))
    if max_wall_time_sec <= 0:
        return None
    started_at = _parse_iso(str(state.get("created_at") or ""))
    if started_at is None:
        return max_wall_time_sec
    current = now or dt.datetime.now()
    elapsed = max(0, int((current - started_at).total_seconds()))
    return max_wall_time_sec - elapsed


def cap_step_timeout(timeout_sec: int, state: dict[str, Any]) -> int:
    remaining = remaining_wall_time_sec(state)
    if remaining is None:
        return max(1, int(timeout_sec))
    return max(1, min(int(timeout_sec), remaining))


def wall_time_exceeded(state: dict[str, Any]) -> bool:
    remaining = remaining_wall_time_sec(state)
    return remaining is not None and remaining <= 0


def mark_wall_time_exceeded(state: dict[str, Any]) -> dict[str, Any]:
    state["status"] = "fail"
    state["wall_time_exceeded"] = True
    state["stop_reason"] = "wall_time_exceeded"
    return state


def apply_context_refresh_policy(
    state: dict[str, Any],
    *,
    failure_threshold: int,
    resume_threshold: int,
    diff_lines_threshold: int,
    diff_categories_threshold: int,
) -> dict[str, Any]:
    reasons: list[str] = []
    steps = state.get("steps")
    if isinstance(steps, dict) and failure_threshold > 0:
        for name, step in steps.items():
            if not isinstance(step, dict):
                continue
            status = str(step.get("status") or "").strip().lower()
            attempt_count = max(0, int(step.get("attempt_count") or 0))
            if status == "fail" and attempt_count >= failure_threshold:
                reasons.append(f"step_failures:{name}>={failure_threshold}")
    resume_count = max(0, int(state.get("resume_count") or 0))
    if resume_threshold > 0 and resume_count >= resume_threshold:
        reasons.append(f"resume_count>={resume_threshold}")
    diff_stats = state.get("diff_stats")
    growth = _coerce_diff_stats((diff_stats or {}).get("growth") if isinstance(diff_stats, dict) else None)
    baseline = _coerce_diff_stats((diff_stats or {}).get("baseline") if isinstance(diff_stats, dict) else None)
    current = _coerce_diff_stats((diff_stats or {}).get("current") if isinstance(diff_stats, dict) else None)
    current_block = (diff_stats or {}).get("current") if isinstance(diff_stats, dict) else {}
    growth_block = (diff_stats or {}).get("growth") if isinstance(diff_stats, dict) else {}
    current_categories = _coerce_text_list((current_block or {}).get("categories"))
    current_axes = _coerce_text_list((current_block or {}).get("axes"))
    new_categories = _coerce_text_list((growth_block or {}).get("new_categories"))
    new_axes = _coerce_text_list((growth_block or {}).get("new_axes"))
    if diff_lines_threshold > 0 and growth["total_lines"] >= diff_lines_threshold:
        reasons.append(f"diff_lines_growth>={diff_lines_threshold}({baseline['total_lines']}->{current['total_lines']})")
    if diff_categories_threshold > 0 and len(new_categories) >= diff_categories_threshold:
        reasons.append(f"diff_categories_added>={diff_categories_threshold}({','.join(new_categories)})")
    if "governance" in current_axes and "implementation" in current_axes and new_axes:
        reasons.append(f"semantic_axes_mix(governance+implementation|new={','.join(new_axes)})")
    state["context_refresh_needed"] = bool(reasons)
    state["context_refresh_reasons"] = reasons
    state["context_refresh_thresholds"] = {
        "failure_threshold": max(0, int(failure_threshold)),
        "resume_threshold": max(0, int(resume_threshold)),
        "diff_lines_threshold": max(0, int(diff_lines_threshold)),
        "diff_categories_threshold": max(0, int(diff_categories_threshold)),
    }
    return state
