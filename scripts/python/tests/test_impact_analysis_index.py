from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "scripts/python/impact_analysis_index.py"


def load_module():
    if not MODULE_PATH.is_file():
        return None
    spec = importlib.util.spec_from_file_location("impact_analysis_index", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def make_directory_link(link: Path, target: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        subprocess.check_call(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )


class ImpactIndexTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = load_module()

    def require_module(self):
        if self.index is None:
            self.fail("scripts/python/impact_analysis_index.py is missing")
        return self.index


class CanonicalIdentityTests(ImpactIndexTestCase):
    def test_jcs_golden_vectors_are_stable(self) -> None:
        index = self.require_module()
        fixture = json.loads(
            (ROOT / "scripts/python/tests/fixtures/impact-index-id-jcs-v1.json").read_text(
                encoding="utf-8"
            )
        )
        for vector in fixture["vectors"]:
            with self.subTest(vector=vector["name"]):
                canonical = index.jcs_bytes(vector["input"])
                self.assertEqual(canonical.decode("utf-8"), vector["canonical_utf8"])
                self.assertEqual(index.sha256_bytes(canonical), vector["expected_sha256"])
                if "expected_index_id" in vector:
                    self.assertEqual(index.derive_index_id(vector["input"]), vector["expected_index_id"])

    def test_jcs_rejects_unsafe_integers_and_non_finite_numbers(self) -> None:
        index = self.require_module()
        for value in (9007199254740992, -9007199254740992, float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(index.ImpactIndexError) as raised:
                    index.jcs_bytes({"value": value})
                self.assertEqual(raised.exception.code, "invalid_manifest")

    def test_json_loader_rejects_duplicate_keys_and_non_finite_constants(self) -> None:
        index = self.require_module()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.json"
            for content, reason in (
                (b'{"key":1,"key":2}', "duplicate"),
                (b'{"value":NaN}', "non-finite"),
                (b'{"value":Infinity}', "non-finite"),
                (b'{"value":-Infinity}', "non-finite"),
            ):
                with self.subTest(content=content):
                    path.write_bytes(content)
                    with self.assertRaises(index.ImpactIndexError) as raised:
                        index.load_json_bytes(path)
                    self.assertEqual(raised.exception.code, "invalid_manifest")
                    self.assertIn(reason, raised.exception.reason)

    def test_artifact_validators_reject_duplicate_keys_before_schema_validation(self) -> None:
        index = self.require_module()
        for validator, content in (
            (index.validate_index_bytes, b'{"schema_version":"a","schema_version":"b"}'),
            (index.validate_manifest_bytes, b'{"schema_version":"a","schema_version":"b"}'),
        ):
            with self.subTest(validator=validator.__name__):
                with self.assertRaises(index.ImpactIndexError) as raised:
                    validator(content)
                self.assertEqual(raised.exception.code, "invalid_manifest")
                self.assertIn("duplicate", raised.exception.reason)

    def test_git_subprocesses_have_an_explicit_timeout(self) -> None:
        index = self.require_module()
        completed = subprocess.CompletedProcess(["git"], 0, stdout=b"", stderr=b"")
        with mock.patch.object(index.subprocess, "run", return_value=completed) as run_mock:
            index._git(Path.cwd(), "status")
        self.assertEqual(run_mock.call_args.kwargs["timeout"], index.GIT_TIMEOUT_SECONDS)

    def test_oversized_identity_blob_is_rejected_before_blob_capture(self) -> None:
        index = self.require_module()
        config = {
            "scan_roots": ["Game.Core"],
            "identity_files": ["Game.Core/Huge.cs"],
            "exclusions": [],
            "source_rules": [
                {
                    "suffixes": [".cs"],
                    "path_prefixes": [],
                    "source_kind": "csharp",
                    "parser_family": "csharp-text",
                    "parser_version": "v1",
                    "binary": False,
                }
            ],
            "maximum_file_size_bytes": 10,
            "allow_identity_only": True,
        }

        class Snapshot:
            entries = [
                SimpleNamespace(
                    mode="100644",
                    object_type="blob",
                    object_id="a" * 40,
                    path="Game.Core/Huge.cs",
                    size_bytes=100,
                )
            ]

            def read_blob(self, entry):
                raise index.ImpactIndexError("internal_error", "oversized blob was captured")

        with self.assertRaises(index.ImpactIndexError) as raised:
            index.build_source_manifest(
                Snapshot(),
                config,
                config_path="Game.Core/Huge.cs",
                aliases_path="Game.Core/Huge.cs",
            )
        self.assertEqual(raised.exception.code, "invalid_manifest")

    def test_repository_path_policy_rejects_escape_and_windows_absolute_forms(self) -> None:
        index = self.require_module()
        for value in ("../secret.txt", "/absolute.txt", "C:/absolute.txt", "C:relative.txt", "//server/share"):
            with self.subTest(value=value):
                with self.assertRaises(index.ImpactIndexError) as raised:
                    index.normalize_repository_path(value)
                self.assertEqual(raised.exception.code, "path_outside_repository")
        self.assertEqual(index.normalize_repository_path(r"Game.Core\Domain.cs"), "Game.Core/Domain.cs")

    def test_config_rules_exclusions_and_required_identities_are_strict(self) -> None:
        index = self.require_module()
        source = json.loads((ROOT / "scripts/python/impact_analysis_config.v1.json").read_text(encoding="utf-8"))
        mutations = {
            "source rule extra": lambda value: value["source_rules"][0].__setitem__("typo", True),
            "source rule missing": lambda value: value["source_rules"][0].pop("binary"),
            "exclusion extra": lambda value: value["exclusions"][0].__setitem__("typo", True),
            "exclusion missing selector": lambda value: value["exclusions"][0].pop("path_prefix"),
            "exclusion both selectors": lambda value: value["exclusions"][0].__setitem__("path_pattern", "*.tmp"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                candidate = json.loads(json.dumps(source))
                mutate(candidate)
                with self.assertRaises(index.ImpactIndexError) as raised:
                    index.validate_config(candidate)
                self.assertEqual(raised.exception.code, "invalid_manifest")
        for required in (
            "scripts/python/impact_analysis_index.py",
            "scripts/python/build_impact_index.py",
            "scripts/python/impact_analysis_config.v1.json",
            "scripts/python/impact_target_aliases.v1.json",
            "scripts/python/impact_runtime.py",
        ):
            with self.subTest(required=required):
                candidate = json.loads(json.dumps(source))
                candidate["identity_files"].remove(required)
                with self.assertRaises(index.ImpactIndexError) as raised:
                    index.validate_config(candidate)
                self.assertEqual(raised.exception.code, "invalid_manifest")

    def test_alias_schema_requires_exact_event_and_contract_tables(self) -> None:
        index = self.require_module()
        source = json.loads((ROOT / "scripts/python/impact_target_aliases.v1.json").read_text(encoding="utf-8"))
        mutations = {
            "missing event": lambda value: value["aliases"].pop("event"),
            "missing contract": lambda value: value["aliases"].pop("contract"),
            "extra kind": lambda value: value["aliases"].__setitem__("class", {}),
            "non object map": lambda value: value["aliases"].__setitem__("event", []),
            "non string mapping": lambda value: value["aliases"]["event"].__setitem__("old", 123),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                candidate = json.loads(json.dumps(source))
                mutate(candidate)
                with self.assertRaises(index.ImpactIndexError) as raised:
                    index.validate_aliases(candidate)
                self.assertEqual(raised.exception.code, "invalid_manifest")

    def test_windows_access_denied_process_probe_treats_pid_as_alive(self) -> None:
        index = self.require_module()
        probe = getattr(index, "_windows_process_info", None)
        self.assertIsNotNone(probe, "a testable Win32 process probe is required")
        open_process = mock.Mock(return_value=0)
        get_process_times = mock.Mock(return_value=0)
        close_handle = mock.Mock(return_value=1)
        kernel32 = SimpleNamespace(
            OpenProcess=open_process,
            GetProcessTimes=get_process_times,
            CloseHandle=close_handle,
        )
        alive, token = probe(123, kernel32=kernel32, get_last_error=lambda: 5)
        self.assertTrue(alive)
        self.assertIsNone(token)
        missing, token = probe(123, kernel32=kernel32, get_last_error=lambda: 87)
        self.assertFalse(missing)
        self.assertIsNone(token)


class RepositoryFixture(ImpactIndexTestCase):
    def setUp(self) -> None:
        self.require_module()
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        subprocess.check_call(["git", "init", "-b", "main"], cwd=self.repo, stdout=subprocess.DEVNULL)
        subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=self.repo)
        subprocess.check_call(["git", "config", "user.name", "Test"], cwd=self.repo)
        subprocess.check_call(["git", "config", "core.autocrlf", "false"], cwd=self.repo)
        for relative in (
            "scripts/python/impact_analysis_handoff.py",
            "scripts/python/impact_analysis_index.py",
            "scripts/python/build_impact_index.py",
            "scripts/python/impact_analysis_config.v1.json",
            "scripts/python/impact_target_aliases.v1.json",
            "scripts/python/impact_runtime.py",
        ):
            source = ROOT / relative
            if not source.is_file():
                self.fail(f"required implementation artifact is missing: {relative}")
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        files = {
            ".gitignore": "logs/\n",
            ".gitattributes": "*.cs text\n*.py text\n*.json text\n*.csproj text\n*.godot text\n*.md text\n",
            "project.godot": "[application]\nconfig/name=\"Fixture\"\n",
            "NewRouge.csproj": "<Project Sdk=\"Godot.NET.Sdk/4.5.1\" />\n",
            "global.json": "{\"sdk\":{\"version\":\"8.0.100\"}}\n",
            "Game.Core/Game.Core.csproj": "<Project Sdk=\"Microsoft.NET.Sdk\" />\n",
            "Game.Core/Domain.cs": "namespace NewRouge.Core; public sealed class Domain {}\n",
            "Game.Core/Contracts/Event.cs": "namespace NewRouge.Core.Contracts; public sealed class Event {}\n",
            "Game.Core.Tests/Game.Core.Tests.csproj": "<Project Sdk=\"Microsoft.NET.Sdk\" />\n",
            "Game.Core.Tests/DomainTests.cs": "namespace NewRouge.Core.Tests; public sealed class DomainTests {}\n",
            "Game.Godot/Scenes/Main.tscn": "[gd_scene format=3]\n[node name=\"Main\" type=\"Node\"]\n",
            "Game.Godot/Scripts/Unsupported.gd": "extends Node\n",
            "Game.Godot/Tests/unsupported.feature": "Feature: unsupported\n",
            "Game.Godot/Translations/unsupported.csv": "key,en\nsample,Sample\n",
            "Tests.Godot/Tests.Godot.csproj": "<Project Sdk=\"Godot.NET.Sdk/4.5.1\" />\n",
            "docs/adr/ADR-0011-windows-only-platform-and-ci.md": "# ADR-0011\n\n- Status: Accepted\n",
            "docs/architecture/base/00-README.md": "# Architecture\n",
            "execution-plans/fixture.md": "# Execution Plan\n",
            "decision-logs/fixture.md": "# Decision Log\n",
            ".taskmaster/tasks/tasks.json": "{\"master\":{\"tasks\":[]}}\n",
        }
        for relative, content in files.items():
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="\n")
        subprocess.check_call(["git", "add", "."], cwd=self.repo)
        subprocess.check_call(["git", "commit", "-m", "seed"], cwd=self.repo, stdout=subprocess.DEVNULL)
        self.revision = run("git", "rev-parse", "HEAD", cwd=self.repo).stdout.strip()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def build(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return self.build_with_ref("refs/heads/main", *extra)

    def build_with_ref(self, trusted_ref: str, *extra: str) -> subprocess.CompletedProcess[str]:
        return run(
            sys.executable,
            "scripts/python/build_impact_index.py",
            "--revision",
            self.revision,
            "--trusted-ref",
            trusted_ref,
            "--output-root",
            "logs/ci",
            *extra,
            cwd=self.repo,
        )

    def commit_all(self, message: str) -> None:
        subprocess.check_call(["git", "add", "."], cwd=self.repo)
        subprocess.check_call(["git", "commit", "-m", message], cwd=self.repo, stdout=subprocess.DEVNULL)
        self.revision = run("git", "rev-parse", "HEAD", cwd=self.repo).stdout.strip()

    def update_config(self, update) -> None:
        path = self.repo / "scripts/python/impact_analysis_config.v1.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        update(config)
        path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    def payload(self, completed: subprocess.CompletedProcess[str]) -> dict:
        self.assertTrue(completed.stdout.strip(), completed.stderr)
        return json.loads(completed.stdout)


class ManifestAndPublicationTests(RepositoryFixture):
    def test_manifest_is_deterministic_and_exact_second_build_reuses_artifact(self) -> None:
        first = self.build()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        first_payload = self.payload(first)
        second = self.build()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        second_payload = self.payload(second)
        self.assertFalse(first_payload["reused"])
        self.assertTrue(second_payload["reused"])
        self.assertEqual(first_payload["index_id"], second_payload["index_id"])
        self.assertEqual(first_payload["source_manifest_sha256"], second_payload["source_manifest_sha256"])
        self.assertEqual(first_payload["index_sha256"], second_payload["index_sha256"])
        index_path = self.repo / first_payload["index_path"]
        manifest_path = self.repo / first_payload["manifest_path"]
        index_doc = json.loads(index_path.read_text(encoding="utf-8"))
        manifest_doc = json.loads(manifest_path.read_text(encoding="utf-8"))
        paths = [item["path"] for item in index_doc["source_manifest"]]
        entries = {item["path"]: item for item in index_doc["source_manifest"]}
        self.assertEqual(paths, sorted(paths, key=lambda value: value.encode("utf-8")))
        self.assertEqual(entries["Game.Core/Contracts/Event.cs"]["source_kind"], "contract")
        self.assertEqual(entries["Game.Godot/Scenes/Main.tscn"]["source_kind"], "scene")
        self.assertEqual(entries[".taskmaster/tasks/tasks.json"]["source_kind"], "task")
        self.assertEqual(
            entries["docs/adr/ADR-0011-windows-only-platform-and-ci.md"]["source_kind"],
            "adr",
        )
        for path in (
            "Game.Godot/Tests/unsupported.feature",
            "Game.Godot/Translations/unsupported.csv",
        ):
            self.assertFalse(entries[path]["included"])
            self.assertEqual(entries[path]["exclusion_reason"], "unsupported_file_class")
        self.assertEqual(manifest_doc["artifact_sha256"], first_payload["index_sha256"])
        self.assertEqual(index_doc["repository_revision"], self.revision)

    def test_crlf_checkout_matching_git_clean_filters_is_not_dirty(self) -> None:
        subprocess.check_call(["git", "config", "core.autocrlf", "true"], cwd=self.repo)
        path = self.repo / "Game.Core/Domain.cs"
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        diff = run("git", "diff", "--quiet", "HEAD", "--", "Game.Core/Domain.cs", cwd=self.repo)
        self.assertEqual(diff.returncode, 0, "fixture must be Git-clean after CRLF checkout normalization")
        completed = self.build()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_missing_or_case_wrong_scan_root_is_invalid_manifest(self) -> None:
        self.update_config(lambda config: config.__setitem__("scan_roots", ["game.core"]))
        self.commit_all("case-wrong root")
        completed = self.build()
        self.assertEqual(completed.returncode, 15, completed.stdout + completed.stderr)
        self.assertEqual(self.payload(completed)["code"], "invalid_manifest")

    def test_identity_only_scan_requires_explicit_policy(self) -> None:
        identity_files = [
            "scripts/python/impact_analysis_handoff.py",
            "scripts/python/impact_analysis_index.py",
            "scripts/python/build_impact_index.py",
            "scripts/python/impact_analysis_config.v1.json",
            "scripts/python/impact_target_aliases.v1.json",
        ]
        self.update_config(
            lambda config: config.update(
                {
                    "scan_roots": ["scripts/python"],
                    "identity_files": identity_files,
                    "allow_identity_only": False,
                }
            )
        )
        self.commit_all("identity only denied")
        denied = self.build()
        self.assertEqual(denied.returncode, 15, denied.stdout + denied.stderr)
        self.update_config(lambda config: config.__setitem__("allow_identity_only", True))
        self.commit_all("identity only allowed")
        allowed = self.build()
        self.assertEqual(allowed.returncode, 0, allowed.stdout + allowed.stderr)

    def test_shared_builder_rejects_output_outside_logs_ci(self) -> None:
        index = self.require_module()
        with self.assertRaises(index.ImpactIndexError) as raised:
            index.build_and_publish_index(
                self.repo,
                revision=self.revision,
                trusted_ref="refs/heads/main",
                config_relative="scripts/python/impact_analysis_config.v1.json",
                aliases_relative="scripts/python/impact_target_aliases.v1.json",
                output_root=self.repo / "outside",
            )
        self.assertEqual(raised.exception.code, "path_outside_repository")

    def test_shared_builder_rejects_output_symlink_escape(self) -> None:
        index = self.require_module()
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        link = self.repo / "logs/ci/escape"
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(outside.name, link, target_is_directory=True)
        except OSError:
            subprocess.check_call(
                ["cmd", "/c", "mklink", "/J", str(link), outside.name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        with self.assertRaises(index.ImpactIndexError) as raised:
            index.build_and_publish_index(
                self.repo,
                revision=self.revision,
                trusted_ref="refs/heads/main",
                config_relative="scripts/python/impact_analysis_config.v1.json",
                aliases_relative="scripts/python/impact_target_aliases.v1.json",
                output_root=link,
            )
        self.assertEqual(raised.exception.code, "path_outside_repository")

    def test_nested_lock_directory_reparse_point_is_rejected_before_write(self) -> None:
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        link = self.repo / "logs/ci/.impact-analysis-locks"
        make_directory_link(link, Path(outside.name))
        with self.assertRaises(self.index.ImpactIndexError) as raised:
            self.index.build_and_publish_index(
                self.repo,
                revision=self.revision,
                trusted_ref="refs/heads/main",
                config_relative="scripts/python/impact_analysis_config.v1.json",
                aliases_relative="scripts/python/impact_target_aliases.v1.json",
                output_root=self.repo / "logs/ci",
            )
        self.assertEqual(raised.exception.code, "path_outside_repository")
        self.assertEqual(list(Path(outside.name).iterdir()), [])

    def test_nested_archive_index_reparse_point_is_rejected_before_write(self) -> None:
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        link = self.repo / "logs/ci/2026-09-04/impact-analysis/indexes"
        make_directory_link(link, Path(outside.name))
        fixed = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)
        with mock.patch.object(self.index, "utc_now", return_value=fixed):
            with self.assertRaises(self.index.ImpactIndexError) as raised:
                self.index.build_and_publish_index(
                    self.repo,
                    revision=self.revision,
                    trusted_ref="refs/heads/main",
                    config_relative="scripts/python/impact_analysis_config.v1.json",
                    aliases_relative="scripts/python/impact_target_aliases.v1.json",
                    output_root=self.repo / "logs/ci",
                )
        self.assertEqual(raised.exception.code, "path_outside_repository")
        self.assertEqual(list(Path(outside.name).iterdir()), [])

    def test_discovery_rejects_reparse_point_ancestor(self) -> None:
        first = self.build()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        payload = self.payload(first)
        date_directory = (self.repo / payload["index_path"]).parents[3]
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        moved = Path(outside.name) / date_directory.name
        shutil.move(str(date_directory), moved)
        make_directory_link(date_directory, moved)
        second = self.build()
        self.assertEqual(second.returncode, 4, second.stdout + second.stderr)
        self.assertEqual(self.payload(second)["code"], "path_outside_repository")

    def test_index_artifact_excludes_non_identity_metadata_and_manifest_preserves_it(self) -> None:
        completed = self.build()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        payload = self.payload(completed)
        index_doc = json.loads((self.repo / payload["index_path"]).read_text(encoding="utf-8"))
        manifest_doc = json.loads((self.repo / payload["manifest_path"]).read_text(encoding="utf-8"))
        for field in ("generated_at", "toolchain", "trusted_ref"):
            self.assertNotIn(field, index_doc)
            self.assertIn(field, manifest_doc)

    def test_generated_at_and_archive_date_use_one_captured_build_time(self) -> None:
        index = self.require_module()
        before_midnight = datetime(2026, 9, 4, 23, 59, 59, tzinfo=timezone.utc)
        after_midnight = datetime(2026, 9, 5, 0, 0, 1, tzinfo=timezone.utc)
        with mock.patch.object(index, "utc_now", side_effect=[before_midnight, after_midnight, after_midnight]):
            result = index.build_and_publish_index(
                self.repo,
                revision=self.revision,
                trusted_ref="refs/heads/main",
                config_relative="scripts/python/impact_analysis_config.v1.json",
                aliases_relative="scripts/python/impact_target_aliases.v1.json",
                output_root=self.repo / "logs/ci",
            )
        manifest = json.loads((self.repo / result["manifest_path"]).read_text(encoding="utf-8"))
        self.assertIn("/2026-09-04/", "/" + result["manifest_path"])
        self.assertTrue(manifest["generated_at"].startswith("2026-09-04T"))

    def test_same_commit_different_trusted_ref_is_not_exact_reuse(self) -> None:
        subprocess.check_call(["git", "tag", "same-commit"], cwd=self.repo)
        first = self.build()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        second = self.build_with_ref("refs/tags/same-commit")
        self.assertEqual(second.returncode, 10, second.stdout + second.stderr)
        self.assertEqual(self.payload(second)["code"], "index_identity_collision")

    def test_exact_reuse_ignores_current_python_patch_version(self) -> None:
        first = self.build()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        current_major_minor = ".".join(platform.python_version().split(".")[:2])
        with mock.patch.object(self.index.platform, "python_version", return_value=f"{current_major_minor}.99"):
            second = self.index.build_and_publish_index(
                self.repo,
                revision=self.revision,
                trusted_ref="refs/heads/main",
                config_relative="scripts/python/impact_analysis_config.v1.json",
                aliases_relative="scripts/python/impact_target_aliases.v1.json",
                output_root=self.repo / "logs/ci",
            )
        self.assertTrue(second["reused"])

    def test_prelock_reuse_reverifies_source_after_discovery(self) -> None:
        first = self.build()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        real_discover = self.index.discover_existing

        def discover_then_mutate(*args, **kwargs):
            result = real_discover(*args, **kwargs)
            (self.repo / "Game.Core/Domain.cs").write_text("mutated during discovery\n", encoding="utf-8")
            return result

        with mock.patch.object(self.index, "discover_existing", side_effect=discover_then_mutate):
            with self.assertRaises(self.index.ImpactIndexError) as raised:
                self.index.build_and_publish_index(
                    self.repo,
                    revision=self.revision,
                    trusted_ref="refs/heads/main",
                    config_relative="scripts/python/impact_analysis_config.v1.json",
                    aliases_relative="scripts/python/impact_target_aliases.v1.json",
                    output_root=self.repo / "logs/ci",
                )
        self.assertEqual(raised.exception.code, "dirty_state")

    def test_inlock_reuse_reverifies_revision_after_discovery(self) -> None:
        first = self.build()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        real_discover = self.index.discover_existing
        calls = 0

        def discover_then_drift(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return None
            result = real_discover(*args, **kwargs)
            (self.repo / "README.md").write_text("ref drift\n", encoding="utf-8")
            subprocess.check_call(["git", "add", "README.md"], cwd=self.repo)
            subprocess.check_call(
                ["git", "commit", "-m", "ref drift"],
                cwd=self.repo,
                stdout=subprocess.DEVNULL,
            )
            return result

        with mock.patch.object(self.index, "discover_existing", side_effect=discover_then_drift):
            with self.assertRaises(self.index.ImpactIndexError) as raised:
                self.index.build_and_publish_index(
                    self.repo,
                    revision=self.revision,
                    trusted_ref="refs/heads/main",
                    config_relative="scripts/python/impact_analysis_config.v1.json",
                    aliases_relative="scripts/python/impact_target_aliases.v1.json",
                    output_root=self.repo / "logs/ci",
                )
        self.assertEqual(raised.exception.code, "revision_mismatch")

    def test_git_blob_and_worktree_verification_use_bounded_set_operations(self) -> None:
        real_git = self.index._git
        calls: list[tuple[str, ...]] = []

        def counted_git(root, *args, **kwargs):
            calls.append(tuple(args))
            return real_git(root, *args, **kwargs)

        with mock.patch.object(self.index, "_git", side_effect=counted_git):
            self.index.build_and_publish_index(
                self.repo,
                revision=self.revision,
                trusted_ref="refs/heads/main",
                config_relative="scripts/python/impact_analysis_config.v1.json",
                aliases_relative="scripts/python/impact_target_aliases.v1.json",
                output_root=self.repo / "logs/ci",
            )
        self.assertEqual(sum(args[:2] == ("cat-file", "--batch") for args in calls), 1)
        self.assertFalse(any(args[:2] == ("cat-file", "blob") for args in calls))
        self.assertFalse(any(args and args[0] == "hash-object" for args in calls))
        self.assertLessEqual(sum(args and args[0] == "status" for args in calls), 2)

    def test_worktree_verification_hashes_bytes_not_only_diff_and_rejects_reparse_ancestor(self) -> None:
        snapshot = self.index.GitTreeSnapshot(self.repo, self.revision, "refs/heads/main")
        tree_entry = next(entry for entry in snapshot.entries if entry.path == "Game.Core/Domain.cs")
        manifest_entry = {
            "path": tree_entry.path,
            "sha256": self.index.sha256_bytes(snapshot.read_blob(tree_entry)),
            "included": True,
        }
        (self.repo / "Game.Core/Domain.cs").write_text("mutated\n", encoding="utf-8")
        real_git = self.index._git

        def hide_diff(root, *args, **kwargs):
            if args[:2] == ("diff", "--name-only"):
                return subprocess.CompletedProcess(["git"], 0, stdout=b"", stderr=b"")
            return real_git(root, *args, **kwargs)

        with mock.patch.object(self.index, "_git", side_effect=hide_diff):
            with self.assertRaises(self.index.ImpactIndexError) as raised:
                snapshot.verify_worktree([manifest_entry])
        self.assertEqual(raised.exception.code, "dirty_state")

        with mock.patch.object(
            self.index,
            "_is_reparse_point",
            side_effect=lambda path: Path(path).name == "Game.Core",
        ):
            with self.assertRaises(self.index.ImpactIndexError) as raised:
                snapshot.verify_worktree([manifest_entry])
        self.assertEqual(raised.exception.code, "source_read_failure")

    def test_config_and_alias_identity_hashes_use_trusted_git_blobs_after_crlf_checkout(self) -> None:
        subprocess.check_call(["git", "config", "core.autocrlf", "true"], cwd=self.repo)
        for relative in (
            "scripts/python/impact_analysis_config.v1.json",
            "scripts/python/impact_target_aliases.v1.json",
        ):
            path = self.repo / relative
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        completed = self.build()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        payload = self.payload(completed)
        index_doc = json.loads((self.repo / payload["index_path"]).read_text(encoding="utf-8"))
        for field, relative in (
            ("analysis_config_sha256", "scripts/python/impact_analysis_config.v1.json"),
            ("alias_table_sha256", "scripts/python/impact_target_aliases.v1.json"),
        ):
            blob = run("git", "show", f"{self.revision}:{relative}", cwd=self.repo)
            self.assertEqual(blob.returncode, 0, blob.stderr)
            self.assertEqual(index_doc[field], self.index.sha256_bytes(blob.stdout.encode("utf-8")))

    def test_index_validator_rejects_non_regular_git_modes(self) -> None:
        completed = self.build()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        payload = self.payload(completed)
        index_doc = json.loads((self.repo / payload["index_path"]).read_text(encoding="utf-8"))
        index_doc["source_manifest"][0]["git_mode"] = "100664"
        with self.assertRaises(self.index.ImpactIndexError) as raised:
            self.index.validate_index_document(index_doc)
        self.assertEqual(raised.exception.code, "invalid_manifest")

    def test_config_rejects_case_insensitive_duplicate_roots_identity_files_and_suffixes(self) -> None:
        source = json.loads((ROOT / "scripts/python/impact_analysis_config.v1.json").read_text(encoding="utf-8"))
        mutations = {
            "scan roots": lambda value: value["scan_roots"].append(value["scan_roots"][0].upper()),
            "identity files": lambda value: value["identity_files"].append(value["identity_files"][0].upper()),
            "suffixes": lambda value: value["source_rules"][0]["suffixes"].append(".CS"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                candidate = json.loads(json.dumps(source))
                mutate(candidate)
                with self.assertRaises(self.index.ImpactIndexError) as raised:
                    self.index.validate_config(candidate)
                self.assertEqual(raised.exception.code, "invalid_manifest")

    def test_aliases_reject_case_insensitive_alias_collisions(self) -> None:
        source = json.loads((ROOT / "scripts/python/impact_target_aliases.v1.json").read_text(encoding="utf-8"))
        source["aliases"]["event"] = {"RewardOffer": "RewardOfferPresentedEvent", "rewardoffer": "Other"}
        with self.assertRaises(self.index.ImpactIndexError) as raised:
            self.index.validate_aliases(source)
        self.assertEqual(raised.exception.code, "invalid_manifest")

    def test_reuse_rejects_self_consistent_tampered_non_identity_lineage(self) -> None:
        first = self.build()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        payload = self.payload(first)
        index_path = self.repo / payload["index_path"]
        manifest_path = self.repo / payload["manifest_path"]
        index_doc = json.loads(index_path.read_text(encoding="utf-8"))
        index_doc["alias_table_sha256"] = "0" * 64
        tampered_bytes = self.index.artifact_json_bytes(index_doc)
        index_path.write_bytes(tampered_bytes)
        manifest_doc = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_doc["artifact_sha256"] = self.index.sha256_bytes(tampered_bytes)
        manifest_path.write_bytes(self.index.artifact_json_bytes(manifest_doc))
        second = self.build()
        self.assertEqual(second.returncode, 10, second.stdout + second.stderr)
        self.assertEqual(self.payload(second)["code"], "index_identity_collision")

    def test_duplicate_index_directories_require_identical_manifest_bytes(self) -> None:
        first = self.build()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        payload = self.payload(first)
        source_dir = (self.repo / payload["index_path"]).parent
        duplicate_dir = (
            self.repo
            / "logs/ci/2026-09-03/impact-analysis/indexes"
            / payload["index_id"]
        )
        duplicate_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, duplicate_dir)
        manifest_path = duplicate_dir / "index-manifest.v1.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["generated_at"] = "2026-09-03T00:00:00Z"
        manifest_path.write_bytes(self.index.artifact_json_bytes(manifest))
        second = self.build()
        self.assertEqual(second.returncode, 10, second.stdout + second.stderr)
        self.assertEqual(self.payload(second)["code"], "index_identity_collision")

    def test_post_lock_source_mutation_is_detected_before_publication(self) -> None:
        index = self.require_module()
        real_acquire = index.IndexLock.acquire

        def mutate_then_acquire(lock):
            (self.repo / "Game.Core/Domain.cs").write_text("changed after preflight\n", encoding="utf-8")
            return real_acquire(lock)

        with mock.patch.object(index.IndexLock, "acquire", new=mutate_then_acquire):
            with self.assertRaises(index.ImpactIndexError) as raised:
                index.build_and_publish_index(
                    self.repo,
                    revision=self.revision,
                    trusted_ref="refs/heads/main",
                    config_relative="scripts/python/impact_analysis_config.v1.json",
                    aliases_relative="scripts/python/impact_target_aliases.v1.json",
                    output_root=self.repo / "logs/ci",
                )
        self.assertEqual(raised.exception.code, "dirty_state")
        self.assertEqual(list((self.repo / "logs").rglob("index-manifest.v1.json")), [])

    def test_post_lock_head_and_ref_drift_is_detected_before_publication(self) -> None:
        index = self.require_module()
        real_acquire = index.IndexLock.acquire

        def drift_then_acquire(lock):
            (self.repo / "README.md").write_text("drift\n", encoding="utf-8")
            subprocess.check_call(["git", "add", "README.md"], cwd=self.repo)
            subprocess.check_call(["git", "commit", "-m", "drift"], cwd=self.repo, stdout=subprocess.DEVNULL)
            return real_acquire(lock)

        with mock.patch.object(index.IndexLock, "acquire", new=drift_then_acquire):
            with self.assertRaises(index.ImpactIndexError) as raised:
                index.build_and_publish_index(
                    self.repo,
                    revision=self.revision,
                    trusted_ref="refs/heads/main",
                    config_relative="scripts/python/impact_analysis_config.v1.json",
                    aliases_relative="scripts/python/impact_target_aliases.v1.json",
                    output_root=self.repo / "logs/ci",
                )
        self.assertEqual(raised.exception.code, "revision_mismatch")

    def test_index_validator_rejects_self_consistent_invalid_source_entry(self) -> None:
        completed = self.build()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        payload = self.payload(completed)
        index_doc = json.loads((self.repo / payload["index_path"]).read_text(encoding="utf-8"))
        index_doc["source_manifest"][0]["parser_family"] = ""
        manifest_sha = self.index.sha256_bytes(self.index.jcs_bytes(index_doc["source_manifest"]))
        index_doc["source_manifest_sha256"] = manifest_sha
        identity = {
            "repository_revision": index_doc["repository_revision"],
            "source_manifest_sha256": manifest_sha,
            "index_schema": index_doc["index_schema"],
            "analyzer_implementation_revision": index_doc["analyzer_implementation_revision"],
            "analysis_config_revision": index_doc["analysis_config_revision"],
        }
        index_doc["index_id"] = self.index.derive_index_id(identity)
        with self.assertRaises(self.index.ImpactIndexError) as raised:
            self.index.validate_index_document(index_doc)
        self.assertEqual(raised.exception.code, "invalid_manifest")

    def test_dirty_included_source_fails_closed_without_publication(self) -> None:
        (self.repo / "Game.Core/Domain.cs").write_text("changed\n", encoding="utf-8")
        completed = self.build()
        self.assertEqual(completed.returncode, 13, completed.stdout + completed.stderr)
        self.assertEqual(self.payload(completed)["code"], "dirty_state")
        self.assertEqual(list((self.repo / "logs").rglob("impact-index.v1.json")), [])

    def test_missing_tracked_source_is_a_source_read_failure(self) -> None:
        (self.repo / "Game.Core/Domain.cs").unlink()
        completed = self.build()
        self.assertEqual(completed.returncode, 8, completed.stdout + completed.stderr)
        self.assertEqual(self.payload(completed)["code"], "source_read_failure")
        self.assertEqual(list((self.repo / "logs").rglob("impact-index.v1.json")), [])

    def test_included_text_bom_is_a_source_read_failure_without_publication(self) -> None:
        path = self.repo / "Game.Core/Domain.cs"
        path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
        self.commit_all("included source with BOM")
        completed = self.build()
        self.assertEqual(completed.returncode, 8, completed.stdout + completed.stderr)
        self.assertEqual(self.payload(completed)["code"], "source_read_failure")
        self.assertEqual(list((self.repo / "logs").rglob("impact-index.v1.json")), [])

    def test_identity_json_bom_is_invalid_manifest_without_publication(self) -> None:
        identity_path = self.repo / "Game.Core/Data/identity.json"
        identity_path.parent.mkdir(parents=True, exist_ok=True)
        identity_path.write_bytes(b'\xef\xbb\xbf{"identity":true}\n')
        self.update_config(
            lambda config: config["identity_files"].append("Game.Core/Data/identity.json")
        )
        self.commit_all("identity json with BOM")
        completed = self.build()
        self.assertEqual(completed.returncode, 15, completed.stdout + completed.stderr)
        self.assertEqual(self.payload(completed)["code"], "invalid_manifest")
        self.assertEqual(list((self.repo / "logs").rglob("impact-index.v1.json")), [])

    def test_config_and_alias_bom_are_invalid_manifest_without_publication(self) -> None:
        for relative in (
            "scripts/python/impact_analysis_config.v1.json",
            "scripts/python/impact_target_aliases.v1.json",
        ):
            with self.subTest(relative=relative):
                path = self.repo / relative
                path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
                completed = self.build()
                self.assertEqual(completed.returncode, 15, completed.stdout + completed.stderr)
                self.assertEqual(self.payload(completed)["code"], "invalid_manifest")
                self.assertEqual(list((self.repo / "logs").rglob("impact-index.v1.json")), [])
                path.write_bytes(path.read_bytes()[3:])

    def test_implementation_python_identity_bom_is_invalid_manifest_without_publication(self) -> None:
        path = self.repo / "scripts/python/impact_analysis_index.py"
        path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
        self.commit_all("implementation identity with BOM")
        with self.assertRaises(self.index.ImpactIndexError) as raised:
            self.index.build_and_publish_index(
                self.repo,
                revision=self.revision,
                trusted_ref="refs/heads/main",
                config_relative="scripts/python/impact_analysis_config.v1.json",
                aliases_relative="scripts/python/impact_target_aliases.v1.json",
                output_root=self.repo / "logs/ci",
            )
        self.assertEqual(raised.exception.code, "invalid_manifest")
        self.assertEqual(list((self.repo / "logs").rglob("impact-index.v1.json")), [])

    def test_missing_implementation_identity_is_invalid_manifest_without_publication(self) -> None:
        path = self.repo / "scripts/python/impact_analysis_index.py"
        path.unlink()
        subprocess.check_call(["git", "add", "-u"], cwd=self.repo)
        subprocess.check_call(
            ["git", "commit", "-m", "missing implementation identity"],
            cwd=self.repo,
            stdout=subprocess.DEVNULL,
        )
        self.revision = run("git", "rev-parse", "HEAD", cwd=self.repo).stdout.strip()
        with self.assertRaises(self.index.ImpactIndexError) as raised:
            self.index.build_and_publish_index(
                self.repo,
                revision=self.revision,
                trusted_ref="refs/heads/main",
                config_relative="scripts/python/impact_analysis_config.v1.json",
                aliases_relative="scripts/python/impact_target_aliases.v1.json",
                output_root=self.repo / "logs/ci",
            )
        self.assertEqual(raised.exception.code, "invalid_manifest")
        self.assertEqual(list((self.repo / "logs").rglob("impact-index.v1.json")), [])

    def test_missing_identity_is_invalid_manifest_without_publication(self) -> None:
        self.update_config(
            lambda config: config["identity_files"].append("Game.Core/Data/missing.json")
        )
        self.commit_all("missing identity")
        completed = self.build()
        self.assertEqual(completed.returncode, 15, completed.stdout + completed.stderr)
        self.assertEqual(self.payload(completed)["code"], "invalid_manifest")
        self.assertEqual(list((self.repo / "logs").rglob("impact-index.v1.json")), [])

    def test_included_invalid_utf8_is_source_read_failure_without_publication(self) -> None:
        path = self.repo / "Game.Core/Domain.cs"
        path.write_bytes(b"namespace NewRouge.Core;\xff\n")
        self.commit_all("included invalid utf8")
        completed = self.build()
        self.assertEqual(completed.returncode, 8, completed.stdout + completed.stderr)
        self.assertEqual(self.payload(completed)["code"], "source_read_failure")
        self.assertEqual(list((self.repo / "logs").rglob("impact-index.v1.json")), [])

    def test_revision_or_trusted_ref_mismatch_is_rejected(self) -> None:
        (self.repo / "README.md").write_text("next\n", encoding="utf-8")
        subprocess.check_call(["git", "add", "README.md"], cwd=self.repo)
        subprocess.check_call(["git", "commit", "-m", "next"], cwd=self.repo, stdout=subprocess.DEVNULL)
        completed = self.build()
        self.assertEqual(completed.returncode, 7, completed.stdout + completed.stderr)
        self.assertEqual(self.payload(completed)["code"], "revision_mismatch")

    def test_malformed_config_returns_invalid_manifest(self) -> None:
        config = self.repo / "scripts/python/impact_analysis_config.v1.json"
        config.write_text("{not-json}\n", encoding="utf-8")
        completed = self.build()
        self.assertEqual(completed.returncode, 15, completed.stdout + completed.stderr)
        self.assertEqual(self.payload(completed)["code"], "invalid_manifest")

    def test_missing_config_returns_invalid_manifest(self) -> None:
        (self.repo / "scripts/python/impact_analysis_config.v1.json").unlink()
        completed = self.build()
        self.assertEqual(completed.returncode, 15, completed.stdout + completed.stderr)
        self.assertEqual(self.payload(completed)["code"], "invalid_manifest")

    def test_existing_different_artifact_is_preserved_as_identity_collision(self) -> None:
        first = self.build()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        payload = self.payload(first)
        index_path = self.repo / payload["index_path"]
        index_path.write_bytes(b"different-existing-bytes")
        second = self.build()
        self.assertEqual(second.returncode, 10, second.stdout + second.stderr)
        self.assertEqual(self.payload(second)["code"], "index_identity_collision")
        self.assertEqual(index_path.read_bytes(), b"different-existing-bytes")

    def test_target_index_directory_path_as_file_is_preserved_as_collision(self) -> None:
        first = self.build()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        payload = self.payload(first)
        directory = (self.repo / payload["index_path"]).parent
        shutil.rmtree(directory)
        directory.write_bytes(b"competing-index-path")
        second = self.build()
        self.assertEqual(second.returncode, 10, second.stdout + second.stderr)
        self.assertEqual(self.payload(second)["code"], "index_identity_collision")
        self.assertEqual(directory.read_bytes(), b"competing-index-path")

    def test_manifest_validator_rejects_invalid_fields_and_lineage(self) -> None:
        completed = self.build()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        payload = self.payload(completed)
        index_bytes = (self.repo / payload["index_path"]).read_bytes()
        index_doc = json.loads(index_bytes.decode("utf-8"))
        manifest_path = self.repo / payload["manifest_path"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_fields = {
            "schema_version",
            "index_schema",
            "index_id",
            "artifact_path",
            "artifact_sha256",
            "repository_revision",
            "trusted_ref",
            "analyzer_implementation_revision",
            "analysis_config_revision",
            "analysis_config_sha256",
            "alias_table_revision",
            "alias_table_sha256",
            "discovery_policy_sha256",
            "source_manifest_sha256",
            "generated_at",
            "toolchain",
        }
        self.assertEqual(set(manifest), expected_fields)
        mutations = {
            "extra field": lambda value: value.__setitem__("unexpected", True),
            "index identity": lambda value: value.__setitem__("index_id", "idx-" + "0" * 64),
            "repository revision": lambda value: value.__setitem__("repository_revision", "0" * 40),
            "trusted ref": lambda value: value.__setitem__("trusted_ref", "refs/heads/other"),
            "timestamp": lambda value: value.__setitem__("generated_at", "2026-09-04T00:00:00+00:00"),
            "toolchain": lambda value: value.__setitem__("toolchain", {"python": 313}),
            "toolchain syntax": lambda value: value.__setitem__("toolchain", {"python": "313"}),
            "artifact hash": lambda value: value.__setitem__("artifact_sha256", "0" * 64),
            "config hash": lambda value: value.__setitem__("analysis_config_sha256", "0" * 64),
            "alias revision": lambda value: value.__setitem__("alias_table_revision", "other"),
            "source manifest hash": lambda value: value.__setitem__("source_manifest_sha256", "0" * 64),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                candidate = json.loads(json.dumps(manifest))
                mutate(candidate)
                with self.assertRaises(self.index.ImpactIndexError) as raised:
                    self.index.validate_manifest_bytes(
                        self.index.artifact_json_bytes(candidate),
                        index_bytes=index_bytes,
                        expected_index=index_doc,
                        expected_trusted_ref="refs/heads/main",
                    )
                self.assertEqual(raised.exception.code, "invalid_manifest")

    def test_manifest_failure_preserves_replaced_index_and_writes_failure_marker(self) -> None:
        index = self.require_module()
        real_publish = index.atomic_publish_bytes
        calls = 0
        competitor = b"competing-index-bytes"
        primary = RuntimeError("manifest publication failed")

        def fail_manifest(destination, data, *, validator, sleep=index.time.sleep):
            nonlocal calls
            calls += 1
            if calls == 1:
                return real_publish(destination, data, validator=validator, sleep=sleep)
            index_path = destination.parent / "impact-index.v1.json"
            index_path.write_bytes(competitor)
            raise primary

        with mock.patch.object(index, "atomic_publish_bytes", side_effect=fail_manifest):
            with self.assertRaisesRegex(RuntimeError, "manifest publication failed"):
                index.build_and_publish_index(
                    self.repo,
                    revision=self.revision,
                    trusted_ref="refs/heads/main",
                    config_relative="scripts/python/impact_analysis_config.v1.json",
                    aliases_relative="scripts/python/impact_target_aliases.v1.json",
                    output_root=self.repo / "logs/ci",
                )
        index_paths = list((self.repo / "logs/ci").rglob("impact-index.v1.json"))
        self.assertEqual(len(index_paths), 1)
        self.assertEqual(index_paths[0].read_bytes(), competitor)
        markers = list((self.repo / "logs/ci").rglob("publication-failure.v1.json"))
        self.assertEqual(len(markers), 1)
        marker = json.loads(markers[0].read_text(encoding="utf-8"))
        self.assertEqual(marker["code"], "index_identity_collision")
        self.assertIn("replaced", marker["reason"])

    def test_failed_first_artifact_publication_removes_owned_empty_index_directory(self) -> None:
        primary = RuntimeError("index publication failed")
        with mock.patch.object(self.index, "atomic_publish_bytes", side_effect=primary):
            with self.assertRaisesRegex(RuntimeError, "index publication failed"):
                self.index.build_and_publish_index(
                    self.repo,
                    revision=self.revision,
                    trusted_ref="refs/heads/main",
                    config_relative="scripts/python/impact_analysis_config.v1.json",
                    aliases_relative="scripts/python/impact_target_aliases.v1.json",
                    output_root=self.repo / "logs/ci",
                )
        candidates = list((self.repo / "logs/ci").glob("*/impact-analysis/indexes/idx-*"))
        self.assertEqual(candidates, [])
        retry = self.build()
        self.assertEqual(retry.returncode, 0, retry.stdout + retry.stderr)

    def test_failed_manifest_publication_removes_owned_index_and_empty_directory(self) -> None:
        real_publish = self.index.atomic_publish_bytes
        calls = 0

        def fail_manifest(destination, data, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return real_publish(destination, data, **kwargs)
            raise RuntimeError("manifest publication failed")

        with mock.patch.object(self.index, "atomic_publish_bytes", side_effect=fail_manifest):
            with self.assertRaisesRegex(RuntimeError, "manifest publication failed"):
                self.index.build_and_publish_index(
                    self.repo,
                    revision=self.revision,
                    trusted_ref="refs/heads/main",
                    config_relative="scripts/python/impact_analysis_config.v1.json",
                    aliases_relative="scripts/python/impact_target_aliases.v1.json",
                    output_root=self.repo / "logs/ci",
                )
        candidates = list((self.repo / "logs/ci").glob("*/impact-analysis/indexes/idx-*"))
        self.assertEqual(candidates, [])
        retry = self.build()
        self.assertEqual(retry.returncode, 0, retry.stdout + retry.stderr)

    def test_reuse_only_reports_stale_when_exact_identity_does_not_exist(self) -> None:
        completed = self.build("--implementation-revision", "newrouge.impact-index-builder.v2", "--reuse-only")
        self.assertEqual(completed.returncode, 6, completed.stdout + completed.stderr)
        self.assertEqual(self.payload(completed)["code"], "stale_index")
        self.assertEqual(list((self.repo / "logs").rglob("impact-index.v1.json")), [])


class LockAndAtomicityTests(ImpactIndexTestCase):
    def setUp(self) -> None:
        self.index = self.require_module()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.lock_path = self.root / "idx-test.lock.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_lock(self, *, host: str, pid: int, process_start: str, age_minutes: int) -> bytes:
        payload = {
            "schema_version": "newrouge.impact-index-lock.v1",
            "index_id": "idx-test",
            "host": host,
            "pid": pid,
            "process_start": process_start,
            "created_at": (datetime.now(timezone.utc) - timedelta(minutes=age_minutes)).isoformat().replace("+00:00", "Z"),
            "owner_token": "existing",
        }
        data = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
        self.lock_path.write_bytes(data)
        return data

    def valid_lock_payload(self) -> dict:
        return {
            "schema_version": "newrouge.impact-index-lock.v1",
            "index_id": "idx-test",
            "host": "local-host",
            "pid": 123,
            "process_start": "start-token",
            "created_at": "2026-09-04T00:00:00Z",
            "owner_token": "owner-token",
        }

    def test_lock_validator_rejects_schema_types_utc_owner_and_index_mismatch(self) -> None:
        validator = getattr(self.index, "validate_lock_bytes", None)
        self.assertIsNotNone(validator, "lock validation API is required")
        mutations = {
            "extra field": lambda value: value.__setitem__("unexpected", True),
            "schema": lambda value: value.__setitem__("schema_version", "other"),
            "index": lambda value: value.__setitem__("index_id", "idx-other"),
            "host": lambda value: value.__setitem__("host", ""),
            "pid type": lambda value: value.__setitem__("pid", "123"),
            "pid range": lambda value: value.__setitem__("pid", 0),
            "process start": lambda value: value.__setitem__("process_start", 123),
            "timestamp offset": lambda value: value.__setitem__("created_at", "2026-09-04T00:00:00+00:00"),
            "timestamp invalid": lambda value: value.__setitem__("created_at", "not-a-time"),
            "owner token": lambda value: value.__setitem__("owner_token", ""),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                payload = self.valid_lock_payload()
                mutate(payload)
                with self.assertRaises(self.index.ImpactIndexError) as raised:
                    validator(self.index.artifact_json_bytes(payload), expected_index_id="idx-test")
                self.assertEqual(raised.exception.code, "lock_unavailable")

    def test_cross_host_lock_retries_exactly_five_times_and_is_never_removed(self) -> None:
        original = self.write_lock(host="other-host", pid=1, process_start="1", age_minutes=60)
        sleeps: list[float] = []
        lock = self.index.IndexLock(
            self.lock_path,
            "idx-test",
            host="local-host",
            pid=os.getpid(),
            process_start="current",
            sleep=sleeps.append,
        )
        with self.assertRaises(self.index.ImpactIndexError) as raised:
            lock.acquire()
        self.assertEqual(raised.exception.code, "lock_unavailable")
        self.assertEqual(sleeps, [1.0, 1.0, 1.0, 1.0, 1.0])
        self.assertEqual(self.lock_path.read_bytes(), original)

    def test_old_same_host_lock_with_reused_pid_is_reclaimed(self) -> None:
        self.write_lock(host=socket.gethostname(), pid=os.getpid(), process_start="old-start", age_minutes=6)
        lock = self.index.IndexLock(
            self.lock_path,
            "idx-test",
            host=socket.gethostname(),
            pid=os.getpid(),
            process_start="new-start",
            sleep=lambda _: None,
            process_start_lookup=lambda _: "new-start",
        )
        lock.acquire()
        current = json.loads(self.lock_path.read_text(encoding="utf-8"))
        self.assertEqual(current["process_start"], "new-start")
        lock.release()
        self.assertFalse(self.lock_path.exists())

    def test_fresh_same_host_lock_is_not_reclaimed(self) -> None:
        original = self.write_lock(host=socket.gethostname(), pid=os.getpid(), process_start="current", age_minutes=0)
        lock = self.index.IndexLock(
            self.lock_path,
            "idx-test",
            host=socket.gethostname(),
            pid=os.getpid(),
            process_start="current",
            sleep=lambda _: None,
            process_start_lookup=lambda _: "current",
        )
        with self.assertRaises(self.index.ImpactIndexError) as raised:
            lock.acquire()
        self.assertEqual(raised.exception.code, "lock_unavailable")
        self.assertEqual(self.lock_path.read_bytes(), original)

    def test_old_live_same_host_lock_is_not_reclaimed_when_start_time_is_unverifiable(self) -> None:
        original = self.write_lock(
            host=socket.gethostname(),
            pid=os.getpid(),
            process_start="recorded-start",
            age_minutes=6,
        )
        lock = self.index.IndexLock(
            self.lock_path,
            "idx-test",
            host=socket.gethostname(),
            pid=os.getpid(),
            process_start="current",
            sleep=lambda _: None,
            process_start_lookup=lambda _: None,
        )
        with self.assertRaises(self.index.ImpactIndexError) as raised:
            lock.acquire()
        self.assertEqual(raised.exception.code, "lock_unavailable")
        self.assertEqual(self.lock_path.read_bytes(), original)

    def test_replaced_stale_lock_is_not_deleted_after_stale_check(self) -> None:
        stale = self.write_lock(host="local-host", pid=1, process_start="old", age_minutes=6)
        replacement_payload = self.valid_lock_payload()
        replacement_payload["host"] = "other-host"
        replacement_payload["owner_token"] = "replacement-owner"
        replacement = self.index.artifact_json_bytes(replacement_payload)
        lock = self.index.IndexLock(
            self.lock_path,
            "idx-test",
            host="local-host",
            pid=os.getpid(),
            process_start="current",
            sleep=lambda _: None,
        )

        def stale_then_replace():
            self.lock_path.write_bytes(replacement)
            return stale

        with mock.patch.object(lock, "_stale_same_host", side_effect=stale_then_replace):
            with self.assertRaises(self.index.ImpactIndexError) as raised:
                lock.acquire()
        self.assertEqual(raised.exception.code, "lock_unavailable")
        self.assertEqual(self.lock_path.read_bytes(), replacement)

    def test_lock_create_oserror_is_lock_unavailable_and_failed_cleanup_is_owner_safe(self) -> None:
        lock = self.index.IndexLock(
            self.lock_path,
            "idx-test",
            host="local-host",
            pid=os.getpid(),
            process_start="current",
            sleep=lambda _: None,
        )
        with mock.patch.object(self.index.os, "open", side_effect=PermissionError("denied")):
            with self.assertRaises(self.index.ImpactIndexError) as raised:
                lock._create()
        self.assertEqual(raised.exception.code, "lock_unavailable")

        replacement = self.index.artifact_json_bytes(self.valid_lock_payload())
        real_fdopen = self.index.os.fdopen

        def fail_after_replacement(descriptor, *args, **kwargs):
            self.lock_path.write_bytes(replacement)
            raise OSError("write denied")

        with mock.patch.object(self.index.os, "fdopen", side_effect=fail_after_replacement):
            with self.assertRaises(self.index.ImpactIndexError) as raised:
                lock._create()
        self.assertEqual(raised.exception.code, "lock_unavailable")
        self.assertEqual(self.lock_path.read_bytes(), replacement)
        self.assertIsNotNone(real_fdopen)

    def test_stale_reclaim_rename_race_never_deletes_replacement_owner(self) -> None:
        stale = self.write_lock(host="local-host", pid=1, process_start="old", age_minutes=6)
        replacement_payload = self.valid_lock_payload()
        replacement_payload["host"] = "other-host"
        replacement_payload["owner_token"] = "replacement-owner"
        replacement = self.index.artifact_json_bytes(replacement_payload)
        real_rename = os.rename
        raced = False

        def replace_before_rename(source, destination):
            nonlocal raced
            if Path(source) == self.lock_path and not raced:
                raced = True
                self.lock_path.write_bytes(replacement)
            return real_rename(source, destination)

        lock = self.index.IndexLock(
            self.lock_path,
            "idx-test",
            host="local-host",
            pid=os.getpid(),
            process_start="current",
            sleep=lambda _: None,
        )
        with mock.patch.object(lock, "_stale_same_host", return_value=stale):
            with mock.patch.object(self.index.os, "rename", side_effect=replace_before_rename):
                with self.assertRaises(self.index.ImpactIndexError) as raised:
                    lock.acquire()
        self.assertEqual(raised.exception.code, "lock_unavailable")
        self.assertEqual(self.lock_path.read_bytes(), replacement)

    def test_release_failure_does_not_mask_primary_exception_or_delete_non_owner(self) -> None:
        for replacement in (None, b"{broken-json"):
            with self.subTest(replacement=replacement):
                lock = self.index.IndexLock(
                    self.lock_path,
                    "idx-test",
                    host="local-host",
                    pid=os.getpid(),
                    process_start="current",
                    sleep=lambda _: None,
                )
                with self.assertRaisesRegex(RuntimeError, "primary failure"):
                    with lock:
                        if replacement is None:
                            self.lock_path.unlink()
                        else:
                            self.lock_path.write_bytes(replacement)
                        raise RuntimeError("primary failure")
                if replacement is not None:
                    self.assertEqual(self.lock_path.read_bytes(), replacement)
                    self.lock_path.unlink()

    def test_release_preserves_well_formed_lock_owned_by_another_builder(self) -> None:
        lock = self.index.IndexLock(
            self.lock_path,
            "idx-test",
            host="local-host",
            pid=os.getpid(),
            process_start="current",
            sleep=lambda _: None,
        )
        lock.acquire()
        replacement_payload = self.valid_lock_payload()
        replacement_payload["owner_token"] = "replacement-owner"
        replacement = self.index.artifact_json_bytes(replacement_payload)
        self.lock_path.write_bytes(replacement)
        lock.release()
        self.assertEqual(self.lock_path.read_bytes(), replacement)

    def test_release_rename_race_never_deletes_replacement_owner(self) -> None:
        lock = self.index.IndexLock(
            self.lock_path,
            "idx-test",
            host="local-host",
            pid=os.getpid(),
            process_start="current",
            sleep=lambda _: None,
        )
        lock.acquire()
        replacement_payload = self.valid_lock_payload()
        replacement_payload["owner_token"] = "replacement-owner"
        replacement = self.index.artifact_json_bytes(replacement_payload)
        real_rename = os.rename
        raced = False

        def replace_before_rename(source, destination):
            nonlocal raced
            if Path(source) == self.lock_path and not raced:
                raced = True
                self.lock_path.write_bytes(replacement)
            return real_rename(source, destination)

        with mock.patch.object(self.index.os, "rename", side_effect=replace_before_rename):
            lock.release()
        self.assertEqual(self.lock_path.read_bytes(), replacement)

    def test_atomic_publication_retries_sharing_violations_then_succeeds(self) -> None:
        destination = self.root / "artifact.json"
        real_rename = os.rename
        attempts = 0
        sleeps: list[float] = []

        def flaky_rename(source, target):
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                error = PermissionError("sharing violation")
                error.winerror = 32
                raise error
            real_rename(source, target)

        with mock.patch.object(self.index.os, "rename", side_effect=flaky_rename):
            self.index.atomic_publish_bytes(
                destination,
                b'{"status":"ok"}\n',
                validator=lambda data: json.loads(data.decode("utf-8")),
                sleep=sleeps.append,
            )
        self.assertEqual(attempts, 3)
        self.assertEqual(sleeps, [0.1, 0.2])
        self.assertEqual(destination.read_bytes(), b'{"status":"ok"}\n')
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_atomic_publication_retry_exhaustion_keeps_final_path_absent(self) -> None:
        destination = self.root / "artifact.json"
        sleeps: list[float] = []
        error = PermissionError("sharing violation")
        error.winerror = 32
        with mock.patch.object(self.index.os, "rename", side_effect=error):
            with self.assertRaises(self.index.ImpactIndexError) as raised:
                self.index.atomic_publish_bytes(
                    destination,
                    b"{}\n",
                    validator=lambda data: json.loads(data.decode("utf-8")),
                    sleep=sleeps.append,
                )
        self.assertEqual(raised.exception.code, "internal_error")
        self.assertEqual(sleeps, [0.1, 0.2, 0.4, 0.8, 1.6])
        self.assertFalse(destination.exists())
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_atomic_publication_never_overwrites_destination_created_during_publish(self) -> None:
        destination = self.root / "artifact.json"
        competitor = b'{"owner":"competitor"}\n'

        def competing_rename(source, target):
            Path(target).write_bytes(competitor)
            raise FileExistsError(str(target))

        with mock.patch.object(self.index.os, "rename", side_effect=competing_rename):
            with self.assertRaises(self.index.ImpactIndexError) as raised:
                self.index.atomic_publish_bytes(
                    destination,
                    b'{"owner":"builder"}\n',
                    validator=lambda data: json.loads(data.decode("utf-8")),
                )
        self.assertEqual(raised.exception.code, "index_identity_collision")
        self.assertEqual(destination.read_bytes(), competitor)

    def test_atomic_publication_does_not_require_hard_links(self) -> None:
        destination = self.root / "artifact.json"
        with mock.patch.object(self.index.os, "link", side_effect=OSError("hard links unavailable")):
            self.index.atomic_publish_bytes(
                destination,
                b'{"status":"ok"}\n',
                validator=lambda data: json.loads(data.decode("utf-8")),
            )
        self.assertEqual(destination.read_bytes(), b'{"status":"ok"}\n')

    def test_cleanup_failure_quarantines_transient_with_explicit_evidence(self) -> None:
        destination = self.root / "indexes/idx-test/artifact.json"
        real_unlink = Path.unlink
        failed_once = False

        def fail_first_transient_unlink(path, *args, **kwargs):
            nonlocal failed_once
            if path.name.endswith(".tmp") and not failed_once:
                failed_once = True
                raise PermissionError("cleanup denied")
            return real_unlink(path, *args, **kwargs)

        with mock.patch.object(Path, "unlink", new=fail_first_transient_unlink):
            with self.assertRaisesRegex(RuntimeError, "validation failed"):
                self.index.atomic_publish_bytes(
                    destination,
                    b"{}\n",
                    validator=lambda _: (_ for _ in ()).throw(RuntimeError("validation failed")),
                )
        markers = list(self.root.rglob("publication-cleanup-failure.*.v1.json"))
        self.assertEqual(len(markers), 1)
        marker = json.loads(markers[0].read_text(encoding="utf-8"))
        self.assertEqual(marker["status"], "failed")
        self.assertTrue(any(item.name.endswith(".tmp") for item in markers[0].parent.iterdir()))

    def test_review_cleanup_diagnostic_never_overwrites_existing_marker(self):
        destination = self.root / "artifact.json"
        existing = self.root / "publication-cleanup-failure.v1.json"
        existing.write_bytes(b"original diagnostic")
        unlink = Path.unlink
        def deny_transient_cleanup(path, *args, **kwargs):
            if path.name.endswith(".tmp"):
                raise PermissionError("transient cleanup denied")
            return unlink(path, *args, **kwargs)
        with mock.patch.object(Path, "unlink", new=deny_transient_cleanup):
            with self.assertRaisesRegex(RuntimeError, "original validation failure"):
                self.index.atomic_publish_bytes(destination, b"{}\n", validator=lambda _: (_ for _ in ()).throw(RuntimeError("original validation failure")))
        self.assertEqual(existing.read_bytes(), b"original diagnostic")
        markers = [p for p in self.root.rglob("publication-cleanup-failure*.json") if p != existing]
        self.assertEqual(len(markers), 1)
        self.assertEqual(json.loads(markers[0].read_bytes())["status"], "failed")

    def test_review_identity_acquisition_failure_prevents_publication(self):
        destination = self.root / "artifact.json"
        stat = Path.stat
        def deny_temporary_stat(path, *args, **kwargs):
            if path.name.endswith(".tmp"):
                raise PermissionError("prepublication identity denied")
            return stat(path, *args, **kwargs)
        with mock.patch.object(Path, "stat", new=deny_temporary_stat):
            with self.assertRaisesRegex(PermissionError, "prepublication identity denied"):
                self.index.atomic_publish_bytes(destination, b"{}\n", validator=lambda data: json.loads(data))
        self.assertFalse(destination.exists())


class HardGateRegistrationTests(unittest.TestCase):
    def test_impact_index_suite_is_registered_in_obligations_hard_gate(self) -> None:
        module_path = ROOT / "scripts/python/run_gate_bundle.py"
        spec = importlib.util.spec_from_file_location("run_gate_bundle_for_impact_index_test", module_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        gate = next(item for item in module._hard_gate_commands([]) if item["name"] == "obligations_unittest")
        self.assertIn("scripts.python.tests.test_impact_analysis_index", gate["cmd"])
        self.assertIn("scripts.python.tests.test_impact_analysis_index_repository_smoke", gate["cmd"])
        self.assertIn("scripts.python.tests.test_analyze_impact_cli", gate["cmd"])
        self.assertIn("scripts.python.tests.test_impact_analyzer", gate["cmd"])

    def test_repository_smoke_declares_real_filters_and_finite_subprocess_timeout(self) -> None:
        module_path = ROOT / "scripts/python/tests/test_impact_analysis_index_repository_smoke.py"
        spec = importlib.util.spec_from_file_location("impact_repository_smoke_contract", module_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertGreater(module.SUBPROCESS_TIMEOUT_SECONDS, 0)
        self.assertIn(".gitattributes", module.REPOSITORY_SUPPORT_FILES)

    def test_cli_help_lists_every_stable_builder_failure(self) -> None:
        completed = run(
            sys.executable,
            "scripts/python/build_impact_index.py",
            "--help",
            cwd=ROOT,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        for code, exit_code in (
            ("path_outside_repository", 4),
            ("stale_index", 6),
            ("revision_mismatch", 7),
            ("source_read_failure", 8),
            ("index_identity_collision", 10),
            ("internal_error", 12),
            ("dirty_state", 13),
            ("invalid_manifest", 15),
            ("lock_unavailable", 16),
            ("underqualified_target", 17),
        ):
            self.assertIn(f"{code}={exit_code}", completed.stdout)

    def test_cli_broad_exception_uses_shared_internal_error_exit_code(self) -> None:
        module_path = ROOT / "scripts/python/build_impact_index.py"
        spec = importlib.util.spec_from_file_location("build_impact_index_broad_exception", module_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        with mock.patch.object(sys, "path", [str(ROOT / "scripts/python"), *sys.path]):
            spec.loader.exec_module(module)
        output = StringIO()
        with mock.patch.object(module, "build_and_publish_index", side_effect=RuntimeError("boom")):
            with mock.patch.object(sys, "argv", [str(module_path), "--revision", "0" * 40]):
                with redirect_stdout(output):
                    result = module.main()
        self.assertEqual(result, 12)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["exit_code"], 12)
        self.assertEqual(payload["code"], "internal_error")


class ProductionReadinessEvidenceTests(unittest.TestCase):
    def test_bom_cleanup_audit_produces_expected_evidence(self) -> None:
        script = ROOT / "scripts/python/audit_impact_index_bom_cleanup.py"
        self.assertTrue(script.is_file(), "reproducible BOM cleanup audit script is required")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "bom-cleanup-evidence.v1.json"
            completed = run(
                sys.executable,
                str(script),
                "--baseline",
                "985f095e4975e7cf1c4477993447c2cfd4f2ed5c",
                "--output",
                str(output),
                cwd=ROOT,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            evidence = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(evidence["status"], "passed")
        self.assertEqual(evidence["included_bom_count"], 0)
        self.assertEqual(evidence["cleaned_prefix_only_count"], 36)
        self.assertEqual(evidence["excluded_baseline_match_count"], 41)
        self.assertNotIn("index_id", evidence)


if __name__ == "__main__":
    unittest.main()
