#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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


gate = _load_module("check_csharp_test_conventions_module", "scripts/python/check_csharp_test_conventions.py")


class CheckCsharpTestConventionsTests(unittest.TestCase):
    def test_validate_csharp_test_file_should_accept_good_names(self) -> None:
        content = "\n".join(
            [
                "using Xunit;",
                "",
                "public sealed class GuildJoinServiceTests",
                "{",
                "    [Fact]",
                "    public void ShouldPublishJoinEvent_WhenMemberJoinsGuild()",
                "    {",
                "        var memberId = \"u1\";",
                "    }",
                "",
                "    private static string BuildPayload()",
                "    {",
                "        return \"ok\";",
                "    }",
                "}",
            ]
        )

        violations = gate.validate_csharp_test_file(
            ref="Game.Core.Tests/GuildJoinServiceTests.cs",
            content=content,
        )

        self.assertEqual([], violations)

    def test_validate_csharp_test_file_should_reject_bad_file_class_method_and_variable_names(self) -> None:
        content = "\n".join(
            [
                "using Xunit;",
                "",
                "public sealed class guild_join_service_tests",
                "{",
                "    [Fact]",
                "    public void should_publish_join_event_when_member_joins_guild()",
                "    {",
                "        var Member_Id = \"u1\";",
                "    }",
                "",
                "    private static string build_payload()",
                "    {",
                "        return \"bad\";",
                "    }",
                "}",
            ]
        )

        violations = gate.validate_csharp_test_file(
            ref="Game.Core.Tests/guild_join_service_tests.cs",
            content=content,
        )

        messages = [str(item.get("message") or "") for item in violations]
        self.assertTrue(any("file name" in message for message in messages))
        self.assertTrue(any("class name" in message for message in messages))
        self.assertTrue(any("ShouldX_WhenY" in message for message in messages))
        self.assertTrue(any("local variable" in message for message in messages))
        self.assertTrue(any("helper method" in message for message in messages))

    def test_main_should_fail_when_task_scoped_test_file_has_violations(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            test_file = root / "Game.Core.Tests" / "guild_join_service_tests.cs"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text(
                "\n".join(
                    [
                        "using Xunit;",
                        "",
                        "public sealed class guild_join_service_tests",
                        "{",
                        "    [Fact]",
                        "    public void should_publish_join_event_when_member_joins_guild()",
                        "    {",
                        "        var Member_Id = \"u1\";",
                        "    }",
                        "}",
                    ]
                ),
                encoding="utf-8",
                newline="\n",
            )

            with mock.patch.object(gate, "repo_root", return_value=root), \
                mock.patch.object(gate, "load_task_csharp_test_refs", return_value=[test_file]), \
                mock.patch.object(sys, "argv", ["check_csharp_test_conventions.py", "--task-id", "11"]):
                rc = gate.main()

        self.assertEqual(1, rc)

    def test_task_requires_csharp_tests_should_return_true_when_metadata_mentions_xunit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "examples" / "taskmaster").mkdir(parents=True, exist_ok=True)
            (root / "examples" / "taskmaster" / "tasks.json").write_text(
                '{"master":{"tasks":[{"id":11,"status":"in-progress","title":"Task 11","details":"Use xUnit for core logic."}]}}\n',
                encoding="utf-8",
            )
            (root / "examples" / "taskmaster" / "tasks_back.json").write_text(
                '[{"taskmaster_id":11,"acceptance":["Core validation uses xUnit."],"test_refs":[]}]\n',
                encoding="utf-8",
            )
            (root / "examples" / "taskmaster" / "tasks_gameplay.json").write_text("[]\n", encoding="utf-8")

            required, reasons = gate.task_requires_csharp_tests(root=root, task_id="11")

        self.assertTrue(required)
        self.assertIn("mentions_xunit", reasons)

    def test_main_should_fail_when_task_requires_csharp_tests_but_has_no_cs_test_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "examples" / "taskmaster").mkdir(parents=True, exist_ok=True)
            (root / "examples" / "taskmaster" / "tasks.json").write_text(
                '{"master":{"tasks":[{"id":11,"status":"in-progress","title":"Task 11","details":"Game.Core feature update."}]}}\n',
                encoding="utf-8",
            )
            (root / "examples" / "taskmaster" / "tasks_back.json").write_text(
                '[{"taskmaster_id":11,"acceptance":["Update Game.Core service."],"test_refs":["Tests.Godot/tests/test_ui_only.gd"]}]\n',
                encoding="utf-8",
            )
            (root / "examples" / "taskmaster" / "tasks_gameplay.json").write_text("[]\n", encoding="utf-8")

            with mock.patch.object(gate, "repo_root", return_value=root), \
                mock.patch.object(sys, "argv", ["check_csharp_test_conventions.py", "--task-id", "11"]):
                rc = gate.main()

        self.assertEqual(1, rc)


if __name__ == "__main__":
    unittest.main()
