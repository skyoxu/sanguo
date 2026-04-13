#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / 'scripts' / 'sc' / 'run_review_pipeline.py'
SC_DIR = REPO_ROOT / 'scripts' / 'sc'
sys.path.insert(0, str(SC_DIR))

import run_review_pipeline as run_review_pipeline_module  # noqa: E402
from _taskmaster import TaskmasterTriplet  # noqa: E402


def _extract_out_dir(output: str) -> Path:
    match = re.search(r'\bout=([^\r\n]+)', output or '')
    if not match:
        raise AssertionError(f'missing out=... in output:\n{output}')
    return Path(match.group(1).strip())


def _stable_subprocess_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in ('DELIVERY_PROFILE', 'SECURITY_PROFILE', 'SC_PIPELINE_RUN_ID', 'SC_TEST_RUN_ID', 'SC_ACCEPTANCE_RUN_ID'):
        env.pop(key, None)
    return env


class RunReviewPipelineDeliveryProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self._review_preflight_patcher = mock.patch.object(
            run_review_pipeline_module,
            "run_review_prerequisite_check",
            return_value=None,
        )
        self._review_preflight_patcher.start()
        self.addCleanup(self._review_preflight_patcher.stop)

    @contextmanager
    def _refactor_summary_fixture(self, *, task_id: str = "1"):
        logs_root = REPO_ROOT / "logs" / "ci"
        logs_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=logs_root) as tmpdir:
            summary_dir = Path(tmpdir) / "sc-build-tdd"
            summary_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "cmd": "sc-build-tdd",
                "task": {"task_id": str(task_id)},
                "stage": "refactor",
                "status": "ok",
            }
            (summary_dir / "summary.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            yield summary_dir / "summary.json"

    def _triplet(self, *, back: dict | None = None, priority: str = "P2", title: str = "Implement feature") -> TaskmasterTriplet:
        return TaskmasterTriplet(
            task_id="1",
            master={
                "id": "1",
                "title": title,
                "priority": priority,
                "details": "Task details.",
            },
            back=back,
            gameplay=None,
            tasks_json_path="examples/taskmaster/tasks.json",
            tasks_back_path="examples/taskmaster/tasks_back.json",
            tasks_gameplay_path="examples/taskmaster/tasks_gameplay.json",
            taskdoc_path=None,
        )

    def _agent_review_payload(self, *, out_dir: Path, run_id: str, verdict: str) -> dict:
        return {
            'schema_version': '1.0.0',
            'cmd': 'sc-agent-review',
            'date': '2026-03-19',
            'reviewer': 'artifact-reviewer',
            'task_id': '1',
            'run_id': run_id,
            'pipeline_out_dir': str(out_dir),
            'pipeline_status': 'ok',
            'failed_step': '',
            'review_verdict': verdict,
            'findings': [
                {
                    'finding_id': f'agent-review-{verdict}',
                    'severity': 'medium',
                    'category': 'llm-review',
                    'owner_step': 'sc-llm-review',
                    'evidence_path': 'logs/ci/fake/review.md',
                    'message': f'agent review reported {verdict}',
                    'suggested_fix': 'rerun llm review after addressing findings',
                    'commands': [],
                }
            ] if verdict != 'pass' else [],
        }

    def test_playable_ea_should_skip_agent_review_post_hook_by_profile(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f'sc-review-pipeline-task-1-{run_id}'
            latest_path = tmp_root / 'sc-review-pipeline-task-1' / 'latest.json'
            argv = [
                str(SCRIPT),
                '--task-id',
                '1',
                '--run-id',
                run_id,
                '--delivery-profile',
                'playable-ea',
                '--reselect-profile',
                '--skip-test',
                '--skip-acceptance',
                '--skip-llm-review',
            ]
            with mock.patch.dict(os.environ, {}, clear=False), \
                mock.patch.object(sys, 'argv', argv), \
                mock.patch.object(run_review_pipeline_module, '_pipeline_run_dir', return_value=out_dir), \
                mock.patch.object(run_review_pipeline_module, '_pipeline_latest_index_path', return_value=latest_path), \
                mock.patch.object(run_review_pipeline_module, 'write_agent_review') as write_agent_review_mock:
                rc = run_review_pipeline_module.main()

            self.assertEqual(0, rc)
            summary = json.loads((out_dir / 'summary.json').read_text(encoding='utf-8'))
            latest = json.loads(latest_path.read_text(encoding='utf-8'))
            self.assertEqual('ok', summary['status'])
            write_agent_review_mock.assert_not_called()
            self.assertNotIn('agent_review_json_path', latest)
            self.assertNotIn('agent_review_md_path', latest)

    def test_agent_review_needs_fix_should_not_change_producer_summary_status(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f'sc-review-pipeline-task-1-{run_id}'
            latest_path = tmp_root / 'sc-review-pipeline-task-1' / 'latest.json'
            payload = self._agent_review_payload(out_dir=out_dir, run_id=run_id, verdict='needs-fix')
            argv = [
                str(SCRIPT),
                '--task-id',
                '1',
                '--run-id',
                run_id,
                '--delivery-profile',
                'fast-ship',
                '--reselect-profile',
                '--skip-test',
                '--skip-acceptance',
                '--skip-llm-review',
            ]
            with mock.patch.dict(os.environ, {}, clear=False), \
                mock.patch.object(sys, 'argv', argv), \
                mock.patch.object(run_review_pipeline_module, '_pipeline_run_dir', return_value=out_dir), \
                mock.patch.object(run_review_pipeline_module, '_pipeline_latest_index_path', return_value=latest_path), \
                mock.patch.object(run_review_pipeline_module, 'write_agent_review', return_value=(payload, [], [])):
                rc = run_review_pipeline_module.main()

            self.assertEqual(0, rc)
            summary = json.loads((out_dir / 'summary.json').read_text(encoding='utf-8'))
            latest = json.loads(latest_path.read_text(encoding='utf-8'))
            hook_log = (out_dir / 'sc-agent-review.log').read_text(encoding='utf-8')

            self.assertEqual('ok', summary['status'])
            self.assertNotIn('agent_review_json_path', latest)
            self.assertNotIn('agent_review_md_path', latest)
            self.assertIn('SC_AGENT_REVIEW status=needs-fix', hook_log)

    def test_standard_should_fail_when_agent_review_needs_fix(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f'sc-review-pipeline-task-1-{run_id}'
            latest_path = tmp_root / 'sc-review-pipeline-task-1' / 'latest.json'
            payload = self._agent_review_payload(out_dir=out_dir, run_id=run_id, verdict='needs-fix')
            argv = [
                str(SCRIPT),
                '--task-id',
                '1',
                '--run-id',
                run_id,
                '--delivery-profile',
                'standard',
                '--reselect-profile',
                '--skip-test',
                '--skip-acceptance',
                '--skip-llm-review',
            ]
            with mock.patch.dict(os.environ, {}, clear=False), \
                mock.patch.object(sys, 'argv', argv), \
                mock.patch.object(run_review_pipeline_module, '_pipeline_run_dir', return_value=out_dir), \
                mock.patch.object(run_review_pipeline_module, '_pipeline_latest_index_path', return_value=latest_path), \
                mock.patch.object(run_review_pipeline_module, 'write_agent_review', return_value=(payload, [], [])):
                rc = run_review_pipeline_module.main()

            self.assertEqual(1, rc)
            summary = json.loads((out_dir / 'summary.json').read_text(encoding='utf-8'))
            hook_log = (out_dir / 'sc-agent-review.log').read_text(encoding='utf-8')
            self.assertEqual('ok', summary['status'])
            self.assertIn('SC_AGENT_REVIEW status=needs-fix', hook_log)

    def test_skip_all_steps_should_generate_agent_review_sidecar(self) -> None:
        with self._refactor_summary_fixture():
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), '--task-id', '1', '--skip-test', '--skip-acceptance', '--skip-llm-review'],
                cwd=str(REPO_ROOT),
                env=_stable_subprocess_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore',
            )
        self.assertEqual(0, proc.returncode, proc.stdout)
        out_dir = _extract_out_dir(proc.stdout or '')
        summary = json.loads((out_dir / 'summary.json').read_text(encoding='utf-8'))
        agent_review = json.loads((out_dir / 'agent-review.json').read_text(encoding='utf-8'))
        latest = json.loads((REPO_ROOT / 'logs' / 'ci' / out_dir.parent.name / 'sc-review-pipeline-task-1' / 'latest.json').read_text(encoding='utf-8'))

        self.assertEqual('ok', summary['status'])
        self.assertEqual('full', summary['run_type'])
        self.assertEqual('pipeline_clean', summary['reason'])
        self.assertEqual('pass', agent_review['review_verdict'])
        self.assertEqual('full', latest['run_type'])
        self.assertEqual('pipeline_clean', latest['reason'])
        self.assertEqual(str(out_dir / 'agent-review.json'), latest['agent_review_json_path'])
        self.assertEqual(str(out_dir / 'agent-review.md'), latest['agent_review_md_path'])
        active = json.loads((REPO_ROOT / 'logs' / 'ci' / 'active-tasks' / 'task-1.active.json').read_text(encoding='utf-8'))
        self.assertEqual('full', active['latest_summary_signals']['run_type'])
        self.assertEqual('pipeline_clean', active['latest_summary_signals']['reason'])
        self.assertEqual('', active['latest_summary_signals']['artifact_integrity_kind'])

    def test_skip_agent_review_should_not_generate_sidecar_outputs(self) -> None:
        with self._refactor_summary_fixture():
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), '--task-id', '1', '--skip-test', '--skip-acceptance', '--skip-llm-review', '--skip-agent-review'],
                cwd=str(REPO_ROOT),
                env=_stable_subprocess_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore',
            )
        self.assertEqual(0, proc.returncode, proc.stdout)
        out_dir = _extract_out_dir(proc.stdout or '')
        latest = json.loads((REPO_ROOT / 'logs' / 'ci' / out_dir.parent.name / 'sc-review-pipeline-task-1' / 'latest.json').read_text(encoding='utf-8'))

        self.assertFalse((out_dir / 'agent-review.json').exists())
        self.assertFalse((out_dir / 'agent-review.md').exists())
        self.assertNotIn('agent_review_json_path', latest)
        self.assertNotIn('agent_review_md_path', latest)

    def test_dry_run_playable_ea_should_relax_acceptance_and_llm_defaults(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), '--task-id', '1', '--delivery-profile', 'playable-ea', '--reselect-profile', '--dry-run', '--skip-test'],
            cwd=str(REPO_ROOT),
            env=_stable_subprocess_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='ignore',
        )
        self.assertEqual(0, proc.returncode, proc.stdout)
        out_dir = _extract_out_dir(proc.stdout or '')
        summary = json.loads((out_dir / 'summary.json').read_text(encoding='utf-8'))
        execution_context = json.loads((out_dir / 'execution-context.json').read_text(encoding='utf-8'))
        repair_guide = json.loads((out_dir / 'repair-guide.json').read_text(encoding='utf-8'))
        steps = {str(item.get('name')): item for item in (summary.get('steps') or [])}
        acceptance_cmd = steps['sc-acceptance-check']['cmd']
        llm_cmd = steps['sc-llm-review']['cmd']

        self.assertEqual('playable-ea', execution_context['delivery_profile'])
        self.assertEqual('host-safe', execution_context['security_profile'])
        self.assertEqual('not-needed', repair_guide['status'])
        self.assertIn('--security-profile', acceptance_cmd)
        self.assertIn('host-safe', acceptance_cmd)
        self.assertNotIn('--require-executed-refs', acceptance_cmd)
        self.assertNotIn('--require-headless-e2e', acceptance_cmd)
        self.assertIn('--semantic-gate', llm_cmd)
        gate_idx = llm_cmd.index('--semantic-gate') + 1
        self.assertEqual('skip', llm_cmd[gate_idx])

    def test_dry_run_standard_should_keep_strict_acceptance_and_llm_defaults(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), '--task-id', '1', '--delivery-profile', 'standard', '--reselect-profile', '--dry-run', '--skip-test'],
            cwd=str(REPO_ROOT),
            env=_stable_subprocess_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='ignore',
        )
        self.assertEqual(0, proc.returncode, proc.stdout)
        out_dir = _extract_out_dir(proc.stdout or '')
        summary = json.loads((out_dir / 'summary.json').read_text(encoding='utf-8'))
        execution_context = json.loads((out_dir / 'execution-context.json').read_text(encoding='utf-8'))
        repair_guide = json.loads((out_dir / 'repair-guide.json').read_text(encoding='utf-8'))
        steps = {str(item.get('name')): item for item in (summary.get('steps') or [])}
        acceptance_cmd = steps['sc-acceptance-check']['cmd']
        llm_cmd = steps['sc-llm-review']['cmd']

        self.assertEqual('standard', execution_context['delivery_profile'])
        self.assertEqual('strict', execution_context['security_profile'])
        self.assertEqual('not-needed', repair_guide['status'])
        self.assertIn('--require-executed-refs', acceptance_cmd)
        self.assertIn('--require-headless-e2e', acceptance_cmd)
        self.assertIn('--security-profile', acceptance_cmd)
        self.assertIn('strict', acceptance_cmd)
        gate_idx = llm_cmd.index('--semantic-gate') + 1
        self.assertEqual('require', llm_cmd[gate_idx])

    def test_delivery_profile_should_set_default_max_step_retries_in_marathon_state(self) -> None:
        with self._refactor_summary_fixture():
            playable = subprocess.run(
                [sys.executable, str(SCRIPT), '--task-id', '1', '--delivery-profile', 'playable-ea', '--reselect-profile', '--dry-run', '--skip-agent-review', '--allow-large-change-scope-rerun'],
                cwd=str(REPO_ROOT),
                env=_stable_subprocess_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore',
            )
            self.assertEqual(1, playable.returncode, playable.stdout)
            playable_out = _extract_out_dir(playable.stdout or '')
            playable_summary = json.loads((playable_out / 'summary.json').read_text(encoding='utf-8'))
            playable_state = json.loads((playable_out / 'marathon-state.json').read_text(encoding='utf-8'))
            self.assertEqual('planned-only', playable_summary['run_type'])
            self.assertEqual('planned_only_incomplete', playable_summary['reason'])
            self.assertEqual(1, playable_state['max_step_retries'])

            standard = subprocess.run(
                [sys.executable, str(SCRIPT), '--task-id', '1', '--delivery-profile', 'standard', '--reselect-profile', '--dry-run', '--skip-agent-review', '--allow-large-change-scope-rerun'],
                cwd=str(REPO_ROOT),
                env=_stable_subprocess_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore',
            )
            self.assertEqual(1, standard.returncode, standard.stdout)
            standard_out = _extract_out_dir(standard.stdout or '')
            standard_summary = json.loads((standard_out / 'summary.json').read_text(encoding='utf-8'))
            standard_state = json.loads((standard_out / 'marathon-state.json').read_text(encoding='utf-8'))
            self.assertEqual('planned-only', standard_summary['run_type'])
            self.assertEqual('planned_only_incomplete', standard_summary['reason'])
            self.assertEqual(0, standard_state['max_step_retries'])

    def test_dry_run_fast_ship_should_apply_task_level_minimal_review_tier(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            argv = [
                str(SCRIPT),
                "--task-id",
                "1",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
                "--reselect-profile",
                "--dry-run",
                "--skip-test",
                "--skip-agent-review",
            ]
            with mock.patch.dict(os.environ, {}, clear=False), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path), \
                mock.patch.object(run_review_pipeline_module, "resolve_triplet", return_value=self._triplet(back={"semantic_review_tier": "minimal"})):
                rc = run_review_pipeline_module.main()

            self.assertEqual(0, rc)
            execution_context = json.loads((out_dir / "execution-context.json").read_text(encoding="utf-8"))
            steps = {str(item.get("name")): item for item in json.loads((out_dir / "summary.json").read_text(encoding="utf-8")).get("steps", [])}
            llm_cmd = steps["sc-llm-review"]["cmd"]

            self.assertEqual("minimal", execution_context["llm_review"]["effective_tier"])
            self.assertEqual("skip", execution_context["llm_review"]["semantic_gate"])
            self.assertIn("--semantic-gate", llm_cmd)
            self.assertEqual("skip", llm_cmd[llm_cmd.index("--semantic-gate") + 1])
            self.assertEqual("code-reviewer,security-auditor", llm_cmd[llm_cmd.index("--agents") + 1])
            self.assertEqual("summary", llm_cmd[llm_cmd.index("--diff-mode") + 1])
            self.assertNotIn("--strict", llm_cmd)

    def test_dry_run_fast_ship_should_apply_task_level_targeted_review_tier_without_semantic_reviewer(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            argv = [
                str(SCRIPT),
                "--task-id",
                "1",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
                "--reselect-profile",
                "--dry-run",
                "--skip-test",
                "--skip-agent-review",
            ]
            with mock.patch.dict(os.environ, {}, clear=False), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path), \
                mock.patch.object(run_review_pipeline_module, "resolve_triplet", return_value=self._triplet(back={"semantic_review_tier": "targeted"})):
                rc = run_review_pipeline_module.main()

            self.assertEqual(0, rc)
            execution_context = json.loads((out_dir / "execution-context.json").read_text(encoding="utf-8"))
            steps = {str(item.get("name")): item for item in json.loads((out_dir / "summary.json").read_text(encoding="utf-8")).get("steps", [])}
            llm_cmd = steps["sc-llm-review"]["cmd"]

            self.assertEqual("targeted", execution_context["llm_review"]["effective_tier"])
            self.assertEqual("warn", execution_context["llm_review"]["semantic_gate"])
            self.assertIn("--semantic-gate", llm_cmd)
            self.assertEqual("warn", llm_cmd[llm_cmd.index("--semantic-gate") + 1])
            self.assertEqual("code-reviewer,security-auditor", llm_cmd[llm_cmd.index("--agents") + 1])
            self.assertEqual("summary", llm_cmd[llm_cmd.index("--diff-mode") + 1])
            self.assertNotIn("--strict", llm_cmd)

    def test_llm_review_dry_plan_should_preserve_narrow_fast_ship_targeted_agents(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "sc" / "llm_review.py"),
                "--dry-run-plan",
                "--delivery-profile",
                "fast-ship",
                "--agents",
                "code-reviewer,security-auditor",
                "--semantic-gate",
                "warn",
            ],
            cwd=str(REPO_ROOT),
            env=_stable_subprocess_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        self.assertEqual(0, proc.returncode, proc.stdout)
        out_dir = _extract_out_dir(proc.stdout or "")
        summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))

        self.assertEqual(["code-reviewer", "security-auditor"], [str(x) for x in (summary.get("agents") or [])])

    def test_dry_run_fast_ship_should_escalate_minimal_tier_for_contract_task(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            argv = [
                str(SCRIPT),
                "--task-id",
                "1",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
                "--reselect-profile",
                "--dry-run",
                "--skip-test",
                "--skip-agent-review",
            ]
            triplet = self._triplet(
                priority="P2",
                title="Update contracts and workflow",
                back={"semantic_review_tier": "minimal", "contractRefs": ["Game.Core/Contracts/Guild/GuildEvent.cs"]},
            )
            with mock.patch.dict(os.environ, {}, clear=False), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path), \
                mock.patch.object(run_review_pipeline_module, "resolve_triplet", return_value=triplet):
                rc = run_review_pipeline_module.main()

            self.assertEqual(0, rc)
            execution_context = json.loads((out_dir / "execution-context.json").read_text(encoding="utf-8"))
            steps = {str(item.get("name")): item for item in json.loads((out_dir / "summary.json").read_text(encoding="utf-8")).get("steps", [])}
            llm_cmd = steps["sc-llm-review"]["cmd"]

            self.assertEqual("full", execution_context["llm_review"]["effective_tier"])
            self.assertIn("contract_refs_present", execution_context["llm_review"]["escalation_reasons"])
            self.assertEqual("warn", llm_cmd[llm_cmd.index("--semantic-gate") + 1])
            self.assertEqual("code-reviewer,security-auditor,semantic-equivalence-auditor", llm_cmd[llm_cmd.index("--agents") + 1])
            self.assertEqual("summary", llm_cmd[llm_cmd.index("--diff-mode") + 1])

    def test_dry_run_should_forward_targeted_llm_agent_timeout_overrides(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            argv = [
                str(SCRIPT),
                "--task-id",
                "1",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
                "--reselect-profile",
                "--dry-run",
                "--skip-test",
                "--skip-agent-review",
            ]
            with mock.patch.dict(os.environ, {}, clear=False), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir), \
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path), \
                mock.patch.object(run_review_pipeline_module, "_derive_llm_agent_timeout_overrides", return_value={"security-auditor": 480}):
                rc = run_review_pipeline_module.main()

            self.assertEqual(0, rc)
            execution_context = json.loads((out_dir / "execution-context.json").read_text(encoding="utf-8"))
            steps = {str(item.get("name")): item for item in json.loads((out_dir / "summary.json").read_text(encoding="utf-8")).get("steps", [])}
            llm_cmd = steps["sc-llm-review"]["cmd"]

            self.assertEqual({"security-auditor": 480}, execution_context["llm_review"]["agent_timeout_overrides"])
            self.assertIn("--agent-timeouts", llm_cmd)
            self.assertEqual("security-auditor=480", llm_cmd[llm_cmd.index("--agent-timeouts") + 1])

    def test_dry_run_should_not_publish_latest_or_active_task_sidecar(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-1" / "latest.json"
            active_task_path = tmp_root / "logs" / "ci" / "active-tasks" / "task-1.active.json"
            argv = [
                str(SCRIPT),
                "--task-id",
                "1",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
                "--reselect-profile",
                "--dry-run",
                "--skip-agent-review",
            ]
            with (
                mock.patch.dict(os.environ, {}, clear=False),
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir),
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path),
                mock.patch.object(run_review_pipeline_module, "resolve_triplet", return_value=self._triplet()),
                mock.patch.object(run_review_pipeline_module, "_derive_change_scope_ceiling_guard", return_value=None),
            ):
                rc = run_review_pipeline_module.main()

            self.assertEqual(1, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertTrue((out_dir / "summary.json").exists())
            self.assertEqual("planned-only", summary["run_type"])
            self.assertEqual("planned_only_incomplete", summary["reason"])
            self.assertFalse(latest_path.exists())
            self.assertFalse(active_task_path.exists())

    def test_dry_run_should_not_overwrite_existing_latest_pointer(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "logs" / "ci" / "2026-04-07" / "sc-review-pipeline-task-1" / "latest.json"
            latest_path.parent.mkdir(parents=True, exist_ok=True)
            latest_path.write_text(
                json.dumps(
                    {
                        "task_id": "1",
                        "run_id": "existingrun",
                        "status": "ok",
                        "date": "2026-04-06",
                        "latest_out_dir": "logs/ci/2026-04-06/sc-review-pipeline-task-1-existingrun",
                        "summary_path": "logs/ci/2026-04-06/sc-review-pipeline-task-1-existingrun/summary.json",
                        "execution_context_path": "logs/ci/2026-04-06/sc-review-pipeline-task-1-existingrun/execution-context.json",
                        "repair_guide_json_path": "logs/ci/2026-04-06/sc-review-pipeline-task-1-existingrun/repair-guide.json",
                        "repair_guide_md_path": "logs/ci/2026-04-06/sc-review-pipeline-task-1-existingrun/repair-guide.md",
                        "marathon_state_path": "logs/ci/2026-04-06/sc-review-pipeline-task-1-existingrun/marathon-state.json",
                        "run_events_path": "logs/ci/2026-04-06/sc-review-pipeline-task-1-existingrun/run-events.jsonl",
                        "harness_capabilities_path": "logs/ci/2026-04-06/sc-review-pipeline-task-1-existingrun/harness-capabilities.json",
                    },
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
            before = latest_path.read_text(encoding="utf-8")
            argv = [
                str(SCRIPT),
                "--task-id",
                "1",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
                "--reselect-profile",
                "--dry-run",
                "--skip-agent-review",
            ]
            with (
                mock.patch.dict(os.environ, {}, clear=False),
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir),
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path),
                mock.patch.object(run_review_pipeline_module, "resolve_triplet", return_value=self._triplet()),
                mock.patch.object(run_review_pipeline_module, "_derive_change_scope_ceiling_guard", return_value=None),
            ):
                rc = run_review_pipeline_module.main()

            self.assertEqual(1, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("planned-only", summary["run_type"])
            self.assertEqual("planned_only_incomplete", summary["reason"])
            self.assertEqual(before, latest_path.read_text(encoding="utf-8"))

    def test_derive_llm_agent_timeout_overrides_should_only_escalate_previously_timed_out_agents(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            previous_run = root / "logs" / "ci" / "2026-04-02" / "sc-review-pipeline-task-1-oldrun"
            llm_dir = root / "logs" / "ci" / "2026-04-02" / "sc-llm-review-task-1"
            previous_run.mkdir(parents=True, exist_ok=True)
            llm_dir.mkdir(parents=True, exist_ok=True)
            (previous_run / "summary.json").write_text(
                json.dumps(
                    {
                        "task_id": "1",
                        "steps": [
                            {
                                "name": "sc-llm-review",
                                "status": "fail",
                                "summary_file": str(llm_dir / "summary.json"),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (previous_run / "execution-context.json").write_text(
                json.dumps({"delivery_profile": "fast-ship", "security_profile": "host-safe"}),
                encoding="utf-8",
            )
            (llm_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "results": [
                            {"agent": "code-reviewer", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                            {"agent": "security-auditor", "status": "fail", "rc": 124, "details": {"verdict": ""}},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(run_review_pipeline_module, "repo_root", return_value=root):
                overrides = run_review_pipeline_module._derive_llm_agent_timeout_overrides(
                    current_out_dir=root / "logs" / "ci" / "2026-04-03" / "sc-review-pipeline-task-1-newrun",
                    task_id="1",
                    delivery_profile="fast-ship",
                    security_profile="host-safe",
                    llm_agents="code-reviewer,security-auditor,semantic-equivalence-auditor",
                    llm_semantic_gate="warn",
                    llm_timeout_sec=900,
                    llm_agent_timeout_sec=240,
                )

            self.assertEqual({"security-auditor": 480}, overrides)

    def test_resolve_pipeline_profiles_should_reject_explicit_mismatch_on_resume(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "delivery profile"):
            run_review_pipeline_module._resolve_pipeline_profiles(
                requested_delivery_profile="fast-ship",
                requested_security_profile=None,
                source_execution_context={"delivery_profile": "standard", "security_profile": "strict"},
                inherit_from_source=True,
            )

    def test_resolve_pipeline_profiles_should_inherit_source_when_resume_has_no_explicit_profile(self) -> None:
        delivery_profile, security_profile = run_review_pipeline_module._resolve_pipeline_profiles(
            requested_delivery_profile=None,
            requested_security_profile=None,
            source_execution_context={"delivery_profile": "playable-ea", "security_profile": "host-safe"},
            inherit_from_source=True,
        )

        self.assertEqual("playable-ea", delivery_profile)
        self.assertEqual("host-safe", security_profile)

    def test_resolve_pipeline_profiles_should_reject_non_resume_profile_drift_without_reselect(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "delivery profile mismatch"):
            run_review_pipeline_module._resolve_pipeline_profiles(
                requested_delivery_profile="playable-ea",
                requested_security_profile="host-safe",
                source_execution_context={"delivery_profile": "fast-ship", "security_profile": "host-safe"},
                inherit_from_source=True,
            )

    def test_derive_delivery_profile_floor_should_raise_playable_ea_for_risky_mixed_changes(self) -> None:
        decision = run_review_pipeline_module._derive_delivery_profile_floor(
            delivery_profile="playable-ea",
            security_profile="host-safe",
            change_scope={
                "changed_paths": [
                    "scripts/sc/run_review_pipeline.py",
                    "Game.Core/Combat/AttackResolver.cs",
                ],
                "unsafe_paths": [
                    "scripts/sc/run_review_pipeline.py",
                    "Game.Core/Combat/AttackResolver.cs",
                ],
            },
            explicit_security_profile=False,
        )

        self.assertTrue(decision["applied"])
        self.assertEqual("fast-ship", decision["delivery_profile"])
        self.assertEqual("host-safe", decision["security_profile"])
        self.assertEqual("risky-change-floor", decision["reason"])

    def test_derive_delivery_profile_floor_should_keep_playable_ea_for_semantic_only_changes(self) -> None:
        decision = run_review_pipeline_module._derive_delivery_profile_floor(
            delivery_profile="playable-ea",
            security_profile="host-safe",
            change_scope={
                "changed_paths": ["docs/architecture/overlays/PRD-template-T2/08/_index.md"],
                "unsafe_paths": [],
            },
            explicit_security_profile=False,
        )

        self.assertFalse(decision["applied"])
        self.assertEqual("playable-ea", decision["delivery_profile"])
        self.assertEqual("host-safe", decision["security_profile"])

    def test_detect_latest_profile_drift_should_report_latest_mismatched_run(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            older = root / "logs" / "ci" / "2026-04-02" / "sc-review-pipeline-task-1-old"
            older.mkdir(parents=True, exist_ok=True)
            (older / "execution-context.json").write_text(
                json.dumps({"run_id": "old", "delivery_profile": "standard", "security_profile": "strict"}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (older / "summary.json").write_text(json.dumps({"status": "ok"}, ensure_ascii=False) + "\n", encoding="utf-8")
            current = root / "logs" / "ci" / "2026-04-03" / "sc-review-pipeline-task-1-current"

            with mock.patch.object(run_review_pipeline_module, "repo_root", return_value=root):
                drift = run_review_pipeline_module._detect_latest_profile_drift(
                    current_out_dir=current,
                    task_id="1",
                    delivery_profile="fast-ship",
                    security_profile="host-safe",
                )

            self.assertIsNotNone(drift)
            assert drift is not None
            self.assertEqual("standard", drift["previous_delivery_profile"])
            self.assertEqual("strict", drift["previous_security_profile"])
            self.assertEqual("fast-ship", drift["current_delivery_profile"])
            self.assertEqual("host-safe", drift["current_security_profile"])

    def test_derive_llm_agent_timeout_overrides_should_add_complexity_bonus_for_strict_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            previous_run = root / "logs" / "ci" / "2026-04-02" / "sc-review-pipeline-task-1-oldrun"
            llm_dir = root / "logs" / "ci" / "2026-04-02" / "sc-llm-review-task-1"
            previous_run.mkdir(parents=True, exist_ok=True)
            llm_dir.mkdir(parents=True, exist_ok=True)
            (previous_run / "summary.json").write_text(
                json.dumps(
                    {
                        "task_id": "1",
                        "steps": [
                            {
                                "name": "sc-llm-review",
                                "status": "fail",
                                "summary_file": str(llm_dir / "summary.json"),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (previous_run / "execution-context.json").write_text(
                json.dumps({"delivery_profile": "standard", "security_profile": "strict"}),
                encoding="utf-8",
            )
            (llm_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "results": [
                            {"agent": "security-auditor", "status": "fail", "rc": 124, "details": {"verdict": ""}},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(run_review_pipeline_module, "repo_root", return_value=root):
                overrides = run_review_pipeline_module._derive_llm_agent_timeout_overrides(
                    current_out_dir=root / "logs" / "ci" / "2026-04-03" / "sc-review-pipeline-task-1-newrun",
                    task_id="1",
                    delivery_profile="standard",
                    security_profile="strict",
                    llm_agents="code-reviewer,security-auditor,semantic-equivalence-auditor,architecture-reviewer",
                    llm_semantic_gate="require",
                    llm_timeout_sec=900,
                    llm_agent_timeout_sec=240,
                )

            self.assertEqual({"security-auditor": 600}, overrides)

    def test_derive_llm_agent_timeout_overrides_should_use_previous_timeout_memory_when_agent_timed_out_again(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            previous_run = root / "logs" / "ci" / "2026-04-02" / "sc-review-pipeline-task-1-oldrun"
            llm_dir = root / "logs" / "ci" / "2026-04-02" / "sc-llm-review-task-1"
            previous_run.mkdir(parents=True, exist_ok=True)
            llm_dir.mkdir(parents=True, exist_ok=True)
            (previous_run / "summary.json").write_text(
                json.dumps(
                    {
                        "task_id": "1",
                        "steps": [
                            {
                                "name": "sc-llm-review",
                                "status": "fail",
                                "summary_file": str(llm_dir / "summary.json"),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (previous_run / "execution-context.json").write_text(
                json.dumps(
                    {
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                        "llm_review": {
                            "agent_timeout_sec": 240,
                            "agent_timeout_overrides": {"security-auditor": 420},
                        },
                    }
                ),
                encoding="utf-8",
            )
            (llm_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "agent": "security-auditor",
                                "status": "fail",
                                "rc": 124,
                                "details": {"verdict": "", "agent_timeout_sec": 420},
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(run_review_pipeline_module, "repo_root", return_value=root):
                overrides = run_review_pipeline_module._derive_llm_agent_timeout_overrides(
                    current_out_dir=root / "logs" / "ci" / "2026-04-03" / "sc-review-pipeline-task-1-newrun",
                    task_id="1",
                    delivery_profile="fast-ship",
                    security_profile="host-safe",
                    llm_agents="security-auditor",
                    llm_semantic_gate="warn",
                    llm_timeout_sec=900,
                    llm_agent_timeout_sec=240,
                )

            self.assertEqual({"security-auditor": 540}, overrides)

    def test_derive_llm_reviewer_subset_should_narrow_to_recent_non_ok_agents_for_safe_semantic_delta(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            previous_run = root / "logs" / "ci" / "2026-04-02" / "sc-review-pipeline-task-1-oldrun"
            llm_dir = root / "logs" / "ci" / "2026-04-02" / "sc-llm-review-task-1"
            previous_run.mkdir(parents=True, exist_ok=True)
            llm_dir.mkdir(parents=True, exist_ok=True)
            (previous_run / "summary.json").write_text(
                json.dumps(
                    {
                        "task_id": "1",
                        "steps": [
                            {"name": "sc-test", "status": "ok"},
                            {"name": "sc-acceptance-check", "status": "ok"},
                            {"name": "sc-llm-review", "status": "fail", "summary_file": str(llm_dir / "summary.json")},
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
            (previous_run / "execution-context.json").write_text(
                json.dumps(
                    {
                        "run_id": "oldrun",
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                    },
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
            (llm_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "results": [
                            {"agent": "code-reviewer", "status": "ok", "rc": 0, "details": {"verdict": "OK"}},
                            {"agent": "security-auditor", "status": "fail", "rc": 124, "details": {"verdict": ""}},
                            {"agent": "semantic-equivalence-auditor", "status": "ok", "rc": 0, "details": {"verdict": "Needs Fix"}},
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )

            with mock.patch.object(run_review_pipeline_module, "repo_root", return_value=root):
                decision = run_review_pipeline_module._derive_llm_reviewer_subset_from_recent_signals(
                    current_out_dir=root / "logs" / "ci" / "2026-04-03" / "sc-review-pipeline-task-1-newrun",
                    task_id="1",
                    delivery_profile="fast-ship",
                    security_profile="host-safe",
                    llm_agents="code-reviewer,security-auditor,semantic-equivalence-auditor",
                    llm_semantic_gate="warn",
                    change_scope={"changed_paths": ["docs/architecture/overlays/PRD-X/08/_index.md"], "unsafe_paths": []},
                    explicit_llm_agents=False,
                )

            self.assertTrue(bool(decision.get("applied")))
            self.assertEqual(["security-auditor", "semantic-equivalence-auditor"], decision.get("agents"))
            self.assertEqual("oldrun", decision.get("source_run_id"))

    def test_derive_llm_reviewer_subset_should_ignore_semantic_skip_from_deferred_stage_guard(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            previous_run = root / "logs" / "ci" / "2026-04-02" / "sc-review-pipeline-task-1-oldrun"
            llm_dir = root / "logs" / "ci" / "2026-04-02" / "sc-llm-review-task-1"
            previous_run.mkdir(parents=True, exist_ok=True)
            llm_dir.mkdir(parents=True, exist_ok=True)
            (previous_run / "summary.json").write_text(
                json.dumps(
                    {
                        "task_id": "1",
                        "steps": [
                            {"name": "sc-test", "status": "ok"},
                            {"name": "sc-acceptance-check", "status": "ok"},
                            {"name": "sc-llm-review", "status": "fail", "summary_file": str(llm_dir / "summary.json")},
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
            (previous_run / "execution-context.json").write_text(
                json.dumps(
                    {
                        "run_id": "oldrun",
                        "delivery_profile": "fast-ship",
                        "security_profile": "host-safe",
                    },
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
            (llm_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "results": [
                            {"agent": "code-reviewer", "status": "fail", "rc": 124, "details": {"verdict": ""}},
                            {
                                "agent": "semantic-equivalence-auditor",
                                "status": "skipped",
                                "rc": 0,
                                "details": {
                                    "reason_code": "deferred_until_prior_reviewers_clean",
                                    "blocked_by_agents": ["code-reviewer"],
                                },
                            },
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )

            with mock.patch.object(run_review_pipeline_module, "repo_root", return_value=root):
                decision = run_review_pipeline_module._derive_llm_reviewer_subset_from_recent_signals(
                    current_out_dir=root / "logs" / "ci" / "2026-04-03" / "sc-review-pipeline-task-1-newrun",
                    task_id="1",
                    delivery_profile="fast-ship",
                    security_profile="host-safe",
                    llm_agents="code-reviewer,security-auditor,semantic-equivalence-auditor",
                    llm_semantic_gate="warn",
                    change_scope={"changed_paths": ["docs/architecture/overlays/PRD-X/08/_index.md"], "unsafe_paths": []},
                    explicit_llm_agents=False,
                )

            self.assertTrue(bool(decision.get("applied")))
            self.assertEqual(["code-reviewer"], decision.get("agents"))

    def test_dry_run_should_apply_recent_llm_reviewer_subset_narrowing(self) -> None:
        run_id = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            out_dir = tmp_root / f"sc-review-pipeline-task-1-{run_id}"
            latest_path = tmp_root / "sc-review-pipeline-task-1" / "latest.json"
            argv = [
                str(SCRIPT),
                "--task-id",
                "1",
                "--run-id",
                run_id,
                "--delivery-profile",
                "fast-ship",
                "--reselect-profile",
                "--dry-run",
                "--skip-test",
                "--skip-agent-review",
            ]
            with (
                mock.patch.dict(os.environ, {}, clear=False),
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(run_review_pipeline_module, "_pipeline_run_dir", return_value=out_dir),
                mock.patch.object(run_review_pipeline_module, "_pipeline_latest_index_path", return_value=latest_path),
                mock.patch.object(run_review_pipeline_module, "resolve_triplet", return_value=self._triplet(back={"semantic_review_tier": "full"})),
                mock.patch.object(
                    run_review_pipeline_module,
                    "_derive_llm_reviewer_subset_from_recent_signals",
                    return_value={
                        "applied": True,
                        "agents": ["security-auditor", "semantic-equivalence-auditor"],
                        "source_run_id": "oldrun",
                        "reason": "recent_llm_signals",
                    },
                ),
            ):
                rc = run_review_pipeline_module.main()

            self.assertEqual(0, rc)
            execution_context = json.loads((out_dir / "execution-context.json").read_text(encoding="utf-8"))
            steps = {str(item.get("name")): item for item in json.loads((out_dir / "summary.json").read_text(encoding="utf-8")).get("steps", [])}
            llm_cmd = steps["sc-llm-review"]["cmd"]

            self.assertEqual(
                ["security-auditor", "semantic-equivalence-auditor"],
                execution_context["llm_review"]["derived_reviewer_subset"]["agents"],
            )
            self.assertEqual("security-auditor,semantic-equivalence-auditor", llm_cmd[llm_cmd.index("--agents") + 1])


if __name__ == '__main__':
    unittest.main()
