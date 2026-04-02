#!/usr/bin/env python3
"""
Compatibility shim for legacy obligations freeze imports.

Use `_obligations_freeze_runtime.py` and `_obligations_freeze_pipeline_steps.py`
for new code. This module stays only to keep older local references import-safe.
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
from typing import Any

from _obligations_freeze_pipeline_steps import parse_eval_aggregate, run_step, write_pipeline_summary
from _obligations_freeze_runtime import known_delivery_profile_choices, resolve_repo_path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def parse_args() -> argparse.Namespace:
    today = today_str()
    parser = argparse.ArgumentParser(description="Run obligations freeze orchestration pipeline.")

    parser.add_argument("--out-dir", default=f"logs/ci/{today}/sc-obligations-freeze-pipeline", help="Pipeline artifact directory.")
    parser.add_argument("--skip-jitter", action="store_true", help="Skip jitter batch step and reuse an existing --raw file.")
    parser.add_argument("--raw", default="", help="Raw jitter JSON. Required when --skip-jitter is used.")
    parser.add_argument("--task-ids", default="")
    parser.add_argument(
        "--tasks-file",
        default="",
        help="Tasks JSON path. Empty means resolve default taskmaster/tasks or examples/taskmaster/tasks at runtime.",
    )
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--start-group", type=int, default=1)
    parser.add_argument("--end-group", type=int, default=0)
    parser.add_argument("--timeout-sec", type=int, default=420)
    parser.add_argument("--round-id-prefix", default="jitter")
    parser.add_argument(
        "--delivery-profile",
        default=None,
        choices=known_delivery_profile_choices(),
        help="Delivery profile forwarded to jitter/extract steps.",
    )
    parser.add_argument("--security-profile", default="", choices=("", "strict", "host-safe"))
    parser.add_argument("--consensus-runs", type=int, default=1)
    parser.add_argument("--min-obligations", type=int, default=0)
    parser.add_argument("--garbled-gate", default="on", choices=("on", "off"))
    parser.add_argument("--auto-escalate", default="on", choices=("on", "off"))
    parser.add_argument("--escalate-max-runs", type=int, default=3)
    parser.add_argument("--max-schema-errors", type=int, default=5)
    parser.add_argument("--reuse-last-ok", action="store_true")
    parser.add_argument("--explain-reuse-miss", action="store_true")
    parser.add_argument("--override-rerun", default="", help="Optional rerun rows JSON for refresh step.")
    parser.add_argument("--draft-json", default="", help="Whitelist draft output path. Default: <out-dir>/obligations-freeze-whitelist.draft.json")
    parser.add_argument("--draft-md", default="", help="Whitelist draft report path. Default: <out-dir>/obligations-freeze-whitelist-draft.md")
    parser.add_argument("--eval-dir", default="", help="Evaluation output directory. Default: <out-dir>/freeze-eval")
    parser.add_argument("--allow-draft-eval", dest="allow_draft_eval", action="store_true", default=True, help="Allow evaluating draft whitelist in evaluate step (default: enabled).")
    parser.add_argument("--no-allow-draft-eval", dest="allow_draft_eval", action="store_false", help="Disable --allow-draft and require non-draft whitelist for evaluate step.")
    parser.add_argument("--require-judgable", action="store_true", help="Fail pipeline if evaluation aggregate.judgable is false.")
    parser.add_argument("--require-freeze-pass", action="store_true", help="Fail pipeline if evaluation aggregate.freeze_gate_pass is false.")
    parser.add_argument("--approve-promote", action="store_true", help="Allow promotion step. Disabled by default as stop-loss.")
    parser.add_argument("--baseline-dir", default=".taskmaster/docs/obligations-freeze-baselines")
    parser.add_argument("--baseline-date", default=today)
    parser.add_argument("--baseline-tag", default="")
    parser.add_argument("--current-baseline", default=".taskmaster/docs/obligations-freeze-whitelist.baseline.current.json")
    parser.add_argument("--promote-report", default="", help="Promote report path. Default: <out-dir>/obligations-freeze-promote.md")
    parser.add_argument("--jitter-timeout-sec", type=int, default=21600, help="External timeout for jitter batch step.")
    parser.add_argument("--step-timeout-sec", type=int, default=1800, help="External timeout for non-jitter steps.")
    return parser.parse_args()


__all__ = [
    "parse_args",
    "parse_eval_aggregate",
    "repo_root",
    "resolve_repo_path",
    "run_step",
    "today_str",
    "write_pipeline_summary",
]
