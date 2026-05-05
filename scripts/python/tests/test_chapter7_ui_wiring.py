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
    def _write_chapter7_profile(self, root: Path, payload: dict) -> Path:
        path = root / "docs" / "workflows" / "chapter7-profile.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        return path

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

    def _write_candidate_sidecar(self, root: Path) -> Path:
        sidecar = root / "docs" / "gdd" / "ui-gdd-flow.candidates.json"
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": "2026-04-23",
            "source_gdd": "docs/gdd/ui-gdd-flow.md",
            "completed_master_tasks_count": 40,
            "needed_wiring_features_count": 40,
            "candidates": [
                {
                    "bucket": "entry",
                    "screen_group": "MainMenu And Boot Flow",
                    "scope_task_ids": [1, 11, 21],
                    "scope_task_refs": "T01, T11, T21",
                    "ui_entry": "MainMenu / Boot Flow",
                    "candidate_type": "task-shaped UI wiring spec",
                    "player_action": "Launch or continue",
                    "system_response": "Show boot state",
                    "empty_state": "Show no active run state until runtime data is available.",
                    "failure_state": "Show startup failure explicitly.",
                    "completion_result": "Player reaches stable entry.",
                    "requirement_ids": ["RQ-ENTRY"],
                    "contract_refs": ["core.lastking.bootstrap.ready", "core.run.started"],
                    "validation_artifact_targets": ["logs/ci/<YYYY-MM-DD>/chapter7-ui-wiring/summary.json"],
                    "suggested_standalone_surfaces": ["MainMenu", "BootStatusPanel"],
                    "test_refs": ["Tests.Godot/tests/UI/test_main_menu.gd"],
                },
                {
                    "bucket": "loop",
                    "screen_group": "Runtime HUD And Outcome Surfaces",
                    "scope_task_ids": [3, 9],
                    "scope_task_refs": "T03, T09",
                    "ui_entry": "HUD / Prompt / Outcome Surfaces",
                    "candidate_type": "task-shaped UI wiring spec",
                    "player_action": "Play a run, observe timing, rewards, prompts, and terminal transitions",
                    "system_response": "Render readable phase, timer, HP, reward, prompt, and win/lose state from runtime events",
                    "empty_state": "Day/Night phase durations must be configuration-driven (not hardcoded): default Day=4:00 and Night=2:00; transition is allowed only when the active phase reaches its configured threshold, and transition cannot be manually forced before threshold.",
                    "failure_state": "Day/Night runtime updates must be driven by the Godot process loop (_Process and/or _PhysicsProcess) into GameStateManager.UpdateDayNightRuntime; when loop updates are paused or stopped, cycle progression must not advance.",
                    "completion_result": "Hard gate: deterministic cycle verification must include a fixed-seed forced-terminal scenario, not only natural Day15 completion paths.",
                    "contract_boundary": "keeps deterministic domain state behind existing contracts, adds no unrelated gameplay behavior",
                    "requirement_ids": ["RQ-HUD"],
                    "contract_refs": ["core.lastking.daynight.terminal", "core.lastking.time_scale.changed"],
                    "validation_artifact_targets": [
                        "logs/ci/<YYYY-MM-DD>/task-triplet-audit/report.json",
                        "logs/unit/<YYYY-MM-DD>/coverage.json",
                        "logs/e2e/<YYYY-MM-DD>/runtime-ui/summary.json",
                    ],
                    "suggested_standalone_surfaces": ["RuntimeHud"],
                    "test_refs": ["Tests.Godot/tests/UI/test_hud_scene.gd"],
                },
            ],
        }
        sidecar.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        return sidecar

    def _write_rich_sample_repo(self, root: Path) -> None:
        tasks_dir = root / ".taskmaster" / "tasks"
        tasks_dir.mkdir(parents=True)
        docs_dir = root / "docs" / "gdd"
        docs_dir.mkdir(parents=True)
        overlay_dir = root / "docs" / "architecture" / "overlays" / "PRD-lastking-T2" / "08"
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
                    "prd_id": "PRD-lastking-T2",
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
                    "PRD-ID: PRD-lastking-T2",
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
                    "PRD-ID: PRD-lastking-T2",
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
                    "PRD-ID: PRD-lastking-T2",
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

    def test_dev_cli_should_forward_parameterized_chapter7_inputs(self) -> None:
        builders = _load_module("dev_cli_builders_module_for_ch7_params", "scripts/python/dev_cli_builders.py")
        dev_cli = _load_module("dev_cli_module_for_ch7_params", "scripts/python/dev_cli.py")
        parser = dev_cli.build_parser()
        args = parser.parse_args(
            [
                "run-chapter7-ui-wiring",
                "--tasks-json-path", ".taskmaster/tasks/custom-tasks.json",
                "--tasks-back-path", ".taskmaster/tasks/custom-back.json",
                "--tasks-gameplay-path", ".taskmaster/tasks/custom-gameplay.json",
                "--overlay-root-path", "docs/architecture/overlays/PRD-custom/08",
                "--ui-gdd-flow-path", "docs/gdd/custom-ui-flow.md",
            ]
        )
        cmd = builders.build_run_chapter7_ui_wiring_cmd(args)

        self.assertIn("--tasks-json-path", cmd)
        self.assertIn(".taskmaster/tasks/custom-tasks.json", cmd)
        self.assertIn("--tasks-back-path", cmd)
        self.assertIn(".taskmaster/tasks/custom-back.json", cmd)
        self.assertIn("--tasks-gameplay-path", cmd)
        self.assertIn(".taskmaster/tasks/custom-gameplay.json", cmd)
        self.assertIn("--overlay-root-path", cmd)
        self.assertIn("docs/architecture/overlays/PRD-custom/08", cmd)
        self.assertIn("--ui-gdd-flow-path", cmd)
        self.assertIn("docs/gdd/custom-ui-flow.md", cmd)
        self.assertNotIn("--alignment-audit-path", cmd)
        self.assertNotIn("--wiring-audit-path", cmd)

    def test_dev_cli_should_forward_optional_audit_reference_paths(self) -> None:
        builders = _load_module("dev_cli_builders_module_for_ch7_audit_params", "scripts/python/dev_cli_builders.py")
        dev_cli = _load_module("dev_cli_module_for_ch7_audit_params", "scripts/python/dev_cli.py")
        parser = dev_cli.build_parser()
        args = parser.parse_args(
            [
                "run-chapter7-ui-wiring",
                "--alignment-audit-path", "docs/gdd/bmad-epic-task-alignment.md",
                "--wiring-audit-path", "docs/gdd/t1-t46-m1-wiring-audit.md",
            ]
        )
        cmd = builders.build_run_chapter7_ui_wiring_cmd(args)

        self.assertIn("--alignment-audit-path", cmd)
        self.assertIn("docs/gdd/bmad-epic-task-alignment.md", cmd)
        self.assertIn("--wiring-audit-path", cmd)
        self.assertIn("docs/gdd/t1-t46-m1-wiring-audit.md", cmd)

    def test_dev_cli_should_forward_optional_task_creation_identity_paths(self) -> None:
        builders = _load_module("dev_cli_builders_module_for_ch7_identity_params", "scripts/python/dev_cli_builders.py")
        dev_cli = _load_module("dev_cli_module_for_ch7_identity_params", "scripts/python/dev_cli.py")
        parser = dev_cli.build_parser()
        args = parser.parse_args(
            [
                "run-chapter7-ui-wiring",
                "--repo-label", "project-x",
                "--back-story-id", "BACKLOG-PROJECT-X-M2",
                "--gameplay-story-id", "PRD-PROJECT-X-v2.0",
            ]
        )
        cmd = builders.build_run_chapter7_ui_wiring_cmd(args)

        self.assertIn("--repo-label", cmd)
        self.assertIn("project-x", cmd)
        self.assertIn("--back-story-id", cmd)
        self.assertIn("BACKLOG-PROJECT-X-M2", cmd)
        self.assertIn("--gameplay-story-id", cmd)
        self.assertIn("PRD-PROJECT-X-v2.0", cmd)

    def test_dev_cli_should_forward_chapter7_profile_path(self) -> None:
        builders = _load_module("dev_cli_builders_module_for_ch7_profile", "scripts/python/dev_cli_builders.py")
        dev_cli = _load_module("dev_cli_module_for_ch7_profile", "scripts/python/dev_cli.py")
        parser = dev_cli.build_parser()
        args = parser.parse_args(
            [
                "run-chapter7-ui-wiring",
                "--chapter7-profile-path", "docs/workflows/chapter7-profile.json",
            ]
        )
        cmd = builders.build_run_chapter7_ui_wiring_cmd(args)

        self.assertIn("--chapter7-profile-path", cmd)
        self.assertIn("docs/workflows/chapter7-profile.json", cmd)

    def test_dev_cli_should_expose_chapter7_backlog_gap_orchestrator(self) -> None:
        builders = _load_module("dev_cli_builders_module_for_ch7_gap", "scripts/python/dev_cli_builders.py")
        dev_cli = _load_module("dev_cli_module_for_ch7_gap", "scripts/python/dev_cli.py")
        parser = dev_cli.build_parser()
        args = parser.parse_args(
            [
                "run-chapter7-backlog-gap",
                "--design-doc-path", "docs/design/m2-gdd.md",
                "--epics-doc-path", "docs/design/m2-epics.md",
                "--duplicate-audit-path", "logs/analysis/latest-gap-audit.md",
            ]
        )
        cmd = builders.build_run_chapter7_backlog_gap_cmd(args)

        self.assertEqual("run-chapter7-backlog-gap", args.cmd)
        self.assertIn("scripts/python/run_chapter7_backlog_gap.py", cmd)
        self.assertIn("--design-doc-path", cmd)
        self.assertIn("docs/design/m2-gdd.md", cmd)
        self.assertIn("--epics-doc-path", cmd)
        self.assertIn("docs/design/m2-epics.md", cmd)
        self.assertIn("--duplicate-audit-path", cmd)
        self.assertIn("logs/analysis/latest-gap-audit.md", cmd)

    def test_dev_cli_should_expose_apply_chapter7_status_patch(self) -> None:
        builders = _load_module("dev_cli_builders_module_for_ch7_apply", "scripts/python/dev_cli_builders.py")
        dev_cli = _load_module("dev_cli_module_for_ch7_apply", "scripts/python/dev_cli.py")
        parser = dev_cli.build_parser()
        args = parser.parse_args(
            [
                "apply-chapter7-status-patch",
                "--patch", "logs/ci/2026-04-27/chapter7-ui-wiring/task-status-patch.json",
                "--dry-run",
            ]
        )
        cmd = builders.build_apply_chapter7_status_patch_cmd(args)

        self.assertEqual("apply-chapter7-status-patch", args.cmd)
        self.assertIn("scripts/python/apply_chapter7_status_patch.py", cmd)
        self.assertIn("--patch", cmd)
        self.assertIn("--dry-run", cmd)

    def test_write_doc_should_generate_governed_gdd_with_newrouge_like_sections(self) -> None:
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
        self.assertIn("## 1. Design Goals", text)
        self.assertIn("## 8. Screen State Matrix", text)
        self.assertIn("## 9. Scope And Non-Goals", text)
        self.assertIn("## 12. Copy And Accessibility", text)
        self.assertIn("## 14. Task Alignment", text)
        self.assertEqual(0, rc)
        self.assertEqual([], payload["missing_done_task_refs"])


    def test_writer_should_prefer_readme_repository_identity_over_generic_solution_name(self) -> None:
        writer = _load_module("chapter7_ui_gdd_writer_module_for_repo_identity", "scripts/python/chapter7_ui_gdd_writer.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "GodotGame.sln").write_text("", encoding="utf-8")
            (root / "README.md").write_text("# samplegame (Godot 4.5.1 + C#)\n", encoding="utf-8")

            display = writer._repo_display_name(root)
            slug = writer._repo_gdd_slug(root)

        self.assertEqual("Samplegame", display)
        self.assertEqual("SAMPLEGAME", slug)

    def test_writer_and_validator_should_support_custom_ui_gdd_path(self) -> None:
        collector = _load_module("collect_ui_wiring_inputs_module_for_custom_writer", "scripts/python/collect_ui_wiring_inputs.py")
        writer = _load_module("chapter7_ui_gdd_writer_module_for_custom_writer", "scripts/python/chapter7_ui_gdd_writer.py")
        validator = _load_module("validate_chapter7_ui_wiring_module_for_custom_writer", "scripts/python/validate_chapter7_ui_wiring.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            summary = collector.build_summary(repo_root=root)
            out = writer.write_ui_gdd_flow(
                repo_root=root,
                summary=summary,
                ui_gdd_flow_path=Path("docs/gdd/project-ui-flow.md"),
                tasks_json_path=Path(".taskmaster/tasks/tasks.json"),
            )
            text = out.read_text(encoding="utf-8")
            rc, payload = validator.validate(
                repo_root=root,
                ui_gdd_flow_path=Path("docs/gdd/project-ui-flow.md"),
            )

        self.assertTrue(str(out).endswith("docs\\gdd\\project-ui-flow.md"))
        self.assertIn("## 5. UI Wiring Matrix", text)
        self.assertEqual(0, rc)
        self.assertEqual("docs/gdd/project-ui-flow.md", payload["target"])

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

    def test_self_check_should_include_write_doc_step_when_requested(self) -> None:
        run_module = _load_module("run_chapter7_ui_wiring_module_for_self_check", "scripts/python/run_chapter7_ui_wiring.py")
        output = io.StringIO()
        with redirect_stdout(output):
            rc = run_module.main(["--delivery-profile", "fast-ship", "--write-doc", "--self-check"])
        payload = json.loads(output.getvalue())

        self.assertEqual(0, rc)
        self.assertEqual(["collect", "write-doc", "validate"], payload["planned_steps"])

    def test_create_tasks_should_consume_only_ui_gdd_candidate_sidecar(self) -> None:
        module = _load_module("create_chapter7_tasks_module", "scripts/python/create_chapter7_tasks_from_ui_candidates.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_sample_repo(root, gdd_text="# stale doc without candidates\n")
            self._write_candidate_sidecar(root)
            rc, payload = module.create_tasks(repo_root=root, dry_run=False)

            tasks = json.loads((root / ".taskmaster" / "tasks" / "tasks.json").read_text(encoding="utf-8"))["master"]["tasks"]
            back = json.loads((root / ".taskmaster" / "tasks" / "tasks_back.json").read_text(encoding="utf-8"))
            gameplay = json.loads((root / ".taskmaster" / "tasks" / "tasks_gameplay.json").read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertEqual("ok", payload["status"])
        self.assertEqual(2, payload["created_count"])
        self.assertEqual([4, 5], payload["created_task_ids"])
        self.assertEqual("Wire UI: MainMenu And Boot Flow", tasks[-2]["title"])
        self.assertEqual("Wire UI: Runtime HUD And Outcome Surfaces", tasks[-1]["title"])
        self.assertEqual("pending", tasks[-1]["status"])
        self.assertIn(3, tasks[-1]["dependencies"])
        self.assertIn(9, tasks[-1]["dependencies"])
        self.assertIn("keeps deterministic domain state behind existing contracts", tasks[-1]["details"])
        self.assertIn("adds no unrelated gameplay behavior", tasks[-1]["details"])
        self.assertEqual("NG-0004", back[-2]["id"])
        self.assertEqual(4, back[-2]["taskmaster_id"])
        self.assertEqual("GM-0104", gameplay[-2]["id"])
        self.assertEqual(4, gameplay[-2]["taskmaster_id"])
        self.assertIn("Tests.Godot/tests/UI/test_hud_scene.gd", gameplay[-1]["test_refs"])
        self.assertIn("Refs: Tests.Godot/tests/UI/test_hud_scene.gd", gameplay[-1]["acceptance"][0])
        runtime_acceptance = " ".join(gameplay[-1]["acceptance"])
        self.assertIn("timing, rewards, prompts, and terminal transitions", runtime_acceptance)
        self.assertIn("phase, timer, HP, reward, prompt, and win/lose state", runtime_acceptance)
        self.assertIn("default Day=4:00 and Night=2:00", runtime_acceptance)
        self.assertIn("active phase reaches its configured threshold", runtime_acceptance)
        self.assertIn("cannot be manually forced before threshold", runtime_acceptance)
        self.assertIn("GameStateManager.UpdateDayNightRuntime", runtime_acceptance)
        self.assertIn("paused or stopped", runtime_acceptance)
        self.assertIn("state remains unchanged", runtime_acceptance)
        self.assertIn("cycle progression must not advance", runtime_acceptance)
        self.assertIn("fixed-seed forced-terminal scenario", runtime_acceptance)
        self.assertIn("logs/ci/<YYYY-MM-DD>/task-triplet-audit/report.json", runtime_acceptance)
        self.assertIn("logs/unit/<YYYY-MM-DD>/coverage.json", runtime_acceptance)
        self.assertIn("logs/e2e/<YYYY-MM-DD>/runtime-ui/summary.json", runtime_acceptance)

    def test_create_tasks_should_support_custom_candidate_sidecar_path(self) -> None:
        module = _load_module("create_chapter7_tasks_module_for_custom_sidecar", "scripts/python/create_chapter7_tasks_from_ui_candidates.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_sample_repo(root, gdd_text="# stale doc without candidates\n")
            source_sidecar = self._write_candidate_sidecar(root)
            custom_sidecar = root / "docs" / "gdd" / "project-ui-flow.candidates.json"
            custom_sidecar.write_text(source_sidecar.read_text(encoding="utf-8"), encoding="utf-8")
            rc, payload = module.create_tasks(
                repo_root=root,
                dry_run=False,
                ui_candidates_path=Path("docs/gdd/project-ui-flow.candidates.json"),
            )

        self.assertEqual(0, rc)
        self.assertEqual("docs/gdd/project-ui-flow.candidates.json", payload["source"])

    def test_create_tasks_should_support_parameterized_overlay_and_story_identity(self) -> None:
        module = _load_module("create_chapter7_tasks_module_for_identity", "scripts/python/create_chapter7_tasks_from_ui_candidates.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_sample_repo(root, gdd_text="# stale doc without candidates\n")
            source_sidecar = self._write_candidate_sidecar(root)
            custom_sidecar = root / "docs" / "design" / "m2-ui-flow.candidates.json"
            custom_sidecar.parent.mkdir(parents=True, exist_ok=True)
            custom_sidecar.write_text(source_sidecar.read_text(encoding="utf-8"), encoding="utf-8")
            rc, payload = module.create_tasks(
                repo_root=root,
                dry_run=False,
                ui_candidates_path=Path("docs/design/m2-ui-flow.candidates.json"),
                overlay_root_path=Path("docs/architecture/overlays/PRD-project-x-M2/08"),
                repo_label="project-x",
                back_story_id="BACKLOG-PROJECT-X-M2",
                gameplay_story_id="PRD-PROJECT-X-v2.0",
            )
            tasks = json.loads((root / ".taskmaster" / "tasks" / "tasks.json").read_text(encoding="utf-8"))["master"]["tasks"]
            back = json.loads((root / ".taskmaster" / "tasks" / "tasks_back.json").read_text(encoding="utf-8"))
            gameplay = json.loads((root / ".taskmaster" / "tasks" / "tasks_gameplay.json").read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertEqual("project-x", payload["repo_label"])
        self.assertEqual("BACKLOG-PROJECT-X-M2", payload["back_story_id"])
        self.assertEqual("PRD-PROJECT-X-v2.0", payload["gameplay_story_id"])
        self.assertEqual("docs/architecture/overlays/PRD-project-x-M2/08", payload["overlay_root"])
        self.assertEqual("docs/design/m2-ui-flow.candidates.json", payload["source"])
        self.assertEqual("docs/architecture/overlays/PRD-project-x-M2/08/_index.md", tasks[-1]["overlay"])
        self.assertEqual("BACKLOG-PROJECT-X-M2", back[-1]["story_id"])
        self.assertEqual("PRD-PROJECT-X-v2.0", gameplay[-1]["story_id"])
        self.assertIn("project-x", back[-1]["labels"])
        self.assertEqual("docs/design/m2-ui-flow.candidates.json", gameplay[-1]["ui_wiring_candidate"]["source"])
        self.assertEqual(
            "docs/architecture/overlays/PRD-project-x-M2/08/_index.md",
            gameplay[-1]["overlay_refs"][0],
        )

    def test_create_tasks_should_allow_profile_override_for_ids_labels_and_refs(self) -> None:
        module = _load_module("create_chapter7_tasks_module_for_profile_override", "scripts/python/create_chapter7_tasks_from_ui_candidates.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_sample_repo(root, gdd_text="# stale doc without candidates\n")
            self._write_candidate_sidecar(root)
            profile_path = self._write_chapter7_profile(
                root,
                {
                    "task_creation": {
                        "adr_refs": ["ADR-9001"],
                        "chapter_refs": ["CH77"],
                        "base_labels": ["custom-view", "ui-slice"],
                        "owners": {"NG": "design", "GM": "implementation"},
                        "source_labels": {"NG": "plan", "GM": "delivery"},
                        "view_id_templates": {"NG": "BK-{task_id:04d}", "GM": "GP-{task_id_plus_1000:04d}"},
                        "default_story_templates": {
                            "back": "BACK-{repo_label_upper_underscore}-ALT",
                            "gameplay": "GAME-{repo_label_upper_underscore}-ALT",
                        },
                    }
                },
            )
            rc, payload = module.create_tasks(
                repo_root=root,
                dry_run=False,
                chapter7_profile_path=profile_path,
                repo_label="project-x",
            )
            tasks = json.loads((root / ".taskmaster" / "tasks" / "tasks.json").read_text(encoding="utf-8"))["master"]["tasks"]
            back = json.loads((root / ".taskmaster" / "tasks" / "tasks_back.json").read_text(encoding="utf-8"))
            gameplay = json.loads((root / ".taskmaster" / "tasks" / "tasks_gameplay.json").read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertTrue(payload["chapter7_profile_path"].endswith("/docs/workflows/chapter7-profile.json"))
        self.assertEqual(["ADR-9001"], tasks[-1]["adrRefs"])
        self.assertEqual(["CH77"], tasks[-1]["archRefs"])
        self.assertEqual("BK-0005", back[-1]["id"])
        self.assertEqual("GP-1005", gameplay[-1]["id"])
        self.assertEqual("design", back[-1]["owner"])
        self.assertEqual("implementation", gameplay[-1]["owner"])
        self.assertEqual("BACK-PROJECT_X-ALT", back[-1]["story_id"])
        self.assertEqual("GAME-PROJECT_X-ALT", gameplay[-1]["story_id"])
        self.assertIn("plan", back[-1]["labels"])
        self.assertIn("delivery", gameplay[-1]["labels"])
        self.assertIn("custom-view", gameplay[-1]["labels"])
        self.assertIn("ui-slice", gameplay[-1]["labels"])

    def test_create_tasks_should_be_idempotent_for_same_candidate_sidecar(self) -> None:
        module = _load_module("create_chapter7_tasks_module_for_idempotency", "scripts/python/create_chapter7_tasks_from_ui_candidates.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_sample_repo(root, gdd_text="# stale doc without candidates\n")
            self._write_candidate_sidecar(root)
            first_rc, first_payload = module.create_tasks(repo_root=root, dry_run=False)
            second_rc, second_payload = module.create_tasks(repo_root=root, dry_run=False)
            tasks = json.loads((root / ".taskmaster" / "tasks" / "tasks.json").read_text(encoding="utf-8"))["master"]["tasks"]

        self.assertEqual(0, first_rc)
        self.assertEqual(0, second_rc)
        self.assertEqual(2, first_payload["created_count"])
        self.assertEqual(0, second_payload["created_count"])
        self.assertEqual([4, 5], second_payload["existing_task_ids"])
        self.assertEqual(5, len(tasks))

    def test_create_tasks_should_refresh_existing_chapter7_tasks_from_candidate_sidecar(self) -> None:
        module = _load_module("create_chapter7_tasks_module_for_refresh", "scripts/python/create_chapter7_tasks_from_ui_candidates.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_sample_repo(root, gdd_text="# stale doc without candidates\n")
            self._write_candidate_sidecar(root)
            first_rc, _ = module.create_tasks(repo_root=root, dry_run=False)

            sidecar = root / "docs" / "gdd" / "ui-gdd-flow.candidates.json"
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
            runtime = next(item for item in payload["candidates"] if item["screen_group"] == "Runtime HUD And Outcome Surfaces")
            runtime["system_response"] = "Render readable phase, timer, HP, reward, prompt, and win/lose state from runtime events"
            runtime["validation_artifact_targets"].append("logs/unit/<YYYY-MM-DD>/coverage.json")
            sidecar.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            second_rc, second_payload = module.create_tasks(repo_root=root, dry_run=False)
            back = json.loads((root / ".taskmaster" / "tasks" / "tasks_back.json").read_text(encoding="utf-8"))
            runtime_task = next(item for item in back if item["taskmaster_id"] == 5)
            runtime_acceptance = " ".join(runtime_task["acceptance"])

        self.assertEqual(0, first_rc)
        self.assertEqual(0, second_rc)
        self.assertEqual(0, second_payload["created_count"])
        self.assertEqual([4, 5], second_payload["updated_task_ids"])
        self.assertIn("phase, timer, HP, reward, prompt, and win/lose state", runtime_acceptance)
        self.assertIn("logs/unit/<YYYY-MM-DD>/coverage.json", runtime_acceptance)

    def test_create_tasks_should_write_contract_refs_from_candidate_events_not_requirements(self) -> None:
        module = _load_module("create_chapter7_tasks_module_for_contract_refs", "scripts/python/create_chapter7_tasks_from_ui_candidates.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_sample_repo(root, gdd_text="# stale doc without candidates\n")
            self._write_candidate_sidecar(root)
            rc, _ = module.create_tasks(repo_root=root, dry_run=False)
            back = json.loads((root / ".taskmaster" / "tasks" / "tasks_back.json").read_text(encoding="utf-8"))
            entry_task = next(item for item in back if item["taskmaster_id"] == 4)

        self.assertEqual(0, rc)
        self.assertEqual(["core.lastking.bootstrap.ready", "core.run.started"], entry_task["contractRefs"])
        self.assertNotIn("RQ-ENTRY", entry_task["contractRefs"])

    def test_orchestrator_self_check_should_include_create_tasks_step_when_requested(self) -> None:
        run_module = _load_module("run_chapter7_ui_wiring_module_for_create_tasks_self_check", "scripts/python/run_chapter7_ui_wiring.py")
        output = io.StringIO()
        with redirect_stdout(output):
            rc = run_module.main(["--delivery-profile", "fast-ship", "--write-doc", "--create-tasks", "--self-check"])
        payload = json.loads(output.getvalue())

        self.assertEqual(0, rc)
        self.assertEqual(["collect", "write-doc", "validate", "create-tasks"], payload["planned_steps"])


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
        self.assertIn("closure-summary", by_type)
        self.assertEqual("non-idempotent-summary", by_type["summary"]["sha256"])

    def test_orchestrator_should_export_closure_summary_with_slice_status(self) -> None:
        run_module = _load_module("run_chapter7_ui_wiring_module_for_closure_summary", "scripts/python/run_chapter7_ui_wiring.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            tasks_json_path = root / ".taskmaster" / "tasks" / "tasks.json"
            tasks_json_payload = json.loads(tasks_json_path.read_text(encoding="utf-8"))
            tasks_json_payload["master"]["tasks"].append(
                {"id": 41, "title": "Wire UI: MainMenu And Boot Flow", "status": "done", "adrRefs": ["ADR-0041"]}
            )
            tasks_json_path.write_text(json.dumps(tasks_json_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            tasks_back_path = root / ".taskmaster" / "tasks" / "tasks_back.json"
            tasks_back_payload = json.loads(tasks_back_path.read_text(encoding="utf-8"))
            tasks_back_payload.append(
                {"id": "NG-0041", "taskmaster_id": 41, "story_id": "BACKLOG-LASTKING-M1", "title": "Wire UI: MainMenu And Boot Flow", "status": "done"}
            )
            tasks_back_path.write_text(json.dumps(tasks_back_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            tasks_gameplay_path = root / ".taskmaster" / "tasks" / "tasks_gameplay.json"
            tasks_gameplay_payload = json.loads(tasks_gameplay_path.read_text(encoding="utf-8"))
            tasks_gameplay_payload.append(
                {"id": "GM-0041", "taskmaster_id": 41, "story_id": "PRD-LASTKING-v1.2", "title": "Wire UI: MainMenu And Boot Flow", "status": "done"}
            )
            tasks_gameplay_path.write_text(json.dumps(tasks_gameplay_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            alignment = root / "docs" / "gdd" / "bmad-epic-task-alignment.md"
            wiring = root / "docs" / "gdd" / "t1-t46-m1-wiring-audit.md"
            alignment.write_text("# alignment\n", encoding="utf-8", newline="\n")
            wiring.write_text(
                "### 6.1.1 MainMenu And Boot Flow（主菜单与启动流程）\n"
                "| Task | Title | Primary Surface/Code | Primary Test/Evidence | Governance Path | Evidence Status | Gap To Close |\n"
                "| --- | --- | --- | --- | --- | --- | --- |\n"
                "| T21 | Lock Windows export profile and Steam runtime startup validation | MainMenu | startup.gd | docs | test-only | Need a governed boot/export status surface. |\n"
                "| T41 | Wire UI: MainMenu And Boot Flow | MainMenu | menu.gd | docs | partial | Need to materialize BootStatusPanel and ContinueGateDialog as stable owned surfaces with direct runtime evidence. |\n"
                "### 6.1.2 Runtime HUD And Outcome（运行时 HUD 与结果）\n"
                "| Task | Title | Primary Surface/Code | Primary Test/Evidence | Governance Path | Evidence Status | Gap To Close |\n"
                "| --- | --- | --- | --- | --- | --- | --- |\n"
                "| T23 | Develop Runtime Speed Controls (Pause, 1x, 2x) with Timer Freeze | HUD | hud.gd | docs | docs-only | Need explicit speed-control widgets and direct runtime evidence that pause and timer freeze are visible and owned by the HUD slice. |\n"
                "| T24 | Create UI Feedback System for Invalid Actions and Errors | HUD | hud.gd | docs | docs-only | Need a concrete prompt/error surface with runtime-triggered messages and direct validation coverage. |\n"
                "| T42 | Wire UI: Runtime HUD And Outcome Surfaces | HUD | hud.gd | docs | partial | Need OutcomePanel and RuntimePromptPanel to exist as stable surfaces with direct runtime assertions. |\n",
                encoding="utf-8",
                newline="\n",
            )
            out_json = root / "logs" / "ci" / "summary.json"
            rc = run_module.main(
                [
                    "--repo-root", str(root),
                    "--delivery-profile", "fast-ship",
                    "--write-doc",
                    "--alignment-audit-path", "docs/gdd/bmad-epic-task-alignment.md",
                    "--wiring-audit-path", "docs/gdd/t1-t46-m1-wiring-audit.md",
                    "--out-json", str(out_json),
                ]
            )
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            closure = json.loads(Path(payload["closure_summary"]).read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertIn("closure_summary", payload)
        self.assertEqual(6, closure["slice_count"])
        self.assertIn("closure_summary_meta", payload)
        entry = next(item for item in closure["slices"] if item["bucket"] == "entry")
        self.assertEqual("partial", entry["evidence_status"])
        self.assertIn("MainMenu", entry["surface_status"]["implemented_surfaces"])
        self.assertIn("BootStatusPanel", entry["surface_status"]["pending_surfaces"])
        self.assertEqual("partial-closure", entry["write_back_recommendation"])
        self.assertEqual("T41", entry["write_back_contract"]["task_ref"])
        self.assertFalse(entry["write_back_contract"]["ready_for_done"])
        self.assertIn("BootStatusPanel", entry["write_back_contract"]["missing_surface_owners"])
        self.assertIn("MainMenu", [item["surface"] for item in entry["standalone_surface_status"]])
        self.assertIn("startup.gd", entry["evidence_paths"]["primary_test_evidence"])
        loop = next(item for item in closure["slices"] if item["bucket"] == "loop")
        self.assertEqual("docs-only", loop["evidence_status"])
        self.assertFalse(loop["epic_usable"])
        self.assertEqual("keep-open", loop["write_back_recommendation"])
        self.assertEqual("T42", loop["write_back_contract"]["task_ref"])
        self.assertEqual("docs-only", loop["write_back_contract"]["must_keep_open_reasons"][-1].split("=")[-1])
        self.assertEqual(0, closure["done_ready_count"])

    def test_orchestrator_should_allow_profile_override_for_closure_task_mapping(self) -> None:
        run_module = _load_module("run_chapter7_ui_wiring_module_for_profile_closure", "scripts/python/run_chapter7_ui_wiring.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            self._write_chapter7_profile(
                root,
                {
                    "buckets": {
                        "entry": {
                            "section_headings": ["### Custom Entry Flow"],
                            "closure_task_ids": [61],
                            "wiring_task_id": 61
                        }
                    }
                },
            )
            tasks_json_path = root / ".taskmaster" / "tasks" / "tasks.json"
            tasks_json_payload = json.loads(tasks_json_path.read_text(encoding="utf-8"))
            tasks_json_payload["master"]["tasks"].append(
                {"id": 61, "title": "Wire UI: MainMenu And Boot Flow", "status": "done", "adrRefs": ["ADR-0061"]}
            )
            tasks_json_path.write_text(json.dumps(tasks_json_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (root / ".taskmaster" / "tasks" / "tasks_back.json").write_text(
                json.dumps(
                    json.loads((root / ".taskmaster" / "tasks" / "tasks_back.json").read_text(encoding="utf-8"))
                    + [{"id": "NG-0061", "taskmaster_id": 61, "story_id": "BACKLOG-LASTKING-M1", "title": "Wire UI: MainMenu And Boot Flow", "status": "done"}],
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
            (root / ".taskmaster" / "tasks" / "tasks_gameplay.json").write_text(
                json.dumps(
                    json.loads((root / ".taskmaster" / "tasks" / "tasks_gameplay.json").read_text(encoding="utf-8"))
                    + [{"id": "GM-0061", "taskmaster_id": 61, "story_id": "PRD-LASTKING-v1.2", "title": "Wire UI: MainMenu And Boot Flow", "status": "done"}],
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
            wiring = root / "docs" / "gdd" / "custom-wiring-audit.md"
            wiring.write_text(
                "### Custom Entry Flow\n"
                "| Task | Title | Primary Surface/Code | Primary Test/Evidence | Governance Path | Evidence Status | Gap To Close |\n"
                "| --- | --- | --- | --- | --- | --- | --- |\n"
                "| T61 | Wire UI: MainMenu And Boot Flow | MainMenu | menu.gd | docs | partial | Need to materialize BootStatusPanel as a stable surface. |\n",
                encoding="utf-8",
                newline="\n",
            )
            out_json = root / "logs" / "ci" / "summary.json"
            rc = run_module.main(
                [
                    "--repo-root", str(root),
                    "--write-doc",
                    "--chapter7-profile-path", "docs/workflows/chapter7-profile.json",
                    "--wiring-audit-path", "docs/gdd/custom-wiring-audit.md",
                    "--out-json", str(out_json),
                ]
            )
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            closure = json.loads(Path(payload["closure_summary"]).read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertTrue(payload["input_contract"]["chapter7_profile_path"].endswith("/docs/workflows/chapter7-profile.json"))
        entry = next(item for item in closure["slices"] if item["bucket"] == "entry")
        self.assertEqual("T61", entry["write_back_contract"]["task_ref"])

    def test_orchestrator_should_export_task_status_patch_preview_when_done_status_conflicts_with_closure(self) -> None:
        run_module = _load_module("run_chapter7_ui_wiring_module_for_status_patch_preview", "scripts/python/run_chapter7_ui_wiring.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            tasks_json_path = root / ".taskmaster" / "tasks" / "tasks.json"
            tasks_json_payload = json.loads(tasks_json_path.read_text(encoding="utf-8"))
            tasks_json_payload["master"]["tasks"].append(
                {"id": 41, "title": "Wire UI: MainMenu And Boot Flow", "status": "done", "adrRefs": ["ADR-0041"]}
            )
            tasks_json_path.write_text(json.dumps(tasks_json_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            tasks_back_path = root / ".taskmaster" / "tasks" / "tasks_back.json"
            tasks_back_payload = json.loads(tasks_back_path.read_text(encoding="utf-8"))
            tasks_back_payload.append(
                {"id": "NG-0041", "taskmaster_id": 41, "story_id": "BACKLOG-LASTKING-M1", "title": "Wire UI: MainMenu And Boot Flow", "status": "done"}
            )
            tasks_back_path.write_text(json.dumps(tasks_back_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            tasks_gameplay_path = root / ".taskmaster" / "tasks" / "tasks_gameplay.json"
            tasks_gameplay_payload = json.loads(tasks_gameplay_path.read_text(encoding="utf-8"))
            tasks_gameplay_payload.append(
                {"id": "GM-0041", "taskmaster_id": 41, "story_id": "PRD-LASTKING-v1.2", "title": "Wire UI: MainMenu And Boot Flow", "status": "done"}
            )
            tasks_gameplay_path.write_text(json.dumps(tasks_gameplay_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            alignment = root / "docs" / "gdd" / "bmad-epic-task-alignment.md"
            wiring = root / "docs" / "gdd" / "t1-t46-m1-wiring-audit.md"
            alignment.write_text("# alignment\n", encoding="utf-8", newline="\n")
            wiring.write_text(
                "### 6.1.1 MainMenu And Boot Flow（主菜单与启动流程）\n"
                "| Task | Title | Primary Surface/Code | Primary Test/Evidence | Governance Path | Evidence Status | Gap To Close |\n"
                "| --- | --- | --- | --- | --- | --- | --- |\n"
                "| T21 | Lock Windows export profile and Steam runtime startup validation | MainMenu | startup.gd | docs | test-only | Need a governed boot/export status surface. |\n"
                "| T41 | Wire UI: MainMenu And Boot Flow | MainMenu | menu.gd | docs | partial | Need to materialize BootStatusPanel and ContinueGateDialog as stable owned surfaces with direct runtime evidence. |\n",
                encoding="utf-8",
                newline="\n",
            )
            out_json = root / "logs" / "ci" / "summary.json"
            rc = run_module.main(
                [
                    "--repo-root", str(root),
                    "--delivery-profile", "fast-ship",
                    "--write-doc",
                    "--alignment-audit-path", "docs/gdd/bmad-epic-task-alignment.md",
                    "--wiring-audit-path", "docs/gdd/t1-t46-m1-wiring-audit.md",
                    "--out-json", str(out_json),
                ]
            )
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            patch_preview = json.loads(Path(payload["task_status_patch_preview"]).read_text(encoding="utf-8"))
            patch_preview_md = Path(payload["task_status_patch_preview_md"]).read_text(encoding="utf-8")
            patch_contract = json.loads(Path(payload["task_status_patch"]).read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertIn("task_status_patch_preview", payload)
        self.assertIn("task_status_patch_preview_md", payload)
        self.assertIn("task_status_patch", payload)
        self.assertGreaterEqual(patch_preview["mismatch_count"], 1)
        first = patch_preview["mismatches"][0]
        self.assertEqual("T41", first["task_ref"])
        self.assertEqual("done", first["current_status"])
        self.assertEqual("review", first["recommended_status"])
        self.assertEqual("partial-closure", first["write_back_recommendation"])
        self.assertIn("# Chapter 7 Task Status Patch Preview", patch_preview_md)
        self.assertIn("## ", patch_preview_md)
        self.assertIn("`review`", patch_preview_md)
        self.assertEqual("chapter7-task-status-patch", patch_contract["contract_type"])
        self.assertGreaterEqual(patch_contract["operation_count"], 1)
        self.assertEqual("replace-task-status", patch_contract["operations"][0]["op"])

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
            ["input-snapshot", "closure-summary", "task-status-patch-preview", "task-status-patch-preview-md", "task-status-patch", "ui-gdd", "candidate-sidecar", "summary"],
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
        self.assertEqual(8, ok_payload["artifact_count"])
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

    def test_orchestrator_should_record_optional_audit_references(self) -> None:
        run_module = _load_module("run_chapter7_ui_wiring_module_for_audit_refs", "scripts/python/run_chapter7_ui_wiring.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            alignment = root / "docs" / "gdd" / "bmad-epic-task-alignment.md"
            wiring = root / "docs" / "gdd" / "t1-t46-m1-wiring-audit.md"
            alignment.write_text("# alignment\n", encoding="utf-8", newline="\n")
            wiring.write_text("# wiring\n", encoding="utf-8", newline="\n")
            out_json = root / "logs" / "ci" / "summary.json"
            rc = run_module.main(
                [
                    "--repo-root", str(root),
                    "--delivery-profile", "fast-ship",
                    "--write-doc",
                    "--alignment-audit-path", "docs/gdd/bmad-epic-task-alignment.md",
                    "--wiring-audit-path", "docs/gdd/t1-t46-m1-wiring-audit.md",
                    "--out-json", str(out_json),
                ]
            )
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            snapshot = json.loads(Path(payload["input_snapshot"]).read_text(encoding="utf-8"))
            manifest = json.loads(Path(payload["artifact_manifest"]).read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertIn("alignment_audit", payload)
        self.assertIn("wiring_audit", payload)
        self.assertIn("audit_references", payload)
        self.assertEqual(2, len(payload["audit_references"]))
        self.assertIn("audit_references", snapshot)
        by_type = {item["artifact_type"]: item for item in manifest["artifacts"]}
        self.assertIn("alignment-audit-reference", by_type)
        self.assertIn("wiring-audit-reference", by_type)

    def test_orchestrator_should_export_input_contract_paths(self) -> None:
        run_module = _load_module("run_chapter7_ui_wiring_module_for_input_contract", "scripts/python/run_chapter7_ui_wiring.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_rich_sample_repo(root)
            alignment = root / "docs" / "gdd" / "bmad-epic-task-alignment.md"
            wiring = root / "docs" / "gdd" / "t1-t46-m1-wiring-audit.md"
            alignment.write_text("# alignment\n", encoding="utf-8", newline="\n")
            wiring.write_text("# wiring\n", encoding="utf-8", newline="\n")
            out_json = root / "logs" / "ci" / "summary.json"
            rc = run_module.main(
                [
                    "--repo-root", str(root),
                    "--delivery-profile", "fast-ship",
                    "--tasks-json-path", ".taskmaster/tasks/tasks.json",
                    "--tasks-back-path", ".taskmaster/tasks/tasks_back.json",
                    "--tasks-gameplay-path", ".taskmaster/tasks/tasks_gameplay.json",
                    "--overlay-root-path", "docs/architecture/overlays/PRD-lastking-T2/08",
                    "--ui-gdd-flow-path", "docs/gdd/ui-gdd-flow.md",
                    "--alignment-audit-path", "docs/gdd/bmad-epic-task-alignment.md",
                    "--wiring-audit-path", "docs/gdd/t1-t46-m1-wiring-audit.md",
                    "--write-doc",
                    "--out-json", str(out_json),
                ]
            )
            payload = json.loads(out_json.read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertIn("input_contract", payload)
        contract = payload["input_contract"]
        self.assertTrue(contract["repo_root"].endswith(root.as_posix()))
        self.assertTrue(contract["tasks_json_path"].endswith("/.taskmaster/tasks/tasks.json"))
        self.assertTrue(contract["tasks_back_path"].endswith("/.taskmaster/tasks/tasks_back.json"))
        self.assertTrue(contract["tasks_gameplay_path"].endswith("/.taskmaster/tasks/tasks_gameplay.json"))
        self.assertTrue(contract["overlay_root_path"].endswith("/docs/architecture/overlays/PRD-lastking-T2/08"))
        self.assertTrue(contract["ui_gdd_flow_path"].endswith("/docs/gdd/ui-gdd-flow.md"))
        self.assertTrue(contract["ui_candidates_path"].endswith("/docs/gdd/ui-gdd-flow.candidates.json"))
        self.assertTrue(contract["alignment_audit_path"].endswith("/docs/gdd/bmad-epic-task-alignment.md"))
        self.assertTrue(contract["wiring_audit_path"].endswith("/docs/gdd/t1-t46-m1-wiring-audit.md"))

    def test_orchestrator_self_check_should_include_parameterized_task_creation_identity(self) -> None:
        run_module = _load_module("run_chapter7_ui_wiring_module_for_identity_self_check", "scripts/python/run_chapter7_ui_wiring.py")
        output = io.StringIO()
        with redirect_stdout(output):
            rc = run_module.main(
                [
                    "--delivery-profile", "fast-ship",
                    "--create-tasks",
                    "--repo-label", "project-x",
                    "--back-story-id", "BACKLOG-PROJECT-X-M2",
                    "--gameplay-story-id", "PRD-PROJECT-X-v2.0",
                    "--self-check",
                ]
            )
        payload = json.loads(output.getvalue())

        self.assertEqual(0, rc)
        self.assertEqual("project-x", payload["repo_label"])
        self.assertEqual("BACKLOG-PROJECT-X-M2", payload["back_story_id"])
        self.assertEqual("PRD-PROJECT-X-v2.0", payload["gameplay_story_id"])

    def test_orchestrator_self_check_should_include_chapter7_profile_path(self) -> None:
        run_module = _load_module("run_chapter7_ui_wiring_module_for_profile_self_check", "scripts/python/run_chapter7_ui_wiring.py")
        output = io.StringIO()
        with redirect_stdout(output):
            rc = run_module.main(
                [
                    "--delivery-profile", "fast-ship",
                    "--chapter7-profile-path", "docs/workflows/chapter7-profile.json",
                    "--self-check",
                ]
            )
        payload = json.loads(output.getvalue())

        self.assertEqual(0, rc)
        self.assertEqual("docs/workflows/chapter7-profile.json", payload["chapter7_profile_path"])

    def test_chapter7_backlog_gap_self_check_should_export_input_contract(self) -> None:
        run_module = _load_module("run_chapter7_backlog_gap_module_for_self_check", "scripts/python/run_chapter7_backlog_gap.py")
        output = io.StringIO()
        with redirect_stdout(output):
            rc = run_module.main(
                [
                    "--repo-root", str(REPO_ROOT),
                    "--delivery-profile", "fast-ship",
                    "--design-doc-path", "_bmad-output/gdd.md",
                    "--epics-doc-path", "_bmad-output/epics.md",
                    "--duplicate-audit-path", "logs/analysis/2026-04-27/t1-t40-duplicate-audit.md",
                    "--self-check",
                ]
            )
        payload = json.loads(output.getvalue())

        self.assertEqual(0, rc)
        self.assertEqual("run-chapter7-backlog-gap", payload["action"])
        self.assertEqual(
            ["load-inputs", "score-stories", "score-gap-signals", "emit-summary"],
            payload["planned_steps"],
        )
        self.assertTrue(payload["input_contract"]["design_doc_path"].endswith("/_bmad-output/gdd.md"))
        self.assertTrue(payload["input_contract"]["epics_doc_path"].endswith("/_bmad-output/epics.md"))
        self.assertTrue(
            payload["input_contract"]["duplicate_audit_path"].endswith("/logs/analysis/2026-04-27/t1-t40-duplicate-audit.md")
        )

    def test_chapter7_backlog_gap_should_bucket_epic_stories_against_existing_tasks(self) -> None:
        run_module = _load_module("run_chapter7_backlog_gap_module_for_bucketing", "scripts/python/run_chapter7_backlog_gap.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_sample_repo(root, gdd_text="# stale doc without candidates\n")
            design = root / "docs" / "design" / "m2-gdd.md"
            design.parent.mkdir(parents=True, exist_ok=True)
            design.write_text(
                "# M2 GDD\n\nCurrent M2 still needs a governed achievements readout surface for players.\n",
                encoding="utf-8",
                newline="\n",
            )
            epics = root / "docs" / "design" / "m2-epics.md"
            epics.write_text(
                "## Epic 1: Runtime\n- As a player, I can launch the game and reach the main menu so that the product feels like a real runnable build.\n",
                encoding="utf-8",
                newline="\n",
            )
            duplicate = root / "logs" / "analysis" / "latest-gap-audit.md"
            duplicate.parent.mkdir(parents=True, exist_ok=True)
            duplicate.write_text(
                "# T1-T40 Duplicate Audit\n\n## High-overlap clusters\n### Cluster A: Foundation / bootstrap / export baseline\n",
                encoding="utf-8",
                newline="\n",
            )
            out_json = root / "logs" / "ci" / "gap-summary.json"
            rc = run_module.main(
                [
                    "--repo-root", str(root),
                    "--design-doc-path", "docs/design/m2-gdd.md",
                    "--epics-doc-path", "docs/design/m2-epics.md",
                    "--duplicate-audit-path", "logs/analysis/latest-gap-audit.md",
                    "--out-json", str(out_json),
                ]
            )
            payload = json.loads(out_json.read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertEqual("ok", payload["status"])
        self.assertEqual(1, payload["story_count"])
        self.assertIn("duplicate_risk_clusters", payload)
        self.assertIn("Cluster A: Foundation / bootstrap / export baseline", payload["duplicate_risk_clusters"])
        self.assertEqual("covered-by-t1-t40", payload["story_mappings"][0]["bucket"])
        self.assertIn("candidate_task_gaps", payload)
        self.assertEqual("review-candidate-gaps", payload["recommendation"]["next_action"])

    def test_apply_chapter7_status_patch_self_check_should_describe_plan(self) -> None:
        run_module = _load_module("apply_chapter7_status_patch_module_for_self_check", "scripts/python/apply_chapter7_status_patch.py")
        output = io.StringIO()
        with redirect_stdout(output):
            rc = run_module.main(
                [
                    "--patch", "logs/ci/2026-04-27/chapter7-ui-wiring/task-status-patch.json",
                    "--dry-run",
                    "--self-check",
                ]
            )
        payload = json.loads(output.getvalue())

        self.assertEqual(0, rc)
        self.assertEqual("apply-chapter7-status-patch", payload["action"])
        self.assertEqual(["load-patch", "apply-operations", "emit-summary"], payload["planned_steps"])
        self.assertTrue(payload["dry_run"])

    def test_apply_chapter7_status_patch_should_support_dry_run_without_writing(self) -> None:
        run_module = _load_module("apply_chapter7_status_patch_module_for_dry_run", "scripts/python/apply_chapter7_status_patch.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tasks_dir = root / ".taskmaster" / "tasks"
            tasks_dir.mkdir(parents=True)
            tasks_json = tasks_dir / "tasks.json"
            tasks_json.write_text(
                json.dumps({"master": {"tasks": [{"id": 41, "title": "Wire UI: MainMenu And Boot Flow", "status": "done"}]}}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            patch = root / "task-status-patch.json"
            patch.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "contract_type": "chapter7-task-status-patch",
                        "status": "ok",
                        "operation_count": 1,
                        "operations": [
                            {
                                "op": "replace-task-status",
                                "path": str(tasks_json.resolve()).replace("\\", "/"),
                                "view": "tasks_json",
                                "task_id": 41,
                                "task_ref": "T41",
                                "from_status": "done",
                                "to_status": "review",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
            out_json = root / "apply-dry-run-summary.json"
            rc = run_module.main(["--patch", str(patch), "--dry-run", "--out-json", str(out_json)])
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            after = json.loads(tasks_json.read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertEqual("ok", payload["status"])
        self.assertTrue(payload["dry_run"])
        self.assertEqual("done", after["master"]["tasks"][0]["status"])

    def test_apply_chapter7_status_patch_should_write_when_not_dry_run(self) -> None:
        run_module = _load_module("apply_chapter7_status_patch_module_for_apply", "scripts/python/apply_chapter7_status_patch.py")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tasks_dir = root / ".taskmaster" / "tasks"
            tasks_dir.mkdir(parents=True)
            tasks_json = tasks_dir / "tasks.json"
            tasks_json.write_text(
                json.dumps({"master": {"tasks": [{"id": 41, "title": "Wire UI: MainMenu And Boot Flow", "status": "done"}]}}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            patch = root / "task-status-patch.json"
            patch.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "contract_type": "chapter7-task-status-patch",
                        "status": "ok",
                        "operation_count": 1,
                        "operations": [
                            {
                                "op": "replace-task-status",
                                "path": str(tasks_json.resolve()).replace("\\", "/"),
                                "view": "tasks_json",
                                "task_id": 41,
                                "task_ref": "T41",
                                "from_status": "done",
                                "to_status": "review",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
            out_json = root / "apply-summary.json"
            rc = run_module.main(["--patch", str(patch), "--out-json", str(out_json)])
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            after = json.loads(tasks_json.read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertEqual("ok", payload["status"])
        self.assertFalse(payload["dry_run"])
        self.assertEqual("review", after["master"]["tasks"][0]["status"])


if __name__ == "__main__":
    unittest.main()
