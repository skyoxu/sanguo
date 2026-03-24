#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

from _obligations_code_fingerprint import build_runtime_code_fingerprint  # noqa: E402
from _obligations_extract_helpers import build_input_hash, is_view_present, normalize_subtasks, validate_verdict_schema  # noqa: E402
from _obligations_guard import apply_deterministic_guards, build_obligation_prompt  # noqa: E402
from _obligations_reuse_index import remember_reusable_ok_result_with_stats  # noqa: E402
from _security_profile import resolve_security_profile  # noqa: E402
from _taskmaster import default_paths, iter_master_tasks, resolve_triplet  # noqa: E402


PROMPT_VERSION = "obligations-v3"


def _today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _pick_task_id(task_files: list[str]) -> str:
    tasks_json_path = default_paths()[0]
    tasks_obj = _load_json(tasks_json_path)
    master_tasks = iter_master_tasks(tasks_obj if isinstance(tasks_obj, dict) else {})
    numeric_ids: list[int] = []
    for item in master_tasks:
        raw = str(item.get("id") or "").strip()
        if not raw:
            continue
        try:
            numeric_ids.append(int(raw))
        except ValueError:
            continue
    for tid in sorted(numeric_ids):
        try:
            triplet = resolve_triplet(task_id=str(tid))
        except Exception:
            continue
        has_acceptance = False
        if is_view_present(triplet.back) and (triplet.back or {}).get("acceptance"):
            has_acceptance = True
        if is_view_present(triplet.gameplay) and (triplet.gameplay or {}).get("acceptance"):
            has_acceptance = True
        if has_acceptance:
            return str(tid)
    raise RuntimeError(f"cannot pick task id with acceptance from task files: {task_files}")


def _build_input_hash_for_task(task_id: str, security_profile: str) -> tuple[str, dict[str, Any]]:
    triplet = resolve_triplet(task_id=task_id)
    title = str(triplet.master.get("title") or "").strip()
    details = str(triplet.master.get("details") or "").strip()
    test_strategy = str(triplet.master.get("testStrategy") or "").strip()
    subtasks = normalize_subtasks(triplet.master.get("subtasks"))

    acceptance_by_view: dict[str, list[Any]] = {}
    if is_view_present(triplet.back):
        acceptance_by_view["back"] = list((triplet.back or {}).get("acceptance") or [])
    if is_view_present(triplet.gameplay):
        acceptance_by_view["gameplay"] = list((triplet.gameplay or {}).get("acceptance") or [])
    if not acceptance_by_view:
        raise RuntimeError(f"task {task_id} has no acceptance views")

    runtime_code_fingerprint, _ = build_runtime_code_fingerprint(
        {
            "build_obligation_prompt": build_obligation_prompt,
            "apply_deterministic_guards": apply_deterministic_guards,
            "validate_verdict_schema": validate_verdict_schema,
        }
    )

    input_fingerprint = {
        "prompt_version": PROMPT_VERSION,
        "runtime_code_fingerprint": runtime_code_fingerprint,
        "task_id": str(task_id),
        "title": title,
        "details": details,
        "test_strategy": test_strategy,
        "subtasks": subtasks,
        "acceptance_by_view": acceptance_by_view,
        "security_profile": security_profile,
    }
    source_excerpt = title or details or "task-source"
    first_view = sorted(acceptance_by_view.keys())[0]
    return build_input_hash(input_fingerprint), {
        "title": title,
        "details": details,
        "acceptance_by_view": acceptance_by_view,
        "source_excerpt": source_excerpt,
        "first_view": first_view,
    }


def _seed_reuse_entry(
    *,
    task_id: str,
    input_hash: str,
    security_profile: str,
    round_prefix: str,
    source_excerpt: str,
    first_view: str,
) -> tuple[Path, Path]:
    logs_root = REPO_ROOT / "logs" / "ci"
    seed_dir = logs_root / _today_str() / f"sc-llm-obligations-task-{task_id}-round-{round_prefix}-seed"
    seed_dir.mkdir(parents=True, exist_ok=True)
    summary_path = seed_dir / "summary.json"
    verdict_path = seed_dir / "verdict.json"
    summary = {"status": "ok", "input_hash": input_hash, "out_dir": str(seed_dir.relative_to(REPO_ROOT)).replace("\\", "/")}
    verdict = {
        "task_id": str(task_id),
        "status": "ok",
        "obligations": [
            {
                "id": "O1",
                "source": "master",
                "kind": "core",
                "text": f"Regression seed obligation for task {task_id}.",
                "source_excerpt": source_excerpt,
                "covered": True,
                "matches": [{"view": first_view, "acceptance_index": 1, "acceptance_excerpt": "seed"}],
                "reason": "seed",
                "suggested_acceptance": [],
            }
        ],
        "uncovered_obligation_ids": [],
        "notes": [],
    }
    ok, errors, normalized = validate_verdict_schema(verdict)
    if not ok:
        raise RuntimeError(f"seed verdict invalid: {errors}")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verdict_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    remember_reusable_ok_result_with_stats(
        task_id=str(task_id),
        input_hash=input_hash,
        prompt_version=PROMPT_VERSION,
        security_profile=security_profile,
        logs_root=logs_root,
        summary_path=summary_path,
        verdict_path=verdict_path,
    )
    return summary_path, verdict_path


