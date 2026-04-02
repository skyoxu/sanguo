#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SC_DIR = REPO_ROOT / "scripts" / "sc"
if str(SC_DIR) not in sys.path:
    sys.path.insert(0, str(SC_DIR))

from _delivery_profile import (  # noqa: E402
    default_security_profile_for_delivery,
    known_delivery_profiles,
    resolve_delivery_profile,
)
from _taskmaster_paths import resolve_default_task_triplet_paths  # noqa: E402

_VALID_SECURITY_PROFILES = {"strict", "host-safe"}


def repo_root() -> Path:
    return REPO_ROOT


def resolve_repo_path(path_text: str, *, root: Path | None = None) -> Path:
    base_root = Path(root) if root is not None else repo_root()
    path = Path(path_text)
    if path.is_absolute():
        return path
    return base_root / path


def default_task_triplet_paths(root: Path | None = None) -> tuple[Path, Path, Path]:
    base_root = Path(root) if root is not None else repo_root()
    return resolve_default_task_triplet_paths(base_root)


def default_tasks_file_path(root: Path | None = None) -> Path:
    return default_task_triplet_paths(root)[0]


def known_delivery_profile_choices() -> tuple[str, ...]:
    return tuple(sorted(known_delivery_profiles()))


def resolve_delivery_and_security(
    delivery_profile: str | None,
    security_profile: str | None,
) -> tuple[str, str]:
    resolved_delivery = resolve_delivery_profile(delivery_profile)
    raw_security = str(security_profile or "").strip().lower()
    resolved_security = raw_security or default_security_profile_for_delivery(resolved_delivery)
    if resolved_security not in _VALID_SECURITY_PROFILES:
        raise ValueError(f"unsupported security profile: {resolved_security}")
    return resolved_delivery, resolved_security
