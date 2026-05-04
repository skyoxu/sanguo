#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PY_DIR = REPO_ROOT / "scripts" / "python"
if str(PY_DIR) not in sys.path:
    sys.path.insert(0, str(PY_DIR))

import _obligations_freeze_runtime as runtime  # noqa: E402


class ObligationsFreezeRuntimeTests(unittest.TestCase):
    def _write_triplet(self, base_dir: Path) -> None:
        base_dir.mkdir(parents=True, exist_ok=True)
        (base_dir / "tasks.json").write_text(
            "{\"master\":{\"tasks\":[{\"id\":1}]}}\n".encode("utf-8").decode("unicode_escape"),
            encoding="utf-8",
        )
        (base_dir / "tasks_back.json").write_text("[]\n".encode("utf-8").decode("unicode_escape"), encoding="utf-8")
        (base_dir / "tasks_gameplay.json").write_text("[]\n".encode("utf-8").decode("unicode_escape"), encoding="utf-8")

    def test_default_tasks_file_should_fallback_to_examples_triplet(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_triplet(root / "examples" / "taskmaster")
            actual = runtime.default_tasks_file_path(root)
        self.assertEqual(root / "examples" / "taskmaster" / "tasks.json", actual)

    def test_default_tasks_file_should_prefer_real_taskmaster_triplet(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_triplet(root / "examples" / "taskmaster")
            self._write_triplet(root / ".taskmaster" / "tasks")
            actual = runtime.default_tasks_file_path(root)
        self.assertEqual(root / ".taskmaster" / "tasks" / "tasks.json", actual)

    def test_should_resolve_standard_delivery_profile_to_strict_security(self) -> None:
        delivery_profile, security_profile = runtime.resolve_delivery_and_security("standard", None)
        self.assertEqual("standard", delivery_profile)
        self.assertEqual("strict", security_profile)

    def test_should_resolve_fast_ship_as_default_profile(self) -> None:
        delivery_profile, security_profile = runtime.resolve_delivery_and_security(None, None)
        self.assertEqual("fast-ship", delivery_profile)
        self.assertEqual("host-safe", security_profile)

    def test_should_preserve_explicit_security_override(self) -> None:
        delivery_profile, security_profile = runtime.resolve_delivery_and_security("playable-ea", "strict")
        self.assertEqual("playable-ea", delivery_profile)
        self.assertEqual("strict", security_profile)


if __name__ == "__main__":
    unittest.main()
