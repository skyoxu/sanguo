#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
sys.path.insert(0, str(SC_DIR))

from _obligations_code_fingerprint import build_runtime_code_fingerprint  # noqa: E402


def _fn_alpha() -> int:
    return 1


def _fn_beta() -> int:
    return 2


class ObligationsCodeFingerprintTests(unittest.TestCase):
    def test_fingerprint_is_stable_with_same_functions(self) -> None:
        fp1, parts1 = build_runtime_code_fingerprint({"a": _fn_alpha, "b": _fn_beta})
        fp2, parts2 = build_runtime_code_fingerprint({"b": _fn_beta, "a": _fn_alpha})
        self.assertEqual(fp1, fp2)
        self.assertEqual(parts1, parts2)

    def test_fingerprint_changes_when_function_source_changes(self) -> None:
        def fn_v1() -> int:
            return 3

        def fn_v2() -> int:
            return 4

        fp1, _ = build_runtime_code_fingerprint({"target": fn_v1})
        fp2, _ = build_runtime_code_fingerprint({"target": fn_v2})
        self.assertNotEqual(fp1, fp2)


if __name__ == "__main__":
    unittest.main()
