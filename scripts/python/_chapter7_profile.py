#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_CHAPTER7_PROFILE_OVERRIDE_PATH = Path("docs/workflows/chapter7-profile.json")
DEFAULT_BUCKET_ORDER = ["entry", "loop", "combat", "economy", "meta", "governance"]


DEFAULT_CHAPTER7_PROFILE: dict[str, Any] = {
    "bucket_order": DEFAULT_BUCKET_ORDER,
    "fallback_bucket": "meta",
    "surface_aliases": {
        "RuntimeHud": ["RuntimeHud", "HUD"],
        "SettingsMenu": ["SettingsMenu", "SettingsPanel", "SettingsScreen"],
    },
    "task_creation": {
        "priority_by_bucket": {
            "entry": "high",
            "loop": "high",
            "combat": "high",
            "economy": "high",
            "meta": "medium",
            "governance": "medium",
            "default": "medium",
        },
        "layer_by_bucket": {
            "entry": "adapter",
            "loop": "adapter",
            "combat": "adapter",
            "economy": "adapter",
            "meta": "adapter",
            "governance": "core",
            "default": "adapter",
        },
        "view_priority_map": {
            "high": "P1",
            "medium": "P2",
            "low": "P3",
        },
        "adr_refs": ["ADR-0010", "ADR-0011", "ADR-0019", "ADR-0025"],
        "chapter_refs": ["CH02", "CH06", "CH07", "CH10"],
        "base_labels": ["taskmaster-view", "chapter7-ui"],
        "owners": {
            "NG": "architecture",
            "GM": "gameplay",
        },
        "source_labels": {
            "NG": "backlog",
            "GM": "prd",
        },
        "view_id_templates": {
            "NG": "NG-{task_id:04d}",
            "GM": "GM-{task_id_plus_100:04d}",
        },
        "default_story_templates": {
            "back": "BACKLOG-{repo_label_upper_underscore}-M1",
            "gameplay": "PRD-{repo_label_upper_underscore}-v1.2",
        },
    },
    "buckets": {
        "entry": {
            "feature_task_ids": [1, 11, 21],
            "feature_families": ["run-entry"],
            "slice_title": "Entry And Bootstrap",
            "screen_group": "MainMenu And Boot Flow",
            "audience": "player-facing",
            "ui_entry": "MainMenu / Boot Flow",
            "player_action": "Launch, continue, retry bootstrap, or enter a run",
            "system_response": "Show canonical startup path, valid continue behavior, and explicit startup failure recovery",
            "suggested_surfaces": ["MainMenu", "BootStatusPanel", "ContinueGateDialog"],
            "section_headings": [
                "### 6.1.1 MainMenu And Boot Flow",
                "### 6.1.1 Entry And Bootstrap",
                "### 6.1.1 MainMenu And Boot Flow（主菜单与启动流程）",
                "### 6.1.1 Entry And Bootstrap（入口与启动）",
            ],
            "scene_rel_path": "Game.Godot/Scenes/UI/MainMenu.tscn",
            "closure_task_ids": [41],
            "wiring_task_id": 41,
            "semantics_defaults": {
                "failure": "startup failure must remain visible and recoverable instead of failing silently.",
                "empty": "show no active run state until runtime data is available.",
                "completion": "player reaches a stable entry path and can distinguish start, continue, failure, and retry outcomes.",
            },
            "screen_contract": {
                "must_show": "start, continue, retry bootstrap, and platform-start validation state.",
                "must_not_hide": "startup failure, continue-gate denial, or export/runtime startup issues behind logs only.",
                "validation_focus": "boot path, continue gate, retry flow, and startup validation evidence.",
            },
            "screen_state": {
                "entry_state": "show start, continue, and startup readiness before any run begins.",
                "interaction_state": "allow start, continue, retry bootstrap, and acknowledgement of startup state.",
                "failure_state": "show startup failure, continue denial, or runtime-start validation failure explicitly.",
                "recovery_exit": "retry bootstrap, acknowledge, or return to menu.",
            },
        },
        "loop": {
            "feature_task_ids": [3, 7, 8, 9, 10, 18, 19, 23, 24],
            "feature_families": ["reward", "rest", "shop", "event"],
            "slice_title": "Core Loop State And Outcome",
            "screen_group": "Runtime HUD And Outcome Surfaces",
            "audience": "player-facing",
            "ui_entry": "HUD / Prompt / Outcome Surfaces",
            "player_action": "Play a run, observe timing, rewards, prompts, and terminal transitions",
            "system_response": "Render readable phase, timer, HP, reward, prompt, and win/lose state from runtime events",
            "suggested_surfaces": ["RuntimeHud", "OutcomePanel", "RuntimePromptPanel"],
            "section_headings": [
                "### 6.1.2 Runtime HUD And Outcome",
                "### 6.1.2 Runtime HUD And Outcome Surfaces",
                "### 6.1.2 Runtime HUD And Outcome（运行时 HUD 与结果）",
            ],
            "scene_rel_path": "Game.Godot/Scenes/UI/HUD.tscn",
            "closure_task_ids": [42],
            "wiring_task_id": 42,
            "semantics_defaults": {
                "failure": "runtime prompts and terminal state must stay visible when loop progression cannot continue normally.",
                "empty": "show no active run state until runtime data is available.",
                "completion": "player can read phase, timing, outcome, and prompt state from governed surfaces.",
            },
            "screen_contract": {
                "must_show": "phase, timer, HP, prompts, reward entry, invalid-action prompts, speed state, and terminal outcomes.",
                "must_not_hide": "terminal or prompt state transitions that occur without visible HUD or outcome feedback.",
                "validation_focus": "HUD state changes, prompts, reward visibility, and win/lose transitions.",
            },
            "screen_state": {
                "entry_state": "show no active run state until runtime data is available.",
                "interaction_state": "show phase, timer, HP, prompts, reward entry, invalid-action prompts, speed state, and terminal outcomes.",
                "failure_state": "show prompt/terminal failure state instead of leaving the HUD stale or blank.",
                "recovery_exit": "acknowledge outcome, continue the run, or return to menu.",
            },
        },
        "combat": {
            "feature_task_ids": [4, 5, 6, 20, 22],
            "feature_families": ["combat", "map"],
            "slice_title": "Combat Pressure And Interaction",
            "screen_group": "Combat Pressure And Interaction Surfaces",
            "audience": "player-facing",
            "ui_entry": "Combat HUD / Pressure / Camera Feedback",
            "player_action": "Fight, observe pressure, targeting, pathing, and camera responses",
            "system_response": "Render enemy pressure, targeting, combat outcomes, and camera interaction without hidden state",
            "suggested_surfaces": ["CombatHud", "PressurePanel", "CameraControlOverlay"],
            "section_headings": [
                "### 6.1.3 Combat Pressure And Interaction",
                "### 6.1.3 Combat Pressure And Interaction Surfaces",
                "### 6.1.3 Combat Pressure And Interaction（战斗压强与交互）",
            ],
            "scene_rel_path": "Game.Godot/Scenes/UI/HUD.tscn",
            "closure_task_ids": [43],
            "wiring_task_id": 43,
            "semantics_defaults": {
                "failure": "blocked, invalid, or hidden combat state must become explicit feedback instead of silent desync.",
                "empty": "show no active pressure or combat state until combat data is available.",
                "completion": "player can explain pressure, targeting, and combat outcomes from visible feedback.",
            },
            "screen_contract": {
                "must_show": "pressure, spawn cadence, targeting, pathing fallback, combat resolution, and camera interaction state.",
                "must_not_hide": "combat pressure or targeting changes that only appear in logs or traces.",
                "validation_focus": "combat feedback, pressure visibility, pathing fallback evidence, and camera interaction smoke checks.",
            },
            "screen_state": {
                "entry_state": "show no active combat state until combat data and camera ownership are ready.",
                "interaction_state": "show pressure, targeting, pathing fallback, combat resolution, and camera interaction state.",
                "failure_state": "show blocked targeting, missing path, or hidden pressure failure explicitly.",
                "recovery_exit": "retry, acknowledge, or return to the governed combat-ready surface.",
            },
        },
        "economy": {
            "feature_task_ids": [12, 13, 14, 15, 16, 17],
            "feature_families": [],
            "slice_title": "Economy Build And Progression",
            "screen_group": "Economy And Progression Panels",
            "audience": "player-facing",
            "ui_entry": "Resource / Build / Progression Panels",
            "player_action": "Spend resources, place/build, train, upgrade, repair, or pick rewards",
            "system_response": "Render deterministic resource, build, queue, upgrade, and progression changes with clear invalid-state feedback",
            "suggested_surfaces": ["ResourcePanel", "BuildPanel", "ProgressionPanel"],
            "section_headings": [
                "### 6.1.4 Economy And Progression",
                "### 6.1.4 Economy And Progression Panels",
                "### 6.1.4 Economy And Progression（经济与成长）",
            ],
            "scene_rel_path": "Game.Godot/Scenes/UI/HUD.tscn",
            "closure_task_ids": [44],
            "wiring_task_id": 44,
            "semantics_defaults": {
                "failure": "invalid build, spend, queue, or upgrade actions must render clear feedback and keep deterministic state intact.",
                "empty": "show no active economy state until owned runtime data is available.",
                "completion": "player can read deterministic resource and progression outcomes from UI state.",
            },
            "screen_contract": {
                "must_show": "resource totals, build placement state, queue state, upgrade/repair state, tech state, and progression results.",
                "must_not_hide": "invalid spend/build/progression transitions without governed feedback.",
                "validation_focus": "resource determinism, build validation, queue behavior, and progression surface evidence.",
            },
            "screen_state": {
                "entry_state": "show no owned economy state until resource/build/progression data is available.",
                "interaction_state": "show resource totals, build placement state, queue state, upgrade/repair state, tech state, and progression results.",
                "failure_state": "show invalid spend/build/progression state without mutating deterministic ownership silently.",
                "recovery_exit": "acknowledge invalid state, retry the action, or return to menu.",
            },
        },
        "meta": {
            "feature_task_ids": [25, 26, 27, 28, 29, 30],
            "feature_families": [],
            "slice_title": "Meta Systems And Platform",
            "screen_group": "Save, Settings, And Meta Surfaces",
            "audience": "player-facing or mixed",
            "ui_entry": "Settings / Save / Meta Surfaces",
            "player_action": "Save, load, localize, tune audio, or inspect platform/runtime status",
            "system_response": "Render persistence, localization, audio, performance, and platform status on governed player-visible surfaces",
            "suggested_surfaces": ["SettingsMenu", "SavePanel", "RunSummaryPanel"],
            "section_headings": [
                "### 6.1.5 Save, Settings, And Meta",
                "### 6.1.5 Save, Settings, And Meta Surfaces",
                "### 6.1.5 Save, Settings, And Meta（存档、设置与元系统）",
            ],
            "scene_rel_path": "Game.Godot/Scenes/UI/SettingsPanel.tscn",
            "closure_task_ids": [45],
            "wiring_task_id": 45,
            "semantics_defaults": {
                "failure": "save, cloud, localization, audio, or platform issues must remain visible and actionable.",
                "empty": "show no persisted or platform state until those services are available.",
                "completion": "player can complete meta interactions without consulting logs.",
            },
            "screen_contract": {
                "must_show": "save/load status, cloud state, localization state, audio state, performance state, and platform/runtime status.",
                "must_not_hide": "persistence or settings failures that are only visible in lower-level logs.",
                "validation_focus": "save/load flow, cloud sync, localization/audio controls, and platform status visibility.",
            },
            "screen_state": {
                "entry_state": "show no persisted/platform state until save, cloud, or settings services are available.",
                "interaction_state": "show save/load status, cloud state, localization state, audio state, performance state, and platform/runtime status.",
                "failure_state": "show persistence or settings failure instead of only writing low-level logs.",
                "recovery_exit": "retry, acknowledge, or return to menu.",
            },
        },
        "governance": {
            "feature_task_ids": [2, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40],
            "feature_families": [],
            "slice_title": "Config Governance And Audit",
            "screen_group": "Config Audit And Migration Surfaces",
            "audience": "operator-facing or mixed",
            "ui_entry": "Config Summary / Audit / Migration Surfaces",
            "player_action": "Inspect config state, validation, governance, migration, and report metadata",
            "system_response": "Render active config, schema status, fallback policy, migration status, and audit metadata without relying on logs-only evidence",
            "suggested_surfaces": ["ConfigAuditPanel", "MigrationStatusDialog", "ReportMetadataPanel"],
            "section_headings": [
                "### 6.1.6 Config Governance And Audit",
                "### 6.1.6 Config Audit And Migration Surfaces",
                "### 6.1.6 Config Governance And Audit（配置治理与审计）",
            ],
            "scene_rel_path": "Game.Godot/Scenes/UI/HUD.tscn",
            "closure_task_ids": [46],
            "wiring_task_id": 46,
            "semantics_defaults": {
                "failure": "must not advance runtime config snapshot when validation or migration fails; visible fallback state is required.",
                "empty": "show no active run state until runtime data is available.",
                "completion": "operator or player can inspect config, validation, migration, and audit state from governed surfaces.",
            },
            "screen_contract": {
                "must_show": "active config, schema status, fallback status, migration state, config audit metadata, and report metadata.",
                "must_not_hide": "validation, fallback, or migration outcomes that do not surface on a governed read surface.",
                "validation_focus": "config validation, governance, migration, and audit metadata evidence.",
            },
            "screen_state": {
                "entry_state": "show no active run state until config, validation, and migration data is available.",
                "interaction_state": "show active config, schema status, fallback status, migration state, config audit metadata, and report metadata.",
                "failure_state": "show validation, fallback, or migration failure on the governed read surface.",
                "recovery_exit": "retry, acknowledge, or return to menu after review.",
            },
        },
    },
}