def _run_extract(*, task_id: str, round_id: str, security_profile: str, timeout_sec: int) -> tuple[int, Path]:
    cmd = [
        "py",
        "-3",
        "scripts/sc/llm_extract_task_obligations.py",
        "--task-id",
        str(task_id),
        "--round-id",
        round_id,
        "--security-profile",
        security_profile,
        "--reuse-last-ok",
        "--garbled-gate",
        "off",
        "--max-schema-errors",
        "5",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=max(30, int(timeout_sec)),
        check=False,
    )
    out_dir = REPO_ROOT / "logs" / "ci" / _today_str() / f"sc-llm-obligations-task-{task_id}-round-{round_id}"
    if proc.returncode != 0:
        raise RuntimeError(f"extract failed round={round_id} rc={proc.returncode}\n{proc.stdout}")
    return proc.returncode, out_dir


def _assert_round_and_index(task_id: str, out_dir: Path, *, require_reuse_hit: bool) -> dict[str, Any]:
    summary_path = out_dir / "summary.json"
    if not summary_path.exists():
        raise RuntimeError(f"summary not found: {summary_path}")
    summary = _load_json(summary_path)
    if str(summary.get("status") or "").strip() != "ok":
        raise RuntimeError("summary.status != ok")
    if bool(require_reuse_hit) and bool(summary.get("reuse_hit")) is not True:
        raise RuntimeError("summary.reuse_hit != true")
    if bool(summary.get("reuse_index_hit")) is not True:
        raise RuntimeError("summary.reuse_index_hit != true")
    if int(summary.get("reuse_index_pruned_count") or 0) != 0:
        raise RuntimeError("summary.reuse_index_pruned_count != 0")

    idx_path = REPO_ROOT / "logs" / "ci" / "sc-llm-obligations-reuse-index.json"
    if not idx_path.exists():
        raise RuntimeError(f"reuse index not found: {idx_path}")
    idx_obj = _load_json(idx_path)
    entries = idx_obj.get("entries") or {}
    if not isinstance(entries, dict) or not entries:
        raise RuntimeError("reuse index entries empty")
    has_task = any(str((v or {}).get("task_id") or "").strip() == str(task_id) for v in entries.values() if isinstance(v, dict))
    if not has_task:
        raise RuntimeError(f"reuse index has no entry for task_id={task_id}")
    return {"summary_path": str(summary_path).replace("\\", "/"), "index_path": str(idx_path).replace("\\", "/"), "entries": len(entries)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Two-round reuse regression for obligations extractor.")
    parser.add_argument("--task-id", default="", help="Optional explicit task id.")
    parser.add_argument(
        "--task-files",
        nargs="+",
        default=[str(path.relative_to(REPO_ROOT)).replace("\\", "/") for path in default_paths()[1:]],
        help="Task view files for candidate lookup context.",
    )
    parser.add_argument("--round-prefix", default="reuse-regression", help="Round id prefix.")
    parser.add_argument("--timeout-sec", type=int, default=180, help="Timeout per llm_extract invocation.")
    args = parser.parse_args()

    task_id = str(args.task_id or "").strip() or _pick_task_id([str(x) for x in (args.task_files or [])])
    security_profile = resolve_security_profile(None)
    input_hash, ctx = _build_input_hash_for_task(task_id=task_id, security_profile=security_profile)
    _seed_reuse_entry(
        task_id=task_id,
        input_hash=input_hash,
        security_profile=security_profile,
        round_prefix=str(args.round_prefix),
        source_excerpt=str(ctx.get("source_excerpt") or "task-source"),
        first_view=str(ctx.get("first_view") or "back"),
    )

    _, out_dir_1 = _run_extract(task_id=task_id, round_id=f"{args.round_prefix}-r1", security_profile=security_profile, timeout_sec=int(args.timeout_sec))
    _, out_dir_2 = _run_extract(task_id=task_id, round_id=f"{args.round_prefix}-r2", security_profile=security_profile, timeout_sec=int(args.timeout_sec))
    _assert_round_and_index(task_id=task_id, out_dir=out_dir_1, require_reuse_hit=True)
    check = _assert_round_and_index(task_id=task_id, out_dir=out_dir_2, require_reuse_hit=True)

    summary = {
        "status": "ok",
        "task_id": str(task_id),
        "security_profile": security_profile,
        "input_hash": input_hash,
        "round_1_out_dir": str(out_dir_1.relative_to(REPO_ROOT)).replace("\\", "/"),
        "round_2_out_dir": str(out_dir_2.relative_to(REPO_ROOT)).replace("\\", "/"),
        "title": ctx.get("title"),
        "acceptance_views": sorted((ctx.get("acceptance_by_view") or {}).keys()),
        "summary_path": check["summary_path"],
        "index_path": check["index_path"],
        "index_entries": check["entries"],
    }
    out_dir = REPO_ROOT / "logs" / "ci" / _today_str() / "obligations-reuse-regression"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "summary.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OBLIGATIONS_REUSE_REGRESSION status=ok task_id={task_id} out={str(out_path).replace('\\', '/')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
