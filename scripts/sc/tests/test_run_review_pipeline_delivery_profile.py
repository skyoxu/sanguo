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
        self.assertEqual('pass', agent_review['review_verdict'])
        self.assertEqual(str(out_dir / 'agent-review.json'), latest['agent_review_json_path'])
        self.assertEqual(str(out_dir / 'agent-review.md'), latest['agent_review_md_path'])

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
            [sys.executable, str(SCRIPT), '--task-id', '1', '--delivery-profile', 'playable-ea', '--dry-run', '--skip-test'],
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
            [sys.executable, str(SCRIPT), '--task-id', '1', '--delivery-profile', 'standard', '--dry-run', '--skip-test'],
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
                [sys.executable, str(SCRIPT), '--task-id', '1', '--delivery-profile', 'playable-ea', '--dry-run', '--skip-agent-review'],
                cwd=str(REPO_ROOT),
                env=_stable_subprocess_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore',
            )
            self.assertEqual(0, playable.returncode, playable.stdout)
            playable_out = _extract_out_dir(playable.stdout or '')
            playable_state = json.loads((playable_out / 'marathon-state.json').read_text(encoding='utf-8'))
            self.assertEqual(1, playable_state['max_step_retries'])

            standard = subprocess.run(
                [sys.executable, str(SCRIPT), '--task-id', '1', '--delivery-profile', 'standard', '--dry-run', '--skip-agent-review'],
                cwd=str(REPO_ROOT),
                env=_stable_subprocess_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore',
            )
            self.assertEqual(0, standard.returncode, standard.stdout)
            standard_out = _extract_out_dir(standard.stdout or '')
            standard_state = json.loads((standard_out / 'marathon-state.json').read_text(encoding='utf-8'))
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
            self.assertEqual("code-reviewer,security-auditor,semantic-equivalence-auditor", llm_cmd[llm_cmd.index("--agents") + 1])
            self.assertEqual("summary", llm_cmd[llm_cmd.index("--diff-mode") + 1])
            self.assertNotIn("--strict", llm_cmd)

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


if __name__ == '__main__':
    unittest.main()
