#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sc-llm-semantic-gate-all: Batch semantic equivalence audit across all tasks.

Purpose:
  Identify tasks whose acceptance set is NOT semantically equivalent to the task description.

Design:
  - This is "stage 2" only (LLM semantic audit).
  - It does NOT re-check deterministic gates already covered by sc-acceptance-check.
  - Output is written to logs/ci/<YYYY-MM-DD>/sc-semantic-gate-all/.

Output format:
  The LLM is instructed to emit strict TSV lines:
    T<id>\tOK|Needs Fix\t<short reason>
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _taskmaster import resolve_triplet
from _util import ci_dir, repo_root, today_str


@dataclass(frozen=True)
class SemanticFinding:
    task_id: int
    verdict: str  # OK | Needs Fix | Unknown
    reason: str


def _strip_refs_clause(text: str) -> str:
    """
    Remove the trailing `Refs:` clause from acceptance items.

    Notes:
      - Stage-2 semantic gate must not infer requirements from test file paths/names.
      - Deterministic refs/anchors checks are handled elsewhere (sc-acceptance-check).
    """

    s = str(text or "").strip()
    idx = s.lower().find("refs:")
    if idx >= 0:
        s = s[:idx].rstrip()
    # Collapse whitespace after truncation.
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _truncate(text: str, *, max_chars: int) -> str:
    s = str(text or "")
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 3] + "..."


def _load_all_task_ids() -> list[int]:
    tasks_json = _read_json(repo_root() / ".taskmaster" / "tasks" / "tasks.json")
    tasks = (tasks_json.get("master") or {}).get("tasks") or []
    out: list[int] = []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        try:
            out.append(int(str(t.get("id") or "").strip()))
        except ValueError:
            continue
    return sorted(set(out))


def _task_brief(task_id: int, *, max_acceptance_items: int) -> str:
    triplet = resolve_triplet(task_id=str(task_id))
    master = triplet.master or {}
    back = triplet.back or {}
    gameplay = triplet.gameplay or {}

    def _list(entry: dict[str, Any], key: str) -> list[str]:
        raw = entry.get(key) or []
        if not isinstance(raw, list):
            return []
        out: list[str] = []
        for x in raw:
            s = str(x or "").strip()
            if s and s not in out:
                out.append(s)
        return out

    def _acc(entry: dict[str, Any]) -> list[str]:
        raw = entry.get("acceptance") or []
        if not isinstance(raw, list):
            return []
        items = [_strip_refs_clause(x) for x in raw]
        return [s for s in items if s][:max_acceptance_items]

    lines: list[str] = []
    lines.append(f"### Task {task_id}: {str(master.get('title') or '').strip()}")
    lines.append(f"- master.description: {_truncate(master.get('description') or '', max_chars=400)}")
    lines.append(f"- master.details: {_truncate(master.get('details') or '', max_chars=800)}")
    lines.append(f"- back.description: {_truncate(back.get('description') or '', max_chars=400)}")
    lines.append(f"- gameplay.description: {_truncate(gameplay.get('description') or '', max_chars=400)}")
    # Extra semantic hints to reduce false positives when master description is short.
    overlay_refs = sorted(set(_list(back, "overlay_refs") + _list(gameplay, "overlay_refs")))
    contract_refs = sorted(set(_list(back, "contractRefs") + _list(gameplay, "contractRefs")))
    labels = sorted(set(_list(back, "labels") + _list(gameplay, "labels")))
    if overlay_refs:
        lines.append(f"- overlay_refs: {', '.join(overlay_refs[:12])}{' ...' if len(overlay_refs) > 12 else ''}")
    if contract_refs:
        lines.append(f"- contractRefs: {', '.join(contract_refs[:20])}{' ...' if len(contract_refs) > 20 else ''}")
    if labels:
        lines.append(f"- labels: {', '.join(labels[:20])}{' ...' if len(labels) > 20 else ''}")

    back_acc = _acc(back)
    gameplay_acc = _acc(gameplay)
    if back_acc:
        lines.append("- acceptance (view=back):")
        for a in back_acc:
            lines.append(f"  - {a}")
    if gameplay_acc:
        lines.append("- acceptance (view=gameplay):")
        for a in gameplay_acc:
            lines.append(f"  - {a}")
    if not back_acc and not gameplay_acc:
        lines.append("- acceptance: (missing in both views)")
    return "\n".join(lines).strip()


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


def _build_batch_prompt(*, batch: list[int], max_acceptance_items: int) -> str:
    blocks: list[str] = []
    blocks.append("Role: semantic-equivalence-auditor (batch)")
    blocks.append("")
    blocks.append("Goal: for each task below, judge whether the acceptance set is semantically equivalent to the task description.")
    blocks.append("Scope: stage-2 only. Do NOT re-check deterministic gates (refs existence, anchors, ADR/security/static scans).")
    blocks.append("Important: DO NOT infer requirements from any test file names/paths; treat refs as non-semantic metadata.")
    blocks.append("")
    blocks.append("Output format (STRICT, no markdown fences):")
    blocks.append("For each task, output exactly one TSV line:")
    blocks.append("T<id>\\tOK|Needs Fix\\t<short reason (<=120 chars)>")
    blocks.append("")
    blocks.append("Rules:")
    blocks.append("- Verdict OK if acceptance covers all REQUIRED behaviors/invariants/failure-semantics implied by the master description/details, and does not CONTRADICT them.")
    blocks.append("- Extra refinements are allowed if they are consistent with the task intent (e.g., stricter validation, additional event metadata, clearer invariants). Do NOT mark Needs Fix solely because acceptance is more detailed than the description.")
    blocks.append("- Mark Needs Fix only if: (a) a described behavior is missing, (b) acceptance contradicts the description, or (c) acceptance introduces a clearly unrelated feature that changes the task meaning.")
    blocks.append("- If the task has both back/gameplay acceptance, treat the union as the acceptance set.")
    blocks.append("- If back/gameplay descriptions conflict with master, treat master as the source of truth; do not mark Needs Fix only due to inconsistent secondary descriptions.")
    blocks.append("- If you are unsure whether something is a mismatch, choose OK (do not guess).")
    blocks.append("")
    blocks.append("Tasks:")
    for tid in batch:
        blocks.append(_task_brief(tid, max_acceptance_items=max_acceptance_items))
        blocks.append("")
    return "\n".join(blocks).strip() + "\n"


