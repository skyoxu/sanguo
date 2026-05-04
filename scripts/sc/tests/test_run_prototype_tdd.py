#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
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


prototype_tdd = _load_module("prototype_tdd_module", "scripts/python/run_prototype_tdd.py")


class RunPrototypeTddTests(unittest.TestCase):
    def test_red_stage_should_accept_failing_step_and_create_record(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-04-09" / "prototype-tdd-hud-loop-red"

            with mock.patch.object(prototype_tdd, "repo_root", return_value=root), \
                mock.patch.object(prototype_tdd, "today_str", return_value="2026-04-09"), \
                mock.patch.object(prototype_tdd, "run_cmd", return_value=(1, "expected red failure\n")):
                rc = prototype_tdd.main(
                    [
                        "--slug",
                        "hud-loop",
                        "--stage",
                        "red",
                        "--dotnet-target",
                        "Game.Core.Tests/Game.Core.Tests.csproj",
                        "--out-dir",
                        str(out_dir),
                    ]
                )

            self.assertEqual(0, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("ok", summary["status"])
            self.assertEqual("fail", summary["expected"])
            self.assertTrue(summary["prototype_record"].endswith("docs/prototypes/2026-04-09-hud-loop.md"))
            self.assertEqual(1, len(summary["steps"]))
            self.assertEqual(1, summary["steps"][0]["rc"])
            record = root / "docs" / "prototypes" / "2026-04-09-hud-loop.md"
            self.assertTrue(record.exists())
            self.assertIn("# Prototype: hud-loop", record.read_text(encoding="utf-8"))

    def test_green_stage_should_fail_when_verification_is_still_red(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-04-09" / "prototype-tdd-hud-loop-green"

            with mock.patch.object(prototype_tdd, "repo_root", return_value=root), \
                mock.patch.object(prototype_tdd, "today_str", return_value="2026-04-09"), \
                mock.patch.object(prototype_tdd, "run_cmd", return_value=(1, "still failing\n")):
                rc = prototype_tdd.main(
                    [
                        "--slug",
                        "hud-loop",
                        "--stage",
                        "green",
                        "--dotnet-target",
                        "Game.Core.Tests/Game.Core.Tests.csproj",
                        "--out-dir",
                        str(out_dir),
                    ]
                )

            self.assertEqual(1, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("unexpected_red", summary["status"])
            self.assertEqual("pass", summary["expected"])

    def test_create_record_only_should_not_require_checks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-04-09" / "prototype-tdd-ui-loop-red"

            with mock.patch.object(prototype_tdd, "repo_root", return_value=root), \
                mock.patch.object(prototype_tdd, "today_str", return_value="2026-04-09"):
                rc = prototype_tdd.main(
                    [
                        "--slug",
                        "ui-loop",
                        "--create-record-only",
                        "--out-dir",
                        str(out_dir),
                    ]
                )

            self.assertEqual(0, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["create_record_only"])
            self.assertEqual([], summary["steps"])

    def test_should_consume_game_type_specifics_from_existing_record(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-04-09" / "prototype-tdd-gravity-room-red"
            record = root / "docs" / "prototypes" / "gravity-room.md"
            record.parent.mkdir(parents=True)
            record.write_text(
                "# Prototype: gravity-room\n\n"
                "## Hypothesis\n- Gravity flipping can support a readable one-room puzzle prototype.\n\n"
                "## Game Type Specifics\n"
                "- Game Type: puzzle\n"
                "- Guide Path: docs/game-type-guides/puzzle.md\n"
                "- Core Puzzle Mechanics: Flip gravity changes the valid path through one constrained room.\n",
                encoding="utf-8",
            )

            with mock.patch.object(prototype_tdd, "repo_root", return_value=root), \
                mock.patch.object(prototype_tdd, "today_str", return_value="2026-04-09"), \
                mock.patch.object(prototype_tdd, "run_cmd", return_value=(1, "expected red failure\n")):
                rc = prototype_tdd.main(
                    [
                        "--slug",
                        "gravity-room",
                        "--stage",
                        "red",
                        "--record-path",
                        "docs/prototypes/gravity-room.md",
                        "--dotnet-target",
                        "Game.Core.Tests/Game.Core.Tests.csproj",
                        "--out-dir",
                        str(out_dir),
                    ]
                )

            self.assertEqual(0, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual("puzzle", summary["prototype_intake"]["game_type_specifics"]["game_type"])
            self.assertEqual(
                "Flip gravity changes the valid path through one constrained room.",
                summary["prototype_intake"]["game_type_specifics"]["selected_sections"][0]["answer"],
            )

    def test_should_consume_prototype_type_kit_from_existing_record(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out_dir = root / "logs" / "ci" / "2026-04-09" / "prototype-tdd-rpg-loop-red"
            record = root / "docs" / "prototypes" / "rpg-loop.md"
            record.parent.mkdir(parents=True)
            record.write_text(
                "# Prototype: rpg-loop\n\n"
                "## Prototype Type Kit\n"
                "- Game Type: rpg\n"
                "- Kit Path: docs/prototype-type-kits/rpg.md\n"
                "### Gameplay Flow / GDD Route\n"
                "- 使用随机遇怪、地图撞怪，还是二者都支持？ 地图撞怪。\n"
                "- 战斗是回合制指令，还是即时碰撞/自动战斗？ 回合制指令。\n"
                "- 胜利后回到地图，还是进入结算后结束 prototype？ 胜利后回到地图。\n"
                "### Prototype Scene UI\n"
                "- 战斗场景需要哪些 UI：HP、指令按钮、战斗日志、技能栏？ HP、Attack、Battle Log。\n"
                "- 地图场景需要哪些 UI：HP、任务提示、小地图、遇怪提示？ HP、遇怪提示。\n"
                "- 失败后是直接 Game Over，还是允许 Retry？ 允许 Retry。\n",
                encoding="utf-8",
            )

            with mock.patch.object(prototype_tdd, "repo_root", return_value=root), \
                mock.patch.object(prototype_tdd, "today_str", return_value="2026-04-09"), \
                mock.patch.object(prototype_tdd, "run_cmd", return_value=(1, "expected red failure\n")):
                rc = prototype_tdd.main(
                    [
                        "--slug",
                        "rpg-loop",
                        "--stage",
                        "red",
                        "--record-path",
                        "docs/prototypes/rpg-loop.md",
                        "--dotnet-target",
                        "Game.Core.Tests/Game.Core.Tests.csproj",
                        "--out-dir",
                        str(out_dir),
                    ]
                )

            self.assertEqual(0, rc)
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            kit = summary["prototype_intake"]["prototype_type_kit"]
            self.assertEqual("rpg", kit["game_type"])
            self.assertEqual("docs/prototype-type-kits/rpg.md", kit["kit_path"])
            self.assertIn("地图撞怪", kit["gameplay_flow"][0]["answer"])
            self.assertIn("Battle Log", kit["prototype_scene_ui"][0]["answer"])


if __name__ == "__main__":
    unittest.main()
