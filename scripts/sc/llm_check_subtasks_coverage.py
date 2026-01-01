#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sc-llm-check-subtasks-coverage

Goal:
  For a Taskmaster task that contains subtasks in tasks.json, semantically check whether
  those subtasks are covered by the task view acceptance criteria (tasks_back/tasks_gameplay).

Why:
  In this repo, deterministic gates (acceptance_check + anchors + executed-refs) treat
  tasks_back/tasks_gameplay acceptance as SSoT. Subtasks often exist only as an LLM-driven
  work breakdown in tasks.json, so we need a semantic mapping:
    - Each subtask should be covered by >= 1 acceptance item (in either view, when present).

This script is intentionally a *pre-flight* aid for pending/in-progress tasks.
It does not run build/tests and it does not modify any files.

Output:
  logs/ci/<YYYY-MM-DD>/sc-llm-subtasks-coverage-task-<id>/
    - prompt.md
    - trace.log
    - output-last-message.txt
    - summary.json
    - report.md

Usage (Windows):
  py -3 scripts/sc/llm_check_subtasks_coverage.py --task-id 17
  py -3 scripts/sc/llm_check_subtasks_coverage.py --task-id 17 --timeout-sec 600
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _bootstrap_imports() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))


_bootstrap_imports()

from _taskmaster import resolve_triplet  # noqa: E402
from _util import ci_dir, repo_root, write_json, write_text  # noqa: E402


