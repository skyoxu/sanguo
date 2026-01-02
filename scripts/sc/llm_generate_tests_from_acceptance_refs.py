#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sc-llm-generate-tests-from-acceptance-refs

Generate missing test files referenced by acceptance "Refs:" using Codex CLI (LLM),
then run deterministic tests (scripts/sc/test.py) to verify.

Optional TDD helper:
  - In --tdd-stage red-first mode, the script selects a primary acceptance ref (prefers .cs)
    via LLM and generates a meaningful failing test for that primary ref first. Other
    referenced test files are generated as scaffolding (not intentionally failing).

This tool is intentionally conservative:
  - It only creates files explicitly referenced by acceptance Refs.
  - It does not invent new paths.
  - It writes prompts/traces/outputs to logs/ci/<date>/sc-llm-acceptance-tests/.

Usage (Windows):
  py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id 11 --verify unit
  py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id 10 --verify all --godot-bin \"$env:GODOT_BIN\"
  py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id 11 --tdd-stage red-first --verify none
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _bootstrap_imports() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))


_bootstrap_imports()

from _taskmaster import resolve_triplet  # noqa: E402
from _util import ci_dir, repo_root, run_cmd, write_json, write_text  # noqa: E402


REFS_RE = re.compile(r"\bRefs\s*:\s*(.+)$", flags=re.IGNORECASE)

AUTO_BEGIN = "<!-- BEGIN AUTO:TEST_ORG_NAMING_REFS -->"
AUTO_END = "<!-- END AUTO:TEST_ORG_NAMING_REFS -->"

ALLOWED_TEST_PREFIXES = ("Game.Core.Tests/", "Tests.Godot/tests/", "Tests/")


