import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts/python'))
from _project_health_runtime_snapshot import prepare_snapshot
from project_health_knowledge import base_dir, write_json
from project_health_runtime import verify


class SnapshotHardeningTests(unittest.TestCase):
    def _git(self, root: Path, *args: str) -> str:
        return subprocess.check_output(
            ['git', '-C', str(root), *args], stderr=subprocess.DEVNULL
        ).decode().strip()

    def _init_repo(self, root: Path) -> str:
        self._git(root, 'init', '-b', 'main')
        return ''

    def test_excluded_import_paths_still_reject_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_repo(root)
            cache = root / 'Tests.Godot/addons/gdUnit4/cache.png.import'
            cache.parent.mkdir(parents=True)
            cache.write_text('generated', encoding='utf-8')
            self._git(root, 'add', '.')
            self._git(root, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'initial')
            revision = self._git(root, 'rev-parse', 'HEAD')
            (root / '.git/info/exclude').write_text('logs/\n', encoding='utf-8')

            with patch('_project_health_runtime_snapshot.stat.S_ISLNK', return_value=True):
                with self.assertRaisesRegex(ValueError, 'tracked symlinks'):
                    prepare_snapshot(root, root / 'logs/main/source', revision, 'main', time.monotonic() + 30)

            source = MagicMock()
            source.is_symlink.return_value = True
            with patch('_project_health_runtime_snapshot.safe_file', return_value=source):
                with self.assertRaisesRegex(ValueError, 'workspace symlinks'):
                    prepare_snapshot(root, root / 'logs/workspace/source', revision, 'workspace', time.monotonic() + 30)

    def test_snapshots_exclude_only_gdunit_plugin_import_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_repo(root)
            excluded = root / 'Tests.Godot/addons/gdUnit4/icons/test.png.import'
            plugin_file = root / 'Tests.Godot/addons/gdUnit4/scripts/gdunit.gd'
            retained = root / 'Game.Godot/Assets/player.png.import'
            excluded.parent.mkdir(parents=True)
            plugin_file.parent.mkdir(parents=True)
            retained.parent.mkdir(parents=True)
            excluded.write_text('plugin-cache', encoding='utf-8')
            plugin_file.write_text('plugin-source', encoding='utf-8')
            retained.write_text('project-import', encoding='utf-8')
            self._git(root, 'add', '.')
            self._git(root, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'initial')
            revision = self._git(root, 'rev-parse', 'HEAD')
            (root / '.git/info/exclude').write_text('logs/\n', encoding='utf-8')

            for mode in ('main', 'workspace'):
                snapshot = root / f'logs/{mode}/source'
                manifest = prepare_snapshot(root, snapshot, revision, mode, time.monotonic() + 30)
                excluded_path = excluded.relative_to(root).as_posix()
                plugin_path = plugin_file.relative_to(root).as_posix()
                retained_path = retained.relative_to(root).as_posix()
                self.assertFalse((snapshot / excluded.relative_to(root)).exists())
                self.assertNotIn(excluded_path, manifest['files'])
                self.assertEqual((snapshot / plugin_file.relative_to(root)).read_text(encoding='utf-8'), 'plugin-source')
                self.assertIn(plugin_path, manifest['files'])
                self.assertEqual((snapshot / retained.relative_to(root)).read_text(encoding='utf-8'), 'project-import')
                self.assertIn(retained_path, manifest['files'])

    def _runtime_fixture(self, root: Path, retained_path: str) -> tuple[str, str]:
        self._init_repo(root)
        ref = 'Tests.Godot/tests/example.gd'
        (root / ref).parent.mkdir(parents=True)
        (root / ref).write_text('extends Node\n', encoding='utf-8')
        retained = root / retained_path
        retained.parent.mkdir(parents=True, exist_ok=True)
        retained.write_text('before-run', encoding='utf-8')
        self._git(root, 'add', '.')
        self._git(root, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'initial')
        revision = self._git(root, 'rev-parse', 'HEAD')
        (root / '.git/info/exclude').write_text('logs/\n', encoding='utf-8')
        write_json(base_dir(root) / 'latest.json', {
            'revision': revision,
            'sources': {
                '.taskmaster/tasks/tasks_gameplay.json': json.dumps([{'taskmaster_id': 18, 'test_refs': [ref]}]),
                ref: 'pass',
            },
            'tasks': [{'task': {'id': 18}, 'godot': {}}],
        })
        return revision, ref

    def test_main_run_remains_verified_when_only_excluded_import_is_regenerated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            excluded_path = 'Tests.Godot/addons/gdUnit4/icons/test.png.import'
            _, ref = self._runtime_fixture(root, excluded_path)

            def passing_run(run_root, task, godot_bin, timeout, source_revision):
                generated = Path(task['_execution_root']) / excluded_path
                generated.parent.mkdir(parents=True, exist_ok=True)
                generated.write_text('regenerated', encoding='utf-8')
                return {
                    'task_id': '18', 'source_revision': source_revision, 'test_refs': [ref], 'scenes': [],
                    'status': 'passed', 'reason': None, 'started_at': 's', 'finished_at': 'f',
                    'evidence_path': 'logs/ci/project-health-knowledge/runtime/task.json', 'exit_code': 0,
                    'runtime_verified': False,
                }

            with patch('project_health_runtime._run_task', side_effect=passing_run):
                result = verify(root, 'godot.exe', 10, task_id='18', mode='main')
            task = result['tasks'][0]
            self.assertEqual(task['status'], 'passed')
            self.assertTrue(task['runtime_verified'])

    def test_main_run_becomes_unverified_when_retained_project_import_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            retained_path = 'Game.Godot/Assets/player.png.import'
            _, ref = self._runtime_fixture(root, retained_path)

            def passing_run(run_root, task, godot_bin, timeout, source_revision):
                changed = Path(task['_execution_root']) / retained_path
                changed.write_text('changed-during-run', encoding='utf-8')
                return {
                    'task_id': '18', 'source_revision': source_revision, 'test_refs': [ref], 'scenes': [],
                    'status': 'passed', 'reason': None, 'started_at': 's', 'finished_at': 'f',
                    'evidence_path': 'logs/ci/project-health-knowledge/runtime/task.json', 'exit_code': 0,
                    'runtime_verified': False,
                }

            with patch('project_health_runtime._run_task', side_effect=passing_run):
                result = verify(root, 'godot.exe', 10, task_id='18', mode='main')
            task = result['tasks'][0]
            self.assertEqual(task['status'], 'runtime_unverified')
            self.assertFalse(task['runtime_verified'])


if __name__ == '__main__':
    unittest.main()