def build_default_chapter7_profile() -> dict[str, Any]:
    return deepcopy(DEFAULT_CHAPTER7_PROFILE)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Chapter 7 profile must be a JSON object: {path}")
    return payload


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _resolve_profile_path(repo_root: Path, value: Path | None) -> Path | None:
    if value is not None:
        path = value if value.is_absolute() else (repo_root / value)
        if not path.exists():
            raise FileNotFoundError(f"missing Chapter 7 profile: {path}")
        return path
    default_path = repo_root / DEFAULT_CHAPTER7_PROFILE_OVERRIDE_PATH
    return default_path if default_path.exists() else None


def load_chapter7_profile(*, repo_root: Path, profile_path: Path | None = None) -> dict[str, Any]:
    profile = build_default_chapter7_profile()
    resolved_path = _resolve_profile_path(repo_root, profile_path)
    if resolved_path is not None:
        profile = _deep_merge(profile, _read_json(resolved_path))
        profile["_loaded_profile_path"] = str(resolved_path.resolve()).replace("\\", "/")
    else:
        profile["_loaded_profile_path"] = ""
    return profile


def bucket_names(profile: dict[str, Any]) -> list[str]:
    names = profile.get("bucket_order") or DEFAULT_BUCKET_ORDER
    return [str(item) for item in names if str(item).strip()]


