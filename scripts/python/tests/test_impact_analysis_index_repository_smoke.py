from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = ROOT / "scripts/python/impact_analysis_config.v1.json"
SUBPROCESS_TIMEOUT_SECONDS = 600
REPOSITORY_SUPPORT_FILES = (".gitattributes",)


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_index_module(path: Path):
    spec = importlib.util.spec_from_file_location("repository_smoke_impact_index", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def logs_fingerprint() -> tuple[tuple[str, str], ...]:
    logs_root = ROOT / "logs"
    if not logs_root.is_dir():
        return ()
    return tuple(
        (path.relative_to(logs_root).as_posix(), sha256_bytes(path.read_bytes()))
        for path in sorted(
            (item for item in logs_root.rglob("*") if item.is_file()),
            key=lambda item: item.relative_to(logs_root).as_posix().encode("utf-8"),
        )
    )


class ImpactIndexRepositorySmokeTests(unittest.TestCase):
    def test_real_tracked_source_universe_builds_and_exactly_reuses(self) -> None:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        roots = tuple(config["scan_roots"])
        identities = set(config["identity_files"])
        tracked = run("git", "ls-files", "-z", cwd=ROOT)
        self.assertEqual(tracked.returncode, 0, tracked.stdout + tracked.stderr)
        tracked_paths = {
            raw
            for raw in tracked.stdout.split("\0")
            if raw
        }
        selected = {
            path
            for path in tracked_paths
            if path in identities
            or any(path == root or path.startswith(root + "/") for root in roots)
        }
        selected.update(identities)
        self.assertTrue(selected)
        before_logs = logs_fingerprint()

        temporary_path: Path | None = None
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            for relative in sorted(selected, key=lambda value: value.encode("utf-8")):
                source = ROOT / relative
                self.assertTrue(source.is_file(), f"required real source is missing: {relative}")
                destination = temporary_path / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)

            subprocess.check_call(
                ["git", "init", "-b", "main"],
                cwd=temporary_path,
                stdout=subprocess.DEVNULL,
                timeout=SUBPROCESS_TIMEOUT_SECONDS,
            )
            subprocess.check_call(
                ["git", "config", "user.email", "impact-smoke@example.com"],
                cwd=temporary_path,
                timeout=SUBPROCESS_TIMEOUT_SECONDS,
            )
            subprocess.check_call(
                ["git", "config", "user.name", "Impact Smoke"],
                cwd=temporary_path,
                timeout=SUBPROCESS_TIMEOUT_SECONDS,
            )
            subprocess.check_call(
                ["git", "config", "core.autocrlf", "false"],
                cwd=temporary_path,
                timeout=SUBPROCESS_TIMEOUT_SECONDS,
            )
            support = ROOT / ".gitattributes"
            if support.is_file():
                shutil.copy2(support, temporary_path / ".gitattributes")
            subprocess.check_call(["git", "add", "."], cwd=temporary_path, timeout=SUBPROCESS_TIMEOUT_SECONDS)
            subprocess.check_call(
                ["git", "commit", "-m", "production readiness smoke"],
                cwd=temporary_path,
                stdout=subprocess.DEVNULL,
                timeout=SUBPROCESS_TIMEOUT_SECONDS,
            )
            revision = run("git", "rev-parse", "HEAD", cwd=temporary_path).stdout.strip()
            command = (
                sys.executable,
                "scripts/python/build_impact_index.py",
                "--revision",
                revision,
                "--trusted-ref",
                "refs/heads/main",
                "--output-root",
                "logs/ci",
            )
            first = run(*command, cwd=temporary_path)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            first_payload = json.loads(first.stdout)
            second = run(*command, "--reuse-only", cwd=temporary_path)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            second_payload = json.loads(second.stdout)
            self.assertFalse(first_payload["reused"])
            self.assertTrue(second_payload["reused"])
            self.assertEqual(first_payload["index_id"], second_payload["index_id"])
            self.assertEqual(first_payload["index_sha256"], second_payload["index_sha256"])

            index_path = temporary_path / first_payload["index_path"]
            manifest_path = temporary_path / first_payload["manifest_path"]
            index_bytes = index_path.read_bytes()
            manifest_bytes = manifest_path.read_bytes()
            index_module = load_index_module(
                temporary_path / "scripts/python/impact_analysis_index.py"
            )
            index_document = index_module.validate_index_bytes(index_bytes)
            manifest_document = index_module.validate_manifest_bytes(
                manifest_bytes,
                index_bytes=index_bytes,
                expected_index=index_document,
                expected_trusted_ref="refs/heads/main",
            )
            self.assertEqual(index_document["repository_revision"], revision)
            self.assertEqual(index_document["index_id"], first_payload["index_id"])
            self.assertEqual(manifest_document["artifact_sha256"], sha256_bytes(index_bytes))
            self.assertEqual(
                {entry["path"] for entry in index_document["source_manifest"]},
                selected,
            )
            theme_entry = next(
                entry
                for entry in index_document["source_manifest"]
                if entry["path"] == "Game.Godot/Themes/default_theme.tres"
            )
            self.assertTrue(theme_entry["included"])
            self.assertEqual(theme_entry["source_kind"], "resource")
            self.assertEqual(theme_entry["parser_family"], "godot-text")
            self.assertEqual(theme_entry["parser_version"], "v1")
            for entry in index_document["source_manifest"]:
                blob = subprocess.run(
                    ["git", "show", f"{revision}:{entry['path']}"],
                    cwd=temporary_path,
                    capture_output=True,
                    timeout=SUBPROCESS_TIMEOUT_SECONDS,
                    check=False,
                )
                self.assertEqual(blob.returncode, 0, blob.stderr)
                self.assertEqual(entry["sha256"], sha256_bytes(blob.stdout), entry["path"])

        self.assertIsNotNone(temporary_path)
        self.assertFalse(temporary_path.exists())
        self.assertEqual(logs_fingerprint(), before_logs)


if __name__ == "__main__":
    unittest.main()
