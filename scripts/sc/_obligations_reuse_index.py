#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import time
from typing import Any

from _obligations_extract_helpers import validate_verdict_schema

REUSE_INDEX_LOCK_TIMEOUT_SEC = 5
REUSE_INDEX_STALE_LOCK_SEC = 120
REUSE_INDEX_RETENTION_DAYS = 14
REUSE_INDEX_MAX_ENTRIES_PER_TASK = 20
REUSE_INDEX_MAX_TOTAL_ENTRIES = 800


def _new_reuse_stats() -> dict[str, Any]:
    return {
        "reuse_index_hit": False,
        "reuse_index_fallback_scan": False,
        "reuse_index_pruned_count": 0,
        "reuse_index_lock_wait_ms": 0,
    }


def merge_reuse_stats(*stats_list: dict[str, Any]) -> dict[str, Any]:
    out = _new_reuse_stats()
    for stats in stats_list:
        if not isinstance(stats, dict):
            continue
        out["reuse_index_hit"] = bool(out["reuse_index_hit"] or bool(stats.get("reuse_index_hit")))
        out["reuse_index_fallback_scan"] = bool(out["reuse_index_fallback_scan"] or bool(stats.get("reuse_index_fallback_scan")))
        out["reuse_index_pruned_count"] = int(out["reuse_index_pruned_count"]) + int(stats.get("reuse_index_pruned_count") or 0)
        out["reuse_index_lock_wait_ms"] = int(out["reuse_index_lock_wait_ms"]) + int(stats.get("reuse_index_lock_wait_ms") or 0)
    return out


def apply_reuse_stats(summary: dict[str, Any], delta: dict[str, Any]) -> None:
    merged = merge_reuse_stats(
        {
            "reuse_index_hit": bool(summary.get("reuse_index_hit")),
            "reuse_index_fallback_scan": bool(summary.get("reuse_index_fallback_scan")),
            "reuse_index_pruned_count": int(summary.get("reuse_index_pruned_count") or 0),
            "reuse_index_lock_wait_ms": int(summary.get("reuse_index_lock_wait_ms") or 0),
        },
        delta,
    )
    summary["reuse_index_hit"] = bool(merged.get("reuse_index_hit"))
    summary["reuse_index_fallback_scan"] = bool(merged.get("reuse_index_fallback_scan"))
    summary["reuse_index_pruned_count"] = int(merged.get("reuse_index_pruned_count") or 0)
    summary["reuse_index_lock_wait_ms"] = int(merged.get("reuse_index_lock_wait_ms") or 0)


def _reuse_index_path(logs_root: Path) -> Path:
    return logs_root / "sc-llm-obligations-reuse-index.json"


def _reuse_index_lock_path(logs_root: Path) -> Path:
    return logs_root / "sc-llm-obligations-reuse-index.lock"


def _make_reuse_key(*, task_id: str, input_hash: str, prompt_version: str, security_profile: str) -> str:
    return "|".join(
        [
            str(task_id or "").strip(),
            str(input_hash or "").strip(),
            str(prompt_version or "").strip(),
            str(security_profile or "").strip(),
        ]
    )


def build_reuse_lookup_key(*, task_id: str, input_hash: str, prompt_version: str, security_profile: str) -> str:
    return _make_reuse_key(task_id=task_id, input_hash=input_hash, prompt_version=prompt_version, security_profile=security_profile)


def _load_reuse_index(logs_root: Path) -> dict[str, Any]:
    path = _reuse_index_path(logs_root)
    if not path.exists():
        return {"version": 1, "entries": {}}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "entries": {}}
    entries = obj.get("entries")
    if not isinstance(entries, dict):
        entries = {}
    return {"version": 1, "entries": entries}


