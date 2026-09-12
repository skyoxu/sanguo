from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(os.path.realpath(os.fspath(left))) == os.path.normcase(os.path.realpath(os.fspath(right)))

def _assert_path_mentioned(test: unittest.TestCase, text: str, path: Path) -> None:
    normalized = os.path.normcase(os.path.realpath(os.fspath(path)))
    test.assertIn(normalized, os.path.normcase(text))


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, encoding="utf-8", capture_output=True, check=False, timeout=120)


class WindowsOutputAliasTests(unittest.TestCase):
    def test_short_repository_alias_accepts_missing_output_and_existing_input(self):
        import ctypes
        from scripts.python import analyze_impact as cli

        with tempfile.TemporaryDirectory(prefix="impact-long-repository-") as directory:
            root = Path(directory).resolve()
            buffer = ctypes.create_unicode_buffer(32768)
            self.assertTrue(ctypes.windll.kernel32.GetShortPathNameW(str(root), buffer, len(buffer)))
            short_root = Path(buffer.value)
            self.assertNotEqual(short_root, root, "Fixture requires Windows 8.3 aliases")
            (root / "logs/ci").mkdir(parents=True)
            output = cli._validated_output(root, str(short_root / "logs/ci/new-output/report.json"))
            self.assertEqual(output, root / "logs/ci/new-output/report.json")
            source = root / "logs/ci/input.json"
            source.write_text("{}", encoding="utf-8")
            self.assertEqual(cli._resolve_inside(root, str(short_root / "logs/ci/input.json")), source)


