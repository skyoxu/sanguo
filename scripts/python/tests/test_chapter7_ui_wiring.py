#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
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

    def _write_rich_sample_repo(self, root: Path) -> None:
        tasks_dir = root / ".taskmaster" / "tasks"
        tasks_dir.mkdir(parents=True)
        (root / "Sanguo.sln").write_text("", encoding="utf-8")
        docs_dir = root / "docs" / "gdd"
        docs_dir.mkdir(parents=True)
        overlay_dir = root / "docs" / "architecture" / "overlays" / "PRD-SANGUO-T2" / "08"
        overlay_dir.mkdir(parents=True)
        (tasks_dir / "tasks.json").write_text(
            json.dumps(
                {
                    "master": {
                        "tasks": [
                            {"id": 1, "title": "Establish baseline runtime", "status": "done", "adrRefs": ["ADR-0001"]},
                            {"id": 2, "title": "Implement config-first balancing system", "status": "done", "adrRefs": ["ADR-0002"]},
                            {"id": 5, "title": "Create enemy spawning system with cadence", "status": "done", "adrRefs": ["ADR-0003"]},
                            {"id": 9, "title": "Create basic UI for day/night and HP display", "status": "done", "adrRefs": ["ADR-0004"]},
                            {"id": 12, "title": "Implement Core Resource System with Integer Safety", "status": "done", "adrRefs": ["ADR-0005"]},
                            {"id": 22, "title": "Implement Camera and Interaction System with Edge and Keyboard Scrolling", "status": "done", "adrRefs": ["ADR-0006"]},
                            {"id": 23, "title": "Develop Runtime Speed Controls (Pause, 1x, 2x) with Timer Freeze", "status": "done", "adrRefs": ["ADR-0007"]},
                            {"id": 25, "title": "Build Save System with Autosave and Migration Handling", "status": "done", "adrRefs": ["ADR-0006"]},
                            {"id": 28, "title": "Set Up Localization (i18n) for zh-CN and en-US", "status": "done", "adrRefs": ["ADR-0008"]},
                            {"id": 29, "title": "Add Audio Settings for Music and SFX Channels", "status": "done", "adrRefs": ["ADR-0009"]},
                            {"id": 30, "title": "Optimize for Performance Targets (45 FPS 1% Low, 60 FPS Average)", "status": "done", "adrRefs": ["ADR-0010"]},
                            {"id": 31, "title": "Scaffold config-contract workspace on existing project", "status": "done", "adrRefs": ["ADR-0007"]},
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
                "title": "Establish baseline runtime",
                "status": "done",
                "labels": ["ci", "startup"],
                "test_refs": ["Tests.Godot/tests/Integration/test_runtime_boot.gd"],
                "acceptance": ["Runtime boots. Refs: Tests.Godot/tests/Integration/test_runtime_boot.gd"],
                "contractRefs": ["core.run.started"],
            },
            {
                "id": "GM-0002",
                "taskmaster_id": 2,
                "title": "Implement config-first balancing system",
                "status": "done",
                "labels": ["config"],
                "test_refs": ["Game.Core.Tests/Domain/GameConfigTests.cs"],
                "acceptance": ["Config renders. Refs: Game.Core.Tests/Domain/GameConfigTests.cs"],
                "contractRefs": ["core.config.loaded"],
            },
            {
                "id": "GM-0005",
                "taskmaster_id": 5,
                "title": "Create enemy spawning system with cadence",
                "status": "done",
                "labels": ["combat"],
                "test_refs": ["Game.Core.Tests/Services/WaveManagerSpawnPolicyTests.cs"],
                "acceptance": ["Spawn cadence visible. Refs: Game.Core.Tests/Services/WaveManagerSpawnPolicyTests.cs"],
                "contractRefs": ["core.wave.spawned"],
            },
            {
                "id": "GM-0009",
                "taskmaster_id": 9,
                "title": "Create basic UI for day/night and HP display",
                "status": "done",
                "labels": ["ui"],
                "test_refs": ["Tests.Godot/tests/UI/test_hud_scene.gd"],
                "acceptance": ["HUD updates. Refs: Tests.Godot/tests/UI/test_hud_scene.gd"],
                "contractRefs": ["core.hud.visible"],
            },
            {
                "id": "GM-0012",
                "taskmaster_id": 12,
                "title": "Implement Core Resource System with Integer Safety",
                "status": "done",
                "labels": ["economy"],
                "test_refs": ["Game.Core.Tests/Services/ResourceManagerTests.cs"],
                "acceptance": ["Resource changes visible. Refs: Game.Core.Tests/Services/ResourceManagerTests.cs"],
                "contractRefs": ["core.resource.changed"],
            },
            {
                "id": "GM-0022",
                "taskmaster_id": 22,
                "title": "Implement Camera and Interaction System with Edge and Keyboard Scrolling",
                "status": "done",
                "labels": ["ui", "camera"],
                "test_refs": ["Tests.Godot/tests/UI/test_hud_scene.gd"],
                "acceptance": ["Camera scrolling is visible. Refs: Tests.Godot/tests/UI/test_hud_scene.gd"],
                "contractRefs": ["core.camera.scrolled"],
            },
            {
                "id": "GM-0023",
                "taskmaster_id": 23,
                "title": "Develop Runtime Speed Controls (Pause, 1x, 2x) with Timer Freeze",
                "status": "done",
                "labels": ["ui", "runtime"],
                "test_refs": ["Tests.Godot/tests/UI/test_hud_scene.gd"],
                "acceptance": ["Runtime speed modes are visible. Refs: Tests.Godot/tests/UI/test_hud_scene.gd"],
                "contractRefs": ["core.time_scale.changed"],
            },
            {
                "id": "GM-0025",
                "taskmaster_id": 25,
                "title": "Build Save System with Autosave and Migration Handling",
                "status": "done",
                "labels": ["save"],
                "test_refs": ["Tests.Godot/tests/Adapters/Save/test_save_manager_daystart_autosave.gd"],
                "acceptance": ["Save path visible. Refs: Tests.Godot/tests/Adapters/Save/test_save_manager_daystart_autosave.gd"],
                "contractRefs": ["core.save.ready"],
            },
            {
                "id": "GM-0028",
                "taskmaster_id": 28,
                "title": "Set Up Localization (i18n) for zh-CN and en-US",
                "status": "done",
                "labels": ["ui", "i18n"],
                "test_refs": ["Tests.Godot/tests/UI/test_hud_scene.gd"],
                "acceptance": ["Language switch is visible. Refs: Tests.Godot/tests/UI/test_hud_scene.gd"],
                "contractRefs": ["core.i18n.changed"],
            },
            {
                "id": "GM-0029",
                "taskmaster_id": 29,
                "title": "Add Audio Settings for Music and SFX Channels",
                "status": "done",
                "labels": ["ui", "audio"],
                "test_refs": ["Tests.Godot/tests/UI/test_hud_scene.gd"],
                "acceptance": ["Audio settings are visible. Refs: Tests.Godot/tests/UI/test_hud_scene.gd"],
                "contractRefs": ["core.audio.changed"],
            },
            {
                "id": "GM-0030",
                "taskmaster_id": 30,
                "title": "Optimize for Performance Targets (45 FPS 1% Low, 60 FPS Average)",
                "status": "done",
                "labels": ["perf"],
                "test_refs": ["Tests.Godot/tests/Integration/test_backup_restore_savegame.gd"],
                "acceptance": ["Performance evidence is visible. Refs: Tests.Godot/tests/Integration/test_backup_restore_savegame.gd"],
                "contractRefs": ["core.perf.sampled"],
            },
            {
                "id": "GM-0031",
                "taskmaster_id": 31,
                "title": "Scaffold config-contract workspace on existing project",
                "status": "done",
                "labels": ["config", "governance"],
                "test_refs": ["Game.Core.Tests/Tasks/Task31ConfigWorkspaceGuardrailsTests.cs"],
                "acceptance": ["Config workspace visible. Refs: Game.Core.Tests/Tasks/Task31ConfigWorkspaceGuardrailsTests.cs"],
                "contractRefs": ["core.config.workspace.ready"],
            },
        ]
        back = [
            {
                "id": "NG-0009",
                "taskmaster_id": 9,
                "title": "Create basic UI for day/night and HP display",
                "status": "done",
                "labels": ["ui", "hud"],
                "test_refs": ["Tests.Godot/tests/UI/test_hud_updates_on_events.gd"],
                "acceptance": ["HUD events visible. Refs: Tests.Godot/tests/UI/test_hud_updates_on_events.gd"],
                "contractRefs": ["core.hud.visible"],
            },
            {
                "id": "NG-0025",
                "taskmaster_id": 25,
                "title": "Build Save System with Autosave and Migration Handling",
                "status": "done",
                "labels": ["save", "meta"],
                "test_refs": ["Game.Core.Tests/Save/SaveResumeBoundaryTests.cs"],
                "acceptance": ["Continue gate visible. Refs: Game.Core.Tests/Save/SaveResumeBoundaryTests.cs"],
                "contractRefs": ["core.save.ready"],
            },
        ]
        (tasks_dir / "tasks_gameplay.json").write_text(json.dumps(gameplay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (tasks_dir / "tasks_back.json").write_text(json.dumps(back, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (overlay_dir / "overlay-manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "prd_id": "PRD-SANGUO-T2",
                    "files": {
                        "index": "_index.md",
                        "feature": "08-Feature-Slice-T2-Core-Loop.md",
                        "contracts": "08-Contracts-T2.md",
                        "testing": "08-Testing-T2.md",
                        "observability": "08-Observability-T2.md",
                        "acceptance": "ACCEPTANCE_CHECKLIST.md",
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (overlay_dir / "08-Feature-Slice-T2-Core-Loop.md").write_text(
            "\n".join(
                [
                    "---",
                    "PRD-ID: PRD-SANGUO-T2",
                    "ADR-Refs:",
                    "  - ADR-0011",
                    "  - ADR-0031",
                    "---",
                    "",
                    "## Acceptance Anchors",
                    "",
                    "- ADR-0022",
                    "- docs/architecture/base/06-runtime-view-loops-state-machines-error-paths-v2.md",
                    "- `T22` camera edge scroll and keyboard scroll must both stay clamped to map bounds.",
                    "- `T23` Pause/1x/2x switching must freeze and resume runtime timers deterministically.",
                    "- `T28` zh-CN/en-US language switch must apply immediately and persist.",
                    "- `T29` Music/SFX channels must apply immediately and persist.",
                    "",
                    "## Execution Slices (P0)",
                    "",
                    "### Slice B - Runtime UX/Save/Platform (`T21-T30`)",
                    "",
                    "- Taskmaster IDs 21-30: runtime UX/save/performance envelope.",
                    "- Key tasks: `T21`, `T22`, `T23`, `T24`, `T25`, `T26`, `T27`, `T28`, `T29`, `T30`.",
                    "- Failure focus:",
                    "  - `T22` edge scroll plus keyboard input must not produce camera jitter.",
                    "  - `T23` pause must not leak timer progress.",
                    "  - `T28` language switch must not require restart.",
                    "  - `T29` audio settings must not reset after restart.",
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (overlay_dir / "08-Testing-T2.md").write_text(
            "\n".join(
                [
                    "---",
                    "PRD-ID: PRD-SANGUO-T2",
                    "---",
                    "",
                    "## Requirement-to-Test Mapping",
                    "",
                    "| Requirement ID | Taskmaster IDs | Primary Tests | Expected Logs |",
                    "| --- | --- | --- | --- |",
                    "| RQ-CAMERA-SCROLL | 22 | `Tests.Godot/tests/UI/test_hud_scene.gd` | `logs/e2e/<YYYY-MM-DD>/runtime-ui/summary.json` |",
                    "| RQ-RUNTIME-SPEED-MODES | 23 | `Tests.Godot/tests/UI/test_hud_scene.gd` | `logs/e2e/<YYYY-MM-DD>/runtime-ui/summary.json` |",
                    "| RQ-SAVE-MIGRATION-CLOUD | 25 | `Tests.Godot/tests/Adapters/Save/test_save_manager_daystart_autosave.gd` | `logs/ci/<YYYY-MM-DD>/save-migration/report.json` |",
                    "| RQ-I18N-LANG-SWITCH | 28 | `Tests.Godot/tests/UI/test_hud_scene.gd` | `logs/e2e/<YYYY-MM-DD>/settings/summary.json` |",
                    "| RQ-AUDIO-CHANNEL-SETTINGS | 29 | `Tests.Godot/tests/UI/test_hud_scene.gd` | `logs/e2e/<YYYY-MM-DD>/settings/summary.json` |",
                    "| RQ-PERF-GATE | 30 | `Tests.Godot/tests/Integration/test_backup_restore_savegame.gd` | `logs/perf/<YYYY-MM-DD>/summary.json` |",
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (overlay_dir / "08-Observability-T2.md").write_text(
            "\n".join(
                [
                    "---",
                    "PRD-ID: PRD-SANGUO-T2",
                    "---",
                    "",
                    "## Task Evidence Matrix (P0)",
                    "",
                    "| Task Group | Required Artifact | Minimum Fields |",
                    "| --- | --- | --- |",
                    "| `T22` camera scroll | `logs/e2e/<YYYY-MM-DD>/runtime-ui/summary.json` | `camera_mode`, `edge_threshold_px`, `keyboard_vector`, `clamped` |",
                    "| `T23` speed modes | `logs/e2e/<YYYY-MM-DD>/runtime-ui/summary.json` | `speed_mode`, `timers_frozen`, `resume_tick`, `status` |",
                    "| `T25` save + migration | `logs/ci/<YYYY-MM-DD>/save-migration/report.json` | `save_version`, `migration_path`, `result`, `error_code` |",
                    "| `T28` i18n switch | `logs/e2e/<YYYY-MM-DD>/settings/summary.json` | `language_from`, `language_to`, `applied`, `persisted` |",
                    "| `T29` audio settings | `logs/e2e/<YYYY-MM-DD>/settings/summary.json` | `channel`, `value`, `applied`, `persisted` |",
                    "| `T30` performance | `logs/perf/<YYYY-MM-DD>/summary.json` | `avg_fps`, `fps_1pct_low`, `samples`, `gate` |",
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (docs_dir / "ui-gdd-flow.md").write_text("# Placeholder\n", encoding="utf-8")

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

    def test_writer_should_prefer_readme_repository_identity_over_generic_solution_name(self) -> None:
        writer = _load_module("chapter7_ui_gdd_writer_module_for_repo_identity", "scripts/python/chapter7_ui_gdd_writer.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "GodotGame.sln").write_text("", encoding="utf-8")
            (root / "README.md").write_text("# sanguo (Godot 4.5.1 + C#)\n", encoding="utf-8")

            display = writer._repo_display_name(root)
            slug = writer._repo_gdd_slug(root)

        self.assertEqual("Sanguo", display)
        self.assertEqual("SANGUO", slug)

    def test_write_doc_should_generate_governed_gdd_with_sanguo_like_sections(self) -> None:
        collector = _load_module("collect_ui_wiring_inputs_module_for_writer", "scripts/python/collect_ui_wiring_inputs.py")
        writer = _load_module("chapter7_ui_gdd_writer_module", "scripts/python/chapter7_ui_gdd_writer.py")
        validator = _load_module("validate_chapter7_ui_wiring_module_for_writer", "scripts/python/validate_chapter7_ui_wiring.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            summary = collector.build_summary(repo_root=root)
            out = writer.write_ui_gdd_flow(repo_root=root, summary=summary)
            text = out.read_text(encoding="utf-8")
            rc, payload = validator.validate(repo_root=root)

        self.assertIn("GDD-ID:", text)
        self.assertIn("GDD-ID: GDD-SANGUO-UI-WIRING-V1", text)
        self.assertIn("Title: Sanguo Chapter 7 UI Wiring Board", text)
        self.assertIn("# Sanguo Chapter 7 UI Wiring Board", text)
        self.assertNotIn("Lastking", text)
        self.assertNotIn("NewRouge", text)
        self.assertNotIn("GDD-LASTKING", text)
        self.assertNotIn("GDD-NEWROUGE", text)
        self.assertIn("## 1. Design Goals", text)
        self.assertIn("## 8. Screen State Matrix", text)
        self.assertIn("## 9. Scope And Non-Goals", text)
        self.assertIn("## 12. Copy And Accessibility", text)
        self.assertIn("## 14. Task Alignment", text)
        self.assertEqual(0, rc)
        self.assertEqual([], payload["missing_done_task_refs"])

    def test_write_doc_should_compress_candidates_into_slice_level_backlog(self) -> None:
        collector = _load_module("collect_ui_wiring_inputs_module_for_slice_writer", "scripts/python/collect_ui_wiring_inputs.py")
        writer = _load_module("chapter7_ui_gdd_writer_module_for_slice_writer", "scripts/python/chapter7_ui_gdd_writer.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            summary = collector.build_summary(repo_root=root)
            out = writer.write_ui_gdd_flow(repo_root=root, summary=summary)
            text = out.read_text(encoding="utf-8")

        candidate_headings = [line for line in text.splitlines() if line.startswith("### Candidate Slice")]
        self.assertGreaterEqual(len(candidate_headings), 5)
        self.assertLessEqual(len(candidate_headings), 8)
        self.assertNotIn("### Candidate T01", text)

    def test_write_doc_should_extract_failure_empty_and_completion_semantics(self) -> None:
        collector = _load_module("collect_ui_wiring_inputs_module_for_semantics", "scripts/python/collect_ui_wiring_inputs.py")
        writer = _load_module("chapter7_ui_gdd_writer_module_for_semantics", "scripts/python/chapter7_ui_gdd_writer.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            summary = collector.build_summary(repo_root=root)
            out = writer.write_ui_gdd_flow(repo_root=root, summary=summary)
            text = out.read_text(encoding="utf-8")

        self.assertIn("- Failure state:", text)
        self.assertIn("- Empty state:", text)
        self.assertIn("- Completion result:", text)
        self.assertIn("must not advance runtime config snapshot", text)
        self.assertIn("show no active run state until runtime data is available", text)

    def test_write_doc_should_distinguish_player_and_operator_facing_slices(self) -> None:
        collector = _load_module("collect_ui_wiring_inputs_module_for_audience", "scripts/python/collect_ui_wiring_inputs.py")
        writer = _load_module("chapter7_ui_gdd_writer_module_for_audience", "scripts/python/chapter7_ui_gdd_writer.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            summary = collector.build_summary(repo_root=root)
            out = writer.write_ui_gdd_flow(repo_root=root, summary=summary)
            text = out.read_text(encoding="utf-8")

        self.assertIn("| Capability Slice | Audience | Task IDs | Player-Facing Meaning | Primary UI Need |", text)
        self.assertIn("| Config Governance And Audit | operator-facing or mixed |", text)
        self.assertIn("Operator-facing read surfaces are allowed", text)

    def test_write_doc_should_generate_screen_level_contracts(self) -> None:
        collector = _load_module("collect_ui_wiring_inputs_module_for_screen_contracts", "scripts/python/collect_ui_wiring_inputs.py")
        writer = _load_module("chapter7_ui_gdd_writer_module_for_screen_contracts", "scripts/python/chapter7_ui_gdd_writer.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            summary = collector.build_summary(repo_root=root)
            out = writer.write_ui_gdd_flow(repo_root=root, summary=summary)
            text = out.read_text(encoding="utf-8")

        self.assertIn("## 7. Screen-Level Contracts", text)
        self.assertIn("### 7.1 MainMenu And Boot Flow", text)
        self.assertIn("### 7.2 Runtime HUD And Outcome Surfaces", text)
        self.assertIn("### 7.3 Combat Pressure And Interaction Surfaces", text)
        self.assertIn("### 7.4 Economy And Progression Panels", text)
        self.assertIn("### 7.5 Save, Settings, And Meta Surfaces", text)
        self.assertIn("### 7.6 Config Audit And Migration Surfaces", text)

    def test_write_doc_should_place_slice_contracts_under_matching_screen_groups(self) -> None:
        collector = _load_module("collect_ui_wiring_inputs_module_for_grouping", "scripts/python/collect_ui_wiring_inputs.py")
        writer = _load_module("chapter7_ui_gdd_writer_module_for_grouping", "scripts/python/chapter7_ui_gdd_writer.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            summary = collector.build_summary(repo_root=root)
            out = writer.write_ui_gdd_flow(repo_root=root, summary=summary)
            text = out.read_text(encoding="utf-8")

        self.assertIn("- Covered slice: Entry And Bootstrap.", text)
        self.assertIn("- Covered slice: Config Governance And Audit.", text)
        self.assertIn("- Must show:", text)
        self.assertIn("- Must not hide:", text)
        self.assertIn("- Validation focus:", text)

    def test_write_doc_should_generate_screen_state_matrix_section(self) -> None:
        collector = _load_module("collect_ui_wiring_inputs_module_for_state_matrix", "scripts/python/collect_ui_wiring_inputs.py")
        writer = _load_module("chapter7_ui_gdd_writer_module_for_state_matrix", "scripts/python/chapter7_ui_gdd_writer.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            summary = collector.build_summary(repo_root=root)
            out = writer.write_ui_gdd_flow(repo_root=root, summary=summary)
            text = out.read_text(encoding="utf-8")

        self.assertIn("## 8. Screen State Matrix", text)
        self.assertIn("| Screen Group | Entry State | Interaction State | Failure State | Recovery / Exit |", text)
        self.assertIn("| MainMenu And Boot Flow |", text)
        self.assertIn("| Config Audit And Migration Surfaces |", text)

    def test_write_doc_should_include_recovery_and_exit_language_in_state_matrix(self) -> None:
        collector = _load_module("collect_ui_wiring_inputs_module_for_recovery_matrix", "scripts/python/collect_ui_wiring_inputs.py")
        writer = _load_module("chapter7_ui_gdd_writer_module_for_recovery_matrix", "scripts/python/chapter7_ui_gdd_writer.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            summary = collector.build_summary(repo_root=root)
            out = writer.write_ui_gdd_flow(repo_root=root, summary=summary)
            text = out.read_text(encoding="utf-8")

        self.assertIn("retry bootstrap", text)
        self.assertIn("return to menu", text)
        self.assertIn("retry, acknowledge, or return", text)

    def test_collect_should_merge_overlay_requirement_and_evidence_context(self) -> None:
        collector = _load_module("collect_ui_wiring_inputs_module_for_overlay_context", "scripts/python/collect_ui_wiring_inputs.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            summary = collector.build_summary(repo_root=root)

        feature = next(item for item in summary["needed_wiring_features"] if item["task_id"] == 28)
        self.assertIn("RQ-I18N-LANG-SWITCH", feature["overlay_requirement_ids"])
        self.assertIn("logs/e2e/<YYYY-MM-DD>/settings/summary.json", feature["overlay_expected_logs"])
        self.assertIn("language_from", feature["overlay_minimum_fields"])
        self.assertIn("language switch must apply immediately and persist", " ".join(feature["overlay_acceptance_notes"]).lower())

    def test_write_doc_should_render_overlay_requirement_and_evidence_sections(self) -> None:
        collector = _load_module("collect_ui_wiring_inputs_module_for_overlay_writer", "scripts/python/collect_ui_wiring_inputs.py")
        writer = _load_module("chapter7_ui_gdd_writer_module_for_overlay_writer", "scripts/python/chapter7_ui_gdd_writer.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            summary = collector.build_summary(repo_root=root)
            out = writer.write_ui_gdd_flow(repo_root=root, summary=summary)
            text = out.read_text(encoding="utf-8")

        self.assertIn("## 13. Test And Acceptance", text)
        self.assertIn("RQ-I18N-LANG-SWITCH", text)
        self.assertIn("logs/e2e/<YYYY-MM-DD>/settings/summary.json", text)
        self.assertIn("language_from, language_to, applied, persisted", text)
        self.assertIn("camera edge scroll and keyboard scroll", text)

    def test_collect_should_filter_overlay_noise_and_keep_task_specific_notes(self) -> None:
        collector = _load_module("collect_ui_wiring_inputs_module_for_overlay_filtering", "scripts/python/collect_ui_wiring_inputs.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            summary = collector.build_summary(repo_root=root)

        feature = next(item for item in summary["needed_wiring_features"] if item["task_id"] == 28)
        notes = " ".join(feature["overlay_acceptance_notes"])
        self.assertIn("T28", notes)
        self.assertNotIn("Taskmaster IDs 21-30", notes)
        self.assertNotIn("Key tasks:", notes)
        self.assertNotIn("ADR-000", notes)
        self.assertNotIn("docs/architecture/base/", notes)

    def test_write_doc_should_group_overlay_acceptance_by_screen_group_not_task(self) -> None:
        collector = _load_module("collect_ui_wiring_inputs_module_for_overlay_grouping", "scripts/python/collect_ui_wiring_inputs.py")
        writer = _load_module("chapter7_ui_gdd_writer_module_for_overlay_grouping", "scripts/python/chapter7_ui_gdd_writer.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            summary = collector.build_summary(repo_root=root)
            out = writer.write_ui_gdd_flow(repo_root=root, summary=summary)
            text = out.read_text(encoding="utf-8")

        self.assertIn("### Save, Settings, And Meta Surfaces", text)
        self.assertIn("- Requirement IDs: `RQ-I18N-LANG-SWITCH`, `RQ-AUDIO-CHANNEL-SETTINGS`, `RQ-PERF-GATE`, `RQ-SAVE-MIGRATION-CLOUD`.", text)
        self.assertIn("- Evidence fields: save_version, migration_path, result, error_code, language_from, language_to, applied, persisted.", text)
        self.assertNotIn("### T28 Set Up Localization", text)
        self.assertNotIn("### T29 Add Audio Settings", text)

    def test_write_doc_should_sort_requirement_ids_by_group_specificity(self) -> None:
        collector = _load_module("collect_ui_wiring_inputs_module_for_requirement_sort", "scripts/python/collect_ui_wiring_inputs.py")
        writer = _load_module("chapter7_ui_gdd_writer_module_for_requirement_sort", "scripts/python/chapter7_ui_gdd_writer.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            summary = collector.build_summary(repo_root=root)
            out = writer.write_ui_gdd_flow(repo_root=root, summary=summary)
            text = out.read_text(encoding="utf-8")

        self.assertIn(
            "- Requirement IDs: `RQ-I18N-LANG-SWITCH`, `RQ-AUDIO-CHANNEL-SETTINGS`, `RQ-PERF-GATE`, `RQ-SAVE-MIGRATION-CLOUD`.",
            text,
        )
        self.assertNotIn(
            "- Requirement IDs: `RQ-SAVE-MIGRATION-CLOUD`, `RQ-I18N-LANG-SWITCH`, `RQ-AUDIO-CHANNEL-SETTINGS`, `RQ-PERF-GATE`.",
            text,
        )

    def test_write_doc_should_render_candidate_as_task_shaped_spec(self) -> None:
        collector = _load_module("collect_ui_wiring_inputs_module_for_candidate_spec", "scripts/python/collect_ui_wiring_inputs.py")
        writer = _load_module("chapter7_ui_gdd_writer_module_for_candidate_spec", "scripts/python/chapter7_ui_gdd_writer.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            summary = collector.build_summary(repo_root=root)
            out = writer.write_ui_gdd_flow(repo_root=root, summary=summary)
            text = out.read_text(encoding="utf-8")

        self.assertIn("### Candidate Slice Save, Settings, And Meta Surfaces", text)
        self.assertIn("- Candidate type: task-shaped UI wiring spec.", text)
        self.assertIn("- Screen group: Save, Settings, And Meta Surfaces.", text)
        self.assertIn("- Requirement IDs: `RQ-I18N-LANG-SWITCH`, `RQ-AUDIO-CHANNEL-SETTINGS`, `RQ-PERF-GATE`, `RQ-SAVE-MIGRATION-CLOUD`.", text)
        self.assertIn("- Validation artifact targets:", text)
        self.assertIn("- Suggested standalone surfaces:", text)

    def test_orchestrator_should_be_idempotent_for_same_inputs(self) -> None:
        collector = _load_module("collect_ui_wiring_inputs_module_for_idempotency", "scripts/python/collect_ui_wiring_inputs.py")
        writer = _load_module("chapter7_ui_gdd_writer_module_for_idempotency", "scripts/python/chapter7_ui_gdd_writer.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            summary1 = collector.build_summary(repo_root=root)
            out1 = writer.write_ui_gdd_flow(repo_root=root, summary=summary1)
            text1 = out1.read_text(encoding="utf-8")

            summary2 = collector.build_summary(repo_root=root)
            out2 = writer.write_ui_gdd_flow(repo_root=root, summary=summary2)
            text2 = out2.read_text(encoding="utf-8")

        self.assertEqual(summary1["completed_master_tasks_count"], summary2["completed_master_tasks_count"])
        self.assertEqual(summary1["needed_wiring_features_count"], summary2["needed_wiring_features_count"])
        self.assertEqual(text1, text2)
        self.assertTrue(text2.endswith("\n"))
        self.assertFalse(text2.endswith("\n\n"))

    def test_self_check_should_include_write_doc_step_when_requested(self) -> None:
        run_module = _load_module("run_chapter7_ui_wiring_module_for_self_check", "scripts/python/run_chapter7_ui_wiring.py")
        output = io.StringIO()
        with redirect_stdout(output):
            rc = run_module.main(["--delivery-profile", "fast-ship", "--write-doc", "--self-check"])
        payload = json.loads(output.getvalue())

        self.assertEqual(0, rc)
        self.assertEqual(["collect", "write-doc", "validate"], payload["planned_steps"])


    def test_write_doc_should_export_stable_candidate_sidecar_json(self) -> None:
        collector = _load_module("collect_ui_wiring_inputs_module_for_candidate_sidecar", "scripts/python/collect_ui_wiring_inputs.py")
        writer = _load_module("chapter7_ui_gdd_writer_module_for_candidate_sidecar", "scripts/python/chapter7_ui_gdd_writer.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            summary = collector.build_summary(repo_root=root)
            writer.write_ui_gdd_flow(repo_root=root, summary=summary)
            sidecar = root / "docs" / "gdd" / "ui-gdd-flow.candidates.json"
            payload1 = json.loads(sidecar.read_text(encoding="utf-8"))

            summary2 = collector.build_summary(repo_root=root)
            writer.write_ui_gdd_flow(repo_root=root, summary=summary2)
            payload2 = json.loads(sidecar.read_text(encoding="utf-8"))

        self.assertTrue(sidecar.name.endswith(".candidates.json"))
        self.assertIn("candidates", payload1)
        self.assertGreaterEqual(len(payload1["candidates"]), 5)
        self.assertEqual(payload1, payload2)
        candidate = next(item for item in payload1["candidates"] if item["screen_group"] == "Save, Settings, And Meta Surfaces")
        self.assertEqual("task-shaped UI wiring spec", candidate["candidate_type"])
        self.assertEqual([25, 28, 29, 30], candidate["scope_task_ids"])
        self.assertIn("RQ-I18N-LANG-SWITCH", candidate["requirement_ids"])
        self.assertIn("logs/e2e/<YYYY-MM-DD>/settings/summary.json", candidate["validation_artifact_targets"])

    def test_orchestrator_should_report_candidate_sidecar_in_summary(self) -> None:
        run_module = _load_module("run_chapter7_ui_wiring_module_for_candidate_summary", "scripts/python/run_chapter7_ui_wiring.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            out_json = root / "logs" / "ci" / "summary.json"
            rc = run_module.main([
                "--repo-root", str(root),
                "--delivery-profile", "fast-ship",
                "--write-doc",
                "--out-json", str(out_json),
            ])
            payload = json.loads(out_json.read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertEqual("ok", payload["status"])
        self.assertIn("candidate_sidecar", payload)
        self.assertTrue(str(payload["candidate_sidecar"]).endswith("docs/gdd/ui-gdd-flow.candidates.json"))
        self.assertNotIn("generated_artifacts", payload)

    def test_orchestrator_should_export_input_snapshot_and_artifact_hashes(self) -> None:
        run_module = _load_module("run_chapter7_ui_wiring_module_for_input_snapshot", "scripts/python/run_chapter7_ui_wiring.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            out_json = root / "logs" / "ci" / "summary.json"
            rc = run_module.main([
                "--repo-root", str(root),
                "--delivery-profile", "fast-ship",
                "--write-doc",
                "--out-json", str(out_json),
            ])
            payload1 = json.loads(out_json.read_text(encoding="utf-8"))
            snapshot1 = json.loads(Path(payload1["input_snapshot"]).read_text(encoding="utf-8"))
            manifest1 = json.loads(Path(payload1["artifact_manifest"]).read_text(encoding="utf-8"))

            rc2 = run_module.main([
                "--repo-root", str(root),
                "--delivery-profile", "fast-ship",
                "--write-doc",
                "--out-json", str(out_json),
            ])
            payload2 = json.loads(out_json.read_text(encoding="utf-8"))
            snapshot2 = json.loads(Path(payload2["input_snapshot"]).read_text(encoding="utf-8"))
            manifest2 = json.loads(Path(payload2["artifact_manifest"]).read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertEqual(0, rc2)
        self.assertIn("input_snapshot", payload1)
        self.assertTrue(str(payload1["input_snapshot"]).endswith("chapter7-ui-wiring/inputs.snapshot.json"))
        self.assertNotIn("artifact_hashes", payload1)
        self.assertNotIn("generated_artifacts", payload1)
        self.assertEqual(snapshot1, snapshot2)
        self.assertEqual(manifest1, manifest2)
        by_type = {item["artifact_type"]: item for item in manifest1["artifacts"]}
        self.assertEqual(payload1["candidate_sidecar"], by_type["candidate-sidecar"]["path"])
        self.assertTrue(by_type["ui-gdd"]["path"].endswith("docs/gdd/ui-gdd-flow.md"))
        self.assertEqual("non-idempotent-summary", by_type["summary"]["sha256"])

    def test_orchestrator_should_export_artifact_manifest_with_stable_entries(self) -> None:
        run_module = _load_module("run_chapter7_ui_wiring_module_for_artifact_manifest", "scripts/python/run_chapter7_ui_wiring.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            out_json = root / "logs" / "ci" / "summary.json"
            rc = run_module.main([
                "--repo-root", str(root),
                "--delivery-profile", "fast-ship",
                "--write-doc",
                "--out-json", str(out_json),
            ])
            payload1 = json.loads(out_json.read_text(encoding="utf-8"))
            manifest1 = json.loads(Path(payload1["artifact_manifest"]).read_text(encoding="utf-8"))

            rc2 = run_module.main([
                "--repo-root", str(root),
                "--delivery-profile", "fast-ship",
                "--write-doc",
                "--out-json", str(out_json),
            ])
            payload2 = json.loads(out_json.read_text(encoding="utf-8"))
            manifest2 = json.loads(Path(payload2["artifact_manifest"]).read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertEqual(0, rc2)
        self.assertIn("artifact_manifest", payload1)
        self.assertTrue(str(payload1["artifact_manifest"]).endswith("chapter7-ui-wiring/artifact-manifest.json"))
        self.assertNotIn("generated_artifacts", payload1)
        self.assertEqual(manifest1, manifest2)
        self.assertEqual(1, manifest1["schema_version"])
        self.assertEqual("fast-ship", manifest1["run_profile"])
        entries = manifest1["artifacts"]
        self.assertGreaterEqual(len(entries), 4)
        self.assertNotIn("artifact_hashes", payload1)
        self.assertEqual(
            ["input-snapshot", "ui-gdd", "candidate-sidecar", "summary"],
            [item["artifact_type"] for item in entries],
        )
        for item in entries:
            self.assertIn("path", item)
            self.assertIn("relative_path", item)
            self.assertIn("sha256", item)
            self.assertIn("producer_step", item)
        self.assertNotIn("artifact_manifest_entries", payload1)

    def test_artifact_manifest_validator_should_verify_contract_and_hashes(self) -> None:
        run_module = _load_module("run_chapter7_ui_wiring_module_for_manifest_validator", "scripts/python/run_chapter7_ui_wiring.py")
        validator = _load_module("validate_chapter7_artifact_manifest_module", "scripts/python/validate_chapter7_artifact_manifest.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            out_json = root / "logs" / "ci" / "summary.json"
            rc = run_module.main([
                "--repo-root", str(root),
                "--delivery-profile", "fast-ship",
                "--write-doc",
                "--out-json", str(out_json),
            ])
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            ok_rc, ok_payload = validator.validate(repo_root=root, manifest_path=Path(payload["artifact_manifest"]))

            candidate = root / "docs" / "gdd" / "ui-gdd-flow.candidates.json"
            candidate.write_text(candidate.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            fail_rc, fail_payload = validator.validate(repo_root=root, manifest_path=Path(payload["artifact_manifest"]))

        self.assertEqual(0, rc)
        self.assertEqual(0, ok_rc)
        self.assertEqual("ok", ok_payload["status"])
        self.assertEqual(1, ok_payload["schema_version"])
        self.assertEqual("fast-ship", ok_payload["run_profile"])
        self.assertEqual(4, ok_payload["artifact_count"])
        self.assertEqual(1, fail_rc)
        self.assertEqual("fail", fail_payload["status"])
        self.assertIn("candidate-sidecar", fail_payload["hash_mismatch_artifact_types"])

    def test_orchestrator_should_run_artifact_manifest_validator_as_final_step(self) -> None:
        run_module = _load_module("run_chapter7_ui_wiring_module_for_manifest_step", "scripts/python/run_chapter7_ui_wiring.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            out_json = root / "logs" / "ci" / "summary.json"
            rc = run_module.main([
                "--repo-root", str(root),
                "--delivery-profile", "fast-ship",
                "--write-doc",
                "--out-json", str(out_json),
            ])
            payload = json.loads(out_json.read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertEqual("artifact-manifest", payload["steps"][-1]["name"])
        self.assertTrue(payload["artifact_manifest_validation"].endswith("artifact-manifest-validation.json"))


if __name__ == "__main__":
    unittest.main()
