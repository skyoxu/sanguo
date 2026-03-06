import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "sc" / "acceptance_check.py"


class AcceptanceCheckCliGuardsTests(unittest.TestCase):
    def _extract_out_dir(self, output: str) -> Path:
        match = re.search(r"\bout=([^\r\n]+)", output or "")
        if not match:
            raise AssertionError(f"Unable to find out=... in output:\n{output}")
        return Path(match.group(1).strip())

    def test_task1_require_headless_should_emit_post_evidence_in_plan(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--task-id",
                "1",
                "--dry-run-plan",
                "--only",
                "tests",
                "--require-headless-e2e",
            ],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        self.assertEqual(0, proc.returncode)
        self.assertIn("SC_ACCEPTANCE_DRY_RUN_PLAN status=ok", proc.stdout or "")

        summary = json.loads((self._extract_out_dir(proc.stdout or "") / "summary.json").read_text(encoding="utf-8"))
        plan = summary.get("step_plan") or []
        post_gate = next(item for item in plan if item.get("name") == "post-evidence-integration")
        self.assertTrue(bool(post_gate.get("enabled")))

    def test_self_check_should_validate_summary_schema(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--self-check"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        self.assertEqual(0, proc.returncode)
        self.assertIn("SC_ACCEPTANCE_SELF_CHECK status=ok", proc.stdout or "")
        out_dir = self._extract_out_dir(proc.stdout or "")
        self.assertTrue((out_dir / "summary.json").exists())
        self.assertFalse((out_dir / "summary.invalid.json").exists())


if __name__ == "__main__":
    unittest.main()
