#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Retention helpers for gate-bundle run directories.
"""

from __future__ import annotations

import datetime as dt
import shutil
from pathlib import Path
from typing import Any


def collect_runs_by_date(ci_root: Path) -> dict[dt.date, list[Path]]:
    grouped: dict[dt.date, list[Path]] = {}
    if not ci_root.exists():
        return grouped

    for date_dir in ci_root.iterdir():
        if not date_dir.is_dir():
            continue
        try:
            day = dt.date.fromisoformat(date_dir.name)
        except ValueError:
            continue
        runs_dir = date_dir / "gate-bundle" / "runs"
        if not runs_dir.exists():
            continue
        run_dirs = [x for x in runs_dir.iterdir() if x.is_dir()]
        if run_dirs:
            grouped[day] = run_dirs
    return grouped


def prune_gate_bundle_runs(
    ci_root: Path,
    *,
    retention_days: int,
    max_runs_per_day: int,
    keep_run_id: str,
) -> dict[str, Any]:
    today = dt.date.today()
    deleted: list[str] = []
    failed: list[dict[str, str]] = []

    grouped = collect_runs_by_date(ci_root)

    # 1) Drop runs older than retention_days
    for day, run_dirs in grouped.items():
        if retention_days >= 0 and (today - day).days > retention_days:
            for run_dir in run_dirs:
                if run_dir.name == keep_run_id:
                    continue
                try:
                    shutil.rmtree(run_dir)
                    deleted.append(str(run_dir).replace("\\", "/"))
                except Exception as exc:  # noqa: BLE001
                    failed.append({"path": str(run_dir).replace("\\", "/"), "error": str(exc)})

    # 2) Keep at most N runs per day
    grouped = collect_runs_by_date(ci_root)
    for _, run_dirs in grouped.items():
        run_dirs_sorted = sorted(run_dirs, key=lambda p: p.stat().st_mtime, reverse=True)
        for run_dir in run_dirs_sorted[max_runs_per_day:]:
            if run_dir.name == keep_run_id:
                continue
            try:
                shutil.rmtree(run_dir)
                deleted.append(str(run_dir).replace("\\", "/"))
            except Exception as exc:  # noqa: BLE001
                failed.append({"path": str(run_dir).replace("\\", "/"), "error": str(exc)})

    return {
        "retention_days": retention_days,
        "max_runs_per_day": max_runs_per_day,
        "keep_run_id": keep_run_id,
        "deleted_count": len(deleted),
        "deleted": sorted(set(deleted)),
        "failed_count": len(failed),
        "failed": failed,
    }
