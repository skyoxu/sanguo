#!/usr/bin/env python3
from __future__ import annotations

import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_TMP_ROOT = REPO_ROOT / "logs" / "test-temp"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


@contextmanager
def repo_temp_dir(name: str):
    root = TEST_TMP_ROOT / f"{name}-{uuid.uuid4().hex}"
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)
