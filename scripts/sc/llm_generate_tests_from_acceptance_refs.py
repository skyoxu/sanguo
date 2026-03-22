#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate missing tests from acceptance refs and verify them."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

def _bootstrap_imports() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

_bootstrap_imports()

import _acceptance_testgen_flow as _flow_helpers  # noqa: E402
import _acceptance_testgen_llm as _llm_helpers  # noqa: E402
import _acceptance_testgen_quality as _quality_helpers  # noqa: E402
import _acceptance_testgen_red as _red_helpers  # noqa: E402
import _acceptance_testgen_refs as _refs_helpers  # noqa: E402
from _taskmaster import resolve_triplet  # noqa: E402
from _util import ci_dir, repo_root, run_cmd, write_json, write_text  # noqa: E402
@dataclass(frozen=True)
class GenResult:
    ref: str
    status: str
    rc: int | None = None
    prompt_path: str | None = None
    trace_path: str | None = None
    output_path: str | None = None
    error: str | None = None
def _read_text(path: Path) -> str:
    return _refs_helpers.read_text(path)


def _truncate(text: str, *, max_chars: int) -> str:
    return _refs_helpers.truncate(text, max_chars=max_chars)
def _extract_testing_framework_excerpt() -> str:
    return _refs_helpers.extract_testing_framework_excerpt(repo_root_fn=repo_root, read_text_fn=_read_text)


def _extract_acceptance_refs_with_anchors(*, acceptance, task_id: str):
    return _refs_helpers.extract_acceptance_refs_with_anchors(acceptance=acceptance, task_id=task_id)


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
            errors="replace",
            cwd=str(repo_root()),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return 124, "codex exec timeout\n", cmd
    except Exception as exc:
        return 1, f"codex exec failed to start: {exc}\n", cmd
    return proc.returncode or 0, proc.stdout or "", cmd


def _extract_json_object(text: str):
    return _llm_helpers.extract_json_object(text)


def _artifact_token_for_ref(ref: str) -> str:
    return _refs_helpers.artifact_token_for_ref(ref)


def _validate_anchor_binding(*, ref: str, content: str, required_anchors: list[str]):
    return _refs_helpers.validate_anchor_binding(ref=ref, content=content, required_anchors=required_anchors)


def _validate_generated_test_content(*, ref: str, content: str):
    return _quality_helpers.validate_generated_test_content(ref=ref, content=content)


def _evaluate_red_verification(*, out_dir: Path, verify_mode: str, test_step, verify_log_text: str):
    return _red_helpers.evaluate_red_verification(
        repo_root=repo_root(),
        out_dir=out_dir,
        verify_mode=verify_mode,
        test_step=test_step,
        verify_log_text=verify_log_text,
    )


def _load_optional_prd_excerpt(*, include_prd_context: bool, prd_context_path: str) -> str:
    return _refs_helpers.load_optional_prd_excerpt(
        include_prd_context=include_prd_context,
        prd_context_path=prd_context_path,
        repo_root_fn=repo_root,
        read_text_fn=_read_text,
        truncate_fn=lambda text: _truncate(text, max_chars=8_000),
    )


def _prompt_for_ref(
    *,
    task_id: str,
    title: str,
    ref: str,
    acceptance_texts: list[str],
    required_anchors: list[str],
    intent: str,
    task_context_markdown: str,
) -> str:
    return _llm_helpers.build_prompt_for_ref(
        task_id=task_id,
        title=title,
        ref=ref,
        acceptance_texts=acceptance_texts,
        required_anchors=required_anchors,
        intent=intent,
        task_context_markdown=task_context_markdown,
        testing_framework_excerpt=_extract_testing_framework_excerpt(),
        truncate_fn=lambda text, limit: _truncate(text, max_chars=limit),
    )


def _is_allowed_test_path(path_text: str) -> bool:
    return _refs_helpers.is_allowed_test_path(path_text)


def _select_primary_ref_prompt(*, task_id: str, title: str, candidates, context_excerpt: str) -> str:
    return _llm_helpers.build_select_primary_ref_prompt(
        task_id=task_id,
        title=title,
        candidates=candidates,
        context_excerpt=context_excerpt,
    )


def _select_primary_ref_with_llm(*, task_id: str, title: str, by_ref, context_excerpt: str, timeout_sec: int, out_dir: Path):
    return _llm_helpers.select_primary_ref_with_llm(
        task_id=task_id,
        title=title,
        by_ref=by_ref,
        context_excerpt=context_excerpt,
        timeout_sec=timeout_sec,
        out_dir=out_dir,
        is_allowed_test_path_fn=_is_allowed_test_path,
        build_prompt_fn=_select_primary_ref_prompt,
        run_codex_exec_fn=_run_codex_exec,
        read_text_fn=_read_text,
        write_text_fn=write_text,
    )


