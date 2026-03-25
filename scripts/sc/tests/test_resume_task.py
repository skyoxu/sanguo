#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
SC_DIR = REPO_ROOT / "scripts" / "sc"
for candidate in (PYTHON_DIR, SC_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


resume_task = _load_module("resume_task_test_module", "scripts/python/resume_task.py")

FIXTURE_ROOT = REPO_ROOT / "scripts" / "sc" / "tests" / "fixtures" / "run_replay" / "pipeline_pass"
LATEST_REL = "logs/ci/2026-03-22/sc-review-pipeline-task-7/latest.json"
OUT_DIR_REL = "logs/ci/2026-03-22/sc-review-pipeline-task-7-11111111111111111111111111111111"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


class ResumeTaskTests(unittest.TestCase):
    def test_build_resume_payload_should_use_active_task_sidecar_when_latest_is_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(FIXTURE_ROOT, root, dirs_exist_ok=True)
            active_path = root / "logs" / "ci" / "active-tasks" / "task-7.active.json"
            _write(
                active_path,
                json.dumps(
                    {
                        "task_id": "7",
                        "run_id": "11111111111111111111111111111111",
                        "status": "fail",
                        "recommended_action": "resume",
                        "recommended_action_why": "Fix the failing step and resume.",
                        "paths": {
                            "latest_json": LATEST_REL,
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
            )

            rc, payload = resume_task.build_resume_payload(
                repo_root=root,
                task_id="7",
                latest="",
                run_id="",
            )

        self.assertEqual(0, rc)
        self.assertEqual("7", payload["task_id"])
        self.assertEqual(LATEST_REL, payload["active_task"]["latest_json"])
        self.assertTrue(payload["active_task"]["path"].endswith("task-7.active.json"))

    def test_build_resume_payload_should_collect_matching_recovery_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(FIXTURE_ROOT, root, dirs_exist_ok=True)
            _write(
                root / "execution-plans" / "2026-03-23-task-7.md",
                "\n".join(
                    [
                        "# Task 7 Resume Plan",
                        "",
                        "- Title: task-7-resume-plan",
                        "- Status: active",
                        "- Branch: main",
                        "- Git Head: 1111111",
                        "- Goal: recover task 7",
                        "- Scope: pipeline recovery",
                        "- Current step: inspect latest sidecars",
                        "- Last completed step: none",
                        "- Stop-loss: do not mutate producer artifacts",
                        "- Next action: inspect latest run and decide resume or fork",
                        "- Recovery command: `py -3 scripts/sc/run_review_pipeline.py --task-id 7 --resume`",
                        "- Open questions: none",
                        "- Exit criteria: recovery path is explicit",
                        "- Related ADRs: none yet",
                        "- Related decision logs: `decision-logs/2026-03-23-task-7.md`",
                        "- Related task id(s): `7`",
                        "- Related run id: `11111111111111111111111111111111`",
                        f"- Related latest.json: `{LATEST_REL}`",
                        f"- Related pipeline artifacts: `{OUT_DIR_REL}`",
                        "",
                    ]
                ),
            )
            _write(
                root / "decision-logs" / "2026-03-23-task-7.md",
                "\n".join(
                    [
                        "# Task 7 Recovery Decision",
                        "",
                        "- Title: task-7-recovery-decision",
                        "- Date: 2026-03-23",
                        "- Status: accepted",
                        "- Supersedes: none",
                        "- Superseded by: none",
                        "- Branch: main",
                        "- Git Head: 1111111",
                        "- Why now: recovery needs a stable decision record",
                        "- Context: inspect latest sidecars before resuming",
                        "- Decision: prefer sidecar-driven recovery",
                        "- Consequences: task recovery becomes deterministic",
                        "- Recovery impact: agents should inspect before resuming",
                        "- Validation: covered by regression tests",
                        "- Related ADRs: none yet",
                        "- Related execution plans: `execution-plans/2026-03-23-task-7.md`",
                        "- Related task id(s): `7`",
                        "- Related run id: `11111111111111111111111111111111`",
                        f"- Related latest.json: `{LATEST_REL}`",
                        f"- Related pipeline artifacts: `{OUT_DIR_REL}`",
                        "",
                    ]
                ),
            )

            rc, payload = resume_task.build_resume_payload(
                repo_root=root,
                task_id="7",
                latest=LATEST_REL,
                run_id="",
            )

        self.assertEqual(0, rc)
        self.assertEqual("7", payload["task_id"])
        self.assertEqual("none", payload["recommended_action"])
        self.assertEqual("inspection", payload["decision_basis"])
        self.assertIn("failure.code=ok", payload["blocking_signals"])
        self.assertIn("no follow-up action is required", payload["recommended_action_why"])
        self.assertEqual("ok", payload["inspection"]["status"])
        self.assertEqual(["execution-plans/2026-03-23-task-7.md"], payload["related_execution_plans"])
        self.assertEqual(["decision-logs/2026-03-23-task-7.md"], payload["related_decision_logs"])
        self.assertEqual("py -3 scripts/sc/run_review_pipeline.py --task-id 7 --resume", payload["candidate_commands"]["resume"])

    def test_build_resume_payload_should_prefer_agent_review_reason_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(FIXTURE_ROOT, root, dirs_exist_ok=True)
            agent_review_path = root / OUT_DIR_REL / "agent-review.json"
            _write(
                agent_review_path,
                json.dumps(
                    {
                        "review_verdict": "block",
                        "recommended_action": "fork",
                        "findings": [
                            {
                                "finding_id": "artifact-integrity",
                                "severity": "high",
                                "category": "artifact-integrity",
                                "owner_step": "producer-pipeline",
                            }
                        ],
                        "explain": {
                            "recommended_action": "fork",
                            "summary": "Recommended fork because integrity findings make the current producer artifacts unreliable.",
                            "reasons": ["agent_review_high_severity_fork_category(artifact-integrity)"],
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
            )

            rc, payload = resume_task.build_resume_payload(
                repo_root=root,
                task_id="7",
                latest=LATEST_REL,
                run_id="",
            )

        self.assertEqual(0, rc)
        self.assertEqual("fork", payload["recommended_action"])
        self.assertEqual("agent-review", payload["decision_basis"])
        self.assertIn("agent_review.recommended_action=fork", payload["blocking_signals"])
        self.assertIn(
            "agent_review.reason=agent_review_high_severity_fork_category(artifact-integrity)",
            payload["blocking_signals"],
        )
        self.assertIn("integrity findings make the current producer artifacts unreliable", payload["recommended_action_why"])

    def test_main_should_write_resume_summary_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(FIXTURE_ROOT, root, dirs_exist_ok=True)
            out_json = root / "logs" / "ci" / "2026-03-23" / "task-resume" / "task-7-resume-summary.json"
            out_md = root / "logs" / "ci" / "2026-03-23" / "task-resume" / "task-7-resume-summary.md"

            rc = resume_task.main(
                [
                    "--repo-root",
                    str(root),
                    "--task-id",
                    "7",
                    "--latest",
                    LATEST_REL,
                    "--out-json",
                    str(out_json),
                    "--out-md",
                    str(out_md),
                ]
            )

            self.assertEqual(0, rc)
            self.assertTrue(out_json.exists())
            self.assertTrue(out_md.exists())
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual("7", payload["task_id"])
            self.assertEqual("ok", payload["inspection"]["status"])
            self.assertIn("Recommended action", out_md.read_text(encoding="utf-8"))
            self.assertIn("Decision basis", out_md.read_text(encoding="utf-8"))
            self.assertIn("Blocking signals", out_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