def bucket_profile(profile: dict[str, Any], bucket: str) -> dict[str, Any]:
    return dict(profile.get("buckets", {}).get(bucket, {}))


def feature_bucket(profile: dict[str, Any], feature: dict[str, Any]) -> str:
    task_id = int(feature["task_id"])
    feature_family = str(feature.get("feature_family") or "").strip()
    for bucket in bucket_names(profile):
        config = bucket_profile(profile, bucket)
        task_ids = {int(item) for item in config.get("feature_task_ids", [])}
        families = {str(item).strip() for item in config.get("feature_families", []) if str(item).strip()}
        if task_id in task_ids or (feature_family and feature_family in families):
            return bucket
    fallback = str(profile.get("fallback_bucket") or "meta").strip()
    return fallback or "meta"


def surface_aliases(profile: dict[str, Any], surface: str) -> list[str]:
    aliases = profile.get("surface_aliases", {}).get(surface) or [surface]
    out: list[str] = []
    seen: set[str] = set()
    for item in [surface, *aliases]:
        value = str(item).strip()
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out or [surface]


def task_creation_config(profile: dict[str, Any]) -> dict[str, Any]:
    return dict(profile.get("task_creation", {}))


def priority_for_bucket(profile: dict[str, Any], bucket: str) -> str:
    config = task_creation_config(profile).get("priority_by_bucket", {})
    return str(config.get(bucket) or config.get("default") or "medium")


