#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
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


batch = _load_module("single_task_light_lane_batch_module", "scripts/python/run_single_task_light_lane_batch.py")


class RunSingleTaskLightLaneBatchTests(unittest.TestCase):
    def test_split_task_ids_should_chunk_by_shard_size(self) -> None:
        self.assertEqual([[1, 2, 3], [4, 5, 6], [7]], batch._split_task_ids([1, 2, 3, 4, 5, 6, 7], 3))

    def test_main_self_check_should_write_shard_plan(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "batch-self-check"
            argv = [
                "run_single_task_light_lane_batch.py",
                "--task-ids",
                "11,12,13,14,15",
                "--max-tasks-per-shard",
                "2",
                "--out-dir",
                str(out_dir),
                "--self-check",
            ]
            with mock.patch.object(batch, "_repo_root", return_value=root), mock.patch.object(
                batch, "_selected_task_ids", return_value=[11, 12, 13, 14, 15]
            ), mock.patch.object(sys, "argv", argv):
                rc = batch.main()

            self.assertEqual(0, rc)
            payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("ok", payload["status"])
            self.assertEqual(3, payload["shard_count"])
            self.assertEqual(
                [
                    [11, 12],
                    [13, 14],
                    [15],
                ],
                [entry["task_ids"] for entry in payload["shards"]],
            )

    def test_main_self_check_should_apply_stable_batch_preset(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "batch-preset-self-check"
            argv = [
                "run_single_task_light_lane_batch.py",
                "--task-ids",
                "11,12,13",
                "--batch-preset",
                "stable-batch",
                "--self-check",
                "--out-dir",
                str(out_dir),
            ]
            with mock.patch.object(batch, "_repo_root", return_value=root), mock.patch.object(
                batch, "_selected_task_ids", return_value=[11, 12, 13]
            ), mock.patch.object(sys, "argv", argv):
                rc = batch.main()

            self.assertEqual(0, rc)
            payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("stable-batch", payload["batch_preset"])
            self.assertEqual("extract-first", payload["batch_lane"])
            self.assertEqual("none", payload["fill_refs_mode"])
            self.assertEqual("skip-soft", payload["downstream_on_extract_fail"])
            self.assertEqual("auto", payload["downstream_on_extract_family_fail"])
            self.assertEqual("degrade", payload["rolling_extract"]["policy"])
            self.assertEqual(0.45, payload["rolling_extract"]["threshold"])
            self.assertEqual("warn", payload["rolling_family"]["policy"])
            self.assertEqual(5, payload["rolling_family"]["streak_threshold"])

    def test_main_self_check_should_keep_explicit_flags_over_preset(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "batch-preset-override-self-check"
            argv = [
                "run_single_task_light_lane_batch.py",
                "--task-ids",
                "11,12,13",
                "--batch-preset",
                "stable-batch",
                "--fill-refs-mode",
                "dry",
                "--rolling-extract-policy",
                "warn",
                "--self-check",
                "--out-dir",
                str(out_dir),
            ]
            with mock.patch.object(batch, "_repo_root", return_value=root), mock.patch.object(
                batch, "_selected_task_ids", return_value=[11, 12, 13]
            ), mock.patch.object(sys, "argv", argv):
                rc = batch.main()

            self.assertEqual(0, rc)
            payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("dry", payload["fill_refs_mode"])
            self.assertEqual("warn", payload["rolling_extract"]["policy"])
            self.assertNotIn("fill_refs_mode", payload["batch_preset_applied"])
            self.assertNotIn("rolling_extract_policy", payload["batch_preset_applied"])

    def test_main_self_check_should_keep_explicit_extract_family_flag_over_preset(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "batch-preset-family-override-self-check"
            argv = [
                "run_single_task_light_lane_batch.py",
                "--task-ids",
                "11,12,13",
                "--batch-preset",
                "stable-batch",
                "--downstream-on-extract-family-fail",
                "off",
                "--self-check",
                "--out-dir",
                str(out_dir),
            ]
            with mock.patch.object(batch, "_repo_root", return_value=root), mock.patch.object(
                batch, "_selected_task_ids", return_value=[11, 12, 13]
            ), mock.patch.object(sys, "argv", argv):
                rc = batch.main()

            self.assertEqual(0, rc)
            payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("off", payload["downstream_on_extract_family_fail"])
            self.assertNotIn("downstream_on_extract_family_fail", payload["batch_preset_applied"])

    def test_main_should_run_isolated_shards_and_write_merged_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "batch-run"
            executed_out_dirs: list[str] = []

            def fake_run_command(_root: Path, cmd: list[str]):
                task_ids = [int(part) for part in cmd[cmd.index("--task-ids") + 1].split(",")]
                shard_out_dir = Path(cmd[cmd.index("--out-dir") + 1])
                executed_out_dirs.append(str(shard_out_dir))
                shard_out_dir.mkdir(parents=True, exist_ok=True)
                results = [
                    {
                        "task_id": task_id,
                        "ok": True,
                        "failed_steps": [],
                        "first_failed_step": "",
                        "steps": [{"step": "extract", "rc": 0}],
                    }
                    for task_id in task_ids
                ]
                (shard_out_dir / "summary.json").write_text(
                    json.dumps(
                        {
                            "task_id_start": task_ids[0],
                            "task_id_end": task_ids[-1],
                            "task_count": len(task_ids),
                            "processed_tasks": len(task_ids),
                            "passed_tasks": len(task_ids),
                            "failed_tasks": 0,
                            "remaining_tasks": 0,
                            "status": "ok",
                            "results": results,
                            "batch_lane_resolved": "extract-first",
                            "fill_refs_mode_resolved": "none",
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

                class _Result:
                    returncode = 0
                    stdout = "ok\n"
                    stderr = ""

                return _Result()

            argv = [
                "run_single_task_light_lane_batch.py",
                "--task-ids",
                "11,12,13,14,15",
                "--max-tasks-per-shard",
                "2",
                "--out-dir",
                str(out_dir),
            ]
            with mock.patch.object(batch, "_repo_root", return_value=root), mock.patch.object(
                batch, "_selected_task_ids", return_value=[11, 12, 13, 14, 15]
            ), mock.patch.object(batch, "_run_command", side_effect=fake_run_command), mock.patch.object(sys, "argv", argv):
                rc = batch.main()

            self.assertEqual(0, rc)
            self.assertEqual(3, len(set(executed_out_dirs)))
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            merged = json.loads((out_dir / "merged" / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("ok", summary["status"])
            self.assertEqual(3, len(summary["shards"]))
            self.assertEqual("logs/ci/batch-run/merged/summary.json", summary["merged_summary_path"])
            self.assertEqual(5, summary["covered_count"])
            self.assertEqual(5, merged["covered_count"])
            self.assertEqual([], merged["missing_task_ids"])
            self.assertEqual(["logs/ci/batch-run/shards/shard-001-t11-12/summary.json"], merged["task_source_candidates"]["11"])

    def test_main_should_surface_extract_signatures_from_merged_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "batch-run-signatures"

            def fake_run_command(_root: Path, cmd: list[str]):
                task_ids = [int(part) for part in cmd[cmd.index("--task-ids") + 1].split(",")]
                shard_out_dir = Path(cmd[cmd.index("--out-dir") + 1])
                shard_out_dir.mkdir(parents=True, exist_ok=True)
                rows = []
                for task_id in task_ids:
                    if task_id == 11:
                        rows.append(
                            {
                                "task_id": task_id,
                                "ok": False,
                                "failed_steps": ["extract"],
                                "first_failed_step": "extract",
                                "steps": [{"step": "extract", "rc": 1, "stderr_tail": "Model output invalid at line 42"}],
                            }
                        )
                    else:
                        rows.append(
                            {
                                "task_id": task_id,
                                "ok": True,
                                "failed_steps": [],
                                "first_failed_step": "",
                                "steps": [{"step": "extract", "rc": 0}],
                            }
                        )
                (shard_out_dir / "summary.json").write_text(
                    json.dumps(
                        {
                            "task_id_start": task_ids[0],
                            "task_id_end": task_ids[-1],
                            "task_count": len(task_ids),
                            "processed_tasks": len(task_ids),
                            "passed_tasks": sum(1 for row in rows if bool(row.get("ok"))),
                            "failed_tasks": sum(1 for row in rows if not bool(row.get("ok"))),
                            "remaining_tasks": 0,
                            "status": "fail" if any(not bool(row.get("ok")) for row in rows) else "ok",
                            "results": rows,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

                class _Result:
                    returncode = 1 if any(not bool(row.get("ok")) for row in rows) else 0
                    stdout = "done\n"
                    stderr = ""

                return _Result()

            argv = [
                "run_single_task_light_lane_batch.py",
                "--task-ids",
                "11,12",
                "--max-tasks-per-shard",
                "1",
                "--out-dir",
                str(out_dir),
            ]
            with mock.patch.object(batch, "_repo_root", return_value=root), mock.patch.object(
                batch, "_selected_task_ids", return_value=[11, 12]
            ), mock.patch.object(batch, "_run_command", side_effect=fake_run_command), mock.patch.object(sys, "argv", argv):
                rc = batch.main()

            self.assertEqual(1, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual({"stderr:model output invalid at line <num>": 1}, summary["extract_fail_signature_counts"])
            self.assertEqual(
                [{"signature": "stderr:model output invalid at line <num>", "count": 1, "task_ids": [11]}],
                summary["extract_fail_top_signatures"],
            )
            self.assertEqual({"stderr:model_output_invalid": 1}, summary["extract_fail_family_counts"])
            self.assertEqual(
                [{"family": "stderr:model_output_invalid", "count": 1, "task_ids": [11]}],
                summary["extract_fail_top_families"],
            )
            self.assertEqual(
                [
                    {
                        "family": "stderr:model_output_invalid",
                        "count": 1,
                        "task_ids": [11],
                        "recommended_action": "tighten_prompt_or_reduce_extract_scope_then_retry",
                        "downstream_policy_hint": "skip-soft",
                        "reason": "model output was invalid; fix extract prompt/scope first and only then continue downstream",
                    }
                ],
                summary["extract_family_recommended_actions"],
            )

    def test_build_extract_family_recommended_actions_should_sort_and_attach_hints(self) -> None:
        actions = batch._build_extract_family_recommended_actions(
            {
                "extract_fail_family_counts": {
                    "stdout:sc_llm_obligations_status_fail": 3,
                    "timeout": 1,
                },
                "extract_fail_family_task_ids": {
                    "stdout:sc_llm_obligations_status_fail": [67, 68, 69],
                    "timeout": [93],
                },
            }
        )
        self.assertEqual(
            [
                {
                    "family": "stdout:sc_llm_obligations_status_fail",
                    "count": 3,
                    "task_ids": [67, 68, 69],
                    "recommended_action": "repair_obligations_or_task_context_before_downstream",
                    "downstream_policy_hint": "skip-all",
                    "reason": "extract already reported obligations failure; align/coverage/review are low-value until obligations recover",
                },
                {
                    "family": "timeout",
                    "count": 1,
                    "task_ids": [93],
                    "recommended_action": "raise_extract_timeout_or_reduce_batch_scope",
                    "downstream_policy_hint": "skip-all",
                    "reason": "extract timed out; retry extract first before spending more downstream work",
                },
            ],
            actions,
        )

    def test_main_should_fail_when_merge_validation_has_hard_issues(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "batch-run-validation-fail"

            def fake_run_command(_root: Path, cmd: list[str]):
                task_ids = [int(part) for part in cmd[cmd.index("--task-ids") + 1].split(",")]
                shard_out_dir = Path(cmd[cmd.index("--out-dir") + 1])
                shard_out_dir.mkdir(parents=True, exist_ok=True)
                rows = [
                    {"task_id": task_ids[0], "ok": True, "failed_steps": [], "first_failed_step": "", "steps": [{"step": "extract", "rc": 0}]},
                    {"task_id": task_ids[0] + 100, "ok": True, "failed_steps": [], "first_failed_step": "", "steps": [{"step": "extract", "rc": 0}]},
                ]
                (shard_out_dir / "summary.json").write_text(
                    json.dumps(
                        {
                            "task_id_start": task_ids[0],
                            "task_id_end": task_ids[0],
                            "task_count": 1,
                            "processed_tasks": 2,
                            "passed_tasks": 2,
                            "failed_tasks": 0,
                            "remaining_tasks": 0,
                            "status": "ok",
                            "results": rows,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

                class _Result:
                    returncode = 0
                    stdout = "done\n"
                    stderr = ""

                return _Result()

            argv = [
                "run_single_task_light_lane_batch.py",
                "--task-ids",
                "11",
                "--max-tasks-per-shard",
                "1",
                "--out-dir",
                str(out_dir),
            ]
            with mock.patch.object(batch, "_repo_root", return_value=root), mock.patch.object(
                batch, "_selected_task_ids", return_value=[11]
            ), mock.patch.object(batch, "_run_command", side_effect=fake_run_command), mock.patch.object(sys, "argv", argv):
                rc = batch.main()

            self.assertEqual(1, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("fail", summary["status"])
            self.assertEqual("fail", summary["merge_validation"]["status"])
            self.assertEqual(2, summary["merge_validation"]["hard_issue_count"])

    def test_main_should_degrade_future_shards_after_rolling_extract_trigger(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "batch-run-degrade"
            commands: list[list[str]] = []

            def fake_run_command(_root: Path, cmd: list[str]):
                commands.append(list(cmd))
                task_ids = [int(part) for part in cmd[cmd.index("--task-ids") + 1].split(",")]
                shard_out_dir = Path(cmd[cmd.index("--out-dir") + 1])
                shard_out_dir.mkdir(parents=True, exist_ok=True)
                task_id = task_ids[0]
                row = {
                    "task_id": task_id,
                    "ok": False if task_id == 11 else True,
                    "failed_steps": ["extract"] if task_id == 11 else [],
                    "first_failed_step": "extract" if task_id == 11 else "",
                    "steps": [{"step": "extract", "rc": 1 if task_id == 11 else 0}],
                }
                (shard_out_dir / "summary.json").write_text(
                    json.dumps(
                        {
                            "task_id_start": task_id,
                            "task_id_end": task_id,
                            "task_count": 1,
                            "processed_tasks": 1,
                            "passed_tasks": 0 if task_id == 11 else 1,
                            "failed_tasks": 1 if task_id == 11 else 0,
                            "remaining_tasks": 0,
                            "status": "fail" if task_id == 11 else "ok",
                            "results": [row],
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

                class _Result:
                    returncode = 1 if task_id == 11 else 0
                    stdout = "done\n"
                    stderr = ""

                return _Result()

            argv = [
                "run_single_task_light_lane_batch.py",
                "--task-ids",
                "11,12",
                "--max-tasks-per-shard",
                "1",
                "--out-dir",
                str(out_dir),
                "--rolling-extract-policy",
                "degrade",
                "--rolling-extract-rate-threshold",
                "0.5",
                "--rolling-extract-min-observed-tasks",
                "1",
            ]
            with mock.patch.object(batch, "_repo_root", return_value=root), mock.patch.object(
                batch, "_selected_task_ids", return_value=[11, 12]
            ), mock.patch.object(batch, "_run_command", side_effect=fake_run_command), mock.patch.object(sys, "argv", argv):
                rc = batch.main()

            self.assertEqual(1, rc)
            self.assertEqual(2, len(commands))
            self.assertNotIn("--no-align-apply", commands[0])
            self.assertIn("--no-align-apply", commands[1])
            self.assertEqual("none", commands[1][commands[1].index("--fill-refs-mode") + 1])
            self.assertEqual("skip-all", commands[1][commands[1].index("--downstream-on-extract-fail") + 1])
            self.assertEqual("skip-all", commands[1][commands[1].index("--downstream-on-extract-family-fail") + 1])
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("degrade", summary["rolling_extract"]["action"])
            self.assertTrue(summary["rolling_extract"]["triggered"])
            self.assertTrue(summary["rolling_extract"]["degraded_mode_active"])

    def test_main_should_stop_future_shards_after_rolling_extract_trigger(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "batch-run-stop"
            commands: list[list[str]] = []

            def fake_run_command(_root: Path, cmd: list[str]):
                commands.append(list(cmd))
                task_id = int(cmd[cmd.index("--task-ids") + 1])
                shard_out_dir = Path(cmd[cmd.index("--out-dir") + 1])
                shard_out_dir.mkdir(parents=True, exist_ok=True)
                (shard_out_dir / "summary.json").write_text(
                    json.dumps(
                        {
                            "task_id_start": task_id,
                            "task_id_end": task_id,
                            "task_count": 1,
                            "processed_tasks": 1,
                            "passed_tasks": 0,
                            "failed_tasks": 1,
                            "remaining_tasks": 0,
                            "status": "fail",
                            "results": [
                                {
                                    "task_id": task_id,
                                    "ok": False,
                                    "failed_steps": ["extract"],
                                    "first_failed_step": "extract",
                                    "steps": [{"step": "extract", "rc": 1}],
                                }
                            ],
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

                class _Result:
                    returncode = 1
                    stdout = "done\n"
                    stderr = ""

                return _Result()

            argv = [
                "run_single_task_light_lane_batch.py",
                "--task-ids",
                "11,12,13",
                "--max-tasks-per-shard",
                "1",
                "--out-dir",
                str(out_dir),
                "--rolling-extract-policy",
                "stop",
                "--rolling-extract-rate-threshold",
                "0.5",
                "--rolling-extract-min-observed-tasks",
                "1",
            ]
            with mock.patch.object(batch, "_repo_root", return_value=root), mock.patch.object(
                batch, "_selected_task_ids", return_value=[11, 12, 13]
            ), mock.patch.object(batch, "_run_command", side_effect=fake_run_command), mock.patch.object(sys, "argv", argv):
                rc = batch.main()

            self.assertEqual(1, rc)
            self.assertEqual(1, len(commands))
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("stop", summary["rolling_extract"]["action"])
            self.assertEqual(2, len(summary["skipped_planned_shards"]))
            self.assertEqual([12], summary["skipped_planned_shards"][0]["task_ids"])

    def test_main_should_stop_future_shards_after_repeated_failure_family(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "batch-run-family-stop"
            commands: list[list[str]] = []

            def fake_run_command(_root: Path, cmd: list[str]):
                commands.append(list(cmd))
                task_id = int(cmd[cmd.index("--task-ids") + 1])
                shard_out_dir = Path(cmd[cmd.index("--out-dir") + 1])
                shard_out_dir.mkdir(parents=True, exist_ok=True)
                row = {
                    "task_id": task_id,
                    "ok": False,
                    "failed_steps": ["extract"],
                    "first_failed_step": "extract",
                    "steps": [
                        {
                            "step": "extract",
                            "rc": 1,
                            "stdout_tail": f"SC_LLM_OBLIGATIONS status=fail out=C:/logs/task-{task_id}",
                        }
                    ],
                }
                (shard_out_dir / "summary.json").write_text(
                    json.dumps(
                        {
                            "task_id_start": task_id,
                            "task_id_end": task_id,
                            "task_count": 1,
                            "processed_tasks": 1,
                            "passed_tasks": 0,
                            "failed_tasks": 1,
                            "remaining_tasks": 0,
                            "status": "fail",
                            "results": [row],
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

                class _Result:
                    returncode = 1
                    stdout = "done\n"
                    stderr = ""

                return _Result()

            argv = [
                "run_single_task_light_lane_batch.py",
                "--task-ids",
                "11,12,13,14",
                "--max-tasks-per-shard",
                "1",
                "--out-dir",
                str(out_dir),
                "--rolling-extract-policy",
                "off",
                "--rolling-family-policy",
                "stop",
                "--rolling-family-streak-threshold",
                "2",
            ]
            with mock.patch.object(batch, "_repo_root", return_value=root), mock.patch.object(
                batch, "_selected_task_ids", return_value=[11, 12, 13, 14]
            ), mock.patch.object(batch, "_run_command", side_effect=fake_run_command), mock.patch.object(sys, "argv", argv):
                rc = batch.main()

            self.assertEqual(1, rc)
            self.assertEqual(2, len(commands))
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("stop", summary["rolling_family"]["action"])
            self.assertTrue(summary["rolling_family"]["triggered"])
            self.assertEqual(1, len(summary["family_hotspots"]))
            self.assertEqual("stdout:sc_llm_obligations_status_fail", summary["family_hotspots"][0]["family"])
            self.assertEqual(11, summary["family_hotspots"][0]["task_id_start"])
            self.assertEqual(12, summary["family_hotspots"][0]["task_id_end"])
            self.assertEqual(1, len(summary["quarantine_ranges"]))
            self.assertEqual(2, len(summary["skipped_planned_shards"]))

    def test_main_should_increase_timeout_and_reduce_next_shard_after_timeout_spike(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "batch-run-backoff"
            commands: list[list[str]] = []

            def fake_run_command(_root: Path, cmd: list[str]):
                commands.append(list(cmd))
                task_ids = [int(part) for part in cmd[cmd.index("--task-ids") + 1].split(",")]
                shard_out_dir = Path(cmd[cmd.index("--out-dir") + 1])
                shard_out_dir.mkdir(parents=True, exist_ok=True)
                rows = []
                for task_id in task_ids:
                    rows.append(
                        {
                            "task_id": task_id,
                            "ok": False if task_id <= 14 else True,
                            "failed_steps": ["extract"] if task_id <= 14 else [],
                            "first_failed_step": "extract" if task_id <= 14 else "",
                            "steps": [{"step": "extract", "rc": 124 if task_id <= 14 else 0}],
                        }
                    )
                (shard_out_dir / "summary.json").write_text(
                    json.dumps(
                        {
                            "task_id_start": task_ids[0],
                            "task_id_end": task_ids[-1],
                            "task_count": len(task_ids),
                            "processed_tasks": len(task_ids),
                            "passed_tasks": sum(1 for row in rows if bool(row.get("ok"))),
                            "failed_tasks": sum(1 for row in rows if not bool(row.get("ok"))),
                            "remaining_tasks": 0,
                            "status": "fail" if any(not bool(row.get("ok")) for row in rows) else "ok",
                            "results": rows,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

                class _Result:
                    returncode = 1 if any(not bool(row.get("ok")) for row in rows) else 0
                    stdout = "done\n"
                    stderr = ""

                return _Result()

            argv = [
                "run_single_task_light_lane_batch.py",
                "--task-ids",
                "11,12,13,14,15,16",
                "--max-tasks-per-shard",
                "4",
                "--llm-timeout-sec",
                "300",
                "--rolling-timeout-backoff-threshold",
                "0.5",
                "--rolling-timeout-backoff-min-observed-tasks",
                "4",
                "--rolling-timeout-backoff-sec",
                "180",
                "--rolling-shard-reduction-factor",
                "0.5",
                "--out-dir",
                str(out_dir),
            ]
            with mock.patch.object(batch, "_repo_root", return_value=root), mock.patch.object(
                batch, "_selected_task_ids", return_value=[11, 12, 13, 14, 15, 16]
            ), mock.patch.object(batch, "_run_command", side_effect=fake_run_command), mock.patch.object(sys, "argv", argv):
                rc = batch.main()

            self.assertEqual(1, rc)
            self.assertEqual(2, len(commands))
            self.assertEqual("11,12,13,14", commands[0][commands[0].index("--task-ids") + 1])
            self.assertEqual("15,16", commands[1][commands[1].index("--task-ids") + 1])
            self.assertEqual("480", commands[1][commands[1].index("--llm-timeout-sec") + 1])
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(1, summary["rolling_extract"]["backoff_adjustment_count"])
            self.assertEqual(480, summary["rolling_extract"]["current_llm_timeout_sec"])
            self.assertEqual(2, summary["rolling_extract"]["current_max_tasks_per_shard"])


if __name__ == "__main__":
    unittest.main()