@dataclass(frozen=True)
class GenResult:
    ref: str
    status: str  # ok|skipped|fail
    rc: int | None = None
    prompt_path: str | None = None
    trace_path: str | None = None
    output_path: str | None = None
    error: str | None = None


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _truncate(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


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


def _split_refs_blob(blob: str) -> list[str]:
    s = str(blob or "").strip()
    s = s.replace("`", "")
    s = s.replace(",", " ")
    s = s.replace(";", " ")
    return [p.strip().replace("\\", "/") for p in s.split() if p.strip()]


def _extract_acceptance_refs(acceptance: Any) -> dict[str, list[str]]:
    # Returns mapping: ref_path -> list of acceptance texts that reference it.
    by_ref: dict[str, list[str]] = {}
    if not isinstance(acceptance, list):
        return by_ref
    for raw in acceptance:
        text = str(raw or "").strip()
        m = REFS_RE.search(text)
        if not m:
            continue
        refs = _split_refs_blob(m.group(1))
        for r in refs:
            if not r:
                continue
            by_ref.setdefault(r, []).append(text)
    return by_ref


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
    text = text.strip()
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


def _prompt_for_ref(
    *,
    task_id: str,
    title: str,
    ref: str,
    acceptance_texts: list[str],
    intent: str,
    task_context_markdown: str,
) -> str:
    ext = Path(ref).suffix.lower()
    if ext == ".gd":
        base_rules = [
            "Target file type: GDScript (GdUnit4 test suite).",
            "- Must be valid .gd, English only.",
            "- Must extend a GdUnit4 suite (res://addons/gdUnit4/src/GdUnitTestSuite.gd).",
            "- Do not rely on external assets; keep it minimal.",
        ]
    else:
        base_rules = [
            "Target file type: C# xUnit test file.",
            "- Must be valid C# code, English only (no Chinese in code/comments/strings).",
            "- Use xUnit + FluentAssertions only.",
            "- Use Should_ naming style.",
        ]

    if intent == "red":
        intent_rules = [
            "TDD intent: RED-FIRST.",
            "- Must include at least one deterministic failing test aligned to acceptance intent.",
            "- Do NOT use trivial failures like assert_true(false) or throwing unconditionally.",
        ]
    else:
        intent_rules = [
            "Intent: SCAFFOLD.",
            "- Should NOT intentionally fail.",
            "- Prefer smoke checks that are likely to hold once basic wiring exists (e.g. type exists, contract constants).",
        ]

    constraints = "\n".join(
        [
            "Hard constraints:",
            "- Output MUST be valid JSON only (no Markdown).",
            "- JSON schema: {\"file_path\": \"<repo-relative>\", \"content\": \"<file content>\"}.",
            f"- file_path MUST be exactly: {ref}",
            "- Do NOT create any other files.",
            *base_rules,
            *intent_rules,
        ]
    )

    testing_excerpt = _extract_testing_framework_excerpt()
    testing_excerpt = _truncate(testing_excerpt, max_chars=10_000)

    acceptance_blob = "\n".join([f"- {t}" for t in acceptance_texts[:10]])
    acceptance_blob = _truncate(acceptance_blob, max_chars=6_000)

    task_context_markdown = _truncate(task_context_markdown or "", max_chars=12_000)

    instruction = "\n".join(
        [
            f"Task id: {task_id}",
            f"Task title: {title}",
            "",
            "Task context (from scripts/sc/analyze.py):",
            task_context_markdown or "(missing)",
            "",
            "Repository testing conventions excerpt (docs/testing-framework.md):",
            testing_excerpt or "(missing)",
            "",
            "Acceptance items referencing this file:",
            acceptance_blob or "(none)",
            "",
            "Generate a minimal failing test skeleton aligned to the acceptance intent.",
        ]
    )

    return "\n\n".join([constraints, instruction]).strip() + "\n"


def _is_allowed_test_path(p: str) -> bool:
    s = str(p or "").strip().replace("\\", "/")
    if not s:
        return False
    if os.path.isabs(s) or (len(s) >= 2 and s[1] == ":"):
        return False
    if not (s.endswith(".cs") or s.endswith(".gd")):
        return False
    return s.startswith(ALLOWED_TEST_PREFIXES)


def _select_primary_ref_prompt(*, task_id: str, title: str, candidates: list[dict[str, Any]]) -> str:
    prd_path = repo_root() / "prd.txt"
    prd = _truncate(_read_text(prd_path), max_chars=8_000) if prd_path.exists() else ""
    constraints = "\n".join(
        [
            "You are selecting a single primary acceptance ref to drive a RED-FIRST test.",
            "",
            "Output constraints:",
            "- Output MUST be a single JSON object, no markdown.",
            "- Keys: primary_ref (string), reason (string).",
            "- primary_ref MUST be one of the provided candidate refs.",
            "",
            "Selection rules (in priority order):",
            "- Prefer C# (.cs) refs over .gd when both exist, because the TDD green/refactor workflow runs faster in .NET.",
            "- Prefer refs tied to concrete behavior (events/state transitions/calculations) over meta/process items.",
            "- Prefer smaller scope (one behavior) over broad integration tests.",
        ]
    )
    return "\n\n".join(
        [
            constraints,
            f"Task: {task_id}",
            f"Title: {title}",
            "",
            "PRD excerpt (truncated):",
            prd or "(empty)",
            "",
            "Candidates (each includes acceptance texts that reference it):",
            json.dumps(candidates, ensure_ascii=False, indent=2),
            "",
            "Return JSON now.",
        ]
    ).strip() + "\n"


def _select_primary_ref_with_llm(
    *,
    task_id: str,
    title: str,
    by_ref: dict[str, list[str]],
    timeout_sec: int,
    out_dir: Path,
) -> tuple[str | None, dict[str, Any]]:
    cs = [r for r in sorted(by_ref.keys()) if r.endswith(".cs") and _is_allowed_test_path(r)]
    gd = [r for r in sorted(by_ref.keys()) if r.endswith(".gd") and _is_allowed_test_path(r)]
    candidates = cs if cs else gd
    if not candidates:
        return None, {"status": "skipped", "reason": "no_candidates"}

    payload = [{"ref": r, "acceptance_texts": by_ref.get(r, [])[:8]} for r in candidates[:20]]
    prompt = _select_primary_ref_prompt(task_id=task_id, title=title, candidates=payload)

    prompt_path = out_dir / f"primary-select-prompt-{task_id}.txt"
    last_msg_path = out_dir / f"primary-select-last-{task_id}.txt"
    trace_path = out_dir / f"primary-select-trace-{task_id}.log"
    write_text(prompt_path, prompt)

    rc, trace_out, cmd = _run_codex_exec(prompt=prompt, out_last_message=last_msg_path, timeout_sec=timeout_sec)
    write_text(trace_path, trace_out)
    last_msg = _read_text(last_msg_path) if last_msg_path.exists() else ""

    meta: dict[str, Any] = {
        "rc": rc,
        "cmd": cmd,
        "prompt_path": str(prompt_path),
        "trace_path": str(trace_path),
        "output_path": str(last_msg_path),
        "candidates": candidates,
    }

    if rc != 0 or not last_msg.strip():
        meta["status"] = "fail"
        meta["error"] = "codex exec failed/empty output"
        return candidates[0], meta

    try:
        obj = _extract_json_object(last_msg)
        primary = str(obj.get("primary_ref") or "").strip().replace("\\", "/")
        reason = str(obj.get("reason") or "").strip()
        if primary not in candidates:
            raise ValueError("primary_ref not in candidates")
        meta["status"] = "ok"
        meta["primary_ref"] = primary
        meta["reason"] = reason
        return primary, meta
    except Exception as exc:  # noqa: BLE001
        meta["status"] = "fail"
        meta["error"] = str(exc)
        return candidates[0], meta


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate missing tests from acceptance Refs using Codex.")
    ap.add_argument("--task-id", required=True, help="Task id (master id, e.g. 11).")
    ap.add_argument("--timeout-sec", type=int, default=600, help="Per-file codex exec timeout (seconds).")
    ap.add_argument("--select-timeout-sec", type=int, default=120, help="LLM primary-ref selection timeout (seconds).")
    ap.add_argument("--tdd-stage", choices=["normal", "red-first"], default="normal")
    ap.add_argument("--verify", choices=["none", "unit", "all", "auto"], default="auto")
    ap.add_argument("--godot-bin", default=None, help="Required when verify=all/auto and .gd files are involved.")
    args = ap.parse_args()

    task_id = str(args.task_id).split(".", 1)[0].strip()
    if not task_id.isdigit():
        print("SC_LLM_ACCEPTANCE_TESTS ERROR: --task-id must be a numeric master id.")
        return 2

    out_dir = ci_dir("sc-llm-acceptance-tests")

    # Hard gate: acceptance refs must be present (syntax-level) before generating.
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
        print(f"SC_LLM_ACCEPTANCE_TESTS ERROR: acceptance refs gate failed rc={gate_rc} out={out_dir}")
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
        print(f"SC_LLM_ACCEPTANCE_TESTS ERROR: sc-analyze failed rc={analyze_rc} out={out_dir}")
        return 1

    ctx_path = repo_root() / "logs" / "ci" / out_dir.parent.name / "sc-analyze" / f"task_context.{task_id}.json"
    # If date inference fails for any reason, fall back to the legacy alias.
    if not ctx_path.exists():
        ctx_path = repo_root() / "logs" / "ci" / out_dir.parent.name / "sc-analyze" / "task_context.json"
    try:
        task_context = json.loads(_read_text(ctx_path) or "{}")
    except Exception:  # noqa: BLE001
        task_context = {}
    if not isinstance(task_context, dict):
        task_context = {}

    task_context_md = str(task_context.get("taskdoc_markdown") or "")
    if not task_context_md:
        taskdoc_path = str(task_context.get("taskdoc_path") or "").strip()
        if taskdoc_path:
            p = Path(taskdoc_path)
            if not p.is_absolute():
                p = repo_root() / p
            if p.exists():
                task_context_md = _read_text(p)

    triplet = resolve_triplet(task_id=task_id)
    title = str(triplet.master.get("title") or "").strip()

    # Governance: allow missing one side, but at least one side must exist.
    if not triplet.back and not triplet.gameplay:
        write_json(out_dir / f"triplet-{task_id}.json", triplet.__dict__)
        print(f"SC_LLM_ACCEPTANCE_TESTS ERROR: task mapping missing in both tasks_back/tasks_gameplay for task_id={task_id}")
        return 1

    back_map = _extract_acceptance_refs((triplet.back or {}).get("acceptance"))
    game_map = _extract_acceptance_refs((triplet.gameplay or {}).get("acceptance"))

    by_ref: dict[str, list[str]] = {}
    for k, v in back_map.items():
        by_ref.setdefault(k, []).extend(v)
    for k, v in game_map.items():
        by_ref.setdefault(k, []).extend(v)

    # De-dup acceptance texts per ref.
    for r, texts in list(by_ref.items()):
        seen = set()
        uniq = []
        for t in texts:
            if t in seen:
                continue
            seen.add(t)
            uniq.append(t)
        by_ref[r] = uniq

    refs = sorted(by_ref.keys())
    results: list[GenResult] = []

    any_gd = False
    created = 0

    primary_ref = None
    if str(args.tdd_stage) == "red-first":
        primary_ref, primary_meta = _select_primary_ref_with_llm(
            task_id=task_id,
            title=title,
            by_ref=by_ref,
            timeout_sec=int(args.select_timeout_sec),
            out_dir=out_dir,
        )
        write_json(out_dir / f"primary-select.{task_id}.json", primary_meta)

    for ref in refs:
        ref_norm = ref.replace("\\", "/")
        disk = repo_root() / ref_norm
        if disk.exists():
            results.append(GenResult(ref=ref_norm, status="skipped", rc=0))
            continue

        if disk.suffix.lower() == ".gd":
            any_gd = True

        if str(args.tdd_stage) == "red-first" and primary_ref and ref_norm == primary_ref:
            intent = "red"
        elif str(args.tdd_stage) == "red-first":
            intent = "scaffold"
        else:
            intent = "red"

        prompt = _prompt_for_ref(
            task_id=task_id,
            title=title,
            ref=ref_norm,
            acceptance_texts=by_ref.get(ref, []),
            intent=intent,
            task_context_markdown=task_context_md,
        )
        prompt_path = out_dir / f"prompt-{task_id}-{Path(ref_norm).name}.txt"
        write_text(prompt_path, prompt)
        output_path = out_dir / f"codex-last-{task_id}-{Path(ref_norm).name}.txt"
        trace_path = out_dir / f"codex-trace-{task_id}-{Path(ref_norm).name}.log"

        rc, trace_out, _cmd = _run_codex_exec(prompt=prompt, out_last_message=output_path, timeout_sec=int(args.timeout_sec))
        write_text(trace_path, trace_out)
        last_msg = _read_text(output_path) if output_path.exists() else ""
        if rc != 0 or not last_msg.strip():
            results.append(
                GenResult(
                    ref=ref_norm,
                    status="fail",
                    rc=rc,
                    prompt_path=str(prompt_path),
                    trace_path=str(trace_path),
                    output_path=str(output_path),
                    error="codex exec failed/empty output",
                )
            )
            continue

        try:
            obj = _extract_json_object(last_msg)
            fp = str(obj.get("file_path") or "").replace("\\", "/")
            content = str(obj.get("content") or "")
            if fp != ref_norm:
                raise ValueError(f"unexpected file_path: {fp}")
            if not content.strip():
                raise ValueError("empty content")
            disk.parent.mkdir(parents=True, exist_ok=True)
            disk.write_text(content.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
            created += 1
            results.append(
                GenResult(
                    ref=ref_norm,
                    status="ok",
                    rc=0,
                    prompt_path=str(prompt_path),
                    trace_path=str(trace_path),
                    output_path=str(output_path),
                )
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                GenResult(
                    ref=ref_norm,
                    status="fail",
                    rc=1,
                    prompt_path=str(prompt_path),
                    trace_path=str(trace_path),
                    output_path=str(output_path),
                    error=str(exc),
                )
            )

    # Sync test_refs from acceptance refs (task-level union evidence).
    sync_cmd = [
        "py",
        "-3",
        "scripts/python/update_task_test_refs_from_acceptance_refs.py",
        "--task-id",
        task_id,
        "--mode",
        "replace",
        "--write",
    ]
    sync_rc, sync_out = run_cmd(sync_cmd, cwd=repo_root(), timeout_sec=60)
    write_text(out_dir / f"sync-test-refs-{task_id}.log", sync_out)

    # Decide verification mode.
    verify = args.verify
    if verify == "auto":
        verify = "all" if any_gd else "unit"

    test_step = None
    if verify != "none":
        if verify == "all":
            godot_bin = args.godot_bin or os.environ.get("GODOT_BIN")
            if not godot_bin:
                write_text(out_dir / f"verify-{task_id}.log", "ERROR: verify=all requires --godot-bin or env GODOT_BIN\n")
                test_step = {"status": "fail", "rc": 2, "error": "missing_godot_bin"}
            else:
                cmd = ["py", "-3", "scripts/sc/test.py", "--type", "all", "--godot-bin", str(godot_bin)]
                rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=1_800)
                write_text(out_dir / f"verify-{task_id}.log", out)
                test_step = {"status": "ok" if rc == 0 else "fail", "rc": rc, "cmd": cmd}
        else:
            cmd = ["py", "-3", "scripts/sc/test.py", "--type", "unit"]
            rc, out = run_cmd(cmd, cwd=repo_root(), timeout_sec=1_800)
            write_text(out_dir / f"verify-{task_id}.log", out)
            test_step = {"status": "ok" if rc == 0 else "fail", "rc": rc, "cmd": cmd}

    summary = {
        "cmd": "sc-llm-generate-tests-from-acceptance-refs",
        "task_id": task_id,
        "title": title,
        "tdd_stage": str(args.tdd_stage),
        "primary_ref": primary_ref,
        "refs_total": len(refs),
        "created": created,
        "sync_test_refs_rc": sync_rc,
        "verify_mode": verify,
        "test_step": test_step,
        "results": [r.__dict__ for r in results],
        "out_dir": str(out_dir),
    }
    write_json(out_dir / f"summary-{task_id}.json", summary)

    if str(args.tdd_stage) == "red-first" and verify != "none" and test_step:
        # In red-first mode, failing tests can be expected. Only hard-fail if generation failed
        # or if verification shows compilation errors.
        gen_fail = any(r.status == "fail" for r in results) or sync_rc != 0
        verify_out = _read_text(out_dir / f"verify-{task_id}.log") if (out_dir / f"verify-{task_id}.log").is_file() else ""
        compilation_error = ("error CS" in verify_out) or ("Build FAILED" in verify_out)
        hard_fail = gen_fail or compilation_error
        print(f"SC_LLM_ACCEPTANCE_TESTS status={'fail' if hard_fail else 'ok'} created={created} out={out_dir}")
        return 1 if hard_fail else 0

    hard_fail = any(r.status == "fail" for r in results) or sync_rc != 0 or (test_step and test_step.get("rc") not in (None, 0))
    print(f"SC_LLM_ACCEPTANCE_TESTS status={'fail' if hard_fail else 'ok'} created={created} out={out_dir}")
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
