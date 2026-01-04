#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sc-llm-extract-task-obligations

Goal:
  Extract a falsifiable set of "must" obligations from tasks.json (master + subtasks),
  then check whether those obligations are covered by >= 1 acceptance item across the
  available task views (tasks_back/tasks_gameplay).

Why:
  Subtasks coverage is necessary but not sufficient: a task can "look covered" while
  still allowing no-op loopholes (e.g., "waiting for player action" implemented as
  "do not call AdvanceTurn").

This script is intentionally pre-flight:
  - It does not run build/tests.
  - It does not modify any files.

Output:
  logs/ci/<YYYY-MM-DD>/sc-llm-obligations-task-<id>/
    - prompt.md
    - trace.log
    - output-last-message.txt
    - summary.json
    - report.md

Usage (Windows):
  py -3 scripts/sc/llm_extract_task_obligations.py --task-id 17
  py -3 scripts/sc/llm_extract_task_obligations.py --task-id 17 --timeout-sec 600
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


def _normalize_subtasks(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for s in raw:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("id") or "").strip()
        title = str(s.get("title") or "").strip()
        details = str(s.get("details") or "").strip()
        test_strategy = str(s.get("testStrategy") or "").strip()
        if not sid or not title:
            continue
        if details:
            details = re.sub(r"\s+", " ", details).strip()
            details = _truncate(details, max_chars=520)
        if test_strategy:
            test_strategy = re.sub(r"\s+", " ", test_strategy).strip()
            test_strategy = _truncate(test_strategy, max_chars=320)
        out.append({"id": sid, "title": title, "details": details, "testStrategy": test_strategy})
    return out


def _format_acceptance(view_name: str, acceptance: list[Any]) -> str:
    out = [f"[{view_name}] acceptance items ({len(acceptance)}):"]
    for idx, raw in enumerate(acceptance, start=1):
        text = _truncate(str(raw or "").strip(), max_chars=520)
        out.append(f"- {view_name}:{idx}: {text}")
    return "\n".join(out)


