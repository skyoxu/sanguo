#!/usr/bin/env python3
"""Run task-scoped Godot evidence checks without changing repository sources."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from project_health_knowledge import base_dir, read_json, write_json
from _project_health_runtime_snapshot import prepare_snapshot

GODOT_REF = "Tests.Godot/"
CLEANUP_MARGIN_SECONDS = 30
REQUIRED_EVIDENCE_FIELDS = {
    "task_id", "source_revision", "test_refs", "scenes", "status",
    "started_at", "finished_at", "evidence_path",
}


def _references(value, sources: dict[str, str]) -> list[str]:
    text = json.dumps(value, ensure_ascii=False)
    refs = re.findall(r"Tests\.Godot/[A-Za-z0-9_./-]+", text.replace("\\\\", "/"))
    refs = [ref.rstrip(".,;/") for ref in refs]
    refs = [ref for ref in refs if '..' not in Path(ref).parts and
            (ref in sources or any(path.startswith(ref.rstrip('/') + '/') for path in sources))]
    return list(dict.fromkeys(refs))


def _task_id(value) -> str:
    text = str(value)
    if not re.fullmatch(r"[1-9][0-9]*", text):
        raise ValueError("taskmaster_id must be a canonical positive numeric id")
    return text


def _gameplay_tasks(root: Path, state: dict | None = None, include_all: bool = False) -> list[dict]:
    if state is None:
        latest = base_dir(root) / "latest.json"
        if not latest.exists():
            raise ValueError("A successful local source scan is required before runtime verification")
        state = read_json(latest)
    source = state.get("sources", {}).get(".taskmaster/tasks/tasks_gameplay.json")
    if not isinstance(source, str):
        raise ValueError("The selected scan does not contain tasks_gameplay.json")
    rows = json.loads(source)
    static_by_id = {_task_id(item["task"]["id"]): item.get("godot", {}) for item in state.get("tasks", [])}
    result, seen = [], set()
    for row in rows:
        task_id = _task_id(row.get("taskmaster_id", ""))
        if task_id not in static_by_id:
            continue
        if task_id in seen:
            continue
        seen.add(task_id)
        refs = _references({"test_refs": row.get("test_refs", []),
                            "acceptance_criteria": row.get("acceptance_criteria", []),
                            "test_strategy": row.get("testStrategy", row.get("test_strategy", []))},
                           state.get("sources", {}))
        static = static_by_id.get(task_id, {})
        explicit_runtime = "gdunit" in json.dumps(row, ensure_ascii=False).casefold()
        reviewed_mapping = bool(static.get("scenes"))
        if include_all or refs or explicit_runtime or reviewed_mapping:
            result.append({**row, "taskmaster_id": task_id,
                           "runtime_test_refs": refs, "static_godot": static})
    return result


def _write_evidence(root: Path, task: dict, revision: str, status: str, reason: str | None,
                    command: list[str], started: str, exit_code: int | None) -> dict:
    task_id = _task_id(task.get("taskmaster_id"))
    refs = task.get("runtime_test_refs", [])
    scenes = [item.get("scene") for item in task.get("static_godot", {}).get("scenes", []) if item.get("scene")]
    evidence = base_dir(root) / "runtime" / f"task-{task_id}-{uuid.uuid4().hex}.json"
    payload = {"schema_version": "newrouge.project-health-runtime.v1", "task_id": task_id,
               "source_revision": revision, "test_refs": refs, "scenes": scenes, "command": command,
               "status": status, "reason": reason, "started_at": started,
               "finished_at": datetime.now(timezone.utc).isoformat(), "exit_code": exit_code,
               "evidence_path": evidence.relative_to(root).as_posix(), "runtime_verified": False}
    write_json(evidence, payload)
    return payload


def _report_counts(report: Path) -> dict:
    path = report / 'run-summary.json'
    return read_json(path).get('results', {}) if path.exists() else {}


def _run_task(root: Path, task: dict, godot_bin: str, timeout: int, revision: str) -> dict:
    refs = task.get("runtime_test_refs", [])
    started = datetime.now(timezone.utc).isoformat()
    if not refs:
        return _write_evidence(root, task, revision, "runtime_unverified",
                               "No task-scoped Godot/GdUnit assertion path was found", [], started, None)
    execution_root = Path(task.get('_execution_root', root))
    report = base_dir(root) / 'runtime' / 'reports' / uuid.uuid4().hex
    command = [sys.executable, str(execution_root / "scripts/python/run_gdunit.py"), "--godot-bin", godot_bin,
               "--project", "Tests.Godot", "--prewarm", "--timeout-sec", str(timeout)]
    if '_execution_root' in task:
        command.extend(['--rd', str(report)])
        previous_reports = execution_root / 'Tests.Godot/reports'
        if previous_reports.exists():
            previous_reports.rename(execution_root.parent / ('reports-' + uuid.uuid4().hex))
    for ref in refs:
        command.extend(["--add", ref.removeprefix("Tests.Godot/")])
    try:
        if '_execution_root' in task:
            report.mkdir(parents=True)
            proc = subprocess.Popen(command, cwd=execution_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, encoding='utf-8', errors='replace')
            try:
                stdout, stderr = proc.communicate(timeout=timeout + CLEANUP_MARGIN_SECONDS)
            except subprocess.TimeoutExpired:
                subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True, timeout=15)
                proc.communicate(timeout=15)
                raise
            proc = subprocess.CompletedProcess(command, proc.returncode, stdout, stderr)
            (report / 'runner-stdout.txt').write_text(stdout, encoding='utf-8')
            (report / 'runner-stderr.txt').write_text(stderr, encoding='utf-8')
        else:
            proc = subprocess.run(command, cwd=execution_root, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=timeout + CLEANUP_MARGIN_SECONDS)
        status = "passed" if proc.returncode == 0 else "failed"
        reason = None if status == "passed" else (proc.stderr or proc.stdout)[-2000:]
        if '_execution_root' in task and status == 'passed':
            counts = _report_counts(report)
            if not (counts.get('tests', 0) > 0 and counts.get('failures') == 0 and counts.get('errors') == 0):
                status, reason = 'failed', 'Missing passing task assertions in the isolated test report'
    except subprocess.TimeoutExpired as exc:
        status, reason = "failed", "runtime test timed out"
        proc = None
    result = _write_evidence(root, task, revision, status, reason, command, started,
                             proc.returncode if proc else None)
    if '_execution_root' in task:
        result['report_path'] = report.relative_to(root).as_posix()
        result['test_results'] = _report_counts(report)
        if status == 'failed' and result['test_results']:
            result['reason'] = f"Task assertion results: {json.dumps(result['test_results'], sort_keys=True)}. {reason}"
    return result


def _main_revision(root: Path) -> str | None:
    proc = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "refs/heads/main"],
                          capture_output=True, text=True, encoding="utf-8")
    return proc.stdout.strip() if proc.returncode == 0 else None


def _scan_revision(root: Path) -> str | None:
    latest = base_dir(root) / "latest.json"
    return read_json(latest).get("revision") if latest.exists() else None


def _complete(result: dict) -> bool:
    return REQUIRED_EVIDENCE_FIELDS <= result.keys() and bool(result.get("test_refs"))


def _unverified_evidence(root: Path, task: dict, revision: str, reason: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return _write_evidence(root, task, revision, "runtime_unverified", reason, [], now, None)


def _runtime_inputs_match(root: Path, revision: str) -> tuple[bool, str | None]:
    if not re.fullmatch(r"[0-9a-f]{40}", revision or ""):
        return False, "Runtime verification requires a local-main Git revision"
    main = _main_revision(root)
    if main != revision:
        return False, "The scanned revision no longer matches local main"
    return True, None


def _persist_result(root: Path, result: dict) -> None:
    path = root / result["evidence_path"]
    write_json(path, result)


def _summary(results: list[dict], timed_out: bool) -> dict:
    return {"total": len(results), "runtime_verified": sum(bool(x.get("runtime_verified")) for x in results),
            "runtime_failed": sum(x["status"] == "failed" for x in results),
            "runtime_unverified": sum(x["status"] == "runtime_unverified" for x in results),
            "global_timeout_reached": timed_out}


def verify(root: Path, godot_bin: str, timeout: int, task_id: str | None = None,
           global_timeout: int = 3600, task_ids: list[str] | None = None,
           all_gameplay: bool = False, mode: str = 'main') -> dict:
    lock = base_dir(root) / 'runtime/batch.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValueError('Another runtime batch is active; inspect batch.lock after an interrupted run')
    try:
        return _verify(root, godot_bin, timeout, task_id, global_timeout, task_ids, all_gameplay, mode)
    finally:
        lock.rmdir()


def _verify(root: Path, godot_bin: str, timeout: int, task_id: str | None,
            global_timeout: int, task_ids: list[str] | None, all_gameplay: bool, mode: str) -> dict:
    scan_path = base_dir(root) / "latest.json"
    if not scan_path.exists():
        raise ValueError("A successful local source scan is required before runtime verification")
    state = read_json(scan_path)
    scan_revision = state.get("revision")
    if mode not in ('main', 'workspace'):
        raise ValueError('Unknown runtime mode')
    tasks = _gameplay_tasks(root, state, include_all=all_gameplay)
    if all_gameplay and (task_id is not None or task_ids is not None):
        raise ValueError("--all-gameplay cannot be combined with task selection")
    selected_ids = None
    if task_ids is not None:
        selected_ids = {_task_id(value) for value in task_ids}
        if not selected_ids:
            raise ValueError("At least one task id is required")
        tasks = [task for task in tasks if task.get("taskmaster_id") in selected_ids]
        found_ids = {task.get("taskmaster_id") for task in tasks}
        missing = sorted(selected_ids - found_ids, key=int)
        if missing:
            raise ValueError(f"Runtime-eligible gameplay tasks not found: {','.join(missing)}")
    elif task_id is not None:
        task_id = _task_id(task_id)
        tasks = [task for task in tasks if task.get("taskmaster_id") == task_id]
        if not tasks:
            raise ValueError("Runtime-eligible gameplay task not found")
    deadline = time.monotonic() + global_timeout
    results = []
    inputs_match, input_reason = (True, None) if mode == 'workspace' else _runtime_inputs_match(root, scan_revision)
    manifest = None
    if not inputs_match:
        results = [_unverified_evidence(root, task, scan_revision, input_reason) for task in tasks]
    else:
        batch = base_dir(root) / 'runtime/batches' / uuid.uuid4().hex
        manifest = prepare_snapshot(root, batch / 'source', scan_revision, mode, deadline)
        for task in tasks:
            task['_execution_root'] = str(batch / 'source')
        for task in tasks:
            remaining = int(deadline - time.monotonic())
            if remaining <= CLEANUP_MARGIN_SECONDS:
                break
            inner_timeout = min(timeout, remaining - CLEANUP_MARGIN_SECONDS)
            results.append(_run_task(root, task, godot_bin, inner_timeout, manifest['source_revision']))
        for task in tasks[len(results):]:
            results.append(_unverified_evidence(root, task, scan_revision,
                           "Global runtime verification timeout reached before this task started"))
    stable = _scan_revision(root) == scan_revision and _main_revision(root) == scan_revision
    inputs_unchanged = manifest is not None and all((batch / 'source' / path).is_file() and
        hashlib.sha256((batch / 'source' / path).read_bytes()).hexdigest() == digest
        for path, digest in manifest['files'].items())
    for result in results:
        result['verification_mode'] = mode
        result['task_definition_revision'] = scan_revision
        result['input_snapshot'] = (batch / 'input-manifest.json').relative_to(root).as_posix() if manifest else None
        result['workspace_verified'] = mode == 'workspace' and result['status'] == 'passed' and inputs_unchanged
        result["runtime_verified"] = (result["status"] == "passed" and _complete(result)
                                      and result["source_revision"] == scan_revision and stable and mode == 'main' and inputs_unchanged)
        if result["status"] == "passed" and (not inputs_unchanged or (mode == 'main' and not stable)):
            result["status"] = "runtime_unverified"
            result["reason"] = "Snapshot inputs, scan or local-main revision changed during runtime verification"
        _persist_result(root, result)
    timed_out = any((result.get("reason") or "").startswith("Global runtime verification timeout")
                    for result in results)
    output = base_dir(root) / "runtime" / ('latest.json' if mode == 'main' else 'workspace-latest.json')
    merge_ids = selected_ids if selected_ids is not None else ({task_id} if task_id is not None else None)
    if mode == 'main' and merge_ids is not None and output.exists():
        previous = read_json(output)
        if previous.get("source_revision") == scan_revision:
            results = [row for row in previous.get("tasks", [])
                       if str(row.get("task_id")) not in merge_ids] + results
    write_json(output, {"schema_version": "newrouge.project-health-runtime-index.v1",
                        "source_revision": scan_revision if mode == 'main' else manifest['source_revision'],
                        "verification_mode": mode, "tasks": results,
                        "summary": _summary(results, timed_out)})
    return read_json(output)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--godot-bin", required=True)
    parser.add_argument("--timeout-sec", type=int, default=600)
    parser.add_argument("--global-timeout-sec", type=int, default=3600)
    parser.add_argument("--task-id")
    parser.add_argument("--task-ids", help="Comma-separated gameplay task ids")
    parser.add_argument("--all-gameplay", action="store_true",
                        help="Audit every master-mapped tasks_gameplay row")
    parser.add_argument('--mode', choices=('main', 'workspace'), default='main')
    args = parser.parse_args(argv)
    try:
        if args.timeout_sec <= 0 or args.global_timeout_sec <= 0:
            raise ValueError("Timeout values must be positive")
        if sum(bool(value) for value in (args.task_id, args.task_ids, args.all_gameplay)) > 1:
            raise ValueError("Use only one task selection mode")
        task_ids = args.task_ids.split(",") if args.task_ids is not None else None
        print(json.dumps(verify(args.repo_root.resolve(), args.godot_bin, args.timeout_sec,
                                args.task_id, args.global_timeout_sec, task_ids,
                                args.all_gameplay, args.mode), ensure_ascii=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}, ensure_ascii=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
