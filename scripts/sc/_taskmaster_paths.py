from __future__ import annotations

from pathlib import Path

_TRIPLET_FILES = ("tasks.json", "tasks_back.json", "tasks_gameplay.json")


def _complete_triplet_dir(base_dir: Path) -> Path | None:
    if all((base_dir / name).exists() for name in _TRIPLET_FILES):
        return base_dir
    return None


def resolve_default_task_triplet_paths(root: Path) -> tuple[Path, Path, Path]:
    base_dir = _complete_triplet_dir(root / ".taskmaster" / "tasks")
    if base_dir is None:
        base_dir = _complete_triplet_dir(root / "examples" / "taskmaster")
    if base_dir is None:
        base_dir = root / ".taskmaster" / "tasks"
    return tuple(base_dir / name for name in _TRIPLET_FILES)
