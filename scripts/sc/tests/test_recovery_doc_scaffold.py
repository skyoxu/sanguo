#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


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


scaffold = _load_module("recovery_doc_scaffold_module", "scripts/python/_recovery_doc_scaffold.py")
validator = _load_module("validate_recovery_docs_module", "scripts/python/validate_recovery_docs.py")


class RecoveryDocScaffoldTests(unittest.TestCase):
    def _write_latest(self, root: Path, task_id: str, run_id: str) -> Path:
        latest_dir = root / "logs" / "ci" / "2026-03-21" / f"sc-review-pipeline-task-{task_id}"
        artifact_dir = root / "logs" / "ci" / "2026-03-21" / f"sc-review-pipeline-task-{task_id}-{run_id}"
        latest_dir.mkdir(parents=True, exist_ok=True)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        latest_path = latest_dir / "latest.json"
        latest_path.write_text(
            json.dumps(
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "latest_out_dir": str(artifact_dir),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return latest_path

    def test_execution_plan_scaffold_should_infer_latest_links_and_validate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "execution-plans").mkdir(parents=True, exist_ok=True)
            (root / "decision-logs").mkdir(parents=True, exist_ok=True)
            self._write_latest(root, "7", "abc123def456")
            out_path = scaffold.ensure_output_path(root, "", "execution-plans", "Demo Plan")
            links = scaffold.infer_recovery_links(root=root, task_id="7")
            content = scaffold.build_execution_plan_markdown(
                root=root,
                title="Demo Plan",
                status="active",
                goal="Ship a safe baseline",
                scope="docs + scripts",
                current_step="wire recovery scaffolds",
                stop_loss="do not change summary schema",
                next_action="run validators",
                exit_criteria="validators pass",
                related_adrs=[],
                related_decision_logs=[],
                links=links,
                branch="feature/demo",
                git_head="0123456789abcdef0123456789abcdef01234567",
            )
            scaffold.write_markdown(out_path, content)
            original_root = validator.REPO_ROOT
            try:
                validator.REPO_ROOT = root
                errors = validator.validate_doc(out_path, validator.EXECUTION_PLAN_FIELDS)
            finally:
                validator.REPO_ROOT = original_root
            self.assertEqual([], errors)
            text = out_path.read_text(encoding="utf-8")
            self.assertIn("`7`", text)
            self.assertIn("`abc123def456`", text)
            self.assertIn("`logs/ci/2026-03-21/sc-review-pipeline-task-7/latest.json`", text)

    def test_decision_log_scaffold_should_emit_explained_na_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "execution-plans").mkdir(parents=True, exist_ok=True)
            (root / "decision-logs").mkdir(parents=True, exist_ok=True)
            out_path = scaffold.ensure_output_path(root, "", "decision-logs", "Decision Example")
            links = scaffold.infer_recovery_links(root=root, task_id="")
            content = scaffold.build_decision_log_markdown(
                root=root,
                title="Decision Example",
                status="proposed",
                why_now="Need a durable scaffold",
                context="Recovery docs are validated in CI",
                decision="Add generator scripts",
                consequences="Less hand-written drift",
                recovery_impact="Agents recover from generated docs faster",
                validation="validate_recovery_docs.py",
                supersedes="none",
                superseded_by="none",
                related_adrs=[],
                related_execution_plans=[],
                links=links,
                branch="feature/demo",
                git_head="fedcba9876543210fedcba9876543210fedcba98",
            )
            scaffold.write_markdown(out_path, content)
            original_root = validator.REPO_ROOT
            try:
                validator.REPO_ROOT = root
                errors = validator.validate_doc(out_path, validator.DECISION_LOG_FIELDS)
            finally:
                validator.REPO_ROOT = original_root
            self.assertEqual([], errors)
            text = out_path.read_text(encoding="utf-8")
            self.assertIn("n/a (no Taskmaster task id linked yet)", text)
            self.assertIn("n/a (no pipeline run id linked yet)", text)
            self.assertIn("n/a (no task-scoped latest.json pointer resolved yet)", text)

    def test_infer_recovery_links_should_ignore_invalid_latest_index_payload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            latest_dir = root / "logs" / "ci" / "2026-03-21" / "sc-review-pipeline-task-7"
            latest_dir.mkdir(parents=True, exist_ok=True)
            latest_path = latest_dir / "latest.json"
            latest_path.write_text(
                json.dumps(
                    {
                        "task_id": "7",
                        "latest_out_dir": 123,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            links = scaffold.infer_recovery_links(root=root, task_id="7")

            self.assertEqual("n/a (no pipeline run id linked yet)", links.run_id)
            self.assertEqual("n/a (no pipeline artifact directory resolved yet)", links.pipeline_artifacts)

    def test_validate_doc_should_allow_non_committed_logs_paths_for_runtime_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan_dir = root / "execution-plans"
            decision_dir = root / "decision-logs"
            plan_dir.mkdir(parents=True, exist_ok=True)
            decision_dir.mkdir(parents=True, exist_ok=True)
            decision_log = decision_dir / "2026-03-19-sidecar-contract.md"
            decision_log.write_text(
                "\n".join(
                    [
                        "# Decision",
                        "",
                        "- Title: Demo",
                        "- Date: 2026-03-19",
                        "- Status: accepted",
                        "- Supersedes: none",
                        "- Superseded by: none",
                        "- Branch: feature/demo",
                        "- Git Head: fedcba9876543210fedcba9876543210fedcba98",
                        "- Why now: keep recovery docs stable",
                        "- Context: runtime artifacts are not committed",
                        "- Decision: preserve logs references",
                        "- Consequences: CI must not require historical runtime logs",
                        "- Recovery impact: later agents can still read the intended path pattern",
                        "- Validation: validate_recovery_docs.py",
                        "- Related ADRs: n/a (no ADR linked yet)",
                        "- Related execution plans: n/a (no execution plan linked yet)",
                        "- Related task id(s): `1`",
                        "- Related run id: `15bcd36f5d344225a3fe0dd470752c88`",
                        "- Related latest.json: `logs/ci/2026-03-19/sc-review-pipeline-task-1/latest.json`",
                        "- Related pipeline artifacts: `logs/ci/2026-03-19/sc-review-pipeline-task-1-15bcd36f5d344225a3fe0dd470752c88/`",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            plan_path = plan_dir / "2026-03-19-phase2-agent-review-sidecar.md"
            plan_path.write_text(
                "\n".join(
                    [
                        "# Execution Plan",
                        "",
                        "- Title: Demo Plan",
                        "- Status: active",
                        "- Branch: feature/demo",
                        "- Git Head: 0123456789abcdef0123456789abcdef01234567",
                        "- Goal: Validate recovery docs",
                        "- Scope: validator behavior",
                        "- Current step: guard runtime paths",
                        "- Last completed step: reproduce CI failure",
                        "- Stop-loss: do not require historical logs to exist in checkout",
                        "- Next action: relax runtime artifact existence checks",
                        "- Recovery command: py -3 scripts/python/validate_recovery_docs.py --dir all",
                        "- Open questions: none",
                        "- Exit criteria: validator accepts historical logs/ references",
                        "- Related ADRs: n/a (no ADR linked yet)",
                        "- Related decision logs: `decision-logs/2026-03-19-sidecar-contract.md`",
                        "- Related task id(s): `1`",
                        "- Related run id: `15bcd36f5d344225a3fe0dd470752c88`",
                        "- Related latest.json: `logs/ci/2026-03-19/sc-review-pipeline-task-1/latest.json`",
                        "- Related pipeline artifacts: `logs/ci/2026-03-19/sc-review-pipeline-task-1-15bcd36f5d344225a3fe0dd470752c88/`",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            original_root = validator.REPO_ROOT
            try:
                validator.REPO_ROOT = root
                errors = validator.validate_doc(plan_path, validator.EXECUTION_PLAN_FIELDS)
            finally:
                validator.REPO_ROOT = original_root
            self.assertEqual([], errors)


if __name__ == "__main__":
    unittest.main()
