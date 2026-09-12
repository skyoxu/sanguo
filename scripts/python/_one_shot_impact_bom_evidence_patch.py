from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "9429c69c2d7e27eeb97e1bcb992e841c8ba3a4e7"
AUDIT = ROOT / "scripts/python/audit_impact_index_bom_cleanup.py"
TEST = ROOT / "scripts/python/tests/test_impact_analysis_index.py"
EVIDENCE = ROOT / "logs/ci/sanguo-bom-evidence.json"


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        list(args),
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        timeout=180,
    )
    if check and completed.returncode:
        raise SystemExit(completed.stdout + completed.stderr)
    return completed


def verify_evidence() -> None:
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    run(
        sys.executable,
        str(AUDIT),
        "--baseline",
        BASELINE,
        "--output",
        str(EVIDENCE),
    )
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    summary = {
        "baseline": evidence["baseline"],
        "included_bom_count": evidence["included_bom_count"],
        "cleaned_prefix_only_count": evidence["cleaned_prefix_only_count"],
        "excluded_baseline_match_count": evidence["excluded_baseline_match_count"],
    }
    print(json.dumps(summary, indent=2))
    if evidence["included_bom_count"] != 0:
        raise SystemExit(f"expected zero current included BOM files, got {evidence['included_bom_count']}")
    if evidence["cleaned_prefix_only_count"] != 19:
        raise SystemExit(f"expected 19 Sanguo BOM-only cleanups, got {evidence['cleaned_prefix_only_count']}")


def restore_audit_from_main() -> None:
    completed = subprocess.run(
        ["git", "show", f"origin/main:{AUDIT.relative_to(ROOT).as_posix()}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
        timeout=60,
    )
    if completed.returncode:
        raise SystemExit(completed.stderr.decode("utf-8", errors="replace"))
    AUDIT.write_bytes(completed.stdout)


def patch_test() -> None:
    text = TEST.read_text(encoding="utf-8")
    old = '''                "985f095e4975e7cf1c4477993447c2cfd4f2ed5c",
                "--output",
                str(output),
                cwd=ROOT,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            evidence = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(evidence["status"], "passed")
        self.assertEqual(evidence["included_bom_count"], 0)
        self.assertEqual(evidence["cleaned_prefix_only_count"], 36)
        self.assertEqual(evidence["excluded_baseline_match_count"], 41)
        self.assertNotIn("index_id", evidence)
'''
    new = f'''                "{BASELINE}",
                "--output",
                str(output),
                cwd=ROOT,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            evidence = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(evidence["status"], "passed")
        self.assertEqual(evidence["baseline"], "{BASELINE}")
        self.assertEqual(evidence["included_bom_count"], 0)
        self.assertEqual(evidence["cleaned_prefix_only_count"], 19)
        included_bom_evidence = [item for item in evidence["files"] if item["included"]]
        self.assertEqual(
            sum(1 for item in included_bom_evidence if item["removed_bom_only"]),
            19,
        )
        self.assertNotIn("index_id", evidence)
'''
    if old not in text:
        raise SystemExit("expected upstream BOM readiness block not found")
    TEST.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def main() -> int:
    verify_evidence()
    restore_audit_from_main()
    patch_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
