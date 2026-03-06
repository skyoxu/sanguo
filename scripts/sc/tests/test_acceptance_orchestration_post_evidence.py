import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / 'scripts' / 'sc'
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

import _acceptance_orchestration as orchestration
from _acceptance_steps import StepResult


class AcceptanceOrchestrationPostEvidenceTests(unittest.TestCase):
    def test_build_step_plan_should_enable_post_evidence_for_task1(self) -> None:
        plan = orchestration.build_step_plan(
            only_steps={'tests'},
            subtasks_mode='skip',
            security_modes={
                'ui_event_json_guards': 'warn',
                'ui_event_source_verify': 'warn',
            },
            has_gd_refs=True,
            needs_env_preflight=True,
            require_headless_e2e=True,
            require_executed_refs=False,
            audit_evidence_mode='off',
            perf_p95_ms=0,
            task_id=1,
        )
        post_gate = next(item for item in plan if item['name'] == 'post-evidence-integration')
        self.assertTrue(bool(post_gate.get('enabled')))
        self.assertEqual('hard', post_gate.get('gate_level'))

    def test_build_step_plan_should_disable_post_evidence_for_non_task1(self) -> None:
        plan = orchestration.build_step_plan(
            only_steps={'tests'},
            subtasks_mode='skip',
            security_modes={
                'ui_event_json_guards': 'warn',
                'ui_event_source_verify': 'warn',
            },
            has_gd_refs=True,
            needs_env_preflight=False,
            require_headless_e2e=True,
            require_executed_refs=False,
            audit_evidence_mode='off',
            perf_p95_ms=0,
            task_id=2,
        )
        post_gate = next(item for item in plan if item['name'] == 'post-evidence-integration')
        self.assertFalse(bool(post_gate.get('enabled')))
        self.assertEqual('task_not_targeted', post_gate.get('reason'))

    def test_run_tests_bundle_should_skip_post_gate_when_headless_evidence_fails(self) -> None:
        triplet = type('Triplet', (), {'task_id': '1'})()
        with (
            patch.object(orchestration, 'step_tests_all', return_value=StepResult(name='tests-all', status='ok', rc=0)),
            patch.object(orchestration, 'step_headless_e2e_evidence', return_value=StepResult(name='headless-e2e-evidence', status='fail', rc=1)),
        ):
            steps = orchestration.run_tests_bundle(
                out_dir=REPO_ROOT / 'logs',
                triplet=triplet,
                only_steps={'tests'},
                has_gd_refs=True,
                require_headless_e2e=True,
                require_executed_refs=False,
                audit_evidence_mode='off',
                godot_bin='C:/Godot/Godot.exe',
                run_id='run123',
            )

        post_gate = next(step for step in steps if step.name == 'post-evidence-integration')
        self.assertEqual('skipped', post_gate.status)
        self.assertEqual('headless_e2e_evidence_failed', (post_gate.details or {}).get('reason'))

    def test_run_tests_bundle_should_disable_global_coverage_gate_for_task1(self) -> None:
        triplet = type('Triplet', (), {'task_id': '1'})()
        with (
            patch.object(orchestration, 'step_tests_all', return_value=StepResult(name='tests-all', status='ok', rc=0)) as step_tests_all_mock,
            patch.object(orchestration, 'step_headless_e2e_evidence', return_value=StepResult(name='headless-e2e-evidence', status='ok', rc=0)),
            patch.object(orchestration, 'step_post_evidence_integration', return_value=StepResult(name='post-evidence-integration', status='ok', rc=0)),
        ):
            orchestration.run_tests_bundle(
                out_dir=REPO_ROOT / 'logs',
                triplet=triplet,
                only_steps={'tests'},
                has_gd_refs=True,
                require_headless_e2e=True,
                require_executed_refs=False,
                audit_evidence_mode='off',
                godot_bin='C:/Godot/Godot.exe',
                run_id='run123',
            )

        self.assertTrue(bool(step_tests_all_mock.call_args.kwargs.get('no_coverage_gate')))


if __name__ == '__main__':
    unittest.main()