def layer_for_bucket(profile: dict[str, Any], bucket: str) -> str:
    config = task_creation_config(profile).get("layer_by_bucket", {})
    return str(config.get(bucket) or config.get("default") or "adapter")


def view_priority_for_bucket(profile: dict[str, Any], bucket: str) -> str:
    master_priority = priority_for_bucket(profile, bucket)
    mapping = task_creation_config(profile).get("view_priority_map", {})
    return str(mapping.get(master_priority) or "P2")


def _repo_label_tokens(repo_label: str) -> dict[str, str]:
    normalized = (repo_label or "").strip() or "taskmaster"
    repo_label_kebab = normalized.replace("_", "-")
    repo_label_upper_underscore = repo_label_kebab.upper().replace("-", "_").replace(".", "_")
    return {
        "repo_label": normalized,
        "repo_label_kebab": repo_label_kebab,
        "repo_label_upper_underscore": repo_label_upper_underscore,
    }


def format_story_id(template: str, repo_label: str) -> str:
    return str(template).format(**_repo_label_tokens(repo_label))


def default_story_ids(profile: dict[str, Any], repo_label: str) -> tuple[str, str]:
    templates = task_creation_config(profile).get("default_story_templates", {})
    back_template = str(templates.get("back") or "BACKLOG-{repo_label_upper_underscore}-M1")
    gameplay_template = str(templates.get("gameplay") or "PRD-{repo_label_upper_underscore}-v1.2")
    return format_story_id(back_template, repo_label), format_story_id(gameplay_template, repo_label)


def owner_for_prefix(profile: dict[str, Any], prefix: str) -> str:
    owners = task_creation_config(profile).get("owners", {})
    return str(owners.get(prefix) or "gameplay")


def source_label_for_prefix(profile: dict[str, Any], prefix: str) -> str:
    labels = task_creation_config(profile).get("source_labels", {})
    return str(labels.get(prefix) or prefix.lower())


def view_id_for_prefix(profile: dict[str, Any], prefix: str, task_id: int) -> str:
    templates = task_creation_config(profile).get("view_id_templates", {})
    template = str(templates.get(prefix) or f"{prefix}-{{task_id:04d}}")
    return template.format(
        prefix=prefix,
        task_id=task_id,
        task_id_plus_100=task_id + 100,
        task_id_plus_1000=task_id + 1000,
    )
