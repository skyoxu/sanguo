#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


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


class Chapter7UiWiringTests(unittest.TestCase):
    def _write_sample_repo(self, root: Path, *, gdd_text: str) -> None:
        tasks_dir = root / ".taskmaster" / "tasks"
        tasks_dir.mkdir(parents=True)
        docs_dir = root / "docs" / "gdd"
        docs_dir.mkdir(parents=True)
        (tasks_dir / "tasks.json").write_text(
            json.dumps(
                {
                    "master": {
                        "tasks": [
                            {"id": 1, "title": "Set up runtime", "status": "done"},
                            {"id": 2, "title": "Implement standalone Reward scene", "status": "done"},
                            {"id": 3, "title": "Future task", "status": "pending"},
                        ]
                    }
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        gameplay = [
            {
                "id": "GM-0001",
                "taskmaster_id": 1,
                "title": "Set up runtime",
                "status": "done",
                "labels": ["ci"],
                "test_refs": ["Game.Core.Tests/Tasks/Task0001Tests.cs"],
                "acceptance": ["Runtime starts. Refs: Game.Core.Tests/Tasks/Task0001Tests.cs"],
                "contractRefs": ["core.run.started"],
            },
            {
                "id": "GM-0002",
                "taskmaster_id": 2,
                "title": "Implement standalone Reward scene",
                "status": "done",
                "labels": ["ui", "reward", "scene"],
                "test_refs": ["Tests.Godot/tests/Scenes/Reward/test_reward_scene.gd"],
                "acceptance": ["Reward has three choices. Refs: Tests.Godot/tests/Scenes/Reward/test_reward_scene.gd"],
                "contractRefs": ["core.reward.offer.presented", "core.reward.offer.selected"],
            },
        ]
        back = [
            {
                "id": "NG-0002",
                "taskmaster_id": 2,
                "title": "Implement standalone Reward scene",
                "status": "done",
                "labels": ["ui", "reward"],
                "test_refs": ["Game.Core.Tests/Tasks/Task0002Tests.cs"],
                "acceptance": ["Reward is traceable. Refs: Game.Core.Tests/Tasks/Task0002Tests.cs"],
                "contractRefs": ["core.reward.offer.presented"],
            }
        ]
        (tasks_dir / "tasks_gameplay.json").write_text(json.dumps(gameplay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (tasks_dir / "tasks_back.json").write_text(json.dumps(back, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (docs_dir / "ui-gdd-flow.md").write_text(gdd_text, encoding="utf-8")

    def test_collect_should_join_done_master_tasks_and_extract_ui_wiring_features(self) -> None:
        module = _load_module("collect_ui_wiring_inputs_module", "scripts/python/collect_ui_wiring_inputs.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_sample_repo(root, gdd_text="# UI\n\nT01 runtime. T02 reward.\n")
            summary = module.build_summary(repo_root=root)

        self.assertEqual(2, summary["completed_master_tasks_count"])
        reward = next(item for item in summary["needed_wiring_features"] if item["task_id"] == 2)
        self.assertEqual("reward", reward["feature_family"])
        self.assertEqual(["GM-0002"], reward["gameplay_view_ids"])
        self.assertEqual(["NG-0002"], reward["back_view_ids"])
        self.assertIn("Tests.Godot/tests/Scenes/Reward/test_reward_scene.gd", reward["test_refs"])

    def test_validate_should_fail_when_done_task_is_missing_from_ui_gdd(self) -> None:
        validator = _load_module("validate_chapter7_ui_wiring_module", "scripts/python/validate_chapter7_ui_wiring.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_sample_repo(
                root,
                gdd_text="# UI\n\n## 5. UI 接线矩阵\n| Capability | UI Surface | Player Action | System Response | Evidence/Test Refs |\n| --- | --- | --- | --- | --- |\n| Runtime | Main | Click | Start | test |\n\n## 9. 未接 UI 功能清单\nnone\n\n## 10. 下一批 UI 接线任务候选\nnone\n",
            )
            rc, payload = validator.validate(repo_root=root)

        self.assertEqual(1, rc)
        self.assertIn(2, payload["missing_done_task_refs"])

    def test_dev_cli_should_expose_chapter7_top_level_orchestrator(self) -> None:
        builders = _load_module("dev_cli_builders_module", "scripts/python/dev_cli_builders.py")
        dev_cli = _load_module("dev_cli_module_for_chapter7", "scripts/python/dev_cli.py")
        parser = dev_cli.build_parser()
        args = parser.parse_args(["run-chapter7-ui-wiring", "--delivery-profile", "fast-ship", "--write-doc"])
        cmd = builders.build_run_chapter7_ui_wiring_cmd(args)

        self.assertEqual("run-chapter7-ui-wiring", args.cmd)
        self.assertIn("scripts/python/run_chapter7_ui_wiring.py", cmd)
        self.assertIn("--write-doc", cmd)
        self.assertIn("fast-ship", cmd)


if __name__ == "__main__":
    unittest.main()
