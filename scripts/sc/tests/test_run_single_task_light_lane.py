#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lane = _load_module("single_task_light_lane_module", "scripts/python/run_single_task_light_lane.py")


def _write_master_tasks(path: Path, tasks: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"master": {"tasks": tasks}}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class RunSingleTaskLightLaneTests(unittest.TestCase):
    def test_derive_route_contract_should_recommend_timeout_backoff_then_rerun(self) -> None:
        route = lane._derive_route_contract(
            {
                "status": "fail",
                "processed_tasks": 2,
                "failed_tasks": 1,
                "failure_category_counts": {"timeout": 1},
            },
            selected=[11, 12],
            delivery_profile="fast-ship",
            align_apply=True,
            fill_refs_after_extract_fail="skip",
            fill_refs_mode="none",
            downstream_on_extract_fail="skip-soft",
            downstream_on_extract_family_fail="auto",
            batch_lane="extract-first",
            wrapper_timeout_sec=None,
            llm_timeout_sec=None,
            root=REPO_ROOT,
        )

        self.assertEqual("timeout-backoff-then-rerun", route["preferred_lane"])
        self.assertEqual("rerun", route["recommended_action"])
        self.assertIn("--resume-failed-task-from first-failed-step", route["recommended_command"])
        self.assertIn("--llm-timeout-sec", route["recommended_command"])
        self.assertEqual(1, len(route["forbidden_commands"]))
        self.assertEqual("", route["blocked_by"])
        self.assertEqual("", route["artifact_integrity"])
        self.assertEqual("no", route["residual_recording"])

    def test_derive_route_contract_should_recommend_retry_soft_steps_only(self) -> None:
        route = lane._derive_route_contract(
            {
                "status": "fail",
                "processed_tasks": 1,
                "failed_tasks": 1,
                "failure_category_counts": {"semantic-needs-fix": 1},
            },
            selected=[11],
            delivery_profile="fast-ship",
            align_apply=True,
            fill_refs_after_extract_fail="skip",
            fill_refs_mode="write-verify",
            downstream_on_extract_fail="continue",
            downstream_on_extract_family_fail="auto",
            batch_lane="standard",
            wrapper_timeout_sec=None,
            llm_timeout_sec=None,
            root=REPO_ROOT,
        )

        self.assertEqual("retry-soft-steps-only", route["preferred_lane"])
        self.assertEqual("rerun", route["recommended_action"])
        self.assertIn("--resume-failed-task-from first-failed-step", route["recommended_command"])
        self.assertEqual([], route["forbidden_commands"])

    def test_derive_route_contract_should_require_inspection_for_preflight_gap(self) -> None:
        route = lane._derive_route_contract(
            {
                "status": "fail",
                "processed_tasks": 1,
                "failed_tasks": 1,
                "failure_category_counts": {"preflight-gap": 1},
            },
            selected=[11],
            delivery_profile="fast-ship",
            align_apply=True,
            fill_refs_after_extract_fail="skip",
            fill_refs_mode="write-verify",
            downstream_on_extract_fail="continue",
            downstream_on_extract_family_fail="auto",
            batch_lane="standard",
            wrapper_timeout_sec=None,
            llm_timeout_sec=None,
            root=REPO_ROOT,
        )

        self.assertEqual("inspect-first", route["preferred_lane"])
        self.assertEqual("inspect", route["recommended_action"])
        self.assertEqual("", route["recommended_command"])
        self.assertEqual([], route["forbidden_commands"])
        self.assertEqual("deterministic_failure", route["blocked_by"])
        self.assertEqual("", route["artifact_integrity"])
        self.assertEqual("no", route["residual_recording"])

    def test_summary_scope_matches_should_fail_when_selected_ids_change(self) -> None:
        scope = lane._build_resume_scope(
            selected=[11, 12],
            delivery_profile="fast-ship",
            align_apply=True,
            fill_refs_after_extract_fail="skip",
            downstream_on_extract_fail="skip-soft",
            downstream_on_extract_family_fail="auto",
            fill_refs_mode="none",
            batch_lane="extract-first",
        )
        self.assertFalse(
            lane._summary_scope_matches(
                {
                    "resume_scope": lane._build_resume_scope(
                        selected=[13],
                        delivery_profile="fast-ship",
                        align_apply=True,
                        fill_refs_after_extract_fail="skip",
                        downstream_on_extract_fail="skip-soft",
                        downstream_on_extract_family_fail="auto",
                        fill_refs_mode="none",
                        batch_lane="extract-first",
                    )
                },
                scope,
            )
        )

    def test_resolve_downstream_on_extract_fail_should_use_skip_soft_for_multi_task_auto(self) -> None:
        self.assertEqual("continue", lane._resolve_downstream_on_extract_fail("auto", selected_count=1))
        self.assertEqual("skip-soft", lane._resolve_downstream_on_extract_fail("auto", selected_count=2))
        self.assertEqual("skip-all", lane._resolve_downstream_on_extract_fail("skip-all", selected_count=9))

    def test_resolve_downstream_on_extract_family_fail_should_apply_auto_family_policies(self) -> None:
        self.assertEqual(
            "skip-all",
            lane._resolve_downstream_on_extract_family_fail("auto", extract_fail_family="timeout"),
        )
        self.assertEqual(
            "skip-all",
            lane._resolve_downstream_on_extract_family_fail(
                "auto",
                extract_fail_family="stdout:sc_llm_obligations_status_fail",
            ),
        )
        self.assertEqual(
            "skip-soft",
            lane._resolve_downstream_on_extract_family_fail(
                "auto",
                extract_fail_family="error:model_output_invalid",
            ),
        )
        self.assertEqual(
            "",
            lane._resolve_downstream_on_extract_family_fail(
                "off",
                extract_fail_family="timeout",
            ),
        )

    def test_steps_should_toggle_align_apply_and_delivery_profile(self) -> None:
        steps_apply = lane._steps(align_apply=True, delivery_profile="fast-ship", llm_timeout_sec=777)
        steps_read_only = lane._steps(align_apply=False, delivery_profile="playable-ea", llm_timeout_sec=None)
        align_apply_cmd = dict(steps_apply)["align"]
        align_read_only_cmd = dict(steps_read_only)["align"]

        self.assertIn("--apply", align_apply_cmd)
        self.assertNotIn("--apply", align_read_only_cmd)
        self.assertIn("--timeout-sec", align_apply_cmd)
        self.assertEqual("777", align_apply_cmd[align_apply_cmd.index("--timeout-sec") + 1])

        for step_name, cmd in steps_read_only[:4]:
            if step_name == "preflight_extract_guard":
                continue
            self.assertIn("--delivery-profile", cmd, msg=step_name)
            idx = cmd.index("--delivery-profile")
            self.assertEqual("playable-ea", cmd[idx + 1], msg=step_name)

    def test_resolve_step_timeout_sec_should_exceed_inner_default_when_auto(self) -> None:
        semantic_timeout = lane._resolve_step_timeout_sec("semantic_gate", delivery_profile="fast-ship", explicit_timeout_sec=None)
        fill_refs_timeout = lane._resolve_step_timeout_sec("fill_refs_write", delivery_profile="fast-ship", explicit_timeout_sec=None)

        self.assertGreaterEqual(semantic_timeout, 600)
        self.assertGreaterEqual(fill_refs_timeout, 420)

    def test_rebuild_counts_should_include_failure_categories(self) -> None:
        summary = {
            "results": [
                {
                    "task_id": 11,
                    "ok": False,
                    "failed_steps": ["extract"],
                    "steps": [{"step": "extract", "rc": 124, "duration_sec": 2.5}],
                },
                {
                    "task_id": 12,
                    "ok": False,
                    "failed_steps": ["coverage"],
                    "steps": [
                        {
                            "step": "coverage",
                            "rc": 1,
                            "duration_sec": 3.25,
                            "inner_summary": {"status": "fail", "uncovered_subtask_ids": ["2"]},
                        }
                    ],
                },
                {
                    "task_id": 13,
                    "ok": False,
                    "failed_steps": ["semantic_gate"],
                    "steps": [
                        {
                            "step": "semantic_gate",
                            "rc": 1,
                            "duration_sec": 4.0,
                            "inner_summary": {
                                "status": "fail",
                                "prompt_trimmed": True,
                                "task_brief_budget": 1800,
                                "prompt_chars": 6200,
                            },
                        }
                    ],
                },
                {
                    "task_id": 14,
                    "ok": False,
                    "failed_steps": ["align"],
                    "steps": [
                        {
                            "step": "align",
                            "rc": 1,
                            "duration_sec": 1.5,
                            "inner_summary": {"status": "fail", "error": "model_output_invalid"},
                        }
                    ],
                },
                {
                    "task_id": 16,
                    "ok": False,
                    "failed_steps": ["extract"],
                    "steps": [
                        {
                            "step": "extract",
                            "rc": 1,
                            "duration_sec": 1.25,
                            "inner_summary": {"status": "fail", "hard_uncovered_count": 3},
                        }
                    ],
                },
                {
                    "task_id": 17,
                    "ok": False,
                    "failed_steps": ["extract"],
                    "steps": [
                        {
                            "step": "extract",
                            "rc": 1,
                            "duration_sec": 1.75,
                            "inner_summary": {"status": "fail", "schema_error_count": 2},
                        }
                    ],
                },
                {
                    "task_id": 18,
                    "ok": False,
                    "failed_steps": ["extract"],
                    "steps": [{"step": "extract", "rc": 1, "duration_sec": 1.0, "stderr_tail": "Model output invalid at line 42"}],
                },
                {
                    "task_id": 19,
                    "ok": False,
                    "failed_steps": ["extract"],
                    "steps": [
                        {
                            "step": "extract",
                            "rc": 1,
                            "duration_sec": 0.75,
                            "inner_summary": {
                                "status": "fail",
                                "error": "model_output_invalid",
                            },
                        }
                    ],
                },
                {
                    "task_id": 20,
                    "ok": False,
                    "failed_steps": ["extract"],
                    "steps": [
                        {
                            "step": "extract",
                            "rc": 1,
                            "duration_sec": 2.0,
                            "stdout_tail": "SC_LLM_OBLIGATIONS status=fail out=C:/buildgame/sanguo/logs/ci/2026-03-28/sc-llm-obligations-task-67",
                        }
                    ],
                },
                {
                    "task_id": 15,
                    "ok": True,
                    "failed_steps": [],
                    "steps": [{"step": "extract", "rc": 0, "duration_sec": 1.5}],
                },
            ]
        }

        lane._rebuild_counts(summary)

        self.assertEqual({"timeout": 1, "coverage-gap": 1, "semantic-needs-fix": 1, "model-fail": 6}, summary["failure_category_counts"])
        self.assertEqual({"timeout": [11], "coverage-gap": [12], "semantic-needs-fix": [13], "model-fail": [14, 16, 17, 18, 19, 20]}, summary["failure_category_task_ids"])
        self.assertEqual({"11": "timeout", "12": "coverage-gap", "13": "semantic-needs-fix", "14": "model-fail", "16": "model-fail", "17": "model-fail", "18": "model-fail", "19": "model-fail", "20": "model-fail"}, summary["failure_category_by_task"])
        self.assertEqual([13], summary["prompt_trimmed_task_ids"])
        self.assertEqual(1, summary["prompt_trimmed_count"])
        self.assertEqual({"timeout": 1, "hard_uncovered": 1, "schema_error": 1, "model_fail": 3}, summary["extract_fail_bucket_counts"])
        self.assertEqual({"timeout": [11], "hard_uncovered": [16], "schema_error": [17], "model_fail": [18, 19, 20]}, summary["extract_fail_bucket_task_ids"])
        self.assertEqual(
            {
                "timeout": 1,
                "hard_uncovered": 1,
                "schema_error": 1,
                "stderr:model output invalid at line <num>": 1,
                "error:model_output_invalid": 1,
                "stdout:sc_llm_obligations status=fail out=<path>": 1,
            },
            summary["extract_fail_signature_counts"],
        )
        self.assertEqual(
            {
                "timeout": [11],
                "hard_uncovered": [16],
                "schema_error": [17],
                "stderr:model output invalid at line <num>": [18],
                "error:model_output_invalid": [19],
                "stdout:sc_llm_obligations status=fail out=<path>": [20],
            },
            summary["extract_fail_signature_task_ids"],
        )
        self.assertEqual(
            {
                "timeout": 1,
                "hard_uncovered": 1,
                "schema_error": 1,
                "stderr:model_output_invalid": 1,
                "error:model_output_invalid": 1,
                "stdout:sc_llm_obligations_status_fail": 1,
            },
            summary["extract_fail_family_counts"],
        )
        self.assertEqual(
            {
                "timeout": [11],
                "hard_uncovered": [16],
                "schema_error": [17],
                "stderr:model_output_invalid": [18],
                "error:model_output_invalid": [19],
                "stdout:sc_llm_obligations_status_fail": [20],
            },
            summary["extract_fail_family_task_ids"],
        )
        self.assertEqual(
            [
                {"signature": "error:model_output_invalid", "count": 1, "task_ids": [19]},
                {"signature": "hard_uncovered", "count": 1, "task_ids": [16]},
                {"signature": "schema_error", "count": 1, "task_ids": [17]},
                {"signature": "stderr:model output invalid at line <num>", "count": 1, "task_ids": [18]},
                {"signature": "stdout:sc_llm_obligations status=fail out=<path>", "count": 1, "task_ids": [20]},
                {"signature": "timeout", "count": 1, "task_ids": [11]},
            ],
            summary["extract_fail_top_signatures"],
        )
        self.assertEqual(
            [
                {"family": "error:model_output_invalid", "count": 1, "task_ids": [19]},
                {"family": "hard_uncovered", "count": 1, "task_ids": [16]},
                {"family": "schema_error", "count": 1, "task_ids": [17]},
                {"family": "stderr:model_output_invalid", "count": 1, "task_ids": [18]},
                {"family": "stdout:sc_llm_obligations_status_fail", "count": 1, "task_ids": [20]},
                {"family": "timeout", "count": 1, "task_ids": [11]},
            ],
            summary["extract_fail_top_families"],
        )
        self.assertEqual(
            [
                {
                    "task_id": 13,
                    "prompt_trimmed": True,
                    "task_brief_budget": 1800,
                    "prompt_chars": 6200,
                }
            ],
            summary["semantic_gate_budget_hits"],
        )
        self.assertEqual({"align": 1.5, "coverage": 3.25, "extract": 10.75, "semantic_gate": 4.0}, summary["step_duration_totals"])
        self.assertEqual({"align": 1.5, "coverage": 3.25, "extract": 1.536, "semantic_gate": 4.0}, summary["step_duration_avg"])
        self.assertEqual({"align": 1, "coverage": 1, "extract": 7, "semantic_gate": 1}, summary["step_duration_task_counts"])
        self.assertEqual(
            [
                {"task_id": 13, "duration_sec": 4.0, "first_failed_step": "", "ok": False},
                {"task_id": 12, "duration_sec": 3.25, "first_failed_step": "", "ok": False},
                {"task_id": 11, "duration_sec": 2.5, "first_failed_step": "", "ok": False},
                {"task_id": 20, "duration_sec": 2.0, "first_failed_step": "", "ok": False},
                {"task_id": 17, "duration_sec": 1.75, "first_failed_step": "", "ok": False},
                {"task_id": 14, "duration_sec": 1.5, "first_failed_step": "", "ok": False},
                {"task_id": 15, "duration_sec": 1.5, "first_failed_step": "", "ok": True},
                {"task_id": 16, "duration_sec": 1.25, "first_failed_step": "", "ok": False},
                {"task_id": 18, "duration_sec": 1.0, "first_failed_step": "", "ok": False},
                {"task_id": 19, "duration_sec": 0.75, "first_failed_step": "", "ok": False},
            ],
            summary["slowest_tasks"],
        )
        self.assertEqual("fix-acceptance-then-rerun-extract", summary["recommended_next_action"])
        self.assertIn("hard uncovered obligations", summary["recommended_next_action_why"])

    def test_taskmaster_tasks_path_should_fallback_to_examples(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            expected = root / "examples" / "taskmaster" / "tasks.json"
            _write_master_tasks(expected, [{"id": 1, "status": "in-progress"}])

            actual = lane._taskmaster_tasks_path(root)

        self.assertEqual(expected, actual)

    def test_select_task_ids_should_prefer_in_progress_when_no_explicit_ids(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tasks_path = root / ".taskmaster" / "tasks" / "tasks.json"
            _write_master_tasks(
                tasks_path,
                [
                    {"id": 1, "status": "done"},
                    {"id": 2, "status": "in-progress"},
                    {"id": 3, "status": "active"},
                    {"id": 4, "status": "working"},
                ],
            )
            args = Namespace(task_ids="", task_id_start=1, task_id_end=0, max_tasks=0)

            selected = lane._select_task_ids(root, args)

        self.assertEqual([2, 3, 4], selected)

    def test_select_task_ids_should_honor_explicit_csv_and_max_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tasks_path = root / ".taskmaster" / "tasks" / "tasks.json"
            _write_master_tasks(
                tasks_path,
                [
                    {"id": 1, "status": "done"},
                    {"id": 2, "status": "done"},
                    {"id": 3, "status": "done"},
                    {"id": 4, "status": "done"},
                ],
            )
            args = Namespace(task_ids="4,3,100,3", task_id_start=1, task_id_end=0, max_tasks=1)

            selected = lane._select_task_ids(root, args)

        self.assertEqual([3], selected)

    def test_main_self_check_should_write_summary_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tasks_path = root / ".taskmaster" / "tasks" / "tasks.json"
            _write_master_tasks(tasks_path, [{"id": 11, "status": "in-progress"}])
            out_dir = root / "logs" / "ci" / "self-check"
            argv = [
                "run_single_task_light_lane.py",
                "--task-ids",
                "11",
                "--out-dir",
                str(out_dir),
                "--self-check",
            ]

            with mock.patch.object(sys, "argv", argv), mock.patch.object(lane, "_repo_root", return_value=root):
                rc = lane.main()

            self.assertEqual(0, rc)
            payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("ok", payload["status"])
            self.assertEqual(["preflight_extract_guard", "extract", "align", "coverage", "semantic_gate", "fill_refs_dry", "fill_refs_write", "fill_refs_verify"], payload["steps"])
            self.assertEqual(11, payload["task_id_start"])
            self.assertEqual(11, payload["task_id_end"])
            self.assertEqual("run-5.1", payload["preferred_lane"])
            self.assertEqual("continue", payload["recommended_action"])
            self.assertIn("--task-ids 11", payload["recommended_command"])
            self.assertEqual([], payload["forbidden_commands"])
            self.assertEqual("self_check", payload["latest_reason"])
            self.assertEqual("n/a", payload["blocked_by"])
            self.assertEqual("", payload["artifact_integrity"])
            self.assertEqual("no", payload["residual_recording"])

    def test_snapshot_inner_artifacts_should_copy_summary_and_task_subdir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_dir = root / "logs" / "ci" / "2026-03-28" / "sc-llm-align-acceptance-semantics"
            (source_dir / "task-11").mkdir(parents=True, exist_ok=True)
            (source_dir / "summary.json").write_text(
                json.dumps({"cmd": "sc-align", "status": "ok"}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (source_dir / "task-11" / "report.md").write_text("task report\n", encoding="utf-8")

            metadata = lane._snapshot_inner_artifacts(
                root=root,
                wrapper_out_dir=root / "logs" / "ci" / "2026-03-28" / "single-task-light-lane-v2",
                task_id=11,
                step_name="align",
                stdout=f"SC_ALIGN_ACCEPTANCE status=ok out={str(source_dir)}",
                stderr="",
            )

            self.assertIn("artifact_dir", metadata)
            artifact_dir = root / metadata["artifact_dir"]
            self.assertTrue((artifact_dir / "summary.json").is_file())
            self.assertTrue((artifact_dir / "task-11" / "report.md").is_file())
            self.assertEqual("ok", metadata["inner_summary"]["status"])

    def test_main_resume_should_skip_completed_tasks_in_same_scope(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tasks_path = root / ".taskmaster" / "tasks" / "tasks.json"
            _write_master_tasks(
                tasks_path,
                [
                    {"id": 11, "status": "in-progress"},
                    {"id": 12, "status": "in-progress"},
                ],
            )
            out_dir = root / "logs" / "ci" / "resume"
            out_dir.mkdir(parents=True, exist_ok=True)
            summary_path = out_dir / "summary.json"
            summary_path.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "task_id": 11,
                                "steps": [{"step": name, "rc": 0} for name in ["preflight_extract_guard", "extract", "align", "coverage", "semantic_gate"]],
                                "failed_steps": [],
                                "first_failed_step": "",
                                "ok": True,
                            }
                        ],
                        "resume_scope": {
                            "task_ids": [11, 12],
                            "delivery_profile": "fast-ship",
                            "align_apply": True,
                            "fill_refs_after_extract_fail": "skip",
                            "downstream_on_extract_fail": "skip-soft",
                            "downstream_on_extract_family_fail": "auto",
                            "fill_refs_mode": "none",
                            "batch_lane": "extract-first",
                            "step_names": ["preflight_extract_guard", "extract", "align", "coverage", "semantic_gate"],
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            argv = [
                "run_single_task_light_lane.py",
                "--task-ids",
                "11,12",
                "--out-dir",
                str(out_dir),
            ]

            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(lane, "_repo_root", return_value=root), \
                mock.patch.object(lane, "_run_step", return_value=(0, "ok", "")) as run_step_mock:
                rc = lane.main()

            self.assertEqual(0, rc)
            self.assertEqual(5, run_step_mock.call_count)
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(2, payload["processed_tasks"])
            self.assertEqual(12, payload["last_task_id"])
            self.assertEqual([11, 12], payload["resume_scope"]["task_ids"])

    def test_main_resume_failed_task_from_first_failed_step_should_reuse_successful_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tasks_path = root / ".taskmaster" / "tasks" / "tasks.json"
            _write_master_tasks(tasks_path, [{"id": 11, "status": "in-progress"}])
            out_dir = root / "logs" / "ci" / "resume-failed"
            out_dir.mkdir(parents=True, exist_ok=True)
            summary_path = out_dir / "summary.json"
            summary_path.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "task_id": 11,
                                "steps": [
                                    {"step": "preflight_extract_guard", "rc": 0, "log": "old/preflight.log"},
                                    {"step": "extract", "rc": 0, "log": "old/extract.log"},
                                    {"step": "align", "rc": 0, "log": "old/align.log"},
                                    {"step": "coverage", "rc": 0, "log": "old/coverage.log"},
                                    {"step": "semantic_gate", "rc": 1, "log": "old/semantic_gate.log"},
                                    {"step": "fill_refs_dry", "rc": 1, "log": "old/fill_refs_dry.log"},
                                    {"step": "fill_refs_write", "rc": 1, "log": "old/fill_refs_write.log"},
                                    {"step": "fill_refs_verify", "rc": 1, "log": "old/fill_refs_verify.log"},
                                ],
                                "failed_steps": ["semantic_gate", "fill_refs_dry", "fill_refs_write", "fill_refs_verify"],
                                "first_failed_step": "semantic_gate",
                                "ok": False,
                            }
                        ],
                        "resume_scope": {
                            "task_ids": [11],
                            "delivery_profile": "fast-ship",
                            "align_apply": True,
                            "fill_refs_after_extract_fail": "skip",
                            "downstream_on_extract_fail": "continue",
                            "downstream_on_extract_family_fail": "auto",
                            "fill_refs_mode": "write-verify",
                            "batch_lane": "standard",
                            "step_names": ["preflight_extract_guard", "extract", "align", "coverage", "semantic_gate", "fill_refs_dry", "fill_refs_write", "fill_refs_verify"],
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            argv = [
                "run_single_task_light_lane.py",
                "--task-ids",
                "11",
                "--out-dir",
                str(out_dir),
                "--resume-failed-task-from",
                "first-failed-step",
            ]

            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(lane, "_repo_root", return_value=root), \
                mock.patch.object(lane, "_run_step", return_value=(0, "ok", "")) as run_step_mock:
                rc = lane.main()

            self.assertEqual(0, rc)
            self.assertEqual(4, run_step_mock.call_count)
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            row = payload["results"][0]
            self.assertEqual("semantic_gate", row["resumed_from_step"])
            self.assertEqual(["preflight_extract_guard", "extract", "align", "coverage"], row["reused_successful_steps"])
            self.assertEqual("old/preflight.log", row["steps"][0]["log"])
            self.assertEqual("old/extract.log", row["steps"][1]["log"])
            self.assertEqual("old/align.log", row["steps"][2]["log"])
            self.assertEqual("old/coverage.log", row["steps"][3]["log"])

    def test_main_should_skip_fill_refs_after_extract_fail_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tasks_path = root / ".taskmaster" / "tasks" / "tasks.json"
            _write_master_tasks(tasks_path, [{"id": 11, "status": "in-progress"}])
            out_dir = root / "logs" / "ci" / "skip-fill-refs"
            argv = [
                "run_single_task_light_lane.py",
                "--task-ids",
                "11",
                "--out-dir",
                str(out_dir),
            ]
            responses = [
                (0, "SC_ACCEPTANCE_EXTRACT_PREFLIGHT status=ok out=fake", ""),
                (1, "SC_LLM_OBLIGATIONS status=fail out=fake", ""),
            ]

            def _fake_run_step(_root: Path, _cmd: list[str], *, timeout_sec: int):
                return responses.pop(0)

            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(lane, "_repo_root", return_value=root), \
                mock.patch.object(lane, "_run_step", side_effect=_fake_run_step) as run_step_mock:
                rc = lane.main()

            self.assertEqual(1, rc)
            self.assertEqual(2, run_step_mock.call_count)
            payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            row = payload["results"][0]
            self.assertEqual("auto", payload["downstream_on_extract_family_fail_resolved"])
            self.assertEqual(
                ["preflight_extract_guard", "extract", "align", "coverage", "semantic_gate", "fill_refs_dry", "fill_refs_write", "fill_refs_verify"],
                [item["step"] for item in row["steps"]],
            )
            skipped = {item["step"]: item for item in row["steps"][2:]}
            self.assertTrue(all(bool(item.get("skipped")) for item in skipped.values()))
            self.assertTrue(
                all(str(item.get("skip_reason")) == "extract_failed_family_policy_skip_all" for item in skipped.values())
            )
            self.assertTrue(
                all(
                    str(item.get("extract_fail_family")) == "stdout:sc_llm_obligations_status_fail"
                    for item in skipped.values()
                )
            )

    def test_main_should_skip_soft_downstream_after_extract_fail_for_multi_task_auto(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tasks_path = root / ".taskmaster" / "tasks" / "tasks.json"
            _write_master_tasks(
                tasks_path,
                [
                    {"id": 11, "status": "in-progress"},
                    {"id": 12, "status": "in-progress"},
                ],
            )
            out_dir = root / "logs" / "ci" / "skip-soft"
            argv = [
                "run_single_task_light_lane.py",
                "--task-ids",
                "11,12",
                "--out-dir",
                str(out_dir),
            ]
            responses = [
                (0, "SC_ACCEPTANCE_EXTRACT_PREFLIGHT status=ok out=fake", ""),
                (1, "SC_LLM_OBLIGATIONS status=fail out=fake", ""),
                (0, "ok", ""),
                (0, "SC_ACCEPTANCE_EXTRACT_PREFLIGHT status=ok out=fake", ""),
                (0, "SC_LLM_OBLIGATIONS status=ok out=fake", ""),
                (0, "ok", ""),
                (0, "ok", ""),
                (0, "ok", ""),
                (0, "ok", ""),
                (0, "ok", ""),
            ]

            def _fake_run_step(_root: Path, _cmd: list[str], *, timeout_sec: int):
                return responses.pop(0)

            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(lane, "_repo_root", return_value=root), \
                mock.patch.object(lane, "_run_step", side_effect=_fake_run_step) as run_step_mock:
                rc = lane.main()

            self.assertEqual(1, rc)
            self.assertEqual(7, run_step_mock.call_count)
            payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("skip-soft", payload["downstream_on_extract_fail_resolved"])
            self.assertEqual("extract-first", payload["batch_lane_resolved"])
            self.assertEqual("none", payload["fill_refs_mode_resolved"])
            row = payload["results"][0]
            self.assertEqual("preflight_extract_guard", row["steps"][0]["step"])
            self.assertEqual("extract", row["steps"][1]["step"])
            self.assertGreaterEqual(payload["failed_tasks"], 1)

    def test_main_should_retry_extract_timeout_once_with_expanded_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tasks_path = root / ".taskmaster" / "tasks" / "tasks.json"
            _write_master_tasks(tasks_path, [{"id": 11, "status": "in-progress"}])
            out_dir = root / "logs" / "ci" / "retry"
            argv = [
                "run_single_task_light_lane.py",
                "--task-ids",
                "11",
                "--out-dir",
                str(out_dir),
            ]
            call_timeouts: list[int] = []
            responses = [
                (0, "SC_ACCEPTANCE_EXTRACT_PREFLIGHT status=ok out=fake", ""),
                (124, "", ""),
                (0, "SC_LLM_OBLIGATIONS status=ok out=fake", ""),
                (0, "ok", ""),
                (0, "ok", ""),
                (0, "ok", ""),
                (0, "ok", ""),
                (0, "ok", ""),
                (0, "ok", ""),
            ]

            def _fake_run_step(_root: Path, _cmd: list[str], *, timeout_sec: int):
                call_timeouts.append(timeout_sec)
                return responses.pop(0)

            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(lane, "_repo_root", return_value=root), \
                mock.patch.object(lane, "_run_step", side_effect=_fake_run_step):
                rc = lane.main()

            self.assertEqual(0, rc)
            self.assertEqual(9, len(call_timeouts))
            self.assertGreater(call_timeouts[2], call_timeouts[1])
            payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            extract_step = payload["results"][0]["steps"][1]
            self.assertEqual(0, extract_step["rc"])
            self.assertEqual(1, extract_step["retry_count"])
            self.assertEqual([124, 0], extract_step["retry_rcs"])
            self.assertEqual({}, payload["failure_category_counts"])

    def test_main_should_skip_extract_when_preflight_guard_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tasks_path = root / ".taskmaster" / "tasks" / "tasks.json"
            _write_master_tasks(tasks_path, [{"id": 11, "status": "in-progress"}])
            out_dir = root / "logs" / "ci" / "preflight-fail"
            argv = [
                "run_single_task_light_lane.py",
                "--task-ids",
                "11",
                "--out-dir",
                str(out_dir),
            ]

            def _fake_run_step(_root: Path, _cmd: list[str], *, timeout_sec: int):
                return 1, "SC_ACCEPTANCE_EXTRACT_PREFLIGHT status=fail out=fake", ""

            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(lane, "_repo_root", return_value=root), \
                mock.patch.object(lane, "_run_step", side_effect=_fake_run_step) as run_step_mock:
                rc = lane.main()

            self.assertEqual(1, rc)
            self.assertEqual(1, run_step_mock.call_count)
            payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            row = payload["results"][0]
            self.assertEqual("preflight-gap", payload["failure_category_by_task"]["11"])
            self.assertEqual("inspect-first", payload["preferred_lane"])
            self.assertEqual("inspect", payload["recommended_action"])
            self.assertEqual("", payload["recommended_command"])
            self.assertEqual("preflight_gap", payload["latest_reason"])
            self.assertEqual("deterministic_failure", payload["blocked_by"])
            self.assertEqual("", payload["artifact_integrity"])
            self.assertEqual("no", payload["residual_recording"])
            self.assertEqual("preflight_extract_guard", row["first_failed_step"])
            self.assertEqual(
                ["preflight_extract_guard", "extract", "align", "coverage", "semantic_gate", "fill_refs_dry", "fill_refs_write", "fill_refs_verify"],
                [item["step"] for item in row["steps"]],
            )
            self.assertEqual(1, row["steps"][0]["rc"])
            for item in row["steps"][1:]:
                self.assertTrue(bool(item.get("skipped")))
                self.assertEqual("preflight_extract_guard_failed", str(item.get("skip_reason")))

    def test_main_should_emit_retry_soft_steps_route_for_semantic_only_failures(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tasks_path = root / ".taskmaster" / "tasks" / "tasks.json"
            _write_master_tasks(tasks_path, [{"id": 11, "status": "in-progress"}])
            out_dir = root / "logs" / "ci" / "semantic-only"
            argv = [
                "run_single_task_light_lane.py",
                "--task-ids",
                "11",
                "--out-dir",
                str(out_dir),
            ]
            responses = [
                (0, "SC_ACCEPTANCE_EXTRACT_PREFLIGHT status=ok out=fake", ""),
                (0, "SC_LLM_OBLIGATIONS status=ok out=fake", ""),
                (0, "SC_ALIGN_ACCEPTANCE status=ok out=fake", ""),
                (0, "SC_COVERAGE status=ok out=fake", ""),
                (1, "SC_SEMANTIC_GATE status=fail out=fake", ""),
                (0, "SC_FILL_REFS status=ok out=fake", ""),
                (0, "SC_FILL_REFS status=ok out=fake", ""),
                (0, "SC_FILL_REFS status=ok out=fake", ""),
            ]

            def _fake_run_step(_root: Path, _cmd: list[str], *, timeout_sec: int):
                return responses.pop(0)

            def _fake_snapshot_inner_artifacts(*_args, **_kwargs):
                step_name = str(_kwargs.get("step_name") or "")
                if step_name == "semantic_gate":
                    return {"inner_summary": {"status": "fail", "prompt_trimmed": False}}
                if step_name == "coverage":
                    return {"inner_summary": {"status": "ok", "uncovered_subtask_ids": []}}
                return {"inner_summary": {"status": "ok"}}

            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(lane, "_repo_root", return_value=root), \
                mock.patch.object(lane, "_run_step", side_effect=_fake_run_step), \
                mock.patch.object(lane, "_snapshot_inner_artifacts", side_effect=_fake_snapshot_inner_artifacts):
                rc = lane.main()

            self.assertEqual(1, rc)
            payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("retry-soft-steps-only", payload["preferred_lane"])
            self.assertEqual("rerun", payload["recommended_action"])
            self.assertIn("--resume-failed-task-from first-failed-step", payload["recommended_command"])
            self.assertEqual([], payload["forbidden_commands"])
            self.assertEqual("soft_steps_failed", payload["latest_reason"])
            self.assertEqual("", payload["blocked_by"])
            self.assertEqual("", payload["artifact_integrity"])
            self.assertEqual("no", payload["residual_recording"])


if __name__ == "__main__":
    unittest.main()