def _build_prompt(
    *,
    task_id: str,
    title: str,
    master_details: str,
    master_test_strategy: str,
    subtasks: list[dict[str, str]],
    acceptance_by_view: dict[str, list[Any]],
) -> str:
    sub_lines = []
    for s in subtasks:
        sid = s.get("id", "").strip()
        st = s.get("title", "").strip()
        sd = s.get("details", "").strip()
        ts = s.get("testStrategy", "").strip()
        if sid and st:
            line = f"- {sid}: {st}"
            if sd:
                line += f" :: {sd}"
            sub_lines.append(line)
            if ts:
                sub_lines.append(f"  testStrategy: {ts}")

    acceptance_blocks = []
    for view_name, acc in acceptance_by_view.items():
        acceptance_blocks.append(_format_acceptance(view_name, acc))

    schema = """
Return JSON only (no Markdown).
Schema:
{
  "task_id": "<id>",
  "status": "ok" | "fail",
  "obligations": [
    {
      "id": "O1",
      "source": "master" | "subtask:<id>",
      "kind": "core" | "godot" | "meta",
      "text": "<one falsifiable obligation>",
      "source_excerpt": "<short verbatim excerpt from the provided task text>",
      "covered": true | false,
      "matches": [
        {"view": "back|gameplay", "acceptance_index": <1-based>, "acceptance_excerpt": "<short>"}
      ],
      "reason": "<one short sentence>",
      "suggested_acceptance": ["<line1>", "<line2>"]
    }
  ],
  "uncovered_obligation_ids": ["O2", "..."],
  "notes": ["<short>", ...]
}

Rules:
- Obligations MUST be falsifiable / auditable: avoid vague statements like "works correctly".
- Avoid no-op loopholes: include at least one "must refuse / must not advance / state unchanged" obligation when applicable.
- Use ONLY the provided task text (master.details/testStrategy + subtasks title/details/testStrategy) to derive obligations.
- Each obligation MUST include source_excerpt copied verbatim from the provided task text; if you cannot cite an excerpt, do NOT include that obligation.
- Be conservative: mark covered ONLY when an acceptance item clearly implies it.
- If ANY obligation is not covered => status must be "fail".
- suggested_acceptance must be minimal and aligned to tasks_back/tasks_gameplay style (Chinese OK). Do NOT include any "Refs:" here.
- Ignore "Local demo paths" / absolute paths; they are not obligations.
"""

    master_details = _truncate(master_details or "", max_chars=8_000)
    master_test_strategy = _truncate(master_test_strategy or "", max_chars=4_000)

    return "\n".join(
        [
            "You are a strict reviewer for a Godot + C# repo.",
            "Acceptance criteria are used as SSoT for deterministic gates; they must cover all must-have obligations.",
            "",
            f"Task: T{task_id} {title}",
            "",
            "Master details:",
            master_details or "(empty)",
            "",
            "Master testStrategy:",
            master_test_strategy or "(empty)",
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


def _is_view_present(view: dict[str, Any] | None) -> bool:
    return isinstance(view, dict) and isinstance(view.get("acceptance"), list)


def _render_report(obj: dict[str, Any]) -> str:
    task_id = str(obj.get("task_id") or "")
    status = str(obj.get("status") or "")
    uncovered = obj.get("uncovered_obligation_ids") or []
    obligations = obj.get("obligations") or []
    lines: list[str] = []
    lines.append("# sc-llm-extract-task-obligations report")
    lines.append("")
    lines.append(f"- task_id: {task_id}")
    lines.append(f"- status: {status}")
    lines.append(f"- uncovered: {len(uncovered) if isinstance(uncovered, list) else 'unknown'}")
    lines.append("")
    if isinstance(obligations, list) and obligations:
        lines.append("## Obligations")
        lines.append("")
        for o in obligations:
            if not isinstance(o, dict):
                continue
            oid = str(o.get("id") or "").strip()
            covered = bool(o.get("covered"))
            text = str(o.get("text") or "").strip()
            excerpt = str(o.get("source_excerpt") or "").strip()
            src = str(o.get("source") or "").strip()
            kind = str(o.get("kind") or "").strip()
            lines.append(f"- {oid} covered={covered} kind={kind} source={src}: {text}")
            if excerpt:
                lines.append(f"  - excerpt: {excerpt}")
            if not covered:
                sug = o.get("suggested_acceptance") or []
                if isinstance(sug, list) and sug:
                    for s in sug[:2]:
                        ss = str(s or "").strip()
                        if ss:
                            lines.append(f"  - suggest: {ss}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="sc-llm-extract-task-obligations (obligations vs acceptance coverage)")
    ap.add_argument("--task-id", default=None, help="Taskmaster id (e.g. 17). Default: first status=in-progress task.")
    ap.add_argument("--timeout-sec", type=int, default=360, help="codex exec timeout in seconds (default: 360).")
    ap.add_argument("--max-prompt-chars", type=int, default=80_000, help="Max prompt size (default: 80000).")
    args = ap.parse_args()

    try:
        triplet = resolve_triplet(task_id=str(args.task_id) if args.task_id else None)
    except Exception as exc:  # noqa: BLE001
        print(f"SC_LLM_OBLIGATIONS status=fail error=resolve_triplet_failed exc={exc}")
        return 2

    out_dir = ci_dir(f"sc-llm-obligations-task-{triplet.task_id}")
    title = str(triplet.master.get("title") or "").strip()
    details = str(triplet.master.get("details") or "").strip()
    test_strategy = str(triplet.master.get("testStrategy") or "").strip()
    subtasks = _normalize_subtasks(triplet.master.get("subtasks"))

    acceptance_by_view: dict[str, list[Any]] = {}
    if _is_view_present(triplet.back):
        acceptance_by_view["back"] = list((triplet.back or {}).get("acceptance") or [])
    if _is_view_present(triplet.gameplay):
        acceptance_by_view["gameplay"] = list((triplet.gameplay or {}).get("acceptance") or [])

    summary: dict[str, Any] = {
        "cmd": "sc-llm-extract-task-obligations",
        "task_id": triplet.task_id,
        "title": title,
        "status": None,
        "subtasks_total": len(subtasks),
        "views_present": sorted(acceptance_by_view.keys()),
        "out_dir": str(out_dir.relative_to(repo_root())).replace("\\", "/"),
        "error": None,
    }

    if not acceptance_by_view:
        summary["status"] = "fail"
        summary["error"] = "no_views_present"
        write_json(out_dir / "summary.json", summary)
        write_text(out_dir / "report.md", _render_report({"task_id": triplet.task_id, "status": "fail"}))
        print(f"SC_LLM_OBLIGATIONS status=fail reason=no_views_present out={out_dir}")
        return 1

    prompt = _build_prompt(
        task_id=str(triplet.task_id),
        title=title,
        master_details=details,
        master_test_strategy=test_strategy,
        subtasks=subtasks,
        acceptance_by_view=acceptance_by_view,
    )
    prompt = _truncate(prompt, max_chars=int(args.max_prompt_chars))
    prompt_path = out_dir / "prompt.md"
    last_msg_path = out_dir / "output-last-message.txt"
    trace_path = out_dir / "trace.log"
    write_text(prompt_path, prompt)

    rc, trace_out, cmd = _run_codex_exec(prompt=prompt, out_last_message=last_msg_path, timeout_sec=int(args.timeout_sec))
    write_text(trace_path, trace_out)
    last_msg = last_msg_path.read_text(encoding="utf-8", errors="ignore") if last_msg_path.exists() else ""

    summary["rc"] = rc
    summary["cmdline"] = cmd

    if rc != 0 or not last_msg.strip():
        summary["status"] = "fail"
        summary["error"] = "codex_exec_failed_or_empty"
        write_json(out_dir / "summary.json", summary)
        print(f"SC_LLM_OBLIGATIONS status=fail rc={rc} out={out_dir}")
        return 1

    try:
        obj = _extract_json_object(last_msg)
    except Exception as exc:  # noqa: BLE001
        summary["status"] = "fail"
        summary["error"] = f"invalid_json:{exc}"
        write_json(out_dir / "summary.json", summary)
        print(f"SC_LLM_OBLIGATIONS status=fail reason=invalid_json out={out_dir}")
        return 1

    status = str(obj.get("status") or "").strip()
    summary["status"] = status
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "verdict.json", obj)
    write_text(out_dir / "report.md", _render_report(obj))

    ok = status == "ok"
    print(f"SC_LLM_OBLIGATIONS status={'ok' if ok else 'fail'} out={out_dir}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
