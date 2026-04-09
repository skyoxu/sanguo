#!/usr/bin/env python3
"""Shared solution path resolver for Python entrypoints."""

from __future__ import annotations

from pathlib import Path


def resolve_solution_path(requested_solution: str | None, *, repo_root: Path | None = None) -> str:
    """Resolve solution path with project-first preference.

    Priority:
    1) explicit --solution when it exists
    2) <repo-name>.sln
    3) GodotGame.sln
    4) Game.sln
    5) first *.sln in repo root
    6) fallback to requested value or Game.sln
    """

    root = Path(repo_root or Path.cwd())
    requested = str(requested_solution or "").strip()
    if requested and requested.lower() != "auto":
        candidate = Path(requested)
        if not candidate.is_absolute():
            candidate = root / candidate
        if candidate.exists():
            return requested

    candidates = sorted(root.glob("*.sln"))
    if candidates:
        preferred_names = (
            f"{root.name}.sln".lower(),
            "godotgame.sln",
            "game.sln",
        )
        by_name = {c.name.lower(): c.name for c in candidates}
        for pref in preferred_names:
            if pref in by_name:
                return by_name[pref]
        return candidates[0].name

    return requested or "Game.sln"


def _looks_like_test_solution(candidate: Path) -> bool:
    try:
        text = candidate.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    normalized = text.replace("\\\\", "\\").lower()
    return "game.core.tests" in normalized or "tests.godot" in normalized


def resolve_test_solution_path(requested_solution: str | None, *, repo_root: Path | None = None) -> str:
    """Resolve solution path with test-bearing preference for test-oriented entrypoints.

    Priority:
    1) explicit --solution when it exists
    2) first solution that looks like it contains test projects, preferring Game.sln
    3) fallback to resolve_solution_path(...)
    """

    root = Path(repo_root or Path.cwd())
    requested = str(requested_solution or "").strip()
    if requested and requested.lower() != "auto":
        candidate = Path(requested)
        if not candidate.is_absolute():
            candidate = root / candidate
        if candidate.exists():
            return requested

    candidates = sorted(root.glob("*.sln"))
    if not candidates:
        return requested or "Game.sln"

    test_candidates = [candidate for candidate in candidates if _looks_like_test_solution(candidate)]
    if test_candidates:
        preferred_names = ("game.sln", f"{root.name}.sln".lower(), "godotgame.sln")
        by_name = {c.name.lower(): c.name for c in test_candidates}
        for pref in preferred_names:
            if pref in by_name:
                return by_name[pref]
        return test_candidates[0].name

    return resolve_solution_path(requested, repo_root=root)
