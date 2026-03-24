from __future__ import annotations

import os
from pathlib import Path

from _util import repo_root, today_str


_DEFAULT_TASK_FILTERS = {
    "1": (
        "FullyQualifiedName~Task1EnvironmentEvidencePersistenceTests"
        "|FullyQualifiedName~Task1WindowsPlatformGateTests"
        "|FullyQualifiedName~Task1ToolchainVersionChecksTests"
    )
}

_DEFAULT_TASK_FILES = {
    "1": [
        Path("Game.Core.Tests/Tasks/Task1EnvironmentEvidencePersistenceTests.cs"),
        Path("Game.Core.Tests/Tasks/Task1WindowsPlatformGateTests.cs"),
        Path("Game.Core.Tests/Tasks/Task1ToolchainVersionChecksTests.cs"),
    ]
}


def _normalize_task_id(task_id: str | int | None) -> str:
    return str(task_id or "").strip().split(".", 1)[0].strip()


def get_post_evidence_test_filter(task_id: str | int | None) -> str | None:
    task_id_s = _normalize_task_id(task_id)
    env_key = f"SC_POST_EVIDENCE_FILTER_TASK_{task_id_s}"
    env_override = str(os.environ.get(env_key) or "").strip()
    if env_override:
        return env_override
    default_filter = _DEFAULT_TASK_FILTERS.get(task_id_s)
    required_files = _DEFAULT_TASK_FILES.get(task_id_s) or []
    if default_filter and all((repo_root() / rel).exists() for rel in required_files):
        return default_filter
    return None


def has_post_evidence_integration(task_id: str | int | None) -> bool:
    return bool(get_post_evidence_test_filter(task_id))


def get_post_evidence_report_dir(task_id: str | int | None) -> Path:
    task_id_s = _normalize_task_id(task_id) or "unknown"
    return Path("logs") / "unit" / today_str() / f"sc-acceptance-post-evidence-task-{task_id_s}"