def _parse_tsv_output(text: str) -> list[SemanticFinding]:
    out: list[SemanticFinding] = []
    if not text:
        return out
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if not line.startswith("T"):
            continue
        # Some models emit literal "\t" sequences instead of actual TAB characters.
        line = line.replace("\\t", "\t")
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        tid_str = parts[0].strip().lstrip("T").strip()
        verdict = parts[1].strip()
        reason = parts[2].strip() if len(parts) >= 3 else ""
        try:
            tid = int(tid_str)
        except ValueError:
            continue
        if verdict not in {"OK", "Needs Fix"}:
            verdict = "Unknown"
        out.append(SemanticFinding(task_id=tid, verdict=verdict, reason=reason))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="sc semantic equivalence gate (batch) for all tasks")
    ap.add_argument(
        "--task-ids",
        default="",
        help="Optional comma-separated task ids to audit (e.g. 1,14,22). When set, only these tasks are included.",
    )
    ap.add_argument("--batch-size", type=int, default=8, help="Task ids per LLM call (default: 8).")
    ap.add_argument("--timeout-sec", type=int, default=900, help="Per-batch timeout seconds (default: 900).")
    ap.add_argument(
        "--consensus-runs",
        type=int,
        default=1,
        help="Run each batch N times and take a majority-vote verdict per task (default: 1).",
    )
    ap.add_argument(
        "--model-reasoning-effort",
        default="low",
        choices=["low", "medium", "high"],
        help="Codex model_reasoning_effort (default: low).",
    )
    ap.add_argument("--max-acceptance-items", type=int, default=12, help="Max acceptance items per view included in prompt.")
    ap.add_argument("--max-tasks", type=int, default=0, help="Limit total tasks (0=all).")
    args = ap.parse_args()

    batch_size = int(args.batch_size)
    if batch_size <= 0:
        print("[sc-semantic-gate-all] ERROR: --batch-size must be > 0")
        return 2

    out_dir = ci_dir("sc-semantic-gate-all")
    out_dir.mkdir(parents=True, exist_ok=True)

    all_ids = _load_all_task_ids()
    if str(args.task_ids or "").strip():
        selected: list[int] = []
        for raw in str(args.task_ids).split(","):
            s = str(raw or "").strip()
            if not s:
                continue
            try:
                selected.append(int(s))
            except ValueError:
                continue
        if selected:
            all_ids = [tid for tid in all_ids if tid in set(selected)]
    if int(args.max_tasks) > 0:
        all_ids = all_ids[: int(args.max_tasks)]

    batches: list[list[int]] = []
    for i in range(0, len(all_ids), batch_size):
        batches.append(all_ids[i : i + batch_size])

    all_findings: dict[int, SemanticFinding] = {}
    for idx, batch in enumerate(batches, 1):
        prompt = _build_batch_prompt(batch=batch, max_acceptance_items=int(args.max_acceptance_items))
        runs = max(1, int(args.consensus_runs))
        per_run: list[dict[int, SemanticFinding]] = []
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
            trace_path.write_text(trace, encoding="utf-8")

            tsv = out_path.read_text(encoding="utf-8", errors="ignore") if out_path.is_file() else ""
            parsed = _parse_tsv_output(tsv)
            run_map: dict[int, SemanticFinding] = {p.task_id: p for p in parsed}
            # Mark missing tasks in this run as unknown for visibility.
            for tid in batch:
                if tid not in run_map:
                    run_map[tid] = SemanticFinding(task_id=tid, verdict="Unknown", reason="no parseable verdict")
            per_run.append(run_map)

        # Consensus: majority vote per task (OK vs Needs Fix). Ties -> Unknown.
        for tid in batch:
            ok = sum(1 for r in per_run if r[tid].verdict == "OK")
            nf = sum(1 for r in per_run if r[tid].verdict == "Needs Fix")
            if ok == nf:
                verdict = "Unknown"
            else:
                verdict = "OK" if ok > nf else "Needs Fix"

            # Pick the first matching reason for the consensus verdict.
            reason = ""
            for r in per_run:
                f = r[tid]
                if f.verdict == verdict:
                    reason = f.reason
                    break
            if verdict == "Unknown" and not reason:
                # Fall back to any reason if available.
                reason = next((r[tid].reason for r in per_run if r[tid].reason), "no consensus verdict")

            all_findings[tid] = SemanticFinding(task_id=tid, verdict=verdict, reason=reason)

        print(f"[sc-semantic-gate-all] batch {idx}/{len(batches)} runs={runs} tasks={len(batch)}")

    needs_fix = sorted([f.task_id for f in all_findings.values() if f.verdict == "Needs Fix"])
    unknown = sorted([f.task_id for f in all_findings.values() if f.verdict == "Unknown"])

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
        "findings": [
            {"task_id": tid, "verdict": f.verdict, "reason": f.reason}
            for tid, f in sorted(all_findings.items(), key=lambda x: x[0])
        ],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"SC_SEMANTIC_GATE_ALL needs_fix={len(needs_fix)} unknown={len(unknown)} out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
