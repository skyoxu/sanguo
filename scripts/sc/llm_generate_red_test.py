#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sc-llm-generate-red-test: Generate a task-aligned failing red test file using Codex CLI.

Why:
  - tasks_back/test_strategy + acceptance are free-text and cannot be fully verified deterministically.
  - This tool uses LLM assistance to draft a meaningful red test skeleton aligned to the task's
    acceptance/test_strategy, instead of a generic "true should be false" placeholder.

Safety/traceability:
  - Always writes prompts + raw outputs to logs/ci/<date>/sc-llm-red-test/.
  - By default it only writes a single file:
      Game.Core.Tests/Tasks/Task<id>RedTests.cs
  - It does NOT claim semantic completion; it only drafts test intent.

Usage (Windows):
  py -3 scripts/sc/llm_generate_red_test.py --task-id 11
  py -3 scripts/sc/llm_generate_red_test.py --task-id 11 --verify-red
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
    # scripts/sc/llm_generate_red_test.py -> scripts/sc
    sys.path.insert(0, str(Path(__file__).resolve().parent))


_bootstrap_imports()

from _taskmaster import resolve_triplet  # noqa: E402
from _util import ci_dir, repo_root, run_cmd, write_json, write_text  # noqa: E402


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _truncate(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def _extract_json_object(text: str) -> dict[str, Any]:
    # Best-effort: allow the model to wrap JSON in markdown fences.
    # We intentionally keep this conservative.
    text = text.strip()
    # Try direct parse first.
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Try to find the first JSON object substring.
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON object found in model output.")
    snippet = m.group(0)
    obj = json.loads(snippet)
    if not isinstance(obj, dict):
        raise ValueError("Model output JSON is not an object.")
    return obj


AUTO_BEGIN = "<!-- BEGIN AUTO:TEST_ORG_NAMING_REFS -->"
AUTO_END = "<!-- END AUTO:TEST_ORG_NAMING_REFS -->"


def _extract_testing_framework_excerpt() -> str:
    path = repo_root() / "docs" / "testing-framework.md"
    if not path.exists():
        return ""
    text = _read_text(path)
    a = text.find(AUTO_BEGIN)
    b = text.find(AUTO_END)
    if a < 0 or b < 0 or b <= a:
        return ""
    excerpt = text[a + len(AUTO_BEGIN) : b].strip()
    return excerpt


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


def _build_prompt(*, task_id: str, context: dict[str, Any]) -> str:
    master = context.get("master") if isinstance(context.get("master"), dict) else {}
    back = context.get("back") if isinstance(context.get("back"), dict) else {}
    gameplay = context.get("gameplay") if isinstance(context.get("gameplay"), dict) else {}

    title = str(master.get("title") or "").strip()
    overlay = str(master.get("overlay") or "").strip()
    adr_refs = master.get("adrRefs") or []
    arch_refs = master.get("archRefs") or []

    back_strategy = back.get("test_strategy") or []
    back_acceptance = back.get("acceptance") or []
    gameplay_strategy = gameplay.get("test_strategy") or []
    gameplay_acceptance = gameplay.get("acceptance") or []

    taskdoc_md = str(context.get("taskdoc_markdown") or "")
    taskdoc_md = _truncate(taskdoc_md, max_chars=12_000)

    testing_excerpt = _extract_testing_framework_excerpt()
    testing_excerpt = _truncate(testing_excerpt, max_chars=10_000)

    constraints = "\n".join(
        [
            "Hard constraints for generated code:",
            "- Output MUST be valid JSON only (no Markdown).",
            "- The JSON MUST contain: {\"file_path\": \"...\", \"content\": \"...\"}.",
            "- file_path MUST be: Game.Core.Tests/Tasks/Task<id>RedTests.cs for this task id.",
            "- content MUST be UTF-8 text, C# only, English only (no Chinese in code/comments/strings).",
            "- Use xUnit + FluentAssertions only; do not introduce new packages.",
            "- Test naming MUST follow Should_ style (e.g. ShouldDoX_WhenY).",
            "- The test(s) MUST reflect acceptance/test_strategy intent and MUST be failing under current code (red stage).",
            "- Prefer a deterministic assertion failure over compile errors, but compile errors are acceptable if unavoidable.",
        ]
    )

    ctx = "\n".join(
        [
            "Task context (from sc-analyze triplet):",
            f"- id: {task_id}",
            f"- title: {title}",
            f"- overlay: {overlay}",
            f"- adrRefs: {', '.join([str(x) for x in adr_refs])}",
            f"- archRefs: {', '.join([str(x) for x in arch_refs])}",
            "",
            "Repository testing conventions excerpt (docs/testing-framework.md):",
            testing_excerpt or "(missing)",
            "",
            "tasks_back.test_strategy:",
            json.dumps(back_strategy, ensure_ascii=False, indent=2),
            "",
            "tasks_back.acceptance:",
            json.dumps(back_acceptance, ensure_ascii=False, indent=2),
            "",
            "tasks_gameplay.test_strategy:",
            json.dumps(gameplay_strategy, ensure_ascii=False, indent=2),
            "",
            "tasks_gameplay.acceptance:",
            json.dumps(gameplay_acceptance, ensure_ascii=False, indent=2),
            "",
            "taskdoc (Serena context, may include symbols/paths):",
            taskdoc_md or "(missing)",
        ]
    )

    instruction = "\n".join(
        [
            "You are generating a red test file for a Godot+C# repo.",
            "The goal is to express task intent as a meaningful failing unit test skeleton.",
            "Keep it minimal: 1-3 tests that cover the highest-value acceptance points that are unit-testable in Game.Core.",
            "Do NOT write TODOs. Do NOT add new production code.",
            "Only output the requested JSON object.",
        ]
    )

    return "\n\n".join([constraints, ctx, instruction]).strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a task-aligned red test file using Codex CLI.")
    ap.add_argument("--task-id", required=True, help="Task id (master id, e.g. 11).")
    ap.add_argument("--timeout-sec", type=int, default=600, help="codex exec timeout in seconds (default: 600).")
    ap.add_argument("--verify-red", action="store_true", help="Run sc-build tdd --stage red after writing the file.")
    args = ap.parse_args()

    task_id = str(args.task_id).split(".", 1)[0].strip()
    if not task_id.isdigit():
        print("SC_LLM_RED_TEST ERROR: --task-id must be a numeric master id (e.g. 11).")
        return 2

    out_dir = ci_dir("sc-llm-red-test")

    # Gate: acceptance must declare deterministic evidence mapping via "Refs:".
    # At red stage we validate only the presence + syntax of refs (not file existence / test_refs inclusion).
    gate_cmd = [
        "py",
        "-3",
        "scripts/python/validate_acceptance_refs.py",
        "--task-id",
        task_id,
        "--stage",
        "red",
        "--out",
        str(out_dir / f"acceptance-refs.{task_id}.json"),
    ]
    gate_rc, gate_out = run_cmd(gate_cmd, cwd=repo_root(), timeout_sec=60)
    write_text(out_dir / f"acceptance-refs.{task_id}.log", gate_out)
    if gate_rc != 0:
        print(f"SC_LLM_RED_TEST ERROR: acceptance refs gate failed rc={gate_rc} out={out_dir}")
        return 1

    # Ensure sc-analyze context exists for this task id (and includes taskdoc if present).
    analyze_cmd = [
        "py",
        "-3",
        "scripts/sc/analyze.py",
        "--task-id",
        task_id,
        "--focus",
        "all",
        "--depth",
        "quick",
        "--format",
        "json",
    ]
    analyze_rc, analyze_out = run_cmd(analyze_cmd, cwd=repo_root(), timeout_sec=900)
    write_text(out_dir / f"analyze-{task_id}.log", analyze_out)
    if analyze_rc != 0:
        print(f"SC_LLM_RED_TEST ERROR: sc-analyze failed rc={analyze_rc} out={out_dir}")
        return 1

    ctx_path = repo_root() / "logs" / "ci" / out_dir.parent.name / "sc-analyze" / f"task_context.{task_id}.json"
    # If date inference fails for any reason, fall back to the legacy alias.
    if not ctx_path.exists():
        ctx_path = repo_root() / "logs" / "ci" / out_dir.parent.name / "sc-analyze" / "task_context.json"
    context = json.loads(_read_text(ctx_path) or "{}")
    if not isinstance(context, dict):
        print(f"SC_LLM_RED_TEST ERROR: invalid task context json: {ctx_path}")
        return 1

    triplet = resolve_triplet(task_id=task_id)
    # Extra guard: ensure mapped views exist.
    if not triplet.back or not triplet.gameplay:
        write_json(out_dir / f"triplet-{task_id}.json", triplet.__dict__)
        print(f"SC_LLM_RED_TEST ERROR: task mapping missing in tasks_back/tasks_gameplay for task_id={task_id}")
        return 1

    prompt = _build_prompt(task_id=task_id, context=context)
    prompt_path = out_dir / f"prompt-{task_id}.txt"
    write_text(prompt_path, prompt)

    last_msg_path = out_dir / f"codex-last-message-{task_id}.txt"
    trace_path = out_dir / f"codex-trace-{task_id}.log"
    rc, trace_out, cmd = _run_codex_exec(prompt=prompt, out_last_message=last_msg_path, timeout_sec=int(args.timeout_sec))
    write_text(trace_path, trace_out)

    last_msg = _read_text(last_msg_path) if last_msg_path.exists() else ""
    meta = {"task_id": task_id, "rc": rc, "cmd": cmd, "prompt": str(prompt_path), "trace": str(trace_path), "last_msg": str(last_msg_path)}
    write_json(out_dir / f"meta-{task_id}.json", meta)

    if rc != 0 or not last_msg.strip():
        print(f"SC_LLM_RED_TEST ERROR: codex exec failed/empty rc={rc} out={out_dir}")
        return 1

    obj = _extract_json_object(last_msg)
    file_path = str(obj.get("file_path") or "")
    content = str(obj.get("content") or "")
    expected_path = f"Game.Core.Tests/Tasks/Task{task_id}RedTests.cs"
    if file_path.replace("\\", "/") != expected_path:
        print(f"SC_LLM_RED_TEST ERROR: unexpected file_path. expected={expected_path} got={file_path}")
        return 1
    if not content.strip():
        print("SC_LLM_RED_TEST ERROR: empty content")
        return 1

    target = repo_root() / expected_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.replace("\r\n", "\n"), encoding="utf-8", newline="\n")

    print(f"SC_LLM_RED_TEST status=ok wrote={expected_path} out={out_dir}")

    if not args.verify_red:
        return 0

    # Verify: red stage should be failing (tdd returns rc=0 when it is red).
    verify_cmd = ["py", "-3", "scripts/sc/build.py", "tdd", "--stage", "red", "--task-id", task_id]
    vrc, vout = run_cmd(verify_cmd, cwd=repo_root(), timeout_sec=900)
    write_text(out_dir / f"verify-red-{task_id}.log", vout)
    if vrc != 0:
        print(f"SC_LLM_RED_TEST ERROR: verify red failed rc={vrc} out={out_dir}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
