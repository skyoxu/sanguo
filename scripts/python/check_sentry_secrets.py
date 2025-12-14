#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lightweight, non-blocking check for Sentry-related secrets and upload marker.

Usage (GitHub Actions, Windows + Python):

    - name: Sentry sourcemap env check (soft gate)
      shell: pwsh
      env:
        SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
        SENTRY_ORG: ${{ secrets.SENTRY_ORG }}
        SENTRY_PROJECT: ${{ secrets.SENTRY_PROJECT }}
      run: |
        py -3 scripts/python/check_sentry_secrets.py

The script will:
    - Detect whether SENTRY_AUTH_TOKEN / SENTRY_ORG / SENTRY_PROJECT are present.
    - Read optional SENTRY_UPLOAD_PERFORMED flag (set by future upload step).
    - Print a single summary line and append it to GITHUB_STEP_SUMMARY (if set):
          Sentry: secrets_detected=<true|false> upload_executed=<true|false>

This is a soft gate: exit code is always 0.
"""

from __future__ import annotations

import os
from pathlib import Path


def main() -> None:
    has_token = bool(os.environ.get("SENTRY_AUTH_TOKEN"))
    has_org = bool(os.environ.get("SENTRY_ORG"))
    has_project = bool(os.environ.get("SENTRY_PROJECT"))
    secrets_detected = has_token and has_org and has_project

    # Future upload step can set this environment variable to "1" or "true"
    upload_flag = os.environ.get("SENTRY_UPLOAD_PERFORMED", "").strip().lower()
    upload_executed = upload_flag in {"1", "true", "yes"}

    line = f"Sentry: secrets_detected={str(secrets_detected).lower()} upload_executed={str(upload_executed).lower()}"
    print(line)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        try:
            summary_file = Path(summary_path)
            with summary_file.open("a", encoding="utf-8", errors="ignore") as fh:
                fh.write(line + "\n")
        except OSError:
            # Best-effort: do not fail the job
            pass


if __name__ == "__main__":
    main()
