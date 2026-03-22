#!/usr/bin/env python3
"""Command builders for quality_gates entrypoints."""

from __future__ import annotations


DEFAULT_GATE_BUNDLE_TASK_FILES = [
    ".taskmaster/tasks/tasks_back.json",
    ".taskmaster/tasks/tasks_gameplay.json",
]


def build_gate_bundle_hard_cmd(
    *,
    delivery_profile: str,
    task_files: list[str],
    out_dir: str,
    run_id: str,
) -> list[str]:
    args = [
        "py",
        "-3",
        "scripts/python/run_gate_bundle.py",
        "--mode",
        "hard",
        "--task-files",
        *task_files,
    ]
    if delivery_profile:
        args += ["--delivery-profile", delivery_profile]
    if out_dir:
        args += ["--out-dir", out_dir]
    if run_id:
        args += ["--run-id", run_id]
    return args


def build_gdunit_hard_cmd(*, godot_bin: str) -> list[str]:
    return [
        "py",
        "-3",
        "scripts/python/run_gdunit.py",
        "--prewarm",
        "--godot-bin",
        godot_bin,
        "--project",
        "Tests.Godot",
        "--add",
        "tests/Adapters/Config",
        "--add",
        "tests/Security/Hard",
        "--timeout-sec",
        "300",
        "--rd",
        "logs/e2e/quality-gates/gdunit-hard",
    ]


def build_smoke_headless_cmd(*, godot_bin: str) -> list[str]:
    return [
        "py",
        "-3",
        "scripts/python/smoke_headless.py",
        "--godot-bin",
        godot_bin,
        "--project-path",
        ".",
        "--scene",
        "res://Game.Godot/Scenes/Main.tscn",
        "--timeout-sec",
        "5",
        "--strict",
    ]