def _run_codex_exec(*, prompt: str, out_last_message: Path, timeout_sec: int) -> tuple[int, str, list[str]]:
    exe = shutil.which("codex")
    if not exe:
        return 127, "codex executable not found in PATH\n", ["codex"]
    cmd = [
        exe,
        "exec",
        "-s",
        "read-only",
        "-C",
        str(repo_root()),
        "--output-last-message",
        str(out_last_message),
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
        return 124, "codex exec timeout\n", cmd
    except Exception as exc:  # noqa: BLE001
        return 1, f"codex exec failed to start: {exc}\n", cmd
    return proc.returncode or 0, proc.stdout or "", cmd


def _extract_json_object(text: str) -> dict[str, Any]:
    text = str(text or "").strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON object found in model output.")
    obj = json.loads(m.group(0))
    if not isinstance(obj, dict):
        raise ValueError("Model output JSON is not an object.")
    return obj


def _truncate(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def _format_acceptance(view_name: str, acceptance: list[Any]) -> str:
    out = [f"[{view_name}] acceptance items ({len(acceptance)}):"]
    for idx, raw in enumerate(acceptance, start=1):
        text = _truncate(str(raw or "").strip(), max_chars=500)
        out.append(f"- {view_name}:{idx}: {text}")
    return "\n".join(out)


def _build_prompt(*, task_id: str, title: str, subtasks: list[dict[str, Any]], acceptance_by_view: dict[str, list[Any]]) -> str:
    sub_lines = []
    for s in subtasks:
        sid = str(s.get("id") or "").strip()
        st = str(s.get("title") or "").strip()
        sd = str(s.get("details") or "").strip()
        if sid and st:
            if sd:
                sd = re.sub(r"\s+", " ", sd).strip()
                sub_lines.append(f"- {sid}: {st} :: {sd}")
            else:
                sub_lines.append(f"- {sid}: {st}")
    acceptance_blocks = []
    for view_name, acc in acceptance_by_view.items():
        acceptance_blocks.append(_format_acceptance(view_name, acc))

    schema = """
Return JSON only (no Markdown).
Schema:
{
  "task_id": "<id>",
  "status": "ok" | "fail",
  "subtasks": [
    {
      "id": "<subtask id from tasks.json>",
      "title": "<subtask title>",
      "covered": true | false,
      "matches": [
        {"view": "back|gameplay", "acceptance_index": <1-based>, "acceptance_excerpt": "<short>"}
      ],
      "reason": "<one short sentence>"
    }
  ],
  "uncovered_subtask_ids": ["<id>", ...],
  "notes": ["<short>", ...]
}

Rules:
- Be conservative: mark a subtask covered ONLY if at least one acceptance item clearly implies it.
- Coverage is semantic (do not require exact wording), but do not guess.
- If ANY subtask is not covered => status must be "fail".
- Use BOTH subtask title and subtask details when judging coverage.
"""

    return "\n".join(
        [
            "You are a strict reviewer for a Godot + C# repo.",
            "Task subtasks are an implementation breakdown; acceptance criteria are the repository SSoT for gating.",
            "Decide whether each subtask is covered by >=1 acceptance item across the available views (back/gameplay).",
            "",
            f"Task: T{task_id} {title}",
            "",
            "Subtasks (from tasks.json):",
            *(sub_lines or ["- (none)"]),
            "",
            "Acceptance criteria (from tasks_back/tasks_gameplay):",
            *acceptance_blocks,
            "",
            schema.strip(),
        ]
    )


def _normalize_subtasks(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out = []
    for s in raw:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("id") or "").strip()
        title = str(s.get("title") or "").strip()
        details = str(s.get("details") or "").strip()
        if not sid or not title:
            continue
        if details:
            details = re.sub(r"\s+", " ", details).strip()
            details = _truncate(details, max_chars=420)
        out.append({"id": sid, "title": title, "details": details})
    return out


def _is_view_present(view: dict[str, Any] | None) -> bool:
    return isinstance(view, dict) and isinstance(view.get("acceptance"), list)


def main() -> int:
    ap = argparse.ArgumentParser(description="sc-llm-check-subtasks-coverage (semantic subtasks vs acceptance check)")
    ap.add_argument("--task-id", default=None, help="Taskmaster id (e.g. 17). Default: first status=in-progress task.")
    ap.add_argument("--timeout-sec", type=int, default=300, help="codex exec timeout in seconds (default: 300).")
    ap.add_argument("--max-prompt-chars", type=int, default=60_000, help="Max prompt size (default: 60000).")
    args = ap.parse_args()

    try:
        triplet = resolve_triplet(task_id=str(args.task_id) if args.task_id else None)
    except Exception as exc:  # noqa: BLE001
        print(f"SC_LLM_SUBTASKS_COVERAGE status=fail error=resolve_triplet_failed exc={exc}")
        return 2

    out_dir = ci_dir(f"sc-llm-subtasks-coverage-task-{triplet.task_id}")
    title = str(triplet.master.get("title") or "").strip()
    raw_subtasks = triplet.master.get("subtasks")
    subtasks = _normalize_subtasks(raw_subtasks)

    acceptance_by_view: dict[str, list[Any]] = {}
    if _is_view_present(triplet.back):
        acceptance_by_view["back"] = list((triplet.back or {}).get("acceptance") or [])
    if _is_view_present(triplet.gameplay):
        acceptance_by_view["gameplay"] = list((triplet.gameplay or {}).get("acceptance") or [])

    summary: dict[str, Any] = {
        "cmd": "sc-llm-subtasks-coverage",
        "task_id": triplet.task_id,
        "title": title,
        "status": None,
        "subtasks_total": len(subtasks),
        "views_present": sorted(acceptance_by_view.keys()),
        "out_dir": str(out_dir.relative_to(repo_root())).replace("\\", "/"),
        "error": None,
    }

    if not subtasks:
        summary["status"] = "ok"
        summary["reason"] = "no_subtasks"
        write_json(out_dir / "summary.json", summary)
        write_text(out_dir / "report.md", f"# T{triplet.task_id} subtasks coverage\n\nStatus: ok\n\nReason: no subtasks\n")
        print(f"SC_LLM_SUBTASKS_COVERAGE status=ok out={out_dir}")
        return 0

    if not acceptance_by_view or not any(acceptance_by_view.values()):
        summary["status"] = "fail"
        summary["error"] = "missing_acceptance_views"
        write_json(out_dir / "summary.json", summary)
        write_text(
            out_dir / "report.md",
            f"# T{triplet.task_id} subtasks coverage\n\nStatus: fail\n\nError: missing acceptance views (tasks_back/tasks_gameplay)\n",
        )
        print(f"SC_LLM_SUBTASKS_COVERAGE status=fail out={out_dir}")
        return 1

    prompt = _build_prompt(task_id=triplet.task_id, title=title, subtasks=subtasks, acceptance_by_view=acceptance_by_view)
    prompt = _truncate(prompt, max_chars=int(args.max_prompt_chars))
    prompt_path = out_dir / "prompt.md"
    write_text(prompt_path, prompt)

    out_last_message = out_dir / "output-last-message.txt"
    rc, trace, cmd = _run_codex_exec(prompt=prompt, out_last_message=out_last_message, timeout_sec=int(args.timeout_sec))
    write_text(out_dir / "trace.log", trace)
    summary["codex"] = {"rc": rc, "cmd": cmd}

    if rc != 0:
        summary["status"] = "fail"
        summary["error"] = "codex_exec_failed"
        write_json(out_dir / "summary.json", summary)
        print(f"SC_LLM_SUBTASKS_COVERAGE status=fail out={out_dir}")
        return 1

    try:
        model_out = out_last_message.read_text(encoding="utf-8", errors="ignore")
        obj = _extract_json_object(model_out)
    except Exception as exc:  # noqa: BLE001
        summary["status"] = "fail"
        summary["error"] = f"invalid_model_output: {exc}"
        write_json(out_dir / "summary.json", summary)
        print(f"SC_LLM_SUBTASKS_COVERAGE status=fail out={out_dir}")
        return 1

    # Normalize verdict
    verdict_status = str(obj.get("status") or "").strip().lower()
    if verdict_status not in ("ok", "fail"):
        verdict_status = "fail"

    uncovered = []
    for it in obj.get("subtasks") or []:
        if not isinstance(it, dict):
            continue
        covered = bool(it.get("covered"))
        sid = str(it.get("id") or "").strip()
        if sid and not covered:
            uncovered.append(sid)

    summary["status"] = verdict_status
    summary["uncovered_subtask_ids"] = uncovered
    summary["verdict_path"] = str((out_dir / "verdict.json").relative_to(repo_root())).replace("\\", "/")

    write_json(out_dir / "verdict.json", obj)
    write_json(out_dir / "summary.json", summary)

    report_lines = [f"# T{triplet.task_id} subtasks coverage", "", f"Status: {verdict_status}", ""]
    report_lines.append("## Subtasks")
    for it in obj.get("subtasks") or []:
        if not isinstance(it, dict):
            continue
        sid = str(it.get("id") or "").strip()
        st = str(it.get("title") or "").strip()
        covered = bool(it.get("covered"))
        reason = str(it.get("reason") or "").strip()
        report_lines.append(f"- {sid}: {st} :: covered={covered}")
        if reason:
            report_lines.append(f"  - reason: {reason}")
        matches = it.get("matches") or []
        if isinstance(matches, list) and matches:
            report_lines.append("  - matches:")
            for m in matches:
                if not isinstance(m, dict):
                    continue
                view = str(m.get("view") or "").strip()
                aidx = m.get("acceptance_index")
                excerpt = str(m.get("acceptance_excerpt") or "").strip()
                report_lines.append(f"    - {view}:{aidx}: {excerpt}")
    report_lines.append("")
    if uncovered:
        report_lines.append("## Uncovered")
        for sid in uncovered:
            report_lines.append(f"- {sid}")
        report_lines.append("")
    notes = obj.get("notes") or []
    if isinstance(notes, list) and notes:
        report_lines.append("## Notes")
        for n in notes:
            report_lines.append(f"- {str(n)}")
        report_lines.append("")
    report_lines.append("See also: verdict.json, prompt.md, trace.log, output-last-message.txt")
    write_text(out_dir / "report.md", "\n".join(report_lines) + "\n")

    print(f"SC_LLM_SUBTASKS_COVERAGE status={verdict_status} out={out_dir}")
    return 0 if verdict_status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
