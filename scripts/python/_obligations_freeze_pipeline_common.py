#!/usr/bin/env python3
"""
Shared helpers for the obligations freeze orchestration pipeline.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

def today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")

def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return repo_root() / path


def known_delivery_profile_choices() -> list[str]:
    config_path = repo_root() / "scripts" / "sc" / "config" / "delivery_profiles.json"
    fallback = ["ea-fast", "normal", "rapid-commercial"]
    if not config_path.exists():
        return fallback
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        return fallback
    choices = [str(key).strip() for key in profiles.keys() if str(key).strip()]
    return sorted(set(choices)) or fallback

def parse_args() -> argparse.Namespace:
    today = today_str()
    parser = argparse.ArgumentParser(description="Run obligations freeze orchestration pipeline.")

    parser.add_argument(
        "--out-dir",
        default=f"logs/ci/{today}/sc-obligations-freeze-pipeline",
        help="Pipeline artifact directory.",
    )
    parser.add_argument(
        "--skip-jitter",
        action="store_true",
        help="Skip jitter batch step and reuse an existing --raw file.",
    )
    parser.add_argument(
        "--raw",
        default="",
        help="Raw jitter JSON. Required when --skip-jitter is used.",
    )

    # Pass-through knobs for run_obligations_jitter_batch5x3.py
    parser.add_argument("--task-ids", default="")
    parser.add_argument(
        "--tasks-file",
        default="",
        help="Optional tasks file path. Empty lets downstream runner auto-resolve .taskmaster/tasks/tasks.json then examples/taskmaster/tasks.json.",
    )
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--start-group", type=int, default=1)
    parser.add_argument("--end-group", type=int, default=0)
    parser.add_argument("--timeout-sec", type=int, default=420)
    parser.add_argument("--round-id-prefix", default="jitter")
    parser.add_argument(
        "--delivery-profile",
        default="",
        choices=[""] + known_delivery_profile_choices(),
        help="Optional delivery profile forwarded to jitter/extract steps.",
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

    parser.add_argument(
        "--override-rerun",
        default="",
        help="Optional rerun rows JSON for refresh step.",
    )
    parser.add_argument(
        "--draft-json",
        default="",
        help="Whitelist draft output path. Default: <out-dir>/obligations-freeze-whitelist.draft.json",
    )
    parser.add_argument(
        "--draft-md",
        default="",
        help="Whitelist draft report path. Default: <out-dir>/obligations-freeze-whitelist-draft.md",
    )
    parser.add_argument(
        "--eval-dir",
        default="",
        help="Evaluation output directory. Default: <out-dir>/freeze-eval",
    )
    parser.add_argument(
        "--allow-draft-eval",
        dest="allow_draft_eval",
        action="store_true",
        default=True,
        help="Allow evaluating draft whitelist in evaluate step (default: enabled).",
    )
    parser.add_argument(
        "--no-allow-draft-eval",
        dest="allow_draft_eval",
        action="store_false",
        help="Disable --allow-draft and require non-draft whitelist for evaluate step.",
    )
    parser.add_argument(
        "--require-judgable",
        action="store_true",
        help="Fail pipeline if evaluation aggregate.judgable is false.",
    )
    parser.add_argument(
        "--require-freeze-pass",
        action="store_true",
        help="Fail pipeline if evaluation aggregate.freeze_gate_pass is false.",
    )

    parser.add_argument(
        "--approve-promote",
        action="store_true",
        help="Allow promotion step. Disabled by default as stop-loss.",
    )
    parser.add_argument("--baseline-dir", default=".taskmaster/config/obligations-freeze-baselines")
    parser.add_argument("--baseline-date", default=today)
    parser.add_argument("--baseline-tag", default="")
    parser.add_argument(
        "--current-baseline",
        default=".taskmaster/config/obligations-freeze-whitelist.baseline.current.json",
    )
    parser.add_argument(
        "--promote-report",
        default="",
        help="Promote report path. Default: <out-dir>/obligations-freeze-promote.md",
    )

    parser.add_argument(
        "--jitter-timeout-sec",
        type=int,
        default=21600,
        help="External timeout for jitter batch step.",
    )
    parser.add_argument(
        "--step-timeout-sec",
        type=int,
        default=1800,
        help="External timeout for non-jitter steps.",
    )
    return parser.parse_args()

def run_step(step_name: str, cmd: list[str], out_dir: Path, timeout_sec: int) -> dict[str, Any]:
    log_path = out_dir / f"{step_name}.log"
    process = subprocess.run(
        cmd,
        cwd=str(repo_root()),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_sec,
    )
    cmd_text = " ".join(shlex.quote(token) for token in cmd)
    body = [
        f"$ {cmd_text}",
        "",
        "### stdout",
        process.stdout or "",
        "",
        "### stderr",
        process.stderr or "",
    ]
    log_path.write_text("\n".join(body), encoding="utf-8")
    return {
        "name": step_name,
        "status": "ok" if process.returncode == 0 else "fail",
        "rc": process.returncode,
        "cmd": cmd,
        "log": str(log_path),
    }

def write_pipeline_summary(out_dir: Path, payload: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def parse_eval_aggregate(eval_dir: Path) -> dict[str, Any] | None:
    summary_file = eval_dir / "summary.json"
    if not summary_file.exists():
        return None
    try:
        parsed = json.loads(summary_file.read_text(encoding="utf-8"))
    except Exception:
        return None
    aggregate = parsed.get("aggregate")
    if isinstance(aggregate, dict):
        return aggregate
    return None
