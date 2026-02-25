#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _to_path(path_text: str, logs_root: Path) -> Path:
    p = Path(str(path_text or "").strip())
    if not p.is_absolute():
        p = logs_root / p
    return p


def _read_runtime_fp(summary_path: Path) -> str:
    try:
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    return str(obj.get("runtime_code_fingerprint") or "").strip()


def explain_reuse_miss(
    *,
    logs_root: Path,
    task_id: str,
    input_hash: str,
    prompt_version: str,
    security_profile: str,
    runtime_code_fingerprint: str,
    sample_limit: int = 5,
) -> dict[str, Any]:
    idx_path = logs_root / "sc-llm-obligations-reuse-index.json"
    out: dict[str, Any] = {
        "target": {
            "task_id": str(task_id or "").strip(),
            "input_hash": str(input_hash or "").strip(),
            "prompt_version": str(prompt_version or "").strip(),
            "security_profile": str(security_profile or "").strip(),
            "runtime_code_fingerprint": str(runtime_code_fingerprint or "").strip(),
        },
        "index_exists": idx_path.exists(),
        "index_entries": 0,
        "mismatch_dimensions": [],
        "candidate_counts": {
            "same_task": 0,
            "same_task_input_hash": 0,
            "same_task_prompt_version": 0,
            "same_task_security_profile": 0,
            "same_task_runtime_code_fingerprint": 0,
        },
        "samples": [],
    }
    if not idx_path.exists():
        out["mismatch_dimensions"] = ["task_id"]
        return out

    try:
        idx_obj = json.loads(idx_path.read_text(encoding="utf-8"))
    except Exception:
        out["mismatch_dimensions"] = ["index_parse_error"]
        return out

    entries = idx_obj.get("entries") or {}
    if not isinstance(entries, dict):
        entries = {}
    out["index_entries"] = len(entries)
    if not entries:
        out["mismatch_dimensions"] = ["task_id"]
        return out

    target_tid = str(task_id or "").strip()
    target_hash = str(input_hash or "").strip()
    target_prompt = str(prompt_version or "").strip()
    target_sec = str(security_profile or "").strip()
    target_fp = str(runtime_code_fingerprint or "").strip()

    same_task = []
    same_task_hash = []
    same_task_prompt = []
    same_task_sec = []
    same_task_fp = []

    for key, raw in entries.items():
        item = raw if isinstance(raw, dict) else {}
        tid = str(item.get("task_id") or "").strip()
        ih = str(item.get("input_hash") or "").strip()
        pv = str(item.get("prompt_version") or "").strip()
        sp = str(item.get("security_profile") or "").strip()
        sfp = _read_runtime_fp(_to_path(str(item.get("summary_path") or ""), logs_root))

        if len(out["samples"]) < int(max(1, sample_limit)):
            out["samples"].append(
                {
                    "key": str(key or "").strip(),
                    "task_id": tid,
                    "input_hash": ih,
                    "prompt_version": pv,
                    "security_profile": sp,
                    "runtime_code_fingerprint": sfp,
                }
            )

        if tid != target_tid:
            continue
        same_task.append(item)
        if ih == target_hash:
            same_task_hash.append(item)
        if pv == target_prompt:
            same_task_prompt.append(item)
        if sp == target_sec:
            same_task_sec.append(item)
        if target_fp and sfp and sfp == target_fp:
            same_task_fp.append(item)

    counts = out["candidate_counts"]
    counts["same_task"] = len(same_task)
    counts["same_task_input_hash"] = len(same_task_hash)
    counts["same_task_prompt_version"] = len(same_task_prompt)
    counts["same_task_security_profile"] = len(same_task_sec)
    counts["same_task_runtime_code_fingerprint"] = len(same_task_fp)

    mismatches: list[str] = []
    if not same_task:
        mismatches.append("task_id")
    else:
        if not same_task_hash:
            mismatches.append("input_hash")
        if not same_task_prompt:
            mismatches.append("prompt_version")
        if not same_task_sec:
            mismatches.append("security_profile")
        if target_fp:
            has_any_cached_fp = any(str(sample.get("runtime_code_fingerprint") or "").strip() for sample in out["samples"])
            if has_any_cached_fp and not same_task_fp:
                mismatches.append("runtime_code_fingerprint")
    out["mismatch_dimensions"] = mismatches
    return out