def _write_reuse_index(logs_root: Path, index_obj: dict[str, Any]) -> None:
    path = _reuse_index_path(logs_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    tmp.write_text(json.dumps(index_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _to_index_path(path: Path, logs_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(logs_root.resolve())).replace("\\", "/")
    except Exception:
        return str(path.resolve()).replace("\\", "/")


def _from_index_path(path_text: str, logs_root: Path) -> Path:
    p = Path(str(path_text or "").strip())
    if not p.is_absolute():
        p = logs_root / p
    return p


def _acquire_reuse_lock(logs_root: Path) -> tuple[int | None, int]:
    logs_root.mkdir(parents=True, exist_ok=True)
    lock_path = _reuse_index_lock_path(logs_root)
    start = time.monotonic()
    deadline = time.monotonic() + REUSE_INDEX_LOCK_TIMEOUT_SEC
    while time.monotonic() < deadline:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()}|{dt.datetime.now(dt.timezone.utc).isoformat()}".encode("utf-8", errors="ignore"))
            return fd, int(max(0.0, time.monotonic() - start) * 1000)
        except FileExistsError:
            try:
                age = time.time() - lock_path.stat().st_mtime
                if age >= REUSE_INDEX_STALE_LOCK_SEC:
                    lock_path.unlink(missing_ok=True)
            except Exception:
                pass
            time.sleep(0.05)
        except Exception:
            return None, int(max(0.0, time.monotonic() - start) * 1000)
    return None, int(max(0.0, time.monotonic() - start) * 1000)


def _release_reuse_lock(logs_root: Path, fd: int | None) -> None:
    if fd is None:
        return
    try:
        os.close(fd)
    except Exception:
        pass
    try:
        _reuse_index_lock_path(logs_root).unlink(missing_ok=True)
    except Exception:
        pass


def _parse_iso_utc(raw: Any) -> dt.datetime:
    text = str(raw or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        value = dt.datetime.fromisoformat(text)
    except Exception:
        return dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)


def _prune_reuse_index_entries(entries: dict[str, Any], *, logs_root: Path) -> tuple[dict[str, Any], int]:
    before_count = len(entries)
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=max(0, REUSE_INDEX_RETENTION_DAYS))
    kept_rows: list[tuple[str, dt.datetime, str, dict[str, Any]]] = []

    for key, raw in entries.items():
        item = raw if isinstance(raw, dict) else {}
        task_id = str(item.get("task_id") or "").strip()
        if not task_id:
            continue
        updated_at = _parse_iso_utc(item.get("updated_at"))
        if updated_at < cutoff:
            continue
        summary_path = _from_index_path(str(item.get("summary_path") or ""), logs_root)
        verdict_path = _from_index_path(str(item.get("verdict_path") or ""), logs_root)
        if not summary_path.exists() or not verdict_path.exists():
            continue
        kept_rows.append((task_id, updated_at, str(key or "").strip(), item))

    kept_rows.sort(key=lambda row: row[1], reverse=True)
    per_task_count: dict[str, int] = {}
    limited_rows: list[tuple[str, dt.datetime, str, dict[str, Any]]] = []
    for row in kept_rows:
        task_id = row[0]
        count = per_task_count.get(task_id, 0)
        if count >= REUSE_INDEX_MAX_ENTRIES_PER_TASK:
            continue
        per_task_count[task_id] = count + 1
        limited_rows.append(row)

    limited_rows = limited_rows[: max(1, REUSE_INDEX_MAX_TOTAL_ENTRIES)]
    out: dict[str, Any] = {}
    for _, _, key, item in limited_rows:
        if key:
            out[key] = item
    return out, max(0, before_count - len(out))


def remember_reusable_ok_result_with_stats(
    *,
    task_id: str,
    input_hash: str,
    prompt_version: str,
    security_profile: str,
    logs_root: Path,
    summary_path: Path,
    verdict_path: Path,
) -> dict[str, Any]:
    stats = _new_reuse_stats()
    key = _make_reuse_key(
        task_id=task_id,
        input_hash=input_hash,
        prompt_version=prompt_version,
        security_profile=security_profile,
    )
    lock_fd, wait_ms = _acquire_reuse_lock(logs_root)
    stats["reuse_index_lock_wait_ms"] = int(wait_ms)
    if lock_fd is None:
        return stats
    try:
        index_obj = _load_reuse_index(logs_root)
        entries = index_obj.get("entries")
        if not isinstance(entries, dict):
            entries = {}
            index_obj["entries"] = entries
        entries[key] = {
            "task_id": str(task_id or "").strip(),
            "input_hash": str(input_hash or "").strip(),
            "prompt_version": str(prompt_version or "").strip(),
            "security_profile": str(security_profile or "").strip(),
            "summary_path": _to_index_path(summary_path, logs_root),
            "verdict_path": _to_index_path(verdict_path, logs_root),
            "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        pruned_entries, pruned_count = _prune_reuse_index_entries(entries, logs_root=logs_root)
        stats["reuse_index_pruned_count"] = int(pruned_count)
        index_obj["entries"] = pruned_entries
        _write_reuse_index(logs_root, index_obj)
    except Exception:
        return stats
    finally:
        _release_reuse_lock(logs_root, lock_fd)
    return stats


def remember_reusable_ok_result(
    *,
    task_id: str,
    input_hash: str,
    prompt_version: str,
    security_profile: str,
    logs_root: Path,
    summary_path: Path,
    verdict_path: Path,
) -> None:
    remember_reusable_ok_result_with_stats(
        task_id=task_id,
        input_hash=input_hash,
        prompt_version=prompt_version,
        security_profile=security_profile,
        logs_root=logs_root,
        summary_path=summary_path,
        verdict_path=verdict_path,
    )


def find_reusable_ok_result_with_stats(
    *,
    task_id: str,
    input_hash: str,
    prompt_version: str = "",
    security_profile: str = "",
    logs_root: Path,
    current_out_dir: Path,
) -> tuple[tuple[Path, dict[str, Any], dict[str, Any]] | None, dict[str, Any]]:
    stats = _new_reuse_stats()
    result = find_reusable_ok_result(
        task_id=task_id,
        input_hash=input_hash,
        prompt_version=prompt_version,
        security_profile=security_profile,
        logs_root=logs_root,
        current_out_dir=current_out_dir,
        _stats=stats,
    )
    return result, stats


def find_reusable_ok_result(
    *,
    task_id: str,
    input_hash: str,
    prompt_version: str = "",
    security_profile: str = "",
    logs_root: Path,
    current_out_dir: Path,
    _stats: dict[str, Any] | None = None,
) -> tuple[Path, dict[str, Any], dict[str, Any]] | None:
    stats = _stats if isinstance(_stats, dict) else _new_reuse_stats()
    key = _make_reuse_key(
        task_id=task_id,
        input_hash=input_hash,
        prompt_version=prompt_version,
        security_profile=security_profile,
    )
    task_prefix = f"sc-llm-obligations-task-{str(task_id).strip()}"
    best: tuple[float, Path, Path, dict[str, Any], dict[str, Any]] | None = None
    if not logs_root.exists():
        return None

    index_obj = _load_reuse_index(logs_root)
    entries = index_obj.get("entries") if isinstance(index_obj, dict) else {}
    if isinstance(entries, dict):
        indexed = entries.get(key)
        if isinstance(indexed, dict):
            summary_path = _from_index_path(str(indexed.get("summary_path") or ""), logs_root)
            verdict_path = _from_index_path(str(indexed.get("verdict_path") or ""), logs_root)
            if verdict_path.parent != current_out_dir and summary_path.exists() and verdict_path.exists():
                try:
                    summary = json.loads(summary_path.read_text(encoding="utf-8"))
                    verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
                except Exception:
                    summary = {}
                    verdict = {}
                if str(summary.get("status") or "").strip().lower() == "ok" and str(summary.get("input_hash") or "").strip() == str(input_hash or "").strip():
                    valid, _, normalized = validate_verdict_schema(verdict if isinstance(verdict, dict) else {})
                    if valid:
                        stats["reuse_index_hit"] = True
                        return verdict_path, summary, normalized
            lock_fd, wait_ms = _acquire_reuse_lock(logs_root)
            stats["reuse_index_lock_wait_ms"] = int(stats.get("reuse_index_lock_wait_ms") or 0) + int(wait_ms)
            if lock_fd is not None:
                try:
                    latest_obj = _load_reuse_index(logs_root)
                    latest_entries = latest_obj.get("entries")
                    if isinstance(latest_entries, dict):
                        latest_entries.pop(key, None)
                        pruned_entries, pruned_count = _prune_reuse_index_entries(latest_entries, logs_root=logs_root)
                        stats["reuse_index_pruned_count"] = int(stats.get("reuse_index_pruned_count") or 0) + int(pruned_count)
                        latest_obj["entries"] = pruned_entries
                        _write_reuse_index(logs_root, latest_obj)
                except Exception:
                    pass
                finally:
                    _release_reuse_lock(logs_root, lock_fd)

    stats["reuse_index_fallback_scan"] = True
    for summary_path in logs_root.rglob("summary.json"):
        parent = summary_path.parent
        if not parent.name.startswith(task_prefix) or parent == current_out_dir:
            continue
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if str(summary.get("status") or "").strip().lower() != "ok":
            continue
        if str(summary.get("input_hash") or "").strip() != str(input_hash or "").strip():
            continue
        verdict_path = parent / "verdict.json"
        if not verdict_path.exists():
            continue
        try:
            verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        valid, _, normalized = validate_verdict_schema(verdict if isinstance(verdict, dict) else {})
        if not valid:
            continue
        mtime = verdict_path.stat().st_mtime
        if best is None or mtime > best[0]:
            best = (mtime, summary_path, verdict_path, summary, normalized)

    if best is None:
        return None
    write_stats = remember_reusable_ok_result_with_stats(
        task_id=task_id,
        input_hash=input_hash,
        prompt_version=prompt_version,
        security_profile=security_profile,
        logs_root=logs_root,
        summary_path=best[1],
        verdict_path=best[2],
    )
    merged = merge_reuse_stats(stats, write_stats)
    stats.clear()
    stats.update(merged)
    return best[2], best[3], best[4]
