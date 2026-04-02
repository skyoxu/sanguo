#!/usr/bin/env python3
"""
Compatibility runner for the legacy obligations freeze pipeline entry.

New code should call `run_obligations_freeze_pipeline.py` directly.
"""

from __future__ import annotations

from run_obligations_freeze_pipeline import main


if __name__ == "__main__":
    raise SystemExit(main())
