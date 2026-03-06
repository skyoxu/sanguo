#!/usr/bin/env python3
"""
Helpers for unified task-level entrypoint policy checks in CI pipeline.
"""

from __future__ import annotations

import io
import os
from typing import Callable, Any


RunCmd = Callable[[list[str], str | None, int], tuple[int, str]]
ReadJson = Callable[[str], Any]


def _safe_int(raw, default):
    try:
        return int(str(raw).strip())
    except Exception:
        return int(default)


def resolve_dotnet_stage_timeout_ms(cli_value):
    """
    Resolve outer timeout for run_dotnet stage.
    Priority:
      1) CLI --dotnet-stage-timeout-ms
      2) env CI_DOTNET_STAGE_TIMEOUT_MS
      3) derived default = max(60m, DOTNET_TEST_TIMEOUT_MS + 5m)
    """
    dotnet_test_timeout_ms = max(60_000, _safe_int(os.environ.get("DOTNET_TEST_TIMEOUT_MS", "1800000"), 1_800_000))
    derived_default = max(3_600_000, dotnet_test_timeout_ms + 300_000)

    if cli_value is not None:
        candidate = _safe_int(cli_value, derived_default)
    else:
        env_value = os.environ.get("CI_DOTNET_STAGE_TIMEOUT_MS", "")
        candidate = _safe_int(env_value, derived_default) if str(env_value).strip() else derived_default

    # Clamp to [5m, 3h] to avoid accidental 0/negative and runaway values.
    return max(300_000, min(candidate, 10_800_000))


def run_unified_entrypoint_gates(
    *,
    root: str,
    ci_dir: str,
    date: str,
    run_cmd: RunCmd,
    read_json: ReadJson,
) -> tuple[dict[str, dict[str, Any]], bool]:
    """
    Run:
    1) hard gate: forbid manual sc triplet command examples
    2) soft warning: whitelist expiry horizon
    """
    details: dict[str, dict[str, Any]] = {}
    hard_fail = False

    rc0, out0 = run_cmd(
        [
            "py",
            "-3",
            "scripts/python/forbid_manual_sc_triplet_examples.py",
            "--root",
            ".",
            "--mode",
            "all",
            "--whitelist",
            "docs/workflows/unified-pipeline-command-whitelist.txt",
            "--whitelist-metadata",
            "require",
        ],
        root,
        900_000,
    )
    with io.open(os.path.join(ci_dir, "forbid-manual-sc-triplet-examples.log"), "w", encoding="utf-8") as f:
        f.write(out0)
    manual_sum = read_json(os.path.join("logs", "ci", date, "forbid-manual-sc-triplet-examples.json")) or {}
    details["manual_triplet_examples"] = {
        "rc": rc0,
        "status": "ok" if rc0 == 0 else "fail",
        "hits_count": manual_sum.get("hits_count"),
        "scanned_files": manual_sum.get("scanned_files"),
        "mode": manual_sum.get("mode"),
    }
    if rc0 != 0:
        hard_fail = True

    rcw, outw = run_cmd(
        [
            "py",
            "-3",
            "scripts/python/warn_whitelist_expiry.py",
            "--root",
            ".",
            "--whitelist",
            "docs/workflows/unified-pipeline-command-whitelist.txt",
        ],
        root,
        900_000,
    )
    with io.open(os.path.join(ci_dir, "whitelist-expiry-warning.log"), "w", encoding="utf-8") as f:
        f.write(outw)
    warn_sum = read_json(os.path.join("logs", "ci", date, "whitelist-expiry-warning.json")) or {}
    details["whitelist_expiry_warning"] = {
        "rc": rcw,
        "status": warn_sum.get("status") or ("ok" if rcw == 0 else "warn"),
        "expiring_soon_count": warn_sum.get("expiring_soon_count"),
        "expired_count": warn_sum.get("expired_count"),
        "warn_days": warn_sum.get("warn_days"),
    }

    return details, hard_fail
