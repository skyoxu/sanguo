"""Failure-oriented tests for MVG planning, selection and runtime evidence."""
import argparse
import copy
import json
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _mvg_manifest import validate_manifest, recommend
from _mvg_execution import read_test_evidence
from run_mvg_acceptance import register_arguments, run


class MvgAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ['Game.Core/A.cs', 'Game.Core.Tests/A.cs']:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('content', encoding='utf-8')
        path = self.root / '.taskmaster/tasks/tasks.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'master': {'tasks': [{'id': 1}, {'id': 2}]}}))
        self.manifest = {
            'schema_version': 'newrouge.mvg-integration.v1', 'mvg_id': 'pilot',
            'flows': [{'id': 'claim', 'outcome': 'Claim once', 'task_ids': [1, 2],
                       'source_paths': ['Game.Core/A.cs'],
                       'handoffs': [{'producer_task': 1, 'consumer_task': 2, 'owner_task': 2,
                                     'contract_ref': 'Game.Core/A.cs', 'behavior': 'One claim',
                                     'test_ids': ['claim-test']}],
                       'test_ids': ['claim-test']}],
            'tests': [{'id': 'claim-test', 'kind': 'dotnet', 'state': 'implemented',
                       'evidence_level': 'domain-integration',
                       'path': 'Game.Core.Tests/A.cs',
                       'selector': 'Game.Core.Tests.A', 'min_tests': 1}]}

    def test_planning_allows_missing_planned_test_but_execution_rejects_it(self):
        self.manifest['tests'][0].update(state='planned', path='Game.Core.Tests/Future.cs')
        self.assertEqual([], validate_manifest(self.root, self.manifest, executable=False))
        self.assertTrue(validate_manifest(self.root, self.manifest, executable=True))

    def test_missing_owner_unknown_task_and_uncovered_handoff_are_rejected(self):
        for change in [dict(owner_task=99), dict(test_ids=[]), dict(contract_ref='../escape')]:
            with self.subTest(change=change):
                doc = copy.deepcopy(self.manifest)
                doc['flows'][0]['handoffs'][0].update(change)
                self.assertTrue(validate_manifest(self.root, doc))

    def test_duplicate_ids_empty_flows_and_unknown_test_are_rejected(self):
        for key, value in [('flows', []), ('tests', self.manifest['tests'] * 2)]:
            doc = copy.deepcopy(self.manifest)
            doc[key] = value
            self.assertTrue(validate_manifest(self.root, doc))
        self.manifest['flows'][0]['test_ids'] = ['unknown']
        self.assertTrue(validate_manifest(self.root, self.manifest))

    def test_recommendation_never_removes_required_tests_and_unknown_falls_back(self):
        known = recommend(self.manifest, ['Game.Core/A.cs'])
        self.assertEqual(['claim'], known['matched_flows'])
        self.assertEqual(['claim-test'], known['required_tests'])
        unknown = recommend(self.manifest, ['Game.Godot/new.gd'])
        self.assertEqual('full-mvg', unknown['recommendation'])
        self.assertEqual(['Game.Godot/new.gd'], unknown['unmapped_changes'])
        self.assertFalse(unknown['authorizes_test_exclusion'])

    def test_zero_skipped_missing_malformed_or_wrong_suite_cannot_pass(self):
        evidence = self.root / 'results.trx'
        self.assertFalse(read_test_evidence(self.root, 'dotnet', 'Expected', 1)['passed'])
        for content in ['bad xml', '<TestRun/>',
                        '<TestRun><UnitTestResult testName="Other" outcome="Passed"/></TestRun>',
                        '<TestRun><UnitTestResult testName="Expected" outcome="NotExecuted"/></TestRun>']:
            evidence.write_text(content)
            self.assertFalse(read_test_evidence(self.root, 'dotnet', 'Expected', 1)['passed'])

    def test_real_failure_is_distinguished_from_missing_evidence(self):
        path = self.root / 'results.trx'
        path.write_text('<TestRun><UnitTestResult testName="Expected.A" outcome="Failed"/></TestRun>')
        result = read_test_evidence(self.root, 'dotnet', 'Expected', 1)
        self.assertFalse(result['passed'])
        self.assertEqual(1, result['failed'])
        path.write_text('<TestRun><UnitTestResult testName="Expected.A" outcome="Passed"/></TestRun>')
        self.assertTrue(read_test_evidence(self.root, 'dotnet', 'Expected', 1)['passed'])

    def test_gdunit_skipped_case_and_foreign_suite_are_rejected(self):
        path = self.root / 'results.xml'
        path.write_text('<testsuites><testsuite name="expected"><testcase name="test_a"><skipped/></testcase></testsuite></testsuites>')
        self.assertFalse(read_test_evidence(self.root, 'gdunit', 'expected', 1)['passed'])
        path.write_text('<testsuites><testsuite name="other"><testcase name="test_a"/></testsuite></testsuites>')
        self.assertFalse(read_test_evidence(self.root, 'gdunit', 'expected', 1)['passed'])
        path.write_text('<testsuites><testsuite name="expected"><testcase name="test_a"/></testsuite></testsuites>')
        self.assertTrue(read_test_evidence(self.root, 'gdunit', 'expected', 1)['passed'])

    def test_planning_success_never_claims_runtime_verification(self):
        path = self.root / 'manifest.json'
        path.write_text(json.dumps(self.manifest))
        parser = argparse.ArgumentParser()
        register_arguments(parser)
        args = parser.parse_args(['--manifest', 'manifest.json', '--mode', 'plan'])
        with patch('run_mvg_acceptance.git', return_value='a' * 40):
            self.assertEqual(0, run(args, self.root))
        summary = json.loads(next(self.root.glob('logs/ci/mvg-acceptance/*/summary.json')).read_text())
        self.assertFalse(summary['runtime_verified'])
        self.assertFalse(summary['authorizes_task_status_write'])

    def test_execution_failure_blocks_runtime_acceptance(self):
        parser = argparse.ArgumentParser()
        register_arguments(parser)
        args = parser.parse_args(['--manifest', 'manifest.json', '--mode', 'run'])
        def snapshot(root, target, revision, mode, deadline):
            target.mkdir(parents=True)
            (target / 'manifest.json').write_text(json.dumps(self.manifest))
            return dict(source_revision='workspace:digest', snapshot_digest='digest')
        with patch('run_mvg_acceptance.git', return_value='a' * 40), \
             patch('run_mvg_acceptance.prepare_snapshot', side_effect=snapshot), \
             patch('run_mvg_acceptance.validate_manifest', return_value=[]), \
             patch('run_mvg_acceptance.execute_test', return_value={'status': 'failed'}) as execute:
            self.assertEqual(1, run(args, self.root))
        self.assertEqual(1, execute.call_count)
        summary = json.loads(next(self.root.glob('logs/ci/mvg-acceptance/*/summary.json')).read_text())
        self.assertFalse(summary['runtime_verified'])
        self.assertEqual('workspace:digest', summary['source_revision'])
        self.assertEqual('blocked', summary['status'])

    def test_similar_class_and_suite_names_cannot_substitute_for_expected(self):
        path = self.root / 'results.trx'
        path.write_text('<TestRun><UnitTestResult testName="ExpectedExtra.A" outcome="Passed"/></TestRun>')
        self.assertFalse(read_test_evidence(self.root, 'dotnet', 'Expected', 1)['passed'])
        path = self.root / 'results.xml'
        path.write_text('<testsuites><testsuite name="expected_extra"><testcase name="test_a"/></testsuite></testsuites>')
        self.assertFalse(read_test_evidence(self.root, 'gdunit', 'expected', 1)['passed'])

    def test_report_counters_and_duplicate_results_are_checked(self):
        path = self.root / 'results.xml'
        for xml in [
            '<testsuites tests="2"><testsuite name="expected" tests="1"><testcase name="a"/></testsuite></testsuites>',
            '<testsuite name="expected" tests="2"><testcase name="a"/></testsuite>',
            '<testsuite name="expected"><testcase name="a"/><testcase name="a"/></testsuite>',
        ]:
            path.write_text(xml)
            self.assertFalse(read_test_evidence(self.root, 'gdunit', 'expected', 1)['passed'])
        path = self.root / 'results.trx'
        path.write_text('<TestRun><UnitTestResult testName="Expected.A" outcome="Passed"/>'
                        '<Counters total="2" passed="2" failed="0"/></TestRun>')
        self.assertFalse(read_test_evidence(self.root, 'dotnet', 'Expected', 1)['passed'])

    def test_commit_recommendation_does_not_include_head_or_working_changes(self):
        from run_mvg_acceptance import changed_paths
        calls = []
        def fake_git(root, *args):
            calls.append(args)
            return 'base-sha' if args[0] == 'rev-parse' else 'Game.Core/A.cs\0'
        with patch('run_mvg_acceptance.git', side_effect=fake_git):
            paths, reason = changed_paths(self.root, 'base', 'old-commit', workspace=False)
        self.assertEqual(['Game.Core/A.cs'], paths)
        self.assertEqual('', reason)
        self.assertIn(('diff', '--name-only', '--no-renames', '-z', 'base-sha', 'old-commit'), calls)
        self.assertFalse(any('HEAD' in call or 'ls-files' in call for call in calls))

    def test_old_commit_uses_its_manifest_and_comparison_target(self):
        def git(*args):
            return subprocess.check_output(['git', '-C', str(self.root), *args], text=True).strip()
        git('init', '-q')
        git('config', 'user.email', 'test@example.invalid')
        git('config', 'user.name', 'Test')
        (self.root / 'manifest.json').write_text(json.dumps(self.manifest))
        git('add', '.')
        git('commit', '-qm', 'initial')
        old = git('rev-parse', 'HEAD')
        changed = copy.deepcopy(self.manifest)
        changed['mvg_id'] = 'different-workspace'
        (self.root / 'manifest.json').write_text(json.dumps(changed))
        parser = argparse.ArgumentParser()
        register_arguments(parser)
        args = parser.parse_args(['--mode', 'recommend', '--snapshot', 'commit',
                                  '--revision', old, '--base', old, '--manifest', 'manifest.json'])
        self.assertEqual(0, run(args, self.root))
        summary = json.loads(next(self.root.glob('logs/ci/mvg-acceptance/*/summary.json')).read_text())
        self.assertEqual('pilot', summary['mvg_id'])
        self.assertEqual(old, summary['recommendation']['comparison_target'])
        self.assertFalse(summary['recommendation']['includes_working_changes'])
        self.assertEqual([], summary['recommendation']['unmapped_changes'])

    def test_godot_prewarm_is_reused_only_after_first_suite_passes(self):
        parser = argparse.ArgumentParser()
        register_arguments(parser)
        args = parser.parse_args(['--manifest', 'manifest.json', '--mode', 'run'])
        doc = copy.deepcopy(self.manifest)
        doc['tests'] = [dict(id=name, kind='gdunit') for name in ['first', 'second']]
        def snapshot(root, target, revision, mode, deadline):
            target.mkdir(parents=True)
            (target / 'manifest.json').write_text(json.dumps(doc))
            return dict(source_revision='workspace:digest', snapshot_digest='digest')
        with patch('run_mvg_acceptance.git', return_value='a' * 40), \
             patch('run_mvg_acceptance.prepare_snapshot', side_effect=snapshot), \
             patch('run_mvg_acceptance.validate_manifest', return_value=[]), \
             patch('run_mvg_acceptance.recommend', return_value={}), \
             patch('run_mvg_acceptance.execute_test', return_value={'status': 'passed'}) as execute:
            self.assertEqual(0, run(args, self.root))
        self.assertEqual([True, False], [c.kwargs['prewarm'] for c in execute.call_args_list])
        self.assertNotEqual(execute.call_args_list[0].args[2], execute.call_args_list[1].args[2])

    def test_workflow_scan_ignores_trigger_paths_but_checks_run_blocks(self):
        from check_workflow_gate_enforcement import _extract_workflow_scripts
        workflow = """on:
  pull_request:
    paths:
      - 'scripts/python/listened.py'
jobs:
  check:
    steps:
      - name: scripts/python/label.py
        run: |
          python scripts/python/real.py
          python scripts/python/second.py
      - run: python scripts/python/inline.py
      - uses: actions/checkout@v4
"""
        self.assertEqual({'scripts/python/real.py', 'scripts/python/second.py',
                          'scripts/python/inline.py'}, _extract_workflow_scripts(workflow))

    def test_suite_setup_errors_override_passing_testcases(self):
        path = self.root / 'results.xml'
        path.write_text('<testsuites><testsuite name="expected" errors="1">'
                        '<testcase name="test_a"/></testsuite></testsuites>')
        result = read_test_evidence(self.root, 'gdunit', 'expected', 1)
        self.assertFalse(result['passed'])
        self.assertEqual('reported-suite-failure', result['reason'])


if __name__ == '__main__':
    unittest.main()
