#!/usr/bin/env python3
"""
Runner for the obligations freeze orchestration pipeline.
"""

from __future__ import annotations

import subprocess
from typing import Any

from _obligations_freeze_pipeline_common import (
    parse_args,
    parse_eval_aggregate,
    repo_root,
    resolve_repo_path,
    run_step,
    today_str,
    write_pipeline_summary,
)


def main() -> int:
    args = parse_args()
    out_dir = resolve_repo_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_path = resolve_repo_path(args.raw) if str(args.raw).strip() else out_dir / "sc-llm-obligations-jitter-batch5x3-raw.json"
    summary_path = out_dir / "sc-llm-obligations-jitter-batch5x3-summary.json"
    summary_report = out_dir / "sc-llm-obligations-jitter-batch5x3-report.md"
    refreshed_summary = out_dir / "sc-llm-obligations-jitter-batch5x3-summary-refreshed.json"
    refreshed_report = out_dir / "sc-llm-obligations-jitter-batch5x3-refreshed-report.md"
    draft_json = resolve_repo_path(args.draft_json) if str(args.draft_json).strip() else out_dir / "obligations-freeze-whitelist.draft.json"
    draft_md = resolve_repo_path(args.draft_md) if str(args.draft_md).strip() else out_dir / "obligations-freeze-whitelist-draft.md"
    eval_dir = resolve_repo_path(args.eval_dir) if str(args.eval_dir).strip() else out_dir / "freeze-eval"
    promote_report = (
        resolve_repo_path(args.promote_report) if str(args.promote_report).strip() else out_dir / "obligations-freeze-promote.md"
    )

    pipeline: dict[str, Any] = {
        "schema_version": "1.0.0",
        "cmd": "run_obligations_freeze_pipeline.py",
        "date": today_str(),
        "status": "ok",
        "out_dir": str(out_dir),
        "steps": [],
        "paths": {
            "raw": str(raw_path),
            "summary": str(summary_path),
            "summary_report": str(summary_report),
            "refreshed_summary": str(refreshed_summary),
            "refreshed_report": str(refreshed_report),
            "draft_json": str(draft_json),
            "draft_md": str(draft_md),
            "eval_dir": str(eval_dir),
            "promote_report": str(promote_report),
        },
    }

    try:
        if not args.skip_jitter:
            cmd = [
                "py",
                "-3",
                "scripts/python/run_obligations_jitter_batch5x3.py",
                "--batch-size",
                str(args.batch_size),
                "--rounds",
                str(args.rounds),
                "--start-group",
                str(args.start_group),
                "--end-group",
                str(args.end_group),
                "--timeout-sec",
                str(args.timeout_sec),
                "--round-id-prefix",
                args.round_id_prefix,
                "--consensus-runs",
                str(args.consensus_runs),
                "--min-obligations",
                str(args.min_obligations),
                "--garbled-gate",
                args.garbled_gate,
                "--auto-escalate",
                args.auto_escalate,
                "--escalate-max-runs",
                str(args.escalate_max_runs),
                "--max-schema-errors",
                str(args.max_schema_errors),
                "--out-raw",
                str(raw_path),
            ]
            if str(args.tasks_file).strip():
                cmd += ["--tasks-file", args.tasks_file]
            if str(args.task_ids).strip():
                cmd += ["--task-ids", args.task_ids]
            if str(getattr(args, "delivery_profile", "")).strip():
                cmd += ["--delivery-profile", str(args.delivery_profile).strip()]
            if str(args.security_profile).strip():
                cmd += ["--security-profile", args.security_profile]
            if bool(args.reuse_last_ok):
                cmd.append("--reuse-last-ok")
            if bool(args.explain_reuse_miss):
                cmd.append("--explain-reuse-miss")
            step = run_step("jitter-batch", cmd, out_dir, timeout_sec=max(60, args.jitter_timeout_sec))
            pipeline["steps"].append(step)
            if step["rc"] != 0:
                pipeline["status"] = "fail"
                write_pipeline_summary(out_dir, pipeline)
                return int(step["rc"])
        elif not raw_path.exists():
            pipeline["status"] = "fail"
            pipeline["error"] = f"missing raw file for --skip-jitter: {raw_path.as_posix()}"
            write_pipeline_summary(out_dir, pipeline)
            print(f"ERROR: {pipeline['error']}")
            return 2

        step = run_step(
            "build-summary",
            [
                "py",
                "-3",
                "scripts/python/build_obligations_jitter_summary.py",
                "--raw",
                str(raw_path),
                "--out-summary",
                str(summary_path),
                "--out-report",
                str(summary_report),
            ],
            out_dir,
            timeout_sec=max(60, args.step_timeout_sec),
        )
        pipeline["steps"].append(step)
        if step["rc"] != 0:
            pipeline["status"] = "fail"
            write_pipeline_summary(out_dir, pipeline)
            return int(step["rc"])

        summary_for_following = summary_path
        if str(args.override_rerun).strip():
            override_rerun = resolve_repo_path(args.override_rerun)
            step = run_step(
                "refresh-summary",
                [
                    "py",
                    "-3",
                    "scripts/python/refresh_obligations_jitter_summary_with_overrides.py",
                    "--base-summary",
                    str(summary_path),
                    "--override-rerun",
                    str(override_rerun),
                    "--out-summary",
                    str(refreshed_summary),
                    "--out-report",
                    str(refreshed_report),
                ],
                out_dir,
                timeout_sec=max(60, args.step_timeout_sec),
            )
            pipeline["steps"].append(step)
            if step["rc"] != 0:
                pipeline["status"] = "fail"
                write_pipeline_summary(out_dir, pipeline)
                return int(step["rc"])
            summary_for_following = refreshed_summary

        step = run_step(
            "generate-draft",
            [
                "py",
                "-3",
                "scripts/python/generate_obligations_freeze_whitelist_draft.py",
                "--summary",
                str(summary_for_following),
                "--out-json",
                str(draft_json),
                "--out-md",
                str(draft_md),
            ],
            out_dir,
            timeout_sec=max(60, args.step_timeout_sec),
        )
        pipeline["steps"].append(step)
        if step["rc"] != 0:
            pipeline["status"] = "fail"
            write_pipeline_summary(out_dir, pipeline)
            return int(step["rc"])

        eval_cmd = [
            "py",
            "-3",
            "scripts/python/evaluate_obligations_freeze_whitelist.py",
            "--whitelist",
            str(draft_json),
            "--summary",
            str(summary_for_following),
            "--out-dir",
            str(eval_dir),
        ]
        if bool(args.allow_draft_eval):
            eval_cmd.append("--allow-draft")
        step = run_step("evaluate", eval_cmd, out_dir, timeout_sec=max(60, args.step_timeout_sec))
        pipeline["steps"].append(step)
        if step["rc"] != 0:
            pipeline["status"] = "fail"
            write_pipeline_summary(out_dir, pipeline)
            return int(step["rc"])

        eval_aggregate = parse_eval_aggregate(eval_dir)
        pipeline["evaluation"] = eval_aggregate
        if bool(args.require_judgable) and (not eval_aggregate or not bool(eval_aggregate.get("judgable"))):
            pipeline["status"] = "fail"
            pipeline["error"] = "evaluation aggregate.judgable is false"
            write_pipeline_summary(out_dir, pipeline)
            print("ERROR: evaluation aggregate.judgable is false")
            return 2
        if bool(args.require_freeze_pass) and (not eval_aggregate or not bool(eval_aggregate.get("freeze_gate_pass"))):
            pipeline["status"] = "fail"
            pipeline["error"] = "evaluation aggregate.freeze_gate_pass is false"
            write_pipeline_summary(out_dir, pipeline)
            print("ERROR: evaluation aggregate.freeze_gate_pass is false")
            return 2

        if bool(args.approve_promote):
            if not str(args.baseline_tag).strip():
                pipeline["status"] = "fail"
                pipeline["error"] = "baseline-tag is required when --approve-promote is used"
                write_pipeline_summary(out_dir, pipeline)
                print("ERROR: baseline-tag is required when --approve-promote is used")
                return 2
            step = run_step(
                "promote",
                [
                    "py",
                    "-3",
                    "scripts/python/promote_obligations_freeze_baseline.py",
                    "--draft",
                    str(draft_json),
                    "--baseline-dir",
                    args.baseline_dir,
                    "--baseline-date",
                    args.baseline_date,
                    "--baseline-tag",
                    args.baseline_tag,
                    "--current",
                    args.current_baseline,
                    "--report",
                    str(promote_report),
                ],
                out_dir,
                timeout_sec=max(60, args.step_timeout_sec),
            )
            pipeline["steps"].append(step)
            if step["rc"] != 0:
                pipeline["status"] = "fail"
                write_pipeline_summary(out_dir, pipeline)
                return int(step["rc"])
        else:
            pipeline["steps"].append(
                {"name": "promote", "status": "skipped", "rc": 0, "reason": "approve_promote_disabled"}
            )

        pipeline["active_summary"] = str(summary_for_following)
        write_pipeline_summary(out_dir, pipeline)
        print(f"OBLIGATIONS_FREEZE_PIPELINE status={pipeline['status']} out={out_dir.as_posix()}")
        return 0
    except subprocess.TimeoutExpired as exc:
        pipeline["status"] = "fail"
        pipeline["error"] = f"step timeout: {exc}"
        write_pipeline_summary(out_dir, pipeline)
        print(f"ERROR: {pipeline['error']}")
        return 124


if __name__ == "__main__":
    raise SystemExit(main())
