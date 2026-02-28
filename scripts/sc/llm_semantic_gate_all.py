#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from _garbled_gate import parse_task_ids_csv, render_top_hits, scan_task_text_integrity
from _semantic_gate_all_contract import (
    evaluate_semantic_gate_exit,
    run_semantic_gate_all_self_check,
    validate_semantic_gate_summary,
)
from _semantic_gate_all_runtime import build_prompt_with_budget, load_task_maps
from _util import ci_dir, repo_root, today_str, write_json, write_text


@dataclass(frozen=True)
class SemanticFinding:
    task_id: int
    verdict: str  # OK | Needs Fix | Unknown
    reason: str


def _run_codex_exec(*, prompt: str, out_path: Path, timeout_sec: int, model_reasoning_effort: str) -> tuple[int, str]:
    exe = shutil.which("codex")
    if not exe:
        return 127, "codex executable not found in PATH\n"
    cmd = [
        exe,
        "exec",
        "-c",
        f'model_reasoning_effort="{model_reasoning_effort}"',
        "-s",
        "read-only",
        "-C",
        str(repo_root()),
        "--output-last-message",
        str(out_path),
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
        return 124, "codex exec timeout\n"
    except Exception as exc:  # noqa: BLE001
        return 1, f"codex exec failed: {exc}\n"
    return proc.returncode or 0, proc.stdout or ""


def _parse_tsv_output(text: str) -> list[SemanticFinding]:
    def _normalize_verdict(raw: str) -> str:
        value = re.sub(r"\s+", " ", str(raw or "").strip()).lower()
        if value in {"ok", "pass", "passed"}:
            return "OK"
        if value in {"needs fix", "needs_fix", "need fix", "fail", "failed"}:
            return "Needs Fix"
        return "Unknown"

    def _parse_task_id(token: str) -> int | None:
        s = str(token or "").strip()
        if not s:
            return None
        if s.lower().startswith("t"):
            s = s[1:].strip()
        if not s.isdigit():
            return None
        return int(s)

    out: list[SemanticFinding] = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        line = line.replace("\\t", "\t")
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        task_id = _parse_task_id(parts[0])
        if task_id is None:
            continue
        verdict = _normalize_verdict(parts[1])
        reason = parts[2].strip() if len(parts) >= 3 else ""
        out.append(SemanticFinding(task_id=task_id, verdict=verdict, reason=reason))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="sc semantic equivalence gate (batch) for all tasks")
    ap.add_argument("--task-ids", default="", help="Optional CSV ids, e.g. 1,14,22")
    ap.add_argument("--batch-size", type=int, default=8, help="Task ids per LLM call")
    ap.add_argument("--timeout-sec", type=int, default=900, help="Per-batch timeout seconds")
    ap.add_argument("--consensus-runs", type=int, default=1, help="Run each batch N times for majority verdict")
    ap.add_argument("--model-reasoning-effort", default="low", choices=["low", "medium", "high"], help="Codex model_reasoning_effort")
    ap.add_argument("--max-acceptance-items", type=int, default=12, help="Max acceptance items per view in prompt")
    ap.add_argument("--max-prompt-chars", type=int, default=60_000, help="Max prompt size after task brief budgeting")
    ap.add_argument("--max-tasks", type=int, default=0, help="Limit total tasks (0=all)")
    ap.add_argument("--max-needs-fix", type=int, default=0, help="Fail when Needs Fix count exceeds this limit")
    ap.add_argument("--max-unknown", type=int, default=0, help="Fail when Unknown count exceeds this limit")
    ap.add_argument("--garbled-gate", default="on", choices=["on", "off"], help="Hard precheck for garbled task/acceptance text")
    ap.add_argument("--self-check", action="store_true", help="Run deterministic local self-check only")
    args = ap.parse_args()

    if bool(args.self_check):
        out_dir = ci_dir("sc-semantic-gate-all-self-check")
        ok, payload, report = run_semantic_gate_all_self_check(parse_tsv_output=_parse_tsv_output)
        write_json(out_dir / "summary.json", payload)
        write_json(out_dir / "verdict.json", payload)
        write_text(out_dir / "report.md", report)
        print(f"SC_SEMANTIC_GATE_ALL_SELF_CHECK status={'ok' if ok else 'fail'} out={out_dir}")
        return 0 if ok else 1

    batch_size = int(args.batch_size)
    if batch_size <= 0:
        print("[sc-semantic-gate-all] ERROR: --batch-size must be > 0")
        return 2
    consensus_runs = int(args.consensus_runs)
    if consensus_runs <= 0 or consensus_runs % 2 == 0:
        print("[sc-semantic-gate-all] ERROR: --consensus-runs must be an odd positive integer (1,3,5,...)")
        return 2
    max_prompt_chars = max(3000, int(args.max_prompt_chars))

    out_dir = ci_dir("sc-semantic-gate-all")
    out_dir.mkdir(parents=True, exist_ok=True)

    task_filter = parse_task_ids_csv(str(args.task_ids).strip()) if str(args.task_ids).strip() else set()
    if str(args.garbled_gate).strip().lower() != "off":
        pre_report = scan_task_text_integrity(task_ids=task_filter or None)
        write_json(out_dir / "garbled-precheck.json", pre_report)
        pre_summary = pre_report.get("summary") or {}
        decode_errors = int(pre_summary.get("decode_errors") or 0)
        parse_errors = int(pre_summary.get("parse_errors") or 0)
        suspicious_hits = int(pre_summary.get("suspicious_hits") or 0)
        if decode_errors > 0 or parse_errors > 0 or suspicious_hits > 0:
            top_hits = render_top_hits(pre_report, limit=8)
            print(
                "[sc-semantic-gate-all] ERROR: garbled precheck failed "
                f"decode_errors={decode_errors} parse_errors={parse_errors} suspicious_hits={suspicious_hits}"
            )
            if top_hits:
                print("[sc-semantic-gate-all] top garbled hits:")
                for line in top_hits:
                    print(f" - {line}")
            return 2

    all_ids, master_by_id, back_by_id, gameplay_by_id = load_task_maps()
    if str(args.task_ids or "").strip():
        all_ids = [tid for tid in all_ids if tid in task_filter]
    if int(args.max_tasks) > 0:
        all_ids = all_ids[: int(args.max_tasks)]
    batches = [all_ids[i : i + batch_size] for i in range(0, len(all_ids), batch_size)]

    all_findings: dict[int, SemanticFinding] = {}
    batch_meta: list[dict[str, Any]] = []
    for idx, batch in enumerate(batches, 1):
        prompt, prompt_trimmed, task_brief_budget = build_prompt_with_budget(
            batch=batch,
            max_acceptance_items=int(args.max_acceptance_items),
            max_prompt_chars=max_prompt_chars,
            master_by_id=master_by_id,
            back_by_id=back_by_id,
            gameplay_by_id=gameplay_by_id,
        )
        runs = consensus_runs
        per_run: list[dict[int, SemanticFinding]] = []
        per_run_meta: list[dict[str, Any]] = []
        for run_idx in range(1, runs + 1):
            suffix = f"-run-{run_idx:02d}" if runs > 1 else ""
            out_path = out_dir / f"batch-{idx:02d}{suffix}.tsv"
            trace_path = out_dir / f"batch-{idx:02d}{suffix}.trace.log"
            rc, trace = _run_codex_exec(
                prompt=prompt,
                out_path=out_path,
                timeout_sec=int(args.timeout_sec),
                model_reasoning_effort=str(args.model_reasoning_effort),
            )
            write_text(trace_path, trace)
            tsv = out_path.read_text(encoding="utf-8", errors="ignore") if out_path.is_file() else ""
            parsed = _parse_tsv_output(tsv)
            run_map = {p.task_id: p for p in parsed}
            for tid in batch:
                if tid not in run_map:
                    run_map[tid] = SemanticFinding(task_id=tid, verdict="Unknown", reason="no parseable verdict")
            per_run.append(run_map)
            per_run_meta.append({"run": run_idx, "rc": rc, "parsed_lines": len(parsed)})

        for tid in batch:
            ok_votes = sum(1 for r in per_run if r[tid].verdict == "OK")
            nf_votes = sum(1 for r in per_run if r[tid].verdict == "Needs Fix")
            verdict = "Unknown" if ok_votes == nf_votes else ("OK" if ok_votes > nf_votes else "Needs Fix")
            reason = next((r[tid].reason for r in per_run if r[tid].verdict == verdict and r[tid].reason), "")
            if verdict == "Unknown" and not reason:
                reason = next((r[tid].reason for r in per_run if r[tid].reason), "no consensus verdict")
            all_findings[tid] = SemanticFinding(task_id=tid, verdict=verdict, reason=reason)

        batch_meta.append(
            {
                "batch_index": idx,
                "task_count": len(batch),
                "prompt_chars": len(prompt),
                "prompt_trimmed": bool(prompt_trimmed),
                "task_brief_budget": int(task_brief_budget),
                "runs": runs,
                "run_meta": per_run_meta,
            }
        )
        print(f"[sc-semantic-gate-all] batch {idx}/{len(batches)} runs={runs} tasks={len(batch)} prompt_chars={len(prompt)}")

    needs_fix = sorted([f.task_id for f in all_findings.values() if f.verdict == "Needs Fix"])
    unknown = sorted([f.task_id for f in all_findings.values() if f.verdict == "Unknown"])
    fail_by_policy, fail_reasons = evaluate_semantic_gate_exit(
        needs_fix_count=len(needs_fix),
        unknown_count=len(unknown),
        max_needs_fix=int(args.max_needs_fix),
        max_unknown=int(args.max_unknown),
    )

    summary = {
        "cmd": "sc-semantic-gate-all",
        "date": today_str(),
        "batches": len(batches),
        "batch_size": batch_size,
        "total_tasks": len(all_ids),
        "counts": {
            "ok": sum(1 for f in all_findings.values() if f.verdict == "OK"),
            "needs_fix": len(needs_fix),
            "unknown": len(unknown),
        },
        "needs_fix": needs_fix,
        "unknown": unknown,
        "findings": [{"task_id": tid, "verdict": f.verdict, "reason": f.reason} for tid, f in sorted(all_findings.items(), key=lambda x: x[0])],
        "max_needs_fix": int(args.max_needs_fix),
        "max_unknown": int(args.max_unknown),
        "fail_reasons": fail_reasons,
        "status": "fail" if fail_by_policy else "ok",
        "config": {
            "consensus_runs": int(consensus_runs),
            "timeout_sec": int(args.timeout_sec),
            "model_reasoning_effort": str(args.model_reasoning_effort),
            "max_acceptance_items": int(args.max_acceptance_items),
            "max_prompt_chars": int(max_prompt_chars),
            "garbled_gate": str(args.garbled_gate),
        },
        "batch_meta": batch_meta,
    }
    summary_ok, summary_errors, checked_summary = validate_semantic_gate_summary(summary)
    if not summary_ok:
        checked_summary["status"] = "fail"
        checked_summary["fail_reasons"] = list(checked_summary.get("fail_reasons") or []) + ["summary_schema_invalid"]
        checked_summary["summary_errors"] = summary_errors
        write_json(out_dir / "summary.json", checked_summary)
        print(f"SC_SEMANTIC_GATE_ALL status=fail reason=summary_schema_invalid out={out_dir}")
        return 1

    write_json(out_dir / "summary.json", checked_summary)
    print(
        "SC_SEMANTIC_GATE_ALL "
        f"status={checked_summary['status']} needs_fix={len(needs_fix)} unknown={len(unknown)} "
        f"limit_needs_fix={int(args.max_needs_fix)} limit_unknown={int(args.max_unknown)} out={out_dir}"
    )
    return 1 if bool(fail_by_policy) else 0


if __name__ == "__main__":
    raise SystemExit(main())