class AnalyzeImpactCliTests(unittest.TestCase):
    # The builder is real; the frozen binding is synthetic, not a freeze integration proof.
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        for relative in (
            "scripts/python/analyze_impact.py",
            "scripts/python/impact_analyzer.py",
            "scripts/python/impact_analysis_handoff.py",
            "scripts/python/impact_analysis_index.py",
            "scripts/python/build_impact_index.py",
            "scripts/python/impact_analysis_config.v1.json",
            "scripts/python/impact_target_aliases.v1.json",
            "scripts/python/impact_runtime.py",
        ):
            destination = self.repo / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        files = {
            "project.godot": "[application]\nconfig/name=\"CLI Harness\"\n",
            "NewRouge.csproj": "<Project />\n",
            "Game.Core/Game.Core.csproj": "<Project />\n",
            "Game.Core.Tests/Game.Core.Tests.csproj": "<Project />\n",
            "Tests.Godot/Tests.Godot.csproj": "<Project />\n",
            "global.json": "{}\n",
            "Game.Godot/README.md": "# fixture\n",
            ".taskmaster/tasks/README.md": "# fixture\n",
            "docs/adr/README.md": "# fixture\n",
            "docs/architecture/README.md": "# fixture\n",
            "execution-plans/README.md": "# fixture\n",
            "decision-logs/README.md": "# fixture\n",
            "Game.Core/ImpactEvent.cs": "namespace Demo; public class ImpactEvent {}\n",
            "Game.Core/Consumer.cs": "namespace Demo; public class Consumer { private ImpactEvent? _event; }\n",
        }
        for relative, content in files.items():
            destination = self.repo / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")
        for command in (("git", "init", "-b", "main"), ("git", "config", "user.email", "cli@example.com"), ("git", "config", "user.name", "CLI Harness"), ("git", "add", "."), ("git", "commit", "-m", "fixture")):
            result = run(*command, cwd=self.repo)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        revision = run("git", "rev-parse", "HEAD", cwd=self.repo)
        self.assertEqual(revision.returncode, 0, revision.stderr)
        self.revision = revision.stdout.strip()
        build = run(sys.executable, "scripts/python/build_impact_index.py", "--revision", self.revision, "--trusted-ref", "refs/heads/main", "--output-root", "logs/ci", cwd=self.repo)
        self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
        self.index_payload = json.loads(build.stdout)
        self.index_path = self.repo / self.index_payload["index_path"]
        self.frozen_path = self.repo / "logs/ci/frozen.json"
        self.frozen_path.parent.mkdir(parents=True, exist_ok=True)
        self.frozen_path.write_text(json.dumps({
            "schema_version": "newrouge.knowledge-frozen-context.v1",
            "freeze_state": "frozen",
            "snapshot": {"commit": self.revision},
            "consumer": "chapter6",
            "task_id": "T-CLI",
            "decision_set_sha256": "1" * 64,
            "freeze_point": "before-red",
            "publication_generation": "generation-1",
            "publication_sha256": "2" * 64,
        }), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def command(self, output="logs/ci/integrity/impact-report.v1.json", **overrides):
        options = {"target": '{"type":"file","id":"Game.Core/ImpactEvent.cs"}',
                   "revision": self.revision, "index": str(self.index_path),
                   "frozen-context": self.frozen_path.relative_to(self.repo).as_posix(), "consumer": "chapter6",
                   "task-id": "T-CLI", "output": output, "repository-root": str(self.repo)}
        options.update(overrides)
        return [item for key, value in options.items() for item in ("--" + key, value)]

    def assert_failure_pair(self, payload):
        self.assertTrue(payload["evidence_saved"])
        report_path = self.repo / payload["report_path"]
        report = json.loads(report_path.read_bytes())
        manifest = json.loads(report_path.with_name("run-manifest.v1.json").read_bytes())
        self.assertEqual(report["status"], payload["code"])
        self.assertEqual(manifest["status"], payload["code"])
        self.assertEqual(manifest["run_id"], payload["run_id"])
        self.assertEqual(manifest["report_path"], payload["report_path"])
        self.assertEqual(manifest["report_sha256"], hashlib.sha256(report_path.read_bytes()).hexdigest())
        self.assertEqual(manifest["report_sha256"], payload["report_sha256"])

    def test_invalid_revision_preserves_failure_pair(self):
        result = run(sys.executable, "scripts/python/analyze_impact.py", *self.command(revision="bad"), cwd=self.repo)
        self.assertEqual(result.returncode, 7)
        self.assert_failure_pair(json.loads(result.stdout))

    def test_nonserializable_target_preserves_failure_pair(self):
        for index, target in enumerate(('{"type":"file","id":NaN}', '{"type":"file","id":"\\ud800"}')):
            with self.subTest(target=target):
                result = run(sys.executable, "scripts/python/analyze_impact.py", *self.command(f"logs/ci/invalid-target-{index}/report.json", target=target), cwd=self.repo)
                self.assertNotEqual(result.returncode, 0)
                self.assert_failure_pair(json.loads(result.stdout))

    def test_invalid_output_uses_isolated_diagnostics(self):
        for output in ("outside.json", "logs/ci/reserved/run-manifest.v1.json", "logs/ci/reserved/CON.json"):
            with self.subTest(output=output):
                result = run(sys.executable, "scripts/python/analyze_impact.py", *self.command(output), cwd=self.repo)
                self.assertNotEqual(result.returncode, 0)
                payload = json.loads(result.stdout)
                self.assert_failure_pair(payload)
                self.assertNotEqual(payload["report_path"], output)
                self.assertFalse((self.repo / output).exists())
        result = run(sys.executable, "scripts/python/analyze_impact.py", *self.command("logs/ci"), cwd=self.repo)
        self.assertEqual(result.returncode, 4)
        self.assert_failure_pair(json.loads(result.stdout))
        self.assertFalse((self.repo / "logs/.impact-report-publish.lock").exists())
        self.assertFalse((self.repo / "logs/run-manifest.v1.json").exists())

    def test_single_existing_artifact_is_preserved_without_binding_it(self):
        for existing_name in ("impact-report.v1.json", "run-manifest.v1.json"):
            with self.subTest(existing=existing_name):
                directory = self.repo / "logs/ci" / existing_name
                directory.mkdir()
                existing = directory / existing_name
                existing.write_bytes(b"original")
                output = directory / "impact-report.v1.json"
                result = run(sys.executable, "scripts/python/analyze_impact.py", *self.command(str(output)), cwd=self.repo)
                self.assertEqual(result.returncode, 10)
                self.assertEqual(existing.read_bytes(), b"original")
                self.assertEqual(list(directory.iterdir()), [existing])
                self.assert_failure_pair(json.loads(result.stdout))

    def test_concurrent_cli_writers_keep_one_consistent_pair(self):
        command = [sys.executable, "scripts/python/analyze_impact.py", *self.command()]
        writers = [subprocess.Popen(command, cwd=self.repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8") for _ in range(2)]
        results = [(writer, writer.communicate(timeout=120)) for writer in writers]
        self.assertEqual(sorted(writer.returncode for writer, _ in results), [0, 10])
        for writer, (stdout, stderr) in results:
            payload = json.loads(stdout)
            if writer.returncode:
                self.assert_failure_pair(payload)
            else:
                report = self.repo / payload["report_path"]
                manifest = json.loads(report.with_name("run-manifest.v1.json").read_bytes())
                self.assertEqual(manifest["run_id"], payload["run_id"])
                self.assertEqual(manifest["report_sha256"], hashlib.sha256(report.read_bytes()).hexdigest())

    def test_manifest_failure_removes_owned_success_and_saves_failure_pair(self):
        from scripts.python import analyze_impact as cli
        publish = cli.atomic_publish_bytes
        output = self.repo / "logs/ci/partial/impact-report.v1.json"
        def fail_manifest(path, *args, **kwargs):
            if _same_path(path, output.with_name("run-manifest.v1.json")):
                raise OSError("injected second publication failure")
            return publish(path, *args, **kwargs)
        stdout = StringIO()
        with mock.patch.object(cli, "atomic_publish_bytes", side_effect=fail_manifest), redirect_stdout(stdout):
            result = cli.main(self.command(str(output)))
        self.assertEqual(result, 12)
        self.assertFalse(output.exists())
        self.assertFalse(output.with_name("run-manifest.v1.json").exists())
        self.assert_failure_pair(json.loads(stdout.getvalue()))

    def test_storage_failure_explicitly_reports_unsaved_evidence(self):
        from scripts.python import analyze_impact as cli
        stdout = StringIO()
        with mock.patch.object(cli, "atomic_publish_bytes", side_effect=PermissionError("storage unavailable")), redirect_stdout(stdout):
            result = cli.main(self.command())
        self.assertEqual(result, 12)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["evidence_saved"])
        self.assertIn("evidence_error", payload)
        self.assertNotIn("report_path", payload)

    def test_reparse_output_escape_is_rejected_and_preserves_destination(self):
        outside = self.repo / "outside"
        outside.mkdir()
        link = self.repo / "logs/ci/redirect"
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], check=True, capture_output=True, timeout=30)
        try:
            result = run(sys.executable, "scripts/python/analyze_impact.py", *self.command("logs/ci/redirect/report.json"), cwd=self.repo)
            self.assertEqual(result.returncode, 4)
            self.assertEqual(list(outside.iterdir()), [])
            self.assert_failure_pair(json.loads(result.stdout))
        finally:
            link.rmdir()

    def test_same_bytes_replacement_is_not_removed_by_compensation(self):
        from scripts.python import analyze_impact as cli
        publish = cli.atomic_publish_bytes
        output = self.repo / "logs/ci/replaced/impact-report.v1.json"
        replacement_identity = None
        def replace_then_fail(path, *args, **kwargs):
            nonlocal replacement_identity
            if _same_path(path, output.with_name("run-manifest.v1.json")):
                replacement = output.with_name("replacement.json")
                replacement.write_bytes(output.read_bytes())
                output.unlink()
                replacement.rename(output)
                replacement_identity = output.stat().st_ino
                raise OSError("injected competing replacement")
            return publish(path, *args, **kwargs)
        stdout = StringIO()
        with mock.patch.object(cli, "atomic_publish_bytes", side_effect=replace_then_fail), redirect_stdout(stdout):
            result = cli.main(self.command(str(output)))
        self.assertEqual(result, 12)
        self.assertEqual(output.stat().st_ino, replacement_identity)
        self.assertFalse(output.with_name("run-manifest.v1.json").exists())
        self.assert_failure_pair(json.loads(stdout.getvalue()))

    def test_lock_cleanup_failure_reports_completed_pair_with_warning(self):
        from scripts.python import analyze_impact as cli
        original = Path.rmdir
        def deny_lock_cleanup(path):
            if path.name == ".impact-report-publish.lock":
                raise PermissionError("injected lock cleanup failure")
            return original(path)
        stdout = StringIO()
        with mock.patch.object(Path, "rmdir", new=deny_lock_cleanup), redirect_stdout(stdout):
            result = cli.main(self.command())
        self.assertEqual(result, 0)
        payload = json.loads(stdout.getvalue())
        self.assertIn("cleanup_warning", payload)
        report = self.repo / payload["report_path"]
        manifest = json.loads(report.with_name("run-manifest.v1.json").read_bytes())
        self.assertEqual(manifest["report_sha256"], hashlib.sha256(report.read_bytes()).hexdigest())

    def test_report_delete_failure_quarantines_owned_report(self):
        from scripts.python import analyze_impact as cli
        publish, unlink = cli.atomic_publish_bytes, Path.unlink
        output = self.repo / "logs/ci/delete-failed/impact-report.v1.json"
        def fail_manifest(path, *args, **kwargs):
            if _same_path(path, output.with_name("run-manifest.v1.json")):
                raise OSError("injected second publication failure")
            return publish(path, *args, **kwargs)
        def fail_delete(path, *args, **kwargs):
            if _same_path(path, output):
                raise PermissionError("injected deletion failure")
            return unlink(path, *args, **kwargs)
        stdout = StringIO()
        with mock.patch.object(cli, "atomic_publish_bytes", side_effect=fail_manifest), mock.patch.object(Path, "unlink", new=fail_delete), redirect_stdout(stdout):
            result = cli.main(self.command(str(output)))
        self.assertEqual(result, 12)
        self.assertFalse(output.exists())
        self.assertEqual(len(list(output.parent.glob(".unpublished-*.tmp"))), 1)
        payload = json.loads(stdout.getvalue())
        self.assertIn("quarantined", payload["reason"])
        self.assert_failure_pair(payload)

    def test_real_cli_success_discovery_and_manifest_hashes(self) -> None:
        output = "logs/ci/cli-run/impact-report.v1.json"
        command = (sys.executable, "scripts/python/analyze_impact.py", "--target", '{"type":"file","id":"Game.Core/ImpactEvent.cs"}', "--revision", self.revision, "--trusted-ref", "refs/heads/main", "--frozen-context", "logs/ci/frozen.json", "--consumer", "chapter6", "--task-id", "T-CLI", "--output", output, "--repository-root", ".")
        result = run(*command, cwd=self.repo)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        report_path = self.repo / payload["report_path"]
        manifest_path = report_path.parent / "run-manifest.v1.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(report["repository_revision"], self.revision)
        self.assertEqual(manifest["repository_revision"], self.revision)
        self.assertEqual(manifest["report_sha256"], hashlib.sha256(report_path.read_bytes()).hexdigest())
        self.assertEqual(manifest["index_sha256"], hashlib.sha256(self.index_path.read_bytes()).hexdigest())

    def test_review_identity_does_not_require_postpublication_stat(self):
        from scripts.python import analyze_impact as cli
        publish, stat = cli.atomic_publish_bytes, Path.stat
        output = self.repo / "logs/ci/stat-after/report.json"
        published = False
        def publish_then_deny_stat(path, *args, **kwargs):
            nonlocal published
            result = publish(path, *args, **kwargs)
            if _same_path(path, output):
                published = True
            return result
        def deny_stat(path, *args, **kwargs):
            if _same_path(path, output) and published:
                raise PermissionError("postpublication metadata denied")
            return stat(path, *args, **kwargs)
        stdout = StringIO()
        with mock.patch.object(cli, "atomic_publish_bytes", side_effect=publish_then_deny_stat), mock.patch.object(Path, "stat", new=deny_stat), redirect_stdout(stdout):
            result = cli.main(self.command(str(output)))
        self.assertEqual(result, 0, stdout.getvalue())
        manifest = json.loads(output.with_name("run-manifest.v1.json").read_bytes())
        self.assertEqual(manifest["report_sha256"], hashlib.sha256(output.read_bytes()).hexdigest())

    def test_review_rollback_queries_preserve_original_error_and_residual(self):
        from scripts.python import analyze_impact as cli
        publish, stat, read = cli.atomic_publish_bytes, Path.stat, Path.read_bytes
        for operation in ("stat", "read"):
            with self.subTest(operation=operation):
                output = self.repo / f"logs/ci/rollback-{operation}/report.json"
                rollback = False
                def fail_manifest(path, *args, **kwargs):
                    nonlocal rollback
                    if _same_path(path, output.with_name("run-manifest.v1.json")):
                        rollback = True
                        raise OSError("original manifest publication failure")
                    return publish(path, *args, **kwargs)
                def deny_stat(path, *args, **kwargs):
                    if _same_path(path, output) and rollback and operation == "stat":
                        raise PermissionError("rollback metadata denied")
                    return stat(path, *args, **kwargs)
                def deny_read(path, *args, **kwargs):
                    if _same_path(path, output) and rollback and operation == "read":
                        raise PermissionError("rollback read denied")
                    return read(path, *args, **kwargs)
                stdout = StringIO()
                with mock.patch.object(cli, "atomic_publish_bytes", side_effect=fail_manifest), mock.patch.object(Path, "stat", new=deny_stat), mock.patch.object(Path, "read_bytes", new=deny_read), redirect_stdout(stdout):
                    result = cli.main(self.command(str(output)))
                self.assertEqual(result, 12)
                payload = json.loads(stdout.getvalue())
                self.assertIn("original manifest publication failure", payload["reason"])
                _assert_path_mentioned(self, payload["reason"], output)
                self.assertIn("residual", payload["reason"])
                self.assertTrue(output.is_file())
                self.assertFalse(output.with_name("run-manifest.v1.json").exists())
                self.assert_failure_pair(payload)

    def test_review_double_rollback_denial_preserves_original_error(self):
        from scripts.python import analyze_impact as cli
        publish, unlink, rename = cli.atomic_publish_bytes, Path.unlink, Path.rename
        output = self.repo / "logs/ci/rollback-denied/report.json"
        def fail_manifest(path, *args, **kwargs):
            if _same_path(path, output.with_name("run-manifest.v1.json")):
                raise OSError("original manifest publication failure")
            return publish(path, *args, **kwargs)
        def deny_unlink(path, *args, **kwargs):
            if _same_path(path, output):
                raise PermissionError("delete denied")
            return unlink(path, *args, **kwargs)
        def deny_rename(path, *args, **kwargs):
            if _same_path(path, output):
                raise PermissionError("quarantine denied")
            return rename(path, *args, **kwargs)
        stdout = StringIO()
        with mock.patch.object(cli, "atomic_publish_bytes", side_effect=fail_manifest), mock.patch.object(Path, "unlink", new=deny_unlink), mock.patch.object(Path, "rename", new=deny_rename), redirect_stdout(stdout):
            result = cli.main(self.command(str(output)))
        self.assertEqual(result, 12)
        payload = json.loads(stdout.getvalue())
        for text in ("original manifest publication failure", "delete denied", "quarantine denied", "residual"):
            self.assertIn(text, payload["reason"])
        _assert_path_mentioned(self, payload["reason"], output)
        self.assertTrue(output.is_file())
        self.assert_failure_pair(payload)

    def test_review_failure_retains_lock_cleanup_diagnostic(self):
        from scripts.python import analyze_impact as cli
        publish, rmdir = cli.atomic_publish_bytes, Path.rmdir
        output = self.repo / "logs/ci/lock-failed/report.json"
        lock = output.parent / ".impact-report-publish.lock"
        def fail_manifest(path, *args, **kwargs):
            if _same_path(path, output.with_name("run-manifest.v1.json")):
                raise OSError("original manifest publication failure")
            return publish(path, *args, **kwargs)
        def deny_rmdir(path, *args, **kwargs):
            if _same_path(path, lock):
                raise PermissionError("lock removal denied")
            return rmdir(path, *args, **kwargs)
        stdout = StringIO()
        with mock.patch.object(cli, "atomic_publish_bytes", side_effect=fail_manifest), mock.patch.object(Path, "rmdir", new=deny_rmdir), redirect_stdout(stdout):
            result = cli.main(self.command(str(output)))
        self.assertEqual(result, 12)
        payload = json.loads(stdout.getvalue())
        for text in ("original manifest publication failure", "lock removal denied"):
            self.assertIn(text, payload["reason"])
        _assert_path_mentioned(self, payload["reason"], lock)
        report = json.loads((self.repo / payload["report_path"]).read_bytes())
        self.assertEqual(report["failure_reason"]["reason"], payload["reason"])
        self.assertTrue(lock.is_dir())
        self.assertFalse(output.exists())
        self.assert_failure_pair(payload)

    def test_review_logs_ci_root_junction_never_receives_fallback(self):
        original = self.repo / "logs/ci"
        redirected = self.repo / "redirected-ci"
        original.rename(redirected)
        before = {p.relative_to(redirected): p.read_bytes() for p in redirected.rglob("*") if p.is_file()}
        subprocess.run(["cmd", "/c", "mklink", "/J", str(original), str(redirected)], check=True, capture_output=True, timeout=30)
        try:
            result = run(sys.executable, "scripts/python/analyze_impact.py", *self.command(), cwd=self.repo)
            self.assertEqual(result.returncode, 4)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["evidence_saved"])
            self.assertIn("evidence_error", payload)
            self.assertNotIn("report_path", payload)
            after = {p.relative_to(redirected): p.read_bytes() for p in redirected.rglob("*") if p.is_file()}
            self.assertEqual(after, before)
        finally:
            original.rmdir()
            redirected.rename(original)

    def test_review_fallback_retains_failed_diagnostic_attempt_lock(self):
        from scripts.python import analyze_impact as cli
        publish, rmdir = cli.atomic_publish_bytes, Path.rmdir
        output = self.repo / "logs/ci/early-lock-failed/report.json"
        lock = output.parent / ".impact-report-publish.lock"
        def fail_manifest(path, *args, **kwargs):
            if _same_path(path, output.with_name("run-manifest.v1.json")):
                raise OSError("diagnostic manifest publication denied")
            return publish(path, *args, **kwargs)
        def deny_rmdir(path, *args, **kwargs):
            if _same_path(path, lock):
                raise PermissionError("diagnostic lock cleanup denied")
            return rmdir(path, *args, **kwargs)
        stdout = StringIO()
        with mock.patch.object(cli, "atomic_publish_bytes", side_effect=fail_manifest), mock.patch.object(Path, "rmdir", new=deny_rmdir), redirect_stdout(stdout):
            result = cli.main(self.command(str(output), revision="bad"))
        self.assertEqual(result, 7)
        payload = json.loads(stdout.getvalue())
        _assert_path_mentioned(self, payload["evidence_warning"], lock)
        report = json.loads((self.repo / payload["report_path"]).read_bytes())
        for text in ("revision must be", "diagnostic manifest publication denied", "diagnostic lock cleanup denied"):
            self.assertIn(text, report["failure_reason"]["reason"])
        _assert_path_mentioned(self, report["failure_reason"]["reason"], lock)
        self.assertTrue(lock.is_dir())
        self.assert_failure_pair(payload)

    def test_review_contender_is_rejected_while_first_writer_is_paused(self):
        from scripts.python import analyze_impact as cli
        publish = cli.atomic_publish_bytes
        output = self.repo / "logs/ci/controlled-race/report.json"
        contender_stdout = StringIO()
        raced = False
        def pause_for_contender(path, *args, **kwargs):
            nonlocal raced
            if _same_path(path, output) and not raced:
                raced = True
                self.assertFalse(output.exists())
                self.assertTrue((output.parent / ".impact-report-publish.lock").is_dir())
                with redirect_stdout(contender_stdout):
                    contender_result = cli.main(self.command(str(output)))
                self.assertEqual(contender_result, 10)
                self.assertFalse(output.exists())
                self.assertFalse(output.with_name("run-manifest.v1.json").exists())
            return publish(path, *args, **kwargs)
        stdout = StringIO()
        with mock.patch.object(cli, "atomic_publish_bytes", side_effect=pause_for_contender), redirect_stdout(stdout):
            result = cli.main(self.command(str(output)))
        self.assertTrue(raced)
        self.assertEqual(result, 0, stdout.getvalue())
        self.assert_failure_pair(json.loads(contender_stdout.getvalue()))
        payload = json.loads(stdout.getvalue())
        manifest = json.loads(output.with_name("run-manifest.v1.json").read_bytes())
        self.assertEqual(manifest["run_id"], payload["run_id"])
        self.assertEqual(manifest["report_sha256"], hashlib.sha256(output.read_bytes()).hexdigest())

    def test_invalid_handoff_fails_closed_without_success_report(self) -> None:
        output = self.repo / "logs/ci/cli-run-invalid/impact-report.v1.json"
        result = run(sys.executable, "scripts/python/analyze_impact.py", "--target", '{"type":"file","id":"Game.Core/ImpactEvent.cs"}', "--revision", self.revision, "--index", str(self.index_path.relative_to(self.repo)), "--frozen-context", "logs/ci/missing.json", "--consumer", "chapter6", "--task-id", "T-CLI", "--output", output.relative_to(self.repo).as_posix(), cwd=self.repo)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(output.exists())
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["status"], "invalid_kcp_binding")

    def test_discovery_rejects_multiple_index_provenances(self) -> None:
        duplicate = self.repo / "logs/ci/duplicate/impact-analysis/indexes/duplicate"
        shutil.copytree(self.index_path.parent, duplicate)
        manifest = duplicate / "index-manifest.v1.json"
        document = json.loads(manifest.read_text(encoding="utf-8"))
        document["trusted_ref"] = "refs/heads/other"
        manifest.write_text(json.dumps(document), encoding="utf-8")
        output = "logs/ci/cli-collision-discovery/impact-report.v1.json"
        result = run(sys.executable, "scripts/python/analyze_impact.py", "--target", '{"type":"file","id":"Game.Core/ImpactEvent.cs"}', "--revision", self.revision, "--frozen-context", "logs/ci/frozen.json", "--consumer", "chapter6", "--task-id", "T-CLI", "--output", output, cwd=self.repo)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads((self.repo / output).read_text(encoding="utf-8"))["status"], "index_identity_collision")

    def test_output_collision_does_not_overwrite_report(self) -> None:
        output = self.repo / "logs/ci/cli-collision/report.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        original = b"existing"
        output.write_bytes(original)
        manifest = output.parent / "run-manifest.v1.json"
        manifest_original = b"existing-manifest"
        manifest.write_bytes(manifest_original)
        result = run(sys.executable, "scripts/python/analyze_impact.py", "--target", '{"type":"file","id":"Game.Core/ImpactEvent.cs"}', "--revision", self.revision, "--index", self.index_path.relative_to(self.repo).as_posix(), "--frozen-context", "logs/ci/frozen.json", "--consumer", "chapter6", "--task-id", "T-CLI", "--output", output.relative_to(self.repo).as_posix(), cwd=self.repo)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output.read_bytes(), original)
        self.assertEqual(manifest.read_bytes(), manifest_original)

    def test_malformed_target_fails_closed(self) -> None:
        output = self.repo / "logs/ci/cli-malformed/impact-report.v1.json"
        result = run(sys.executable, "scripts/python/analyze_impact.py", "--target", "{type:unknown}", "--revision", self.revision, "--index", self.index_path.relative_to(self.repo).as_posix(), "--frozen-context", "logs/ci/frozen.json", "--consumer", "chapter6", "--task-id", "T-CLI", "--output", output.relative_to(self.repo).as_posix(), cwd=self.repo)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(output.exists())
        self.assert_failure_pair(json.loads(result.stdout))


if __name__ == "__main__":
    unittest.main()
