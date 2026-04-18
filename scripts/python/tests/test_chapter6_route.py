#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


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


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


chapter6_route = _load_module("chapter6_route_module", "scripts/python/chapter6_route.py")


class Chapter6RouteTests(unittest.TestCase):
    def _build_run_68_route_payload(self) -> dict[str, object]:
        return {
            "task_id": "15",
            "run_id": "run-15",
            "preferred_lane": "run-6.8",
            "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15",
            "forbidden_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15"],
            "reviewer_anchor_hit": True,
            "changed_paths": ["docs/architecture/overlays/PRD-1/08/overview.md"],
            "six_eight_worthwhile": True,
            "full_67_recommended": False,
            "repo_noise_classification": "task-issue",
            "repo_noise_reason": "",
            "recommended_action": "needs-fix-fast",
            "recommended_action_why": "",
            "latest_reason": "rerun_blocked:repeat_review_needs_fix",
            "chapter6_next_action": "needs-fix-fast",
            "blocked_by": "rerun_guard",
            "residual_recording": {
                "eligible": False,
                "reason": "no_low_priority_findings",
                "performed": False,
                "decision_log_path": "",
                "execution_plan_path": "",
            },
        }

    def test_should_route_to_68_when_reviewer_anchor_fix_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            execution_context = root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run" / "execution-context.json"
            _write_json(execution_context, {"git": {"head": "base", "status_short": []}})
            payload = {
                "task_id": "15",
                "run_id": "run-15",
                "recommended_action": "needs-fix-fast",
                "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15",
                "forbidden_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15"],
                "candidate_commands": {
                    "needs_fix_fast": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15",
                    "rerun": "py -3 scripts/sc/run_review_pipeline.py --task-id 15",
                },
                "latest_summary_signals": {"reason": "rerun_blocked:repeat_review_needs_fix"},
                "chapter6_hints": {
                    "next_action": "needs-fix-fast",
                    "can_skip_6_7": True,
                    "can_go_to_6_8": True,
                    "blocked_by": "rerun_guard",
                    "rerun_forbidden": True,
                },
                "inspection": {
                    "failure": {"code": "review-needs-fix", "message": "Needs Fix remains."},
                    "paths": {
                        "latest": "logs/ci/2026-04-10/sc-review-pipeline-task-15/latest.json",
                        "out_dir": "logs/ci/2026-04-10/sc-review-pipeline-task-15-run",
                        "execution_context": "logs/ci/2026-04-10/sc-review-pipeline-task-15-run/execution-context.json",
                    },
                },
            }

            with (
                mock.patch.object(chapter6_route, "build_resume_payload", return_value=(1, payload)),
                mock.patch.object(
                    chapter6_route,
                    "_derive_change_scope",
                    return_value={"changed_paths": ["docs/architecture/overlays/PRD-1/08/overview.md"]},
                ),
            ):
                _, route = chapter6_route.route_chapter6(repo_root=root, task_id="15")

        self.assertEqual("run-6.8", route["preferred_lane"])
        self.assertTrue(route["six_eight_worthwhile"])
        self.assertTrue(route["reviewer_anchor_hit"])
        self.assertFalse(route["full_67_recommended"])

    def test_should_not_recommend_68_without_reviewer_anchor_fix(self) -> None:
        payload = {
            "task_id": "15",
            "run_id": "run-15",
            "recommended_action": "needs-fix-fast",
            "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15",
            "forbidden_commands": ["py -3 scripts/sc/run_review_pipeline.py --task-id 15"],
            "candidate_commands": {
                "inspect": "py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 15",
                "needs_fix_fast": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15",
            },
            "latest_summary_signals": {"reason": "rerun_blocked:repeat_review_needs_fix"},
            "chapter6_hints": {
                "next_action": "needs-fix-fast",
                "can_skip_6_7": True,
                "can_go_to_6_8": True,
                "blocked_by": "rerun_guard",
                "rerun_forbidden": True,
            },
            "inspection": {
                "failure": {"code": "review-needs-fix", "message": "Needs Fix remains."},
                "paths": {"latest": "logs/ci/2026-04-10/sc-review-pipeline-task-15/latest.json"},
            },
        }

        with (
            mock.patch.object(chapter6_route, "build_resume_payload", return_value=(1, payload)),
            mock.patch.object(chapter6_route, "_derive_change_scope", return_value={"changed_paths": ["README.md"]}),
        ):
            _, route = chapter6_route.route_chapter6(repo_root=REPO_ROOT, task_id="15")

        self.assertEqual("inspect-first", route["preferred_lane"])
        self.assertFalse(route["six_eight_worthwhile"])
        self.assertFalse(route["reviewer_anchor_hit"])
        self.assertEqual(
            "py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 15",
            route["recommended_command"],
        )

    def test_should_classify_repo_noise_when_lock_contention_is_detected(self) -> None:
        payload = {
            "task_id": "15",
            "run_id": "run-15",
            "recommended_action": "inspect",
            "recommended_command": "py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 15",
            "forbidden_commands": [],
            "candidate_commands": {},
            "latest_summary_signals": {"reason": "step_failed"},
            "chapter6_hints": {"next_action": "inspect", "blocked_by": "deterministic_failure"},
            "inspection": {
                "failure": {
                    "code": "step-failed",
                    "message": "The process cannot access the file because it is being used by another process.",
                },
                "validation_errors": [],
                "missing_artifacts": [],
                "paths": {"latest": "logs/ci/2026-04-10/sc-review-pipeline-task-15/latest.json"},
            },
        }

        with mock.patch.object(chapter6_route, "build_resume_payload", return_value=(1, payload)):
            _, route = chapter6_route.route_chapter6(repo_root=REPO_ROOT, task_id="15")

        self.assertEqual("repo-noise-stop", route["preferred_lane"])
        self.assertEqual("repo-noise", route["repo_noise_classification"])

    def test_should_classify_repo_noise_from_prior_route_reason(self) -> None:
        payload = {
            "task_id": "15",
            "run_id": "run-15",
            "recommended_action": "inspect",
            "recommended_command": "py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 15",
            "forbidden_commands": [],
            "candidate_commands": {},
            "latest_summary_signals": {"reason": "rerun_blocked:chapter6_route_repo_noise_stop"},
            "chapter6_hints": {"next_action": "inspect", "blocked_by": "recent_failure_summary"},
            "inspection": {
                "failure": {"code": "step-failed", "message": "summary only"},
                "paths": {"latest": "logs/ci/2026-04-10/sc-review-pipeline-task-15/latest.json"},
            },
        }

        with mock.patch.object(chapter6_route, "build_resume_payload", return_value=(1, payload)):
            _, route = chapter6_route.route_chapter6(repo_root=REPO_ROOT, task_id="15")

        self.assertEqual("repo-noise-stop", route["preferred_lane"])
        self.assertEqual(
            "prior chapter6-route already classified this run as repo-noise",
            route["repo_noise_reason"],
        )

    def test_should_classify_repo_noise_from_recent_failure_family(self) -> None:
        payload = {
            "task_id": "15",
            "run_id": "run-15",
            "recommended_action": "inspect",
            "recommended_command": "py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 15",
            "forbidden_commands": [],
            "candidate_commands": {},
            "latest_summary_signals": {"reason": "step_failed:sc-test"},
            "recent_failure_summary": {
                "latest_failure_family": "step-failed:sc-test|The process cannot access the file because it is being used by another process.",
                "same_family_count": 2,
                "stop_full_rerun_recommended": True,
                "recommendation_basis": "same failure family repeated in 2 consecutive recent failed runs",
            },
            "chapter6_hints": {"next_action": "inspect", "blocked_by": "recent_failure_summary"},
            "inspection": {
                "failure": {"code": "step-failed", "message": "summary only"},
                "paths": {"latest": "logs/ci/2026-04-10/sc-review-pipeline-task-15/latest.json"},
            },
        }

        with mock.patch.object(chapter6_route, "build_resume_payload", return_value=(1, payload)):
            _, route = chapter6_route.route_chapter6(repo_root=REPO_ROOT, task_id="15")

        self.assertEqual("repo-noise-stop", route["preferred_lane"])
        self.assertEqual(
            "recent failure family repeats a repo-noise signature",
            route["repo_noise_reason"],
        )

    def test_should_route_to_fix_deterministic_when_latest_failure_is_step_failed(self) -> None:
        payload = {
            "task_id": "15",
            "run_id": "run-15",
            "recommended_action": "inspect",
            "recommended_command": "py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 15",
            "forbidden_commands": [],
            "candidate_commands": {
                "inspect": "py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 15",
                "rerun": "py -3 scripts/sc/run_review_pipeline.py --task-id 15",
            },
            "latest_summary_signals": {"reason": "step_failed:sc-test"},
            "chapter6_hints": {"next_action": "inspect", "blocked_by": "waste_signals"},
            "inspection": {
                "failure": {"code": "step-failed", "message": "sc-test failed before review."},
                "paths": {"latest": "logs/ci/2026-04-10/sc-review-pipeline-task-15/latest.json"},
            },
        }

        with mock.patch.object(chapter6_route, "build_resume_payload", return_value=(1, payload)):
            _, route = chapter6_route.route_chapter6(repo_root=REPO_ROOT, task_id="15")

        self.assertEqual("fix-deterministic", route["preferred_lane"])
        self.assertEqual("task-issue", route["repo_noise_classification"])

    def test_should_require_real_artifacts_before_recommending_full_67(self) -> None:
        payload = {
            "task_id": "15",
            "run_id": "run-15",
            "recommended_action": "rerun",
            "recommended_command": "py -3 scripts/sc/run_review_pipeline.py --task-id 15",
            "forbidden_commands": [],
            "candidate_commands": {
                "inspect": "py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 15",
                "rerun": "py -3 scripts/sc/run_review_pipeline.py --task-id 15",
            },
            "latest_summary_signals": {"reason": "planned_only_incomplete", "artifact_integrity_kind": "planned_only_incomplete"},
            "chapter6_hints": {
                "next_action": "rerun",
                "can_skip_6_7": False,
                "can_go_to_6_8": False,
                "blocked_by": "artifact_integrity",
                "rerun_forbidden": False,
            },
            "inspection": {
                "failure": {"code": "artifact-incomplete", "message": "Latest bundle is planned-only."},
                "paths": {"latest": "logs/ci/2026-04-10/sc-review-pipeline-task-15/latest.json"},
            },
        }

        with mock.patch.object(chapter6_route, "build_resume_payload", return_value=(1, payload)):
            _, route = chapter6_route.route_chapter6(repo_root=REPO_ROOT, task_id="15")

        self.assertEqual("inspect-first", route["preferred_lane"])
        self.assertFalse(route["full_67_recommended"])
        self.assertEqual(
            "py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 15",
            route["recommended_command"],
        )

    def test_should_keep_continue_command_when_preferred_lane_falls_back_to_inspect_first_for_clean_run(self) -> None:
        payload = {
            "task_id": "15",
            "run_id": "run-15",
            "recommended_action": "continue",
            "recommended_command": "n/a",
            "forbidden_commands": [],
            "candidate_commands": {
                "inspect": "py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id 15",
            },
            "latest_summary_signals": {"reason": "pipeline_clean"},
            "chapter6_hints": {
                "next_action": "continue",
                "can_skip_6_7": True,
                "can_go_to_6_8": False,
                "blocked_by": "",
                "rerun_forbidden": False,
            },
            "inspection": {
                "failure": {"code": "ok", "message": ""},
                "paths": {"latest": "logs/ci/2026-04-10/sc-review-pipeline-task-15/latest.json"},
            },
        }

        with (
            mock.patch.object(chapter6_route, "build_resume_payload", return_value=(0, payload)),
            mock.patch.object(chapter6_route, "_derive_change_scope", return_value={"changed_paths": ["docs/architecture/overlays/PRD-1/08/overview.md"]}),
        ):
            _, route = chapter6_route.route_chapter6(repo_root=REPO_ROOT, task_id="15")

        self.assertEqual("inspect-first", route["preferred_lane"])
        self.assertEqual("continue", route["chapter6_next_action"])
        self.assertEqual("n/a", route["recommended_command"])

    def test_should_record_residual_docs_when_only_low_priority_findings_remain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            out_dir = root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run"
            out_dir.mkdir(parents=True, exist_ok=True)
            _write_json(
                out_dir / "agent-review.json",
                {
                    "review_verdict": "needs-fix",
                    "findings": [
                        {
                            "finding_id": "llm-semantic-1",
                            "severity": "medium",
                            "category": "llm-review",
                            "owner_step": "sc-llm-review",
                            "message": "Evidence wording is still too weak.",
                            "suggested_fix": "Tighten the evidence wording.",
                            "commands": [],
                        }
                    ],
                },
            )
            _write_json(
                out_dir / "llm-review-low-priority-findings.json",
                {
                    "item_count": 1,
                    "findings": [
                        {
                            "severity": "P2",
                            "agent": "semantic-equivalence-auditor",
                            "message": "Evidence wording is still too weak.",
                            "source_path": "logs/ci/2026-04-10/sc-review-pipeline-task-15-run/review-semantic-equivalence-auditor.md",
                        }
                    ],
                },
            )
            payload = {
                "task_id": "15",
                "run_id": "run-15",
                "recommended_action": "needs-fix-fast",
                "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15",
                "forbidden_commands": [],
                "candidate_commands": {"needs_fix_fast": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15"},
                "latest_summary_signals": {"reason": "rerun_blocked:repeat_review_needs_fix"},
                "chapter6_hints": {
                    "next_action": "needs-fix-fast",
                    "can_skip_6_7": True,
                    "can_go_to_6_8": True,
                    "blocked_by": "rerun_guard",
                    "rerun_forbidden": True,
                },
                "inspection": {
                    "failure": {"code": "review-needs-fix", "message": "Only low priority findings remain."},
                    "paths": {
                        "latest": "logs/ci/2026-04-10/sc-review-pipeline-task-15/latest.json",
                        "out_dir": "logs/ci/2026-04-10/sc-review-pipeline-task-15-run",
                    },
                },
            }

            with (
                mock.patch.object(chapter6_route, "build_resume_payload", return_value=(1, payload)),
                mock.patch.object(chapter6_route, "_derive_change_scope", return_value={"changed_paths": ["README.md"]}),
            ):
                _, route = chapter6_route.route_chapter6(repo_root=root, task_id="15", record_residual=True)

            record = route["residual_recording"]
            self.assertEqual("record-residual", route["preferred_lane"])
            self.assertTrue(record["eligible"])
            self.assertTrue(record["performed"])
            self.assertTrue((root / record["decision_log_path"]).exists())
            self.assertTrue((root / record["execution_plan_path"]).exists())

    def test_should_not_record_residual_docs_when_high_severity_finding_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            out_dir = root / "logs" / "ci" / "2026-04-10" / "sc-review-pipeline-task-15-run"
            out_dir.mkdir(parents=True, exist_ok=True)
            _write_json(
                out_dir / "agent-review.json",
                {
                    "review_verdict": "block",
                    "findings": [
                        {
                            "finding_id": "artifact-integrity-1",
                            "severity": "high",
                            "category": "artifact-integrity",
                            "owner_step": "producer-pipeline",
                            "message": "Producer bundle is stale.",
                            "suggested_fix": "Regenerate the run.",
                            "commands": [],
                        }
                    ],
                },
            )
            payload = {
                "task_id": "15",
                "run_id": "run-15",
                "recommended_action": "needs-fix-fast",
                "recommended_command": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15",
                "forbidden_commands": [],
                "candidate_commands": {"needs_fix_fast": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 15"},
                "latest_summary_signals": {"reason": "rerun_blocked:repeat_review_needs_fix"},
                "chapter6_hints": {
                    "next_action": "needs-fix-fast",
                    "can_skip_6_7": True,
                    "can_go_to_6_8": True,
                    "blocked_by": "rerun_guard",
                    "rerun_forbidden": True,
                },
                "inspection": {
                    "failure": {"code": "review-needs-fix", "message": "High severity finding remains."},
                    "paths": {
                        "latest": "logs/ci/2026-04-10/sc-review-pipeline-task-15/latest.json",
                        "out_dir": "logs/ci/2026-04-10/sc-review-pipeline-task-15-run",
                    },
                },
            }

            with (
                mock.patch.object(chapter6_route, "build_resume_payload", return_value=(1, payload)),
                mock.patch.object(chapter6_route, "_derive_change_scope", return_value={"changed_paths": ["README.md"]}),
            ):
                _, route = chapter6_route.route_chapter6(repo_root=root, task_id="15", record_residual=True)

            record = route["residual_recording"]
            self.assertFalse(record["eligible"])
            self.assertFalse(record["performed"])
            self.assertFalse((root / "decision-logs").exists())
            self.assertFalse((root / "execution-plans").exists())

    def test_compact_payload_should_match_example_json(self) -> None:
        expected_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-chapter6-route-compact.example.json"
        expected = json.loads(expected_path.read_text(encoding="utf-8"))

        actual = chapter6_route._compact_payload(self._build_run_68_route_payload())

        self.assertEqual(expected, actual)

    def test_main_recommendation_only_json_should_match_example(self) -> None:
        expected_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-chapter6-route-compact.example.json"
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        stdout = io.StringIO()

        with (
            mock.patch.object(chapter6_route, "route_chapter6", return_value=(0, self._build_run_68_route_payload())),
            redirect_stdout(stdout),
        ):
            exit_code = chapter6_route.main(
                [
                    "--task-id",
                    "15",
                    "--recommendation-only",
                    "--recommendation-format",
                    "json",
                ]
            )

        self.assertEqual(0, exit_code)
        self.assertEqual(expected, json.loads(stdout.getvalue()))

    def test_main_recommendation_only_kv_should_match_example(self) -> None:
        expected_path = REPO_ROOT / "docs" / "workflows" / "examples" / "sc-chapter6-route-compact.stdout.example.txt"
        expected = expected_path.read_text(encoding="utf-8")
        stdout = io.StringIO()

        with (
            mock.patch.object(chapter6_route, "route_chapter6", return_value=(0, self._build_run_68_route_payload())),
            redirect_stdout(stdout),
        ):
            exit_code = chapter6_route.main(
                [
                    "--task-id",
                    "15",
                    "--recommendation-only",
                ]
            )

        self.assertEqual(0, exit_code)
        self.assertEqual(expected, stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
