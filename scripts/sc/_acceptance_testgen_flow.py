from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable


def load_task_context(
    *,
    task_id: str,
    out_dir: Path,
    repo_root_fn: Callable[[], Path],
    read_text_fn: Callable[[Path], str],
) -> dict[str, Any]:
    ctx_path = repo_root_fn() / "logs" / "ci" / out_dir.parent.name / "sc-analyze" / f"task_context.{task_id}.json"
    if not ctx_path.exists():
        ctx_path = repo_root_fn() / "logs" / "ci" / out_dir.parent.name / "sc-analyze" / "task_context.json"
    try:
        task_context = json.loads(read_text_fn(ctx_path) or "{}")
    except Exception:
        task_context = {}
    return task_context if isinstance(task_context, dict) else {}


def collect_refs(
    *,
    task_id: str,
    triplet: Any,
    out_dir: Path,
    extract_acceptance_refs_with_anchors_fn: Callable[..., dict[str, list[dict[str, str]]]],
    is_allowed_test_path_fn: Callable[[str], bool],
    write_json_fn: Callable[[Path, object], None],
) -> tuple[dict[str, list[dict[str, str]]], list[str], list[str]]:
    back_map = extract_acceptance_refs_with_anchors_fn(acceptance=(triplet.back or {}).get("acceptance"), task_id=task_id)
    game_map = extract_acceptance_refs_with_anchors_fn(acceptance=(triplet.gameplay or {}).get("acceptance"), task_id=task_id)
    by_ref: dict[str, list[dict[str, str]]] = {}
    for mapping in (back_map, game_map):
        for ref, entries in mapping.items():
            by_ref.setdefault(ref, []).extend(entries)
    for ref, entries in list(by_ref.items()):
        seen = set()
        unique: list[dict[str, str]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            anchor = str(entry.get("anchor") or "").strip()
            text = str(entry.get("text") or "").strip()
            key = (anchor, text)
            if key in seen:
                continue
            seen.add(key)
            unique.append({"anchor": anchor, "text": text})
        by_ref[ref] = unique
    refs_all = sorted(by_ref.keys())
    refs = [ref for ref in refs_all if is_allowed_test_path_fn(ref)]
    skipped = [ref for ref in refs_all if not is_allowed_test_path_fn(ref)]
    write_json_fn(
        out_dir / f"refs-filtered.{task_id}.json",
        {
            "task_id": task_id,
            "total_refs": len(refs_all),
            "selected_test_refs": refs,
            "skipped_non_test_refs": skipped,
        },
    )
    return by_ref, refs, skipped


def run_verify(
    *,
    verify: str,
    task_id: str,
    any_gd: bool,
    godot_bin: str | None,
    out_dir: Path,
    strict_red: bool,
    run_cmd_fn: Callable[..., tuple[int, str]],
    repo_root_fn: Callable[[], Path],
    write_text_fn: Callable[[Path, str], None],
) -> tuple[str, dict[str, Any] | None]:
    mode = "all" if verify == "auto" and any_gd else ("unit" if verify == "auto" else verify)
    if mode == "none":
        return mode, None
    if mode == "all":
        resolved_godot_bin = godot_bin or os.environ.get("GODOT_BIN")
        if not resolved_godot_bin:
            write_text_fn(out_dir / f"verify-{task_id}.log", "ERROR: verify=all requires --godot-bin or env GODOT_BIN\n")
            return mode, {"status": "fail", "rc": 2, "error": "missing_godot_bin"}
        cmd = [
            "py",
            "-3",
            "scripts/sc/test.py",
            "--type",
            "all",
            "--task-id",
            task_id,
            "--godot-bin",
            str(resolved_godot_bin),
        ]
        if strict_red:
            cmd.append("--skip-smoke")
    else:
        cmd = ["py", "-3", "scripts/sc/test.py", "--type", "unit", "--task-id", task_id]
        if strict_red:
            cmd += ["--no-coverage-gate", "--no-coverage-report"]
    rc, out = run_cmd_fn(cmd, cwd=repo_root_fn(), timeout_sec=1_800)
    write_text_fn(out_dir / f"verify-{task_id}.log", out)
    return mode, {"status": "ok" if rc == 0 else "fail", "rc": rc, "cmd": cmd}
