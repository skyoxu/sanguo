#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
PYTHON_DIR = REPO_ROOT / "scripts" / "python"
for candidate in (SC_DIR, PYTHON_DIR):
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


artifact_schema = _load_module("artifact_schema_test_module", "scripts/sc/_artifact_schema.py")
inspect_run = _load_module("inspect_run_test_module", "scripts/python/inspect_run.py")

FIXTURE_ROOT = REPO_ROOT / "scripts" / "sc" / "tests" / "fixtures" / "run_replay"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_pipeline_bundle(
    root: Path,
    *,
    task_id: str = "7",
    run_id: str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    status: str = "ok",
    include_run_completed: bool = True,
) -> tuple[Path, Path]:
    out_dir = root / "logs" / "ci" / "2026-03-22" / f"sc-review-pipeline-task-{task_id}-{run_id}"
    latest_dir = root / "logs" / "ci" / "2026-03-22" / f"sc-review-pipeline-task-{task_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    latest_dir.mkdir(parents=True, exist_ok=True)
    (latest_dir / "latest.json").write_text(
        json.dumps(
            {
                "task_id": task_id,
                "run_id": run_id,
                "status": status,
                "date": "2026-03-22",
                "started_at_utc": "2026-03-22T10:00:00+00:00",
                "finished_at_utc": "2026-03-22T10:01:00+00:00" if include_run_completed else "",
                "run_type": "deterministic-only",
                "latest_out_dir": str(out_dir),
                "summary_path": str(out_dir / "summary.json"),
                "execution_context_path": str(out_dir / "execution-context.json"),
                "repair_guide_json_path": str(out_dir / "repair-guide.json"),
                "repair_guide_md_path": str(out_dir / "repair-guide.md"),
                "marathon_state_path": str(out_dir / "marathon-state.json"),
                "run_events_path": str(out_dir / "run-events.jsonl"),
                "harness_capabilities_path": str(out_dir / "harness-capabilities.json"),
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    (out_dir / "summary.json").write_text(
        json.dumps(
            {
                "cmd": "sc-review-pipeline",
                "task_id": task_id,
                "requested_run_id": run_id,
                "run_id": run_id,
                "allow_overwrite": False,
                "force_new_run_id": False,
                "status": status,
                "started_at_utc": "2026-03-22T10:00:00+00:00",
                "finished_at_utc": "2026-03-22T10:01:00+00:00" if include_run_completed else "",
                "elapsed_sec": 12,
                "run_type": "deterministic-only",
                "reason": "pipeline_clean" if status == "ok" else "step_failed",
                "reuse_mode": "none",
                "steps": [
                    {
                        "name": "sc-test",
                        "cmd": ["py", "-3", "scripts/sc/test.py"],
                        "rc": 0,
                        "status": "ok",
                        "log": str(out_dir / "sc-test.log"),
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    (out_dir / "execution-context.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "cmd": "sc-review-pipeline",
                "date": "2026-03-22",
                "task_id": task_id,
                "requested_run_id": run_id,
                "run_id": run_id,
                "status": status,
                "run_type": "deterministic-only",
                "reason": "pipeline_clean" if status == "ok" else "step_failed",
                "reuse_mode": "none",
                "started_at_utc": "2026-03-22T10:00:00+00:00",
                "finished_at_utc": "2026-03-22T10:01:00+00:00" if include_run_completed else "",
                "delivery_profile": "fast-ship",
                "security_profile": "host-safe",
                "failed_step": "" if status == "ok" else "sc-test",
                "paths": {},
                "git": {},
                "recovery": {},
                "marathon": {},
                "agent_review": {},
                "llm_review": {},
                "approval": {},
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    (out_dir / "repair-guide.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "status": "not-needed" if status == "ok" else "needs-fix",
                "task_id": task_id,
                "summary_status": status,
                "failed_step": "" if status == "ok" else "sc-test",
                "approval": {},
                "recommendations": [] if status == "ok" else [{"id": "fix", "title": "fix", "why": "because"}],
                "generated_from": {},
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    (out_dir / "repair-guide.md").write_text("# repair\n", encoding="utf-8")
    (out_dir / "marathon-state.json").write_text("{}", encoding="utf-8")
    run_events = []
    if include_run_completed:
        run_events.append(
            {
                "schema_version": "1.0.0",
                "ts": "2026-03-22T10:01:00Z",
                "event": "run_completed",
                "task_id": task_id,
                "run_id": run_id,
                "delivery_profile": "fast-ship",
                "security_profile": "host-safe",
                "step_name": None,
                "status": status,
                "details": {"agent_review_rc": 0},
            }
        )
    (out_dir / "run-events.jsonl").write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in run_events) + ("\n" if run_events else ""),
        encoding="utf-8",
    )
    (out_dir / "harness-capabilities.json").write_text("{}", encoding="utf-8")
    (out_dir / "sc-test.log").write_text("ok\n", encoding="utf-8")
    return latest_dir / "latest.json", out_dir


def _write_local_hard_bundle(root: Path, *, run_id: str = "run-local", status: str = "fail", failed_step: str = "run-dotnet") -> tuple[Path, Path]:
    out_dir = root / "logs" / "ci" / "2026-03-22" / "local-hard-checks-run-local"
    latest_path = root / "logs" / "ci" / "2026-03-22" / "local-hard-checks-latest.json"
    out_dir.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(
        json.dumps(
            {
                "cmd": "local-hard-checks",
                "task_id": "repo",
                "run_id": run_id,
                "status": status,
                "out_dir": str(out_dir),
                "summary_path": str(out_dir / "summary.json"),
                "execution_context_path": str(out_dir / "execution-context.json"),
                "repair_guide_json_path": str(out_dir / "repair-guide.json"),
                "repair_guide_md_path": str(out_dir / "repair-guide.md"),
                "run_events_path": str(out_dir / "run-events.jsonl"),
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    (out_dir / "summary.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "protocol_version": "1.0.0",
                "cmd": "local-hard-checks",
                "task_id": "repo",
                "requested_run_id": run_id,
                "run_id": run_id,
                "delivery_profile": "fast-ship",
                "security_profile": "host-safe",
                "status": status,
                "failed_step": failed_step,
                "started_at": "2026-03-22T10:00:00Z",
                "finished_at": "2026-03-22T10:01:00Z",
                "out_dir": str(out_dir),
                "steps": [
                    {
                        "name": "run-dotnet",
                        "cmd": ["dotnet", "test"],
                        "rc": 1 if status == "fail" else 0,
                        "status": status,
                        "log": str(out_dir / "run-dotnet.log"),
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    (out_dir / "execution-context.json").write_text(
        json.dumps(
            {
                "cmd": "local-hard-checks",
                "task_id": "repo",
                "requested_run_id": run_id,
                "run_id": run_id,
                "delivery_profile": "fast-ship",
                "security_profile": "host-safe",
                "status": status,
                "failed_step": failed_step,
                "artifacts": {
                    "summary_json": str(out_dir / "summary.json"),
                    "execution_context_json": str(out_dir / "execution-context.json"),
                    "repair_guide_json": str(out_dir / "repair-guide.json"),
                    "repair_guide_md": str(out_dir / "repair-guide.md"),
                    "run_events_jsonl": str(out_dir / "run-events.jsonl"),
                    "harness_capabilities_json": str(out_dir / "harness-capabilities.json"),
                    "run_id_txt": str(out_dir / "run_id.txt"),
                },
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    (out_dir / "repair-guide.json").write_text(
        json.dumps(
            {
                "cmd": "local-hard-checks",
                "task_id": "repo",
                "run_id": run_id,
                "status": status,
                "failed_step": failed_step,
                "artifacts": {
                    "summary_json": str(out_dir / "summary.json"),
                    "execution_context_json": str(out_dir / "execution-context.json"),
                },
                "next_actions": ["fix dotnet"],
                "rerun_command": ["py", "-3", "scripts/python/dev_cli.py", "run-local-hard-checks"],
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    (out_dir / "repair-guide.md").write_text("# repair\n", encoding="utf-8")
    (out_dir / "run-events.jsonl").write_text("", encoding="utf-8")
    (out_dir / "harness-capabilities.json").write_text("{}", encoding="utf-8")
    (out_dir / "run_id.txt").write_text(f"{run_id}\n", encoding="utf-8")
    (out_dir / "run-dotnet.log").write_text("fail\n", encoding="utf-8")
    return latest_path, out_dir


class RunArtifactSchemaTests(unittest.TestCase):
    def test_pipeline_fixture_sidecars_should_validate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            latest_path, out_dir = _write_pipeline_bundle(root)
            latest = _read_json(latest_path)
            artifact_schema.validate_pipeline_latest_index_payload(latest)
            artifact_schema.validate_pipeline_execution_context_payload(_read_json(out_dir / "execution-context.json"))
            artifact_schema.validate_pipeline_repair_guide_payload(_read_json(out_dir / "repair-guide.json"))

    def test_local_hard_fixture_sidecars_should_validate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            latest_path, out_dir = _write_local_hard_bundle(root)
            latest = _read_json(latest_path)
            artifact_schema.validate_local_hard_checks_latest_index_payload(latest)
            artifact_schema.validate_local_hard_checks_execution_context_payload(_read_json(out_dir / "execution-context.json"))
            artifact_schema.validate_local_hard_checks_repair_guide_payload(_read_json(out_dir / "repair-guide.json"))

    def test_pipeline_execution_context_should_accept_extended_chapter6_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _latest_path, out_dir = _write_pipeline_bundle(root)
            payload = _read_json(out_dir / "execution-context.json")
            payload["diagnostics"] = {
                "profile_drift": {
                    "previous_delivery_profile": "standard",
                    "previous_security_profile": "strict",
                    "current_delivery_profile": "fast-ship",
                    "current_security_profile": "host-safe",
                },
                "acceptance_preflight": {
                    "status": "ok",
                    "reason": "ready",
                },
                "waste_signals": {
                    "unit_failed_but_engine_lane_ran": True,
                },
                "rerun_guard": {
                    "kind": "deterministic_green_llm_not_clean",
                    "blocked": True,
                    "recommended_path": "llm-only",
                    "override": "allow-full-rerun",
                    "fingerprint": "sc-test|unit|2|compile_error",
                },
                "reuse_decision": {
                    "mode": "deterministic-only-reuse",
                    "blocked": False,
                },
                "llm_timeout_memory": {
                    "overrides": {
                        "code-reviewer": 480,
                    },
                    "planned_agents": [
                        "code-reviewer",
                        "architecture-reviewer",
                    ]
                },
                "llm_retry_stop_loss": {
                    "blocked": True,
                    "timed_out_step": "sc-llm-review",
                    "retry_count": 1,
                    "deterministic_ok": True,
                },
            }
            artifact_schema.validate_pipeline_execution_context_payload(payload)

    def test_pipeline_latest_index_should_reject_unbudgeted_field(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            latest_path, _out_dir = _write_pipeline_bundle(root)
            latest = _read_json(latest_path)
            latest["unexpected_field"] = "drift"
            with self.assertRaises(artifact_schema.ArtifactSchemaError):
                artifact_schema.validate_pipeline_latest_index_payload(latest)


class InspectRunTests(unittest.TestCase):
    def test_inspect_run_should_report_pipeline_fixture_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_pipeline_bundle(root)
            latest = "logs/ci/2026-03-22/sc-review-pipeline-task-7/latest.json"
            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, latest=latest)
            self.assertEqual(0, rc)
            self.assertEqual("pipeline", payload["kind"])
            self.assertEqual("ok", payload["status"])
            self.assertEqual("ok", payload["failure"]["code"])
            self.assertEqual("7", payload["task_id"])
            self.assertEqual("not-needed", payload["repair_status"])

    def test_inspect_run_should_fail_when_ok_latest_has_no_run_completed_event(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_pipeline_bundle(root, include_run_completed=False)
            latest = "logs/ci/2026-03-22/sc-review-pipeline-task-7/latest.json"
            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, latest=latest)
            self.assertEqual(1, rc)
            self.assertEqual("fail", payload["status"])
            self.assertEqual("artifact-incomplete", payload["failure"]["code"])
            self.assertEqual("rerun", payload["chapter6_hints"]["next_action"])
            self.assertEqual("planned_only_incomplete", payload["latest_summary_signals"]["reason"]) if payload["latest_summary_signals"].get("run_type") == "planned-only" else None

    def test_inspect_run_should_expose_recent_failure_summary_and_block_repeat_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for run_id in ("11111111111111111111111111111111", "22222222222222222222222222222222"):
                latest_path, out_dir = _write_pipeline_bundle(root, task_id="9", run_id=run_id, status="fail")
                summary = _read_json(out_dir / "summary.json")
                summary["reason"] = "step_failed:sc-test"
                summary["steps"] = [
                    {
                        "name": "sc-test",
                        "cmd": ["py", "-3", "scripts/sc/test.py"],
                        "rc": 2,
                        "status": "fail",
                        "log": str(out_dir / "sc-test.log"),
                        "summary_file": str(out_dir / "child-artifacts" / "sc-test" / "summary.json"),
                    }
                ]
                (out_dir / "child-artifacts" / "sc-test").mkdir(parents=True, exist_ok=True)
                (out_dir / "child-artifacts" / "sc-test" / "summary.json").write_text(
                    json.dumps(
                        {
                            "cmd": "sc-test",
                            "status": "fail",
                            "steps": [
                                {
                                    "name": "unit",
                                    "status": "fail",
                                    "rc": 2,
                                    "reason": "compile_error",
                                }
                            ],
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                execution_context = _read_json(out_dir / "execution-context.json")
                execution_context["status"] = "fail"
                (out_dir / "execution-context.json").write_text(json.dumps(execution_context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                repair_guide = _read_json(out_dir / "repair-guide.json")
                repair_guide["status"] = "needs-fix"
                (out_dir / "repair-guide.json").write_text(json.dumps(repair_guide, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                latest = _read_json(latest_path)
                latest["status"] = "fail"
                (latest_path).write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            latest = "logs/ci/2026-03-22/sc-review-pipeline-task-9/latest.json"
            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, latest=latest)

            self.assertEqual(1, rc)
            self.assertEqual(2, payload["recent_failure_summary"]["same_family_count"])
            self.assertTrue(payload["recent_failure_summary"]["stop_full_rerun_recommended"])
            self.assertEqual("inspect", payload["chapter6_hints"]["next_action"])
            self.assertEqual("recent_failure_summary", payload["chapter6_hints"]["blocked_by"])
            self.assertTrue(payload["chapter6_hints"]["rerun_forbidden"])
            self.assertEqual(
                "Recent failed runs already repeat the same failure family; inspect the repeated fingerprint and fix the root cause before paying for another full rerun.",
                payload["recommended_action_why"],
            )

    def test_inspect_run_should_classify_local_hard_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_local_hard_bundle(root)
            latest = "logs/ci/2026-03-22/local-hard-checks-latest.json"
            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, latest=latest)
            self.assertEqual(1, rc)
            self.assertEqual("local-hard-checks", payload["kind"])
            self.assertEqual("fail", payload["status"])
            self.assertEqual("step-failed", payload["failure"]["code"])
            self.assertEqual("run-dotnet", payload["failed_step"])

    def test_inspect_run_should_resolve_explicit_latest_bundle_outside_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            latest_path, _out_dir = _write_pipeline_bundle(root)
            rc, payload = inspect_run.inspect_run_artifacts(repo_root=REPO_ROOT, latest=str(latest_path))
            self.assertEqual(0, rc)
            self.assertEqual("ok", payload["failure"]["code"])

    def test_inspect_run_should_expose_latest_summary_signals_from_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-56-run-a"
            latest_dir = root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-56"
            out_dir.mkdir(parents=True, exist_ok=True)
            latest_dir.mkdir(parents=True, exist_ok=True)

            (latest_dir / "latest.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "run_id": "run-a",
                        "status": "fail",
                        "latest_out_dir": str(out_dir),
                        "summary_path": str(out_dir / "summary.json"),
                        "execution_context_path": str(out_dir / "execution-context.json"),
                        "repair_guide_json_path": str(out_dir / "repair-guide.json"),
                        "repair_guide_md_path": str(out_dir / "repair-guide.md"),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (out_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "cmd": "sc-review-pipeline",
                        "task_id": "56",
                        "requested_run_id": "run-a",
                        "run_id": "run-a",
                        "allow_overwrite": False,
                        "force_new_run_id": False,
                        "status": "fail",
                        "started_at_utc": "2026-04-06T00:00:00+00:00",
                        "finished_at_utc": "2026-04-06T00:00:05+00:00",
                        "elapsed_sec": 5,
                        "run_type": "full",
                        "reason": "rerun_blocked:deterministic_green_llm_not_clean",
                        "reuse_mode": "deterministic-only-reuse",
                        "diagnostics": {
                            "rerun_guard": {"blocked": True},
                            "llm_timeout_memory": {"code-reviewer": 480},
                        },
                        "steps": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (out_dir / "execution-context.json").write_text(
                json.dumps(
                    {
                        "task_id": "56",
                        "run_id": "run-a",
                        "status": "fail",
                        "schema_version": "1.0.0",
                        "date": "2026-04-06",
                        "cmd": "sc-review-pipeline",
                        "approval": {},
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "failed_step": "",
                        "paths": {},
                        "git": {},
                        "recovery": {},
                        "marathon": {},
                        "llm_review": {},
                        "agent_review": {},
                        "requested_run_id": "run-a",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (out_dir / "repair-guide.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "status": "needs-fix",
                        "summary_status": "fail",
                        "failed_step": "",
                        "task_id": "56",
                        "approval": {},
                        "generated_from": {},
                        "recommendations": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (out_dir / "repair-guide.md").write_text("# repair\n", encoding="utf-8")

            rc, payload = inspect_run.inspect_run_artifacts(
                repo_root=root,
                latest="logs/ci/2026-04-06/sc-review-pipeline-task-56/latest.json",
            )

            self.assertEqual(1, rc)
            self.assertEqual(
                {
                    "reason": "rerun_blocked:deterministic_green_llm_not_clean",
                    "run_type": "full",
                    "reuse_mode": "deterministic-only-reuse",
                    "failure_kind": "step-failed",
                    "artifact_integrity_kind": "",
                    "diagnostics_keys": ["llm_timeout_memory", "rerun_guard"],
                },
                payload.get("latest_summary_signals"),
            )
            self.assertEqual(
                {
                    "next_action": "needs-fix-fast",
                    "can_skip_6_7": True,
                    "can_go_to_6_8": True,
                    "blocked_by": "rerun_guard",
                    "rerun_forbidden": True,
                    "rerun_override_flag": "--allow-full-rerun",
                },
                payload.get("chapter6_hints"),
            )
            self.assertEqual(
                "Deterministic evidence is already green; do not pay for another full 6.7. Continue with 6.8 or needs-fix-fast.",
                payload.get("recommended_action_why"),
            )

    def test_inspect_run_should_accept_legacy_pipeline_summary_without_chapter6_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            latest_path, out_dir = _write_pipeline_bundle(
                root,
                task_id="14",
                run_id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                status="ok",
            )
            legacy_summary = _read_json(out_dir / "summary.json")
            legacy_summary.pop("reason", None)
            legacy_summary.pop("reuse_mode", None)
            legacy_summary.pop("elapsed_sec", None)
            (out_dir / "summary.json").write_text(
                json.dumps(legacy_summary, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, latest=str(latest_path))

            self.assertEqual(0, rc)
            self.assertEqual("ok", payload["status"])
            self.assertEqual("ok", payload["failure"]["code"])
            self.assertEqual([], payload["validation_errors"])
            self.assertEqual(
                {
                    "reason": "pipeline_clean",
                    "run_type": "deterministic-only",
                    "reuse_mode": "none",
                    "failure_kind": "ok",
                    "artifact_integrity_kind": "",
                    "diagnostics_keys": [],
                },
                payload["latest_summary_signals"],
            )
            self.assertEqual(
                {
                    "next_action": "continue",
                    "can_skip_6_7": True,
                    "can_go_to_6_8": False,
                    "blocked_by": "",
                    "rerun_forbidden": False,
                    "rerun_override_flag": "",
                },
                payload["chapter6_hints"],
            )
            self.assertEqual(
                "Inspection is green; continue local work without reopening the full review pipeline.",
                payload["recommended_action_why"],
            )

    def test_inspect_run_should_route_repeat_review_needs_fix_rerun_block_to_needs_fix_fast(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            latest_path, out_dir = _write_pipeline_bundle(
                root,
                task_id="14",
                run_id="cccccccccccccccccccccccccccccccc",
                status="fail",
            )
            summary = _read_json(out_dir / "summary.json")
            summary["reason"] = "rerun_blocked:repeat_review_needs_fix"
            summary["diagnostics"] = {
                "rerun_guard": {
                    "kind": "repeat_review_needs_fix",
                    "blocked": True,
                    "recommended_path": "needs-fix-fast",
                }
            }
            (out_dir / "summary.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, latest=str(latest_path))

            self.assertEqual(1, rc)
            self.assertEqual("rerun_blocked:repeat_review_needs_fix", payload["latest_summary_signals"]["reason"])

            self.assertEqual("needs-fix-fast", payload["recommended_action"])

            self.assertEqual(
                {
                    "next_action": "needs-fix-fast",
                    "can_skip_6_7": True,
                    "can_go_to_6_8": True,
                    "blocked_by": "rerun_guard",
                    "rerun_forbidden": True,
                    "rerun_override_flag": "--allow-full-rerun",
                },
                payload["chapter6_hints"],
            )
            self.assertIn("needs-fix-fast", payload["recommended_action_why"])

            self.assertEqual(
                "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
                payload["recommended_command"],
            )
            self.assertIn(
                "py -3 scripts/sc/run_review_pipeline.py --task-id 14",
                payload["forbidden_commands"],
            )

    def test_inspect_run_should_prefer_summary_recommendation_fields_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            latest_path, out_dir = _write_pipeline_bundle(
                root,
                task_id="14",
                run_id="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                status="fail",
            )
            summary = _read_json(out_dir / "summary.json")
            summary["reason"] = "rerun_blocked:repeat_review_needs_fix"
            summary["recommended_action"] = "needs-fix-fast"
            summary["recommended_action_why"] = "summary owns the recommendation"
            summary["candidate_commands"] = {
                "needs_fix_fast": "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
                "rerun": "py -3 scripts/sc/run_review_pipeline.py --task-id 14",
            }
            summary["recommended_command"] = "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1"
            summary["forbidden_commands"] = ["py -3 scripts/sc/run_review_pipeline.py --task-id 14"]
            summary["chapter6_hints"] = {
                "next_action": "needs-fix-fast",
                "can_skip_6_7": True,
                "can_go_to_6_8": True,
                "blocked_by": "rerun_guard",
                "rerun_forbidden": True,
                "rerun_override_flag": "--allow-full-rerun",
            }
            (out_dir / "summary.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, latest=str(latest_path))

            self.assertEqual(1, rc)
            self.assertEqual("needs-fix-fast", payload["recommended_action"])
            self.assertEqual(
                "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
                payload["recommended_command"],
            )
            self.assertEqual(
                ["py -3 scripts/sc/run_review_pipeline.py --task-id 14"],
                payload["forbidden_commands"],
            )
            self.assertEqual(
                "py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 14 --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
                payload["candidate_commands"]["needs_fix_fast"],
            )

    def test_inspect_run_should_surface_bottleneck_fields_from_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            latest_path, out_dir = _write_pipeline_bundle(
                root,
                task_id="14",
                run_id="ffffffffffffffffffffffffffffffff",
                status="fail",
            )
            summary = _read_json(out_dir / "summary.json")
            summary["reason"] = "rerun_blocked:repeat_review_needs_fix"
            summary["dominant_cost_phase"] = "sc-llm-review"
            summary["step_duration_totals"] = {
                "sc-llm-review": 12.5,
                "sc-test": 4.0,
            }
            summary["step_duration_avg"] = {
                "sc-llm-review": 12.5,
                "sc-test": 4.0,
            }
            (out_dir / "summary.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, latest=str(latest_path))

            self.assertEqual(1, rc)
            self.assertEqual("sc-llm-review", payload["dominant_cost_phase"])
            self.assertEqual(
                {"sc-llm-review": 12.5, "sc-test": 4.0},
                payload["step_duration_totals"],
            )
            self.assertEqual(
                {"sc-llm-review": 12.5, "sc-test": 4.0},
                payload["step_duration_avg"],
            )


    def test_inspect_run_should_route_llm_retry_stop_loss_from_execution_context_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            latest_path, out_dir = _write_pipeline_bundle(
                root,
                task_id="14",
                run_id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                status="fail",
            )
            summary = _read_json(out_dir / "summary.json")
            summary["reason"] = "step_failed:sc-llm-review"
            summary["steps"] = [
                {
                    "name": "sc-test",
                    "cmd": ["py", "-3", "scripts/sc/test.py"],
                    "rc": 0,
                    "status": "ok",
                    "log": str(out_dir / "sc-test.log"),
                },
                {
                    "name": "sc-acceptance-check",
                    "cmd": ["py", "-3", "scripts/sc/acceptance_check.py"],
                    "rc": 0,
                    "status": "ok",
                    "log": str(out_dir / "sc-acceptance.log"),
                },
                {
                    "name": "sc-llm-review",
                    "cmd": ["py", "-3", "scripts/sc/llm_review.py"],
                    "rc": 124,
                    "status": "fail",
                    "log": str(out_dir / "sc-llm-review.log"),
                },
            ]
            summary.pop("diagnostics", None)
            (out_dir / "summary.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            execution_context = _read_json(out_dir / "execution-context.json")
            execution_context["failed_step"] = "sc-llm-review"
            execution_context["diagnostics"] = {
                "llm_retry_stop_loss": {
                    "blocked": True,
                    "step_name": "sc-llm-review",
                }
            }
            (out_dir / "execution-context.json").write_text(
                json.dumps(execution_context, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, latest=str(latest_path))

            self.assertEqual(1, rc)
            self.assertEqual(
                {
                    "reason": "step_failed:sc-llm-review",
                    "run_type": "deterministic-only",
                    "reuse_mode": "none",
                    "failure_kind": "step-failed",
                    "artifact_integrity_kind": "",
                    "diagnostics_keys": ["llm_retry_stop_loss"],
                },
                payload["latest_summary_signals"],
            )
            self.assertEqual(
                {
                    "next_action": "needs-fix-fast",
                    "can_skip_6_7": True,
                    "can_go_to_6_8": True,
                    "blocked_by": "llm_retry_stop_loss",
                    "rerun_forbidden": True,
                    "rerun_override_flag": "--allow-full-rerun",
                },
                payload["chapter6_hints"],
            )
            self.assertEqual(
                "This run already stopped after the first costly llm timeout; continue with the narrow llm-only closure path instead of reopening deterministic steps.",
                payload["recommended_action_why"],
            )

    def test_inspect_run_should_route_sc_test_retry_stop_loss_from_execution_context_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            latest_path, out_dir = _write_pipeline_bundle(
                root,
                task_id="14",
                run_id="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                status="fail",
            )
            summary = _read_json(out_dir / "summary.json")
            summary["reason"] = "step_failed:sc-test"
            summary["steps"] = [
                {
                    "name": "sc-test",
                    "cmd": ["py", "-3", "scripts/sc/test.py"],
                    "rc": 1,
                    "status": "fail",
                    "log": str(out_dir / "sc-test.log"),
                }
            ]
            summary.pop("diagnostics", None)
            (out_dir / "summary.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            execution_context = _read_json(out_dir / "execution-context.json")
            execution_context["failed_step"] = "sc-test"
            execution_context["diagnostics"] = {
                "sc_test_retry_stop_loss": {
                    "blocked": True,
                    "step_name": "sc-test",
                }
            }
            (out_dir / "execution-context.json").write_text(
                json.dumps(execution_context, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, latest=str(latest_path))

            self.assertEqual(1, rc)
            self.assertEqual(
                {
                    "reason": "step_failed:sc-test",
                    "run_type": "deterministic-only",
                    "reuse_mode": "none",
                    "failure_kind": "step-failed",
                    "artifact_integrity_kind": "",
                    "diagnostics_keys": ["sc_test_retry_stop_loss"],
                },
                payload["latest_summary_signals"],
            )
            self.assertEqual(
                {
                    "next_action": "rerun",
                    "can_skip_6_7": False,
                    "can_go_to_6_8": False,
                    "blocked_by": "sc_test_retry_stop_loss",
                    "rerun_forbidden": True,
                    "rerun_override_flag": "",
                },
                payload["chapter6_hints"],
            )
            self.assertEqual(
                "The pipeline already proved the unit root cause and stopped the same-run retry; fix the unit issue first, then start a fresh run.",
                payload["recommended_action_why"],
            )

    def test_inspect_run_should_prefer_recent_real_latest_over_newer_dry_run_latest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            older_latest, older_out = _write_pipeline_bundle(
                root,
                task_id="14",
                run_id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                status="ok",
            )
            older_latest_copy = root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14" / "latest.json"
            older_latest_copy.parent.mkdir(parents=True, exist_ok=True)
            older_latest_copy.write_text(older_latest.read_text(encoding="utf-8"), encoding="utf-8")
            newer_latest, newer_out = _write_pipeline_bundle(
                root,
                task_id="14",
                run_id="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                status="ok",
            )
            dry_summary = _read_json(newer_out / "summary.json")
            dry_summary["reason"] = "in_progress"
            dry_summary["steps"] = [
                {
                    "name": "sc-test",
                    "cmd": ["py", "-3", "scripts/sc/test.py"],
                    "rc": 0,
                    "status": "planned",
                    "log": str(newer_out / "sc-test.log"),
                },
                {
                    "name": "sc-acceptance-check",
                    "cmd": ["py", "-3", "scripts/sc/acceptance_check.py"],
                    "rc": 0,
                    "status": "planned",
                    "log": str(newer_out / "sc-acceptance-check.log"),
                },
            ]
            (newer_out / "summary.json").write_text(
                json.dumps(dry_summary, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            newer_latest.touch()

            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, kind="pipeline", task_id="14")

            self.assertEqual(0, rc)
            self.assertEqual("ok", payload["failure"]["code"])
            self.assertEqual(older_latest_copy.relative_to(root).as_posix(), payload["paths"]["latest"])
            self.assertEqual(older_out.relative_to(root).as_posix(), payload["paths"]["out_dir"])

    def test_inspect_run_should_prefer_recent_real_latest_over_newer_planned_only_latest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            older_latest, older_out = _write_pipeline_bundle(
                root,
                task_id="14",
                run_id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                status="ok",
            )
            older_latest_copy = root / "logs" / "ci" / "2026-04-06" / "sc-review-pipeline-task-14" / "latest.json"
            older_latest_copy.parent.mkdir(parents=True, exist_ok=True)
            older_latest_copy.write_text(older_latest.read_text(encoding="utf-8"), encoding="utf-8")

            newer_latest, newer_out = _write_pipeline_bundle(
                root,
                task_id="14",
                run_id="dddddddddddddddddddddddddddddddd",
                status="ok",
            )
            planned_summary = _read_json(newer_out / "summary.json")
            planned_summary["steps"] = [
                {"name": "sc-test", "cmd": ["py", "-3", "scripts/sc/test.py"], "rc": 0, "status": "planned"},
                {"name": "sc-acceptance-check", "cmd": ["py", "-3", "scripts/sc/acceptance_check.py"], "rc": 0, "status": "planned"},
                {"name": "sc-llm-review", "cmd": ["py", "-3", "scripts/sc/llm_review.py"], "rc": 0, "status": "planned"},
            ]
            planned_summary["finished_at_utc"] = "2026-03-22T10:01:00+00:00"
            planned_summary.pop("run_type", None)
            planned_summary.pop("reason", None)
            (newer_out / "summary.json").write_text(
                json.dumps(planned_summary, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            newer_latest_payload = _read_json(newer_latest)
            newer_latest_payload["run_type"] = "planned-only"
            newer_latest_payload["reason"] = "planned_only_incomplete"
            newer_latest.write_text(
                json.dumps(newer_latest_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            newer_latest.touch()

            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, kind="pipeline", task_id="14")

            self.assertEqual(0, rc)
            self.assertEqual("ok", payload["failure"]["code"])
            self.assertEqual(older_latest_copy.relative_to(root).as_posix(), payload["paths"]["latest"])
            self.assertEqual(older_out.relative_to(root).as_posix(), payload["paths"]["out_dir"])

    def test_inspect_run_should_fail_planned_only_terminal_bundle_even_when_latest_status_is_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            latest_path, out_dir = _write_pipeline_bundle(root, task_id="14", run_id="cccccccccccccccccccccccccccccccc", status="ok")
            summary = _read_json(out_dir / "summary.json")
            summary["steps"] = [
                {"name": "sc-test", "cmd": ["py", "-3", "scripts/sc/test.py"], "rc": 0, "status": "planned"},
                {"name": "sc-acceptance-check", "cmd": ["py", "-3", "scripts/sc/acceptance_check.py"], "rc": 0, "status": "planned"},
                {"name": "sc-llm-review", "cmd": ["py", "-3", "scripts/sc/llm_review.py"], "rc": 0, "status": "planned"},
            ]
            summary.pop("reason", None)
            summary.pop("run_type", None)
            summary["finished_at_utc"] = ""
            (out_dir / "summary.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            latest = _read_json(latest_path)
            latest["reason"] = "in_progress"
            latest_path.write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            rc, payload = inspect_run.inspect_run_artifacts(repo_root=root, latest=str(latest_path))

            self.assertEqual(1, rc)
            self.assertEqual("fail", payload["status"])
            self.assertEqual("artifact-incomplete", payload["failure"]["code"])
            self.assertEqual(
                {
                    "reason": "planned_only_incomplete",
                    "run_type": "planned-only",
                    "reuse_mode": "none",
                    "failure_kind": "artifact-incomplete",
                    "artifact_integrity_kind": "planned_only_incomplete",
                    "diagnostics_keys": [],
                },
                payload["latest_summary_signals"],
            )
            self.assertEqual(
                {
                    "next_action": "rerun",
                    "can_skip_6_7": False,
                    "can_go_to_6_8": False,
                    "blocked_by": "artifact_integrity",
                    "rerun_forbidden": False,
                    "rerun_override_flag": "",
                },
                payload["chapter6_hints"],
            )
            self.assertEqual(
                "The latest bundle only contains planned-only evidence; rerun 6.7 from a real producer bundle before trusting later Chapter 6 steps.",
                payload["recommended_action_why"],
            )


if __name__ == "__main__":
    unittest.main()
