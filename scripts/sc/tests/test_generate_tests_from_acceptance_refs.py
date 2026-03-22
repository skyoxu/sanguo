#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))


def _load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gen_script = _load_module("sc_generate_tests_from_acceptance_refs_module", "scripts/sc/llm_generate_tests_from_acceptance_refs.py")


class _FakeTriplet:
    def __init__(self, task_id: str = "11") -> None:
        self.task_id = task_id
        self.master = {"title": "Generate missing tests"}
        self.back = {
            "acceptance": [
                "Main behavior is covered. Refs: Game.Core.Tests/FooTests.cs logs/ci/evidence.json",
            ]
        }
        self.gameplay = None


class GenerateTestsFromAcceptanceRefsTests(unittest.TestCase):
    def test_extract_acceptance_refs_with_anchors_should_tag_each_item(self) -> None:
        refs = gen_script._extract_acceptance_refs_with_anchors(
            acceptance=[
                "Alpha path. Refs: Game.Core.Tests/FooTests.cs",
                "Beta path. Refs: Tests.Godot/tests/test_bar.gd",
            ],
            task_id="11",
        )
        self.assertEqual(["ACC:T11.1"], [item["anchor"] for item in refs["Game.Core.Tests/FooTests.cs"]])
        self.assertEqual(["ACC:T11.2"], [item["anchor"] for item in refs["Tests.Godot/tests/test_bar.gd"]])

    def test_extract_json_object_should_parse_fenced_json(self) -> None:
        text = """some text
```json
{"file_path":"Game.Core.Tests/FooTests.cs","content":"ok"}
```
"""
        obj = gen_script._extract_json_object(text)
        self.assertEqual("Game.Core.Tests/FooTests.cs", obj["file_path"])

    def test_validate_anchor_binding_should_accept_cs_anchor_near_fact(self) -> None:
        content = "\n".join(
            [
                "using Xunit;",
                "// ACC:T11.1",
                "[Fact]",
                "public void Should_Do_Work() {}",
            ]
        )
        ok, error = gen_script._validate_anchor_binding(
            ref="Game.Core.Tests/FooTests.cs",
            content=content,
            required_anchors=["ACC:T11.1"],
        )
        self.assertTrue(ok)
        self.assertIsNone(error)

    def test_select_primary_ref_with_llm_should_fallback_to_first_candidate_on_invalid_model_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            with mock.patch.object(gen_script, "_run_codex_exec", return_value=(0, "trace", ["codex"])), \
                mock.patch.object(gen_script, "_read_text", return_value='{"primary_ref":"Tests/Unknown.cs","reason":"bad"}'):
                primary, meta = gen_script._select_primary_ref_with_llm(
                    task_id="11",
                    title="Generate tests",
                    by_ref={
                        "Game.Core.Tests/FooTests.cs": ["Alpha"],
                        "Tests.Godot/tests/test_bar.gd": ["Beta"],
                    },
                    context_excerpt="",
                    timeout_sec=30,
                    out_dir=out_dir,
                )

        self.assertEqual("Game.Core.Tests/FooTests.cs", primary)
        self.assertEqual("fail", meta["status"])

    def test_generate_missing_files_should_mark_all_new_refs_as_red_in_red_first_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "logs" / "ci" / "2026-03-20" / "sc-llm-acceptance-tests"
            intents: list[str] = []

            def fake_prompt_for_ref(**kwargs):
                intents.append(str(kwargs["intent"]))
                return "{}"

            def fake_codex_exec(*, prompt: str, out_last_message: Path, timeout_sec: int):  # noqa: ARG001
                payload = {
                    "file_path": "Game.Core.Tests/FooTests.cs" if "FooTests.cs" in str(out_last_message) else "Tests.Godot/tests/test_bar.gd",
                    "content": "\n".join(
                        [
                            "using FluentAssertions;",
                            "using Xunit;",
                            "",
                            "namespace Game.Core.Tests;",
                            "",
                            "public sealed class FooTests",
                            "{",
                            "    // ACC:T11.1",
                            "    [Fact]",
                            "    public void ShouldPublishJoinEvent_WhenMemberJoinsGuild()",
                            "    {",
                            "        var memberId = \"u1\";",
                            "        memberId.Should().Be(\"u1\");",
                            "    }",
                            "}",
                        ]
                    ) if "FooTests.cs" in str(out_last_message) else "\n".join(
                        [
                            "extends \"res://addons/gdUnit4/src/core/GdUnitTestSuite.gd\"",
                            "# ACC:T11.2",
                            "func test_join_event_is_emitted() -> void:",
                            "    assert_bool(true).is_true()",
                        ]
                    ),
                }
                out_last_message.parent.mkdir(parents=True, exist_ok=True)
                out_last_message.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                return 0, "trace ok\n", ["codex"]

            with mock.patch.object(gen_script, "repo_root", return_value=root), \
                mock.patch.object(gen_script, "_prompt_for_ref", side_effect=fake_prompt_for_ref), \
                mock.patch.object(gen_script, "_run_codex_exec", side_effect=fake_codex_exec):
                results, created, any_gd, _primary_ref = gen_script._generate_missing_files(
                    refs=["Game.Core.Tests/FooTests.cs", "Tests.Godot/tests/test_bar.gd"],
                    by_ref={
                        "Game.Core.Tests/FooTests.cs": [{"anchor": "ACC:T11.1", "text": "Alpha"}],
                        "Tests.Godot/tests/test_bar.gd": [{"anchor": "ACC:T11.2", "text": "Beta"}],
                    },
                    task_id="11",
                    title="Generate missing tests",
                    args=SimpleNamespace(
                        tdd_stage="red-first",
                        include_prd_context=False,
                        prd_context_path=".taskmaster/docs/prd.txt",
                        select_timeout_sec=30,
                        timeout_sec=30,
                    ),
                    task_context_md="Task context markdown",
                    out_dir=out_dir,
                )

        self.assertEqual(["red", "red"], intents)
        self.assertEqual(2, created)
        self.assertTrue(any_gd)
        self.assertEqual(["ok", "ok"], [item.status for item in results])

    def test_main_should_generate_allowed_missing_test_and_skip_non_test_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "logs" / "ci" / "2026-03-20" / "sc-llm-acceptance-tests"
            analyze_dir = root / "logs" / "ci" / "2026-03-20" / "sc-analyze"
            analyze_dir.mkdir(parents=True, exist_ok=True)
            (analyze_dir / "task_context.11.json").write_text(
                json.dumps({"taskdoc_markdown": "Task context markdown"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            argv = ["llm_generate_tests_from_acceptance_refs.py", "--task-id", "11", "--verify", "unit"]

            def fake_run_cmd(cmd: list[str], cwd: Path, timeout_sec: int):  # noqa: ARG001
                cmd_text = " ".join(cmd)
                if "validate_acceptance_refs.py" in cmd_text:
                    return 0, "acceptance refs ok\n"
                if "scripts/sc/analyze.py" in cmd_text:
                    return 0, "analyze ok\n"
                if "update_task_test_refs_from_acceptance_refs.py" in cmd_text:
                    return 0, "sync ok\n"
                if cmd[:4] == ["py", "-3", "scripts/sc/test.py", "--type"]:
                    return 0, "SC_TEST status=ok out=logs/ci/2026-03-20/sc-test\n"
                raise AssertionError(f"unexpected command: {cmd}")

            def fake_codex_exec(*, prompt: str, out_last_message: Path, timeout_sec: int):  # noqa: ARG001
                payload = {
                    "file_path": "Game.Core.Tests/FooTests.cs",
                    "content": "\n".join(
                        [
                            "using FluentAssertions;",
                            "using Xunit;",
                            "",
                            "namespace Game.Core.Tests;",
                            "",
                            "public sealed class FooTests",
                            "{",
                            "    // ACC:T11.1",
                            "    [Fact]",
                            "    public void ShouldPublishJoinEvent_WhenMemberJoinsGuild()",
                            "    {",
                            "        var memberId = \"u1\";",
                            "        memberId.Should().Be(\"u1\");",
                            "    }",
                            "}",
                        ]
                    ),
                }
                out_last_message.parent.mkdir(parents=True, exist_ok=True)
                out_last_message.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                return 0, "trace ok\n", ["codex"]

            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(gen_script, "repo_root", return_value=root), \
                mock.patch.object(gen_script, "ci_dir", return_value=out_dir), \
                mock.patch.object(gen_script, "resolve_triplet", return_value=_FakeTriplet()), \
                mock.patch.object(gen_script, "run_cmd", side_effect=fake_run_cmd), \
                mock.patch.object(gen_script, "_run_codex_exec", side_effect=fake_codex_exec):
                rc = gen_script.main()

            self.assertEqual(0, rc)
            summary = json.loads((out_dir / "summary-11.json").read_text(encoding="utf-8"))
            self.assertEqual(1, summary["created"])
            self.assertEqual("unit", summary["verify_mode"])
            self.assertEqual("ok", summary["results"][0]["status"])
            self.assertTrue((root / "Game.Core.Tests" / "FooTests.cs").exists())
            filtered = json.loads((out_dir / "refs-filtered.11.json").read_text(encoding="utf-8"))
            self.assertEqual(["logs/ci/evidence.json"], filtered["skipped_non_test_refs"])

    def test_main_should_fail_red_first_when_verify_returns_unexpected_green_for_new_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "logs" / "ci" / "2026-03-20" / "sc-llm-acceptance-tests"
            analyze_dir = root / "logs" / "ci" / "2026-03-20" / "sc-analyze"
            analyze_dir.mkdir(parents=True, exist_ok=True)
            (analyze_dir / "task_context.11.json").write_text(
                json.dumps({"taskdoc_markdown": "Task context markdown"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            argv = [
                "llm_generate_tests_from_acceptance_refs.py",
                "--task-id",
                "11",
                "--tdd-stage",
                "red-first",
                "--verify",
                "unit",
            ]

            def fake_run_cmd(cmd: list[str], cwd: Path, timeout_sec: int):  # noqa: ARG001
                cmd_text = " ".join(cmd)
                if "validate_acceptance_refs.py" in cmd_text:
                    return 0, "acceptance refs ok\n"
                if "scripts/sc/analyze.py" in cmd_text:
                    return 0, "analyze ok\n"
                if "update_task_test_refs_from_acceptance_refs.py" in cmd_text:
                    return 0, "sync ok\n"
                if cmd[:4] == ["py", "-3", "scripts/sc/test.py", "--type"]:
                    return 0, "SC_TEST status=ok out=logs/ci/2026-03-20/sc-test\n"
                raise AssertionError(f"unexpected command: {cmd}")

            def fake_codex_exec(*, prompt: str, out_last_message: Path, timeout_sec: int):  # noqa: ARG001
                payload = {
                    "file_path": "Game.Core.Tests/FooTests.cs",
                    "content": "\n".join(
                        [
                            "using FluentAssertions;",
                            "using Xunit;",
                            "",
                            "namespace Game.Core.Tests;",
                            "",
                            "public sealed class FooTests",
                            "{",
                            "    // ACC:T11.1",
                            "    [Fact]",
                            "    public void ShouldPublishJoinEvent_WhenMemberJoinsGuild()",
                            "    {",
                            "        var memberId = \"u1\";",
                            "        memberId.Should().Be(\"u1\");",
                            "    }",
                            "}",
                        ]
                    ),
                }
                out_last_message.parent.mkdir(parents=True, exist_ok=True)
                out_last_message.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                return 0, "trace ok\n", ["codex"]

            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(gen_script, "repo_root", return_value=root), \
                mock.patch.object(gen_script, "ci_dir", return_value=out_dir), \
                mock.patch.object(gen_script, "resolve_triplet", return_value=_FakeTriplet()), \
                mock.patch.object(gen_script, "run_cmd", side_effect=fake_run_cmd), \
                mock.patch.object(gen_script, "_run_codex_exec", side_effect=fake_codex_exec):
                rc = gen_script.main()

        self.assertEqual(1, rc)

    def test_main_should_force_verify_for_red_first_when_verify_none_creates_new_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "logs" / "ci" / "2026-03-20" / "sc-llm-acceptance-tests"
            analyze_dir = root / "logs" / "ci" / "2026-03-20" / "sc-analyze"
            analyze_dir.mkdir(parents=True, exist_ok=True)
            (analyze_dir / "task_context.11.json").write_text(
                json.dumps({"taskdoc_markdown": "Task context markdown"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            argv = [
                "llm_generate_tests_from_acceptance_refs.py",
                "--task-id",
                "11",
                "--tdd-stage",
                "red-first",
                "--verify",
                "none",
            ]
            seen_test_cmds: list[list[str]] = []

            def fake_run_cmd(cmd: list[str], cwd: Path, timeout_sec: int):  # noqa: ARG001
                cmd_text = " ".join(cmd)
                if "validate_acceptance_refs.py" in cmd_text:
                    return 0, "acceptance refs ok\n"
                if "scripts/sc/analyze.py" in cmd_text:
                    return 0, "analyze ok\n"
                if "update_task_test_refs_from_acceptance_refs.py" in cmd_text:
                    return 0, "sync ok\n"
                if cmd[:4] == ["py", "-3", "scripts/sc/test.py", "--type"]:
                    seen_test_cmds.append(cmd)
                    return 1, "SC_TEST status=fail out=logs/ci/2026-03-20/sc-test\n"
                raise AssertionError(f"unexpected command: {cmd}")

            def fake_codex_exec(*, prompt: str, out_last_message: Path, timeout_sec: int):  # noqa: ARG001
                payload = {
                    "file_path": "Game.Core.Tests/FooTests.cs",
                    "content": "\n".join(
                        [
                            "using FluentAssertions;",
                            "using Xunit;",
                            "",
                            "namespace Game.Core.Tests;",
                            "",
                            "public sealed class FooTests",
                            "{",
                            "    // ACC:T11.1",
                            "    [Fact]",
                            "    public void ShouldPublishJoinEvent_WhenMemberJoinsGuild()",
                            "    {",
                            "        var actualValue = 1;",
                            "        actualValue.Should().Be(2);",
                            "    }",
                            "}",
                        ]
                    ),
                }
                out_last_message.parent.mkdir(parents=True, exist_ok=True)
                out_last_message.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                return 0, "trace ok\n", ["codex"]

            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(gen_script, "repo_root", return_value=root), \
                mock.patch.object(gen_script, "ci_dir", return_value=out_dir), \
                mock.patch.object(gen_script, "resolve_triplet", return_value=_FakeTriplet()), \
                mock.patch.object(gen_script, "run_cmd", side_effect=fake_run_cmd), \
                mock.patch.object(gen_script, "_run_codex_exec", side_effect=fake_codex_exec):
                rc = gen_script.main()

        self.assertEqual(0, rc)
        self.assertEqual(1, len(seen_test_cmds))


if __name__ == "__main__":
    unittest.main()
