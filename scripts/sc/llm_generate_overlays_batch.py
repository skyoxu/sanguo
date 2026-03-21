#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import llm_generate_overlays_from_prd as single_run
from _overlay_generator_batch import (
    build_batch_run_name,
    build_page_run_suffix,
    classify_child_failure,
    default_batch_suffix,
    render_batch_report_markdown,
    resolve_target_pages,
)
from _overlay_generator_support import infer_prd_id, load_task_payloads, normalize_relpath, write_json, write_text
from _util import ci_dir, repo_root


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch-run overlay generation/validation and collect per-page diff summaries.")
    parser.add_argument("--prd", required=True, help="Primary PRD markdown path.")
    parser.add_argument("--prd-id", default="", help="Overlay PRD-ID. If omitted, infer from task overlay refs.")
    parser.add_argument("--prd-docs", default="", help="Additional PRD markdown paths, comma-separated.")
    parser.add_argument("--pages", default="", help="Optional comma-separated overlay filenames. If omitted, derive from --page-family.")
    parser.add_argument(
        "--page-family",
        default="all",
        choices=["all", "core", "contracts", "feature", "governance", "routing"],
        help="Target overlay page family when --pages is omitted.",
    )
    parser.add_argument(
        "--page-mode",
        default="scaffold",
        choices=["scaffold", "patch", "replace"],
        help="Single-page generation mode passed through to the child runner.",
    )
    parser.add_argument("--timeout-sec", type=int, default=1200, help="Per-page child timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Run child generator in dry-run mode.")
    parser.add_argument("--apply", action="store_true", help="Run child generator in apply mode.")
    parser.add_argument("--batch-suffix", default="", help="Optional batch output suffix. If omitted, generate a unique suffix.")
    return parser


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_page_diff(summary: dict[str, object], page: str) -> dict[str, object]:
    for item in summary.get("files") or []:
        if isinstance(item, dict) and str(item.get("filename") or "") == page:
            return item
    return {}


def main() -> int:
    args = _build_parser().parse_args()
    root = repo_root()
    prd_path = Path(args.prd)
    if not prd_path.is_absolute():
        prd_path = (root / prd_path).resolve()
    if not prd_path.exists():
        print(f"SC_LLM_OVERLAY_BATCH status=fail error=prd_not_found path={prd_path}")
        return 2

    tasks_json, tasks_back, tasks_gameplay = load_task_payloads(root)
    prd_id = infer_prd_id(args.prd_id, tasks_json, tasks_back, tasks_gameplay)
    batch_suffix = args.batch_suffix or default_batch_suffix()
    batch_out_dir = ci_dir(build_batch_run_name(prd_id, batch_suffix))
    pages = resolve_target_pages(repo_root=root, prd_id=prd_id, page_family=args.page_family, pages_csv=args.pages)
    if not pages:
        write_json(
            batch_out_dir / "summary.json",
            {"status": "fail", "error": "no_target_pages", "prd_id": prd_id, "page_family": args.page_family, "pages": args.pages},
        )
        print(f"SC_LLM_OVERLAY_BATCH status=fail error=no_target_pages prd_id={prd_id} out={batch_out_dir}")
        return 2

    page_logs_dir = batch_out_dir / "page-logs"
    page_logs_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    failure_count = 0

    for page in pages:
        child_suffix = build_page_run_suffix(batch_suffix, page)
        child_out_dir = ci_dir(single_run._build_output_dir_name(prd_id, child_suffix))
        cmd = [
            "py",
            "-3",
            "scripts/sc/llm_generate_overlays_from_prd.py",
            "--prd",
            str(prd_path),
            "--prd-id",
            prd_id,
            "--prd-docs",
            str(args.prd_docs or ""),
            "--page-filter",
            page,
            "--page-mode",
            args.page_mode,
            "--timeout-sec",
            str(args.timeout_sec),
            "--run-suffix",
            child_suffix,
        ]
        if args.dry_run:
            cmd.append("--dry-run")
        if args.apply:
            cmd.append("--apply")

        proc = subprocess.run(
            cmd,
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        write_text(page_logs_dir / f"{page.replace('/', '_').replace(':', '_')}.log", proc.stdout or "")

        child_summary_path = child_out_dir / "summary.json"
        child_summary = _read_json(child_summary_path) if child_summary_path.exists() else {}
        child_status = str(child_summary.get("status") or ("ok" if proc.returncode == 0 else "fail"))
        failure_info = classify_child_failure(
            rc=proc.returncode,
            child_status=child_status,
            child_summary=child_summary,
        )

        diff_status = ""
        similarity_ratio = None
        diff_summary_path = child_out_dir / "diff-summary.json"
        if diff_summary_path.exists():
            diff_summary = _read_json(diff_summary_path)
            file_entry = _find_page_diff(diff_summary, page)
            diff_status = str(file_entry.get("status") or "")
            similarity_ratio = file_entry.get("similarity_ratio")

        record = {
            "page": page,
            "rc": proc.returncode,
            "child_status": child_status,
            "failure_type": failure_info["failure_type"],
            "child_error": failure_info["child_error"],
            "child_mode": str(child_summary.get("mode") or ("dry-run" if args.dry_run else "simulate")),
            "diff_status": diff_status,
            "similarity_ratio": similarity_ratio,
            "child_out_dir": normalize_relpath(child_out_dir, root=root),
            "child_summary_path": normalize_relpath(child_summary_path, root=root) if child_summary_path.exists() else "",
        }
        if proc.returncode != 0 or child_status != "ok":
            failure_count += 1
        results.append(record)

    summary = {
        "status": "ok" if failure_count == 0 else "fail",
        "prd_id": prd_id,
        "page_count": len(pages),
        "success_count": len(pages) - failure_count,
        "failure_count": failure_count,
        "batch_out_dir": normalize_relpath(batch_out_dir, root=root),
        "results": results,
    }
    write_json(batch_out_dir / "summary.json", summary)
    write_text(batch_out_dir / "report.md", render_batch_report_markdown(summary))
    print(
        "SC_LLM_OVERLAY_BATCH status={status} prd_id={prd_id} pages={pages} out={out}".format(
            status=summary["status"],
            prd_id=prd_id,
            pages=len(pages),
            out=batch_out_dir,
        )
    )
    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