def _generate_missing_files(*, refs: list[str], by_ref, task_id: str, title: str, args, task_context_md: str, out_dir: Path):
    results: list[GenResult] = []
    created = 0
    any_gd = any(Path(ref).suffix.lower() == ".gd" for ref in refs)
    primary_ref = None
    context_excerpt = _load_optional_prd_excerpt(
        include_prd_context=bool(args.include_prd_context),
        prd_context_path=str(args.prd_context_path),
    )
    if str(args.tdd_stage) == "red-first":
        primary_ref, primary_meta = _select_primary_ref_with_llm(
            task_id=task_id,
            title=title,
            by_ref={ref: [item.get("text", "") for item in entries] for ref, entries in by_ref.items()},
            context_excerpt=context_excerpt,
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
        intent = "red" if str(args.tdd_stage) == "red-first" else "scaffold"
        required_anchors = sorted({item.get("anchor", "") for item in by_ref.get(ref, []) if str(item.get("anchor", "")).strip()})
        prompt = _prompt_for_ref(
            task_id=task_id,
            title=title,
            ref=ref_norm,
            acceptance_texts=[item.get("text", "") for item in by_ref.get(ref, [])],
            required_anchors=required_anchors,
            intent=intent,
            task_context_markdown=task_context_md,
        )
        token = _artifact_token_for_ref(ref_norm)
        prompt_path = out_dir / f"prompt-{task_id}-{token}.txt"
        output_path = out_dir / f"codex-last-{task_id}-{token}.txt"
        trace_path = out_dir / f"codex-trace-{task_id}-{token}.log"
        write_text(prompt_path, prompt)
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
            file_path = str(obj.get("file_path") or "").replace("\\", "/")
            content = str(obj.get("content") or "")
            if file_path != ref_norm:
                raise ValueError(f"unexpected file_path: {file_path}")
            if not content.strip():
                raise ValueError("empty content")
            valid_content, quality_errors = _validate_generated_test_content(ref=ref_norm, content=content)
            if not valid_content:
                raise ValueError("; ".join(quality_errors))
            ok, anchor_error = _validate_anchor_binding(ref=ref_norm, content=content, required_anchors=required_anchors)
            if not ok:
                raise ValueError(anchor_error or "anchor binding validation failed")
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
        except Exception as exc:
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
    return results, created, any_gd, primary_ref


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate missing tests from acceptance Refs using Codex.")
    ap.add_argument("--task-id", required=True, help="Task id (master id, e.g. 11).")
    ap.add_argument("--timeout-sec", type=int, default=600, help="Per-file codex exec timeout (seconds).")
    ap.add_argument("--select-timeout-sec", type=int, default=120, help="LLM primary-ref selection timeout (seconds).")
    ap.add_argument("--tdd-stage", choices=["normal", "red-first"], default="normal")
    ap.add_argument("--verify", choices=["none", "unit", "all", "auto"], default="auto")
    ap.add_argument("--godot-bin", default=None, help="Required when verify=all/auto and .gd files are involved.")
    ap.add_argument("--include-prd-context", action="store_true", help="Include PRD excerpt in primary-ref selection prompt.")
    ap.add_argument("--prd-context-path", default=".taskmaster/docs/prd.txt", help="Repo-relative PRD path.")
    args = ap.parse_args()

    task_id = str(args.task_id).split(".", 1)[0].strip()
    if not task_id.isdigit():
        print("SC_LLM_ACCEPTANCE_TESTS ERROR: --task-id must be a numeric master id.")
        return 2

    out_dir = ci_dir("sc-llm-acceptance-tests")
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
    gate_json_path = out_dir / f"acceptance-refs.{task_id}.json"
    write_text(out_dir / f"acceptance-refs.{task_id}.log", gate_out)
    if gate_rc != 0:
        proceed_with_warning = False
        try:
            gate_obj = json.loads(_read_text(gate_json_path)) if gate_json_path.exists() else {}
            errs = gate_obj.get("errors") if isinstance(gate_obj, dict) else None
            proceed_with_warning = isinstance(errs, list) and bool(errs) and all("not an allowed test path" in str(err or "") for err in errs)
        except Exception:
            proceed_with_warning = False
        if not proceed_with_warning:
            print(f"SC_LLM_ACCEPTANCE_TESTS ERROR: acceptance refs gate failed rc={gate_rc} out={out_dir}")
            return 1
        print("SC_LLM_ACCEPTANCE_TESTS WARN: acceptance refs include non-test paths; continuing with test-path subset only.")

    analyze_cmd = ["py", "-3", "scripts/sc/analyze.py", "--task-id", task_id, "--focus", "all", "--depth", "quick", "--format", "json"]
    analyze_rc, analyze_out = run_cmd(analyze_cmd, cwd=repo_root(), timeout_sec=900)
    write_text(out_dir / f"analyze-{task_id}.log", analyze_out)
    if analyze_rc != 0:
        print("SC_LLM_ACCEPTANCE_TESTS WARN: sc-analyze returned non-zero; attempting to continue with available task_context artifacts.")

    task_context = _flow_helpers.load_task_context(
        task_id=task_id,
        out_dir=out_dir,
        repo_root_fn=repo_root,
        read_text_fn=_read_text,
    )
    task_context_md = str(task_context.get("taskdoc_markdown") or "")
    if not task_context_md:
        taskdoc_path = str(task_context.get("taskdoc_path") or "").strip()
        if taskdoc_path:
            taskdoc = Path(taskdoc_path)
            if not taskdoc.is_absolute():
                taskdoc = repo_root() / taskdoc_path
            if taskdoc.exists():
                task_context_md = _read_text(taskdoc)

    triplet = resolve_triplet(task_id=task_id)
    title = str(triplet.master.get("title") or "").strip()
    if not triplet.back and not triplet.gameplay:
        write_json(out_dir / f"triplet-{task_id}.json", triplet.__dict__)
        print(f"SC_LLM_ACCEPTANCE_TESTS ERROR: task mapping missing in both tasks_back/tasks_gameplay for task_id={task_id}")
        return 1

    by_ref, refs, _skipped = _flow_helpers.collect_refs(
        task_id=task_id,
        triplet=triplet,
        out_dir=out_dir,
        extract_acceptance_refs_with_anchors_fn=_extract_acceptance_refs_with_anchors,
        is_allowed_test_path_fn=_is_allowed_test_path,
        write_json_fn=write_json,
    )
    if not refs:
        print(f"SC_LLM_ACCEPTANCE_TESTS ERROR: no allowed test refs found for task_id={task_id}.")
        return 1

    results, created, any_gd, primary_ref = _generate_missing_files(
        refs=refs,
        by_ref=by_ref,
        task_id=task_id,
        title=title,
        args=args,
        task_context_md=task_context_md,
        out_dir=out_dir,
    )
    sync_cmd = ["py", "-3", "scripts/python/update_task_test_refs_from_acceptance_refs.py", "--task-id", task_id, "--mode", "replace", "--write"]
    sync_rc, sync_out = run_cmd(sync_cmd, cwd=repo_root(), timeout_sec=60)
    write_text(out_dir / f"sync-test-refs-{task_id}.log", sync_out)
    require_strict_red = str(args.tdd_stage) == "red-first" and created > 0
    effective_verify = str(args.verify)
    if require_strict_red:
        effective_verify = "all" if any_gd else "unit"
    verify_mode, test_step = _flow_helpers.run_verify(
        verify=effective_verify,
        task_id=task_id,
        any_gd=any_gd,
        godot_bin=args.godot_bin,
        out_dir=out_dir,
        strict_red=require_strict_red,
        run_cmd_fn=run_cmd,
        repo_root_fn=repo_root,
        write_text_fn=write_text,
    )

    summary = {
        "cmd": "sc-llm-generate-tests-from-acceptance-refs",
        "task_id": task_id,
        "title": title,
        "tdd_stage": str(args.tdd_stage),
        "primary_ref": primary_ref,
        "refs_total": len(refs),
        "created": created,
        "sync_test_refs_rc": sync_rc,
        "verify_mode": verify_mode,
        "test_step": test_step,
        "results": [result.__dict__ for result in results],
        "out_dir": str(out_dir),
    }

    if require_strict_red:
        verify_log = out_dir / f"verify-{task_id}.log"
        verify_out = _read_text(verify_log) if verify_log.is_file() else ""
        red_verify = _evaluate_red_verification(
            out_dir=out_dir,
            verify_mode=verify_mode,
            test_step=test_step,
            verify_log_text=verify_out,
        )
        summary["red_verify"] = red_verify
    write_json(out_dir / f"summary-{task_id}.json", summary)

    if require_strict_red:
        gen_fail = any(result.status == "fail" for result in results) or sync_rc != 0
        red_verify = summary.get("red_verify") if isinstance(summary.get("red_verify"), dict) else {}
        hard_fail = gen_fail or str(red_verify.get("status")) != "ok"
        print(f"SC_LLM_ACCEPTANCE_TESTS status={'fail' if hard_fail else 'ok'} created={created} out={out_dir}")
        return 1 if hard_fail else 0

    hard_fail = any(result.status == "fail" for result in results) or sync_rc != 0 or (test_step and test_step.get("rc") not in (None, 0))
    print(f"SC_LLM_ACCEPTANCE_TESTS status={'fail' if hard_fail else 'ok'} created={created} out={out_dir}")
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
