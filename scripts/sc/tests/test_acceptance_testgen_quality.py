#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


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


quality = _load_module("sc_acceptance_testgen_quality_module", "scripts/sc/_acceptance_testgen_quality.py")


class AcceptanceTestgenQualityTests(unittest.TestCase):
    def test_validate_generated_test_content_should_accept_csharp_should_when_naming(self) -> None:
        content = "\n".join(
            [
                "using FluentAssertions;",
                "using Xunit;",
                "",
                "namespace Game.Core.Tests;",
                "",
                "public sealed class GuildMemberJoinTests",
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
        )

        ok, errors = quality.validate_generated_test_content(
            ref="Game.Core.Tests/GuildMemberJoinTests.cs",
            content=content,
        )

        self.assertTrue(ok)
        self.assertEqual([], errors)

    def test_validate_generated_test_content_should_reject_bad_csharp_file_class_method_and_local_names(self) -> None:
        content = "\n".join(
            [
                "using Xunit;",
                "",
                "public sealed class guild_member_join_tests",
                "{",
                "    // ACC:T11.1",
                "    [Fact]",
                "    public void should_publish_join_event_when_member_joins_guild()",
                "    {",
                "        var Member_Id = \"u1\";",
                "    }",
                "}",
            ]
        )

        ok, errors = quality.validate_generated_test_content(
            ref="Game.Core.Tests/guild_member_join_tests.cs",
            content=content,
        )

        self.assertFalse(ok)
        self.assertTrue(any("file name" in error for error in errors))
        self.assertTrue(any("class name" in error for error in errors))
        self.assertTrue(any("ShouldX_WhenY" in error for error in errors))
        self.assertTrue(any("local variable" in error for error in errors))

    def test_validate_generated_test_content_should_accept_gdscript_test_naming(self) -> None:
        content = "\n".join(
            [
                "extends \"res://addons/gdUnit4/src/core/GdUnitTestSuite.gd\"",
                "# ACC:T11.2",
                "func test_join_event_is_emitted() -> void:",
                "    assert_bool(true).is_true()",
            ]
        )

        ok, errors = quality.validate_generated_test_content(
            ref="Tests.Godot/tests/test_join_event_is_emitted.gd",
            content=content,
        )

        self.assertTrue(ok)
        self.assertEqual([], errors)


if __name__ == "__main__":
    unittest.main()
