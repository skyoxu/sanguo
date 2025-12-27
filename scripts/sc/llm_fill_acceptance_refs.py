#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sc-llm-fill-acceptance-refs

Use Codex CLI (LLM) to propose 1..N test file paths for each acceptance item, then
write them into tasks_back.json/tasks_gameplay.json as "Refs:" suffixes.

Primary goal:
  - Deterministic traceability: every acceptance item has Refs: ... pointing to
    repo-relative .cs/.gd test files under allowed test roots.

Design constraints:
  - Prefer existing test files when possible.
  - Default: do NOT overwrite existing "Refs:".
  - Optional: overwrite existing refs via --overwrite-existing.
  - This script only updates metadata (acceptance/test_refs). It does NOT create tests.
    (Use scripts/sc/llm_generate_tests_from_acceptance_refs.py after refs exist.)

Outputs:
  logs/ci/<YYYY-MM-DD>/sc-llm-acceptance-refs/
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _bootstrap_imports() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))


_bootstrap_imports()

from _taskmaster import default_paths, iter_master_tasks, load_json  # noqa: E402
from _util import ci_dir, repo_root, run_cmd, today_str, write_json, write_text  # noqa: E402


REFS_RE = re.compile(r"\bRefs\s*:\s*(.+)$", flags=re.IGNORECASE)

AUTO_BEGIN = "<!-- BEGIN AUTO:TEST_ORG_NAMING_REFS -->"
AUTO_END = "<!-- END AUTO:TEST_ORG_NAMING_REFS -->"


ALLOWED_TEST_PREFIXES = (
    "Game.Core.Tests/",
    "Tests.Godot/tests/",
    "Tests/",
)


@dataclass(frozen=True)
class ItemKey:
    view: str  # back|gameplay
    index: int


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _truncate(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def _extract_testing_framework_excerpt() -> str:
    path = repo_root() / "docs" / "testing-framework.md"
    if not path.exists():
        return ""
    text = _read_text(path)
    a = text.find(AUTO_BEGIN)
    b = text.find(AUTO_END)
    if a < 0 or b < 0 or b <= a:
        return ""
    excerpt = text[a + len(AUTO_BEGIN) : b].strip()
    return excerpt


def _run_codex_exec(*, prompt: str, out_last_message: Path, timeout_sec: int) -> tuple[int, str, list[str]]:
    exe = shutil.which("codex")
    if not exe:
        return 127, "codex executable not found in PATH\n", ["codex"]
    cmd = [
        exe,
        "exec",
        "-s",
        "read-only",
        "-C",
        str(repo_root()),
        "--output-last-message",
        str(out_last_message),
        "-",
    ]
    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            encoding="utf-8",
            errors="ignore",
            cwd=str(repo_root()),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return 124, "codex exec timeout\n", cmd
    except Exception as exc:  # noqa: BLE001
        return 1, f"codex exec failed to start: {exc}\n", cmd
    return proc.returncode or 0, proc.stdout or "", cmd


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON object found in model output.")
    obj = json.loads(m.group(0))
    if not isinstance(obj, dict):
        raise ValueError("Model output JSON is not an object.")
    return obj


def _is_abs_path(p: str) -> bool:
    s = str(p or "").strip()
    if not s:
        return False
    if os.path.isabs(s):
        return True
    if len(s) >= 2 and s[1] == ":":
        return True
    return False


def _is_allowed_test_path(p: str) -> bool:
    s = str(p or "").strip().replace("\\", "/")
    if not s or _is_abs_path(s):
        return False
    if not (s.endswith(".cs") or s.endswith(".gd")):
        return False
    return s.startswith(ALLOWED_TEST_PREFIXES)


def _strip_refs_suffix(s: str) -> str:
    return REFS_RE.sub("", s).rstrip()


def _split_refs_blob(blob: str) -> list[str]:
    s = str(blob or "").strip()
    s = s.replace("`", "")
    s = s.replace(",", " ")
    s = s.replace(";", " ")
    return [p.strip().replace("\\", "/") for p in s.split() if p.strip()]


def _extract_refs_from_acceptance_item(text: str) -> list[str]:
    m = REFS_RE.search(str(text or "").strip())
    if not m:
        return []
    return _split_refs_blob(m.group(1))


def _extract_prd_excerpt() -> str:
    root = repo_root()
    prd = root / "prd.txt"
    prd_yuan = root / "prd_yuan.md"
    blob = ""
    if prd.exists():
        blob += _read_text(prd) + "\n"
    if prd_yuan.exists():
        blob += _read_text(prd_yuan) + "\n"
    blob = blob.strip()
    return _truncate(blob, max_chars=10_000)


def _list_existing_tests() -> list[str]:
    root = repo_root()
    out: list[str] = []
    for base, ext in [("Game.Core.Tests", ".cs"), ("Tests.Godot/tests", ".gd")]:
        p = root / base
        if not p.exists():
            continue
        for f in p.rglob(f"*{ext}"):
            if not f.is_file():
                continue
            rel = str(f.relative_to(root)).replace("\\", "/")
            if _is_allowed_test_path(rel):
                out.append(rel)
    out.sort()
    return out


def _pick_existing_candidates(*, all_tests: list[str], task_id: int, title: str, limit: int) -> list[str]:
    tid = str(task_id)
    by_tid = [p for p in all_tests if re.search(rf"\bTask{re.escape(tid)}\b", p, flags=re.IGNORECASE)]
    if by_tid:
        return by_tid[:limit]

    tokens = [t for t in re.split(r"[^A-Za-z0-9]+", title) if t]
    tokens = tokens[:6]
    if not tokens:
        return []
    picked: list[str] = []
    for p in all_tests:
        pl = p.lower()
        if any(tok.lower() in pl for tok in tokens):
            picked.append(p)
            if len(picked) >= limit:
                break
    return picked


def _default_ref_for(*, task_id: int, prefer_gd: bool) -> str:
    if prefer_gd:
        return f"Tests.Godot/tests/Scenes/Sanguo/test_task{task_id}_acceptance.gd"
    return f"Game.Core.Tests/Tasks/Task{task_id}AcceptanceTests.cs"


def _build_prompt(
    *,
    prd_excerpt: str,
    task_id: int,
    master: dict[str, Any] | None,
    back: dict[str, Any] | None,
    gameplay: dict[str, Any] | None,
    missing_items: dict[ItemKey, str],
    existing_candidates: list[str],
    max_refs_per_item: int,
) -> str:
    title = str((master or {}).get("title") or "").strip()
    master_details = _truncate(str((master or {}).get("details") or ""), max_chars=2_000)
    back_strategy = (back or {}).get("test_strategy") or []
    gameplay_strategy = (gameplay or {}).get("test_strategy") or []

    def _as_lines(v: Any, max_items: int) -> list[str]:
        if not isinstance(v, list):
            return []
        items = [str(x).strip() for x in v if str(x).strip()]
        return items[:max_items]

    back_acceptance = _as_lines((back or {}).get("acceptance"), 50)
    gameplay_acceptance = _as_lines((gameplay or {}).get("acceptance"), 50)

    input_items = []
    for k, text in sorted(missing_items.items(), key=lambda kv: (kv[0].view, kv[0].index)):
        input_items.append({"view": k.view, "index": k.index, "text": text})

    constraints = "\n".join(
        [
            "Output format constraints:",
            "- Output MUST be a single JSON object (no markdown fences).",
            "- Each input item MUST map to 1..N paths (array of strings).",
            f"- Max paths per item: {max_refs_per_item}.",
            "- Paths MUST be repo-relative and MUST NOT be absolute Windows paths.",
            "- Paths MUST end with .cs or .gd and be under one of:",
            f"  - {', '.join(ALLOWED_TEST_PREFIXES)}",
            "- Prefer selecting from existing candidate test files when they fit.",
            "- If no existing file fits, propose a NEW path following repo conventions.",
            "- Do NOT use placeholder-like names such as:",
            f"  - Game.Core.Tests/Tasks/Task{task_id}AcceptanceTests.cs",
            f"  - Tests.Godot/tests/Scenes/Sanguo/test_task{task_id}_acceptance.gd",
            "- Prefer subject-based naming and directory semantics:",
            "  - Core domain/value objects: Game.Core.Tests/Domain/<Subject>Tests.cs",
            "  - Core services/game loop:   Game.Core.Tests/Services/<Subject>Tests.cs",
            "  - Task-scoped only when truly cross-cutting: Game.Core.Tests/Tasks/Task<id><Topic>Tests.cs",
            "    - <Topic> must be short English PascalCase (2-5 words), describing behavior, not 'Acceptance'.",
            "  - Godot scene/UI behaviors:",
            "    - Tests.Godot/tests/Scenes/Sanguo/test_sanguo_<scene>_<behavior>.gd",
            "    - Tests.Godot/tests/UI/test_hud_<behavior>.gd",
        ]
    )

    testing_excerpt = _extract_testing_framework_excerpt()
    testing_excerpt = _truncate(testing_excerpt, max_chars=6_000)

    return "\n\n".join(
        [
            "Role: acceptance-refs-planner",
            "",
            "You will propose test file references for acceptance items.",
            "",
            constraints,
            "",
            "Repository testing conventions excerpt (docs/testing-framework.md):",
            testing_excerpt or "(missing)",
            "",
            "PRD (truncated excerpt):",
            prd_excerpt or "(empty)",
            "",
            "Task Context:",
            f"- task_id: {task_id}",
            f"- title: {title or '(empty)'}",
            f"- master.details (truncated): {master_details or '(empty)'}",
            "",
            "Triplet hints:",
            f"- back.layer: {str((back or {}).get('layer') or '')}",
            f"- gameplay.layer: {str((gameplay or {}).get('layer') or '')}",
            "",
            "Existing candidate test files (prefer these if appropriate):",
            "\n".join([f"- {p}" for p in existing_candidates]) if existing_candidates else "(none)",
            "",
            "Input acceptance items needing Refs:",
            json.dumps(input_items, ensure_ascii=False, indent=2),
            "",
            "Return JSON with this schema:",
            json.dumps(
                {
                    "task_id": task_id,
                    "items": [
                        {"view": "back", "index": 0, "paths": ["Game.Core.Tests/Tasks/Task1AcceptanceTests.cs"]},
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "",
            "Additional context (do not copy verbatim into output):",
            f"- back.test_strategy: {json.dumps(back_strategy, ensure_ascii=False)[:2000]}",
            f"- gameplay.test_strategy: {json.dumps(gameplay_strategy, ensure_ascii=False)[:2000]}",
            f"- back.acceptance (first): {back_acceptance[0] if back_acceptance else '(none)'}",
            f"- gameplay.acceptance (first): {gameplay_acceptance[0] if gameplay_acceptance else '(none)'}",
        ]
    ).strip() + "\n"


def _apply_paths_to_view_entry(
    *,
    root: Path,
    entry: dict[str, Any],
    view_label: str,
    task_id: int,
    overwrite_existing: bool,
    paths_by_index: dict[int, list[str]],
    prefer_gd: bool,
    existing_cs_hint: str | None,
    existing_gd_hint: str | None,
) -> dict[str, Any]:
    acceptance = entry.get("acceptance")
    if not isinstance(acceptance, list):
        return {"view": view_label, "task_id": task_id, "updated": 0}

    test_refs = entry.get("test_refs")
    if not isinstance(test_refs, list):
        test_refs = []
    norm_test_refs = [str(x).strip().replace("\\", "/") for x in test_refs if str(x).strip()]

    updated = 0
    new_acceptance: list[str] = []
    for idx, raw in enumerate(acceptance):
        text = str(raw or "").strip()
        if not text:
            new_acceptance.append(text)
            continue

        had_refs = bool(REFS_RE.search(text))
        if had_refs and not overwrite_existing:
            new_acceptance.append(text)
            continue

        if idx not in paths_by_index:
            # If overwriting but model did not return a mapping for this index,
            # keep original.
            new_acceptance.append(text)
            continue

        candidate = [p.replace("\\", "/") for p in paths_by_index[idx] if str(p).strip()]
        valid = [p for p in candidate if _is_allowed_test_path(p)]

        # Prefer existing files.
        existing = [p for p in valid if (root / p).exists()]

        # If the model proposes only non-existing paths but we already have existing tests
        # for this task, bind to the existing tests to avoid creating brittle placeholders.
        desired_ext = ".gd" if (prefer_gd or any(p.endswith(".gd") for p in valid)) else ".cs"
        hint = existing_gd_hint if desired_ext == ".gd" else existing_cs_hint
        if not existing and hint and _is_allowed_test_path(hint) and (root / hint).exists():
            chosen = [hint]
        else:
            chosen = existing if existing else valid

        if not chosen:
            chosen = [_default_ref_for(task_id=task_id, prefer_gd=prefer_gd)]

        chosen = chosen[: max(1, min(len(chosen), 5))]
        if overwrite_existing:
            text = _strip_refs_suffix(text)
        new_text = f"{text} Refs: {' '.join(chosen)}"
        new_acceptance.append(new_text)
        updated += 1

        for p in chosen:
            if p not in norm_test_refs:
                norm_test_refs.append(p)

    entry["acceptance"] = new_acceptance
    entry["test_refs"] = norm_test_refs
    return {"view": view_label, "task_id": task_id, "updated": updated}


def main() -> int:
    ap = argparse.ArgumentParser(description="Fill acceptance Refs: using Codex CLI (LLM).")
    ap.add_argument("--all", action="store_true", help="Process all tasks in tasks_back/tasks_gameplay.")
    ap.add_argument("--task-id", default=None, help="Process a single task id (master id).")
    ap.add_argument("--write", action="store_true", help="Write JSON files in-place. Without this flag, dry-run.")
    ap.add_argument("--overwrite-existing", action="store_true", help="Overwrite existing Refs: in acceptance items.")
    ap.add_argument("--timeout-sec", type=int, default=300, help="codex exec timeout per task (default: 300).")
    ap.add_argument("--max-refs-per-item", type=int, default=2, help="Max refs per acceptance item (default: 2).")
    ap.add_argument("--candidate-limit", type=int, default=30, help="Max existing candidate tests to provide to the model.")
    ap.add_argument("--max-tasks", type=int, default=0, help="Optional safety cap; 0 means no limit.")
    args = ap.parse_args()

    root = repo_root()
    out_dir = ci_dir("sc-llm-acceptance-refs")

    tasks_json_p, back_p, gameplay_p = default_paths()
    tasks_json = load_json(tasks_json_p)
    master_by_id = {str(t.get("id")): t for t in iter_master_tasks(tasks_json)}

    back = load_json(back_p)
    gameplay = load_json(gameplay_p)
    if not isinstance(back, list) or not isinstance(gameplay, list):
        print("SC_LLM_ACCEPTANCE_REFS ERROR: tasks_back/tasks_gameplay must be JSON arrays.")
        return 2

    all_tests = _list_existing_tests()
    prd_excerpt = _extract_prd_excerpt()

    # Build a map for quick lookup.
    back_by_id = {int(t.get("taskmaster_id")): t for t in back if isinstance(t, dict) and isinstance(t.get("taskmaster_id"), int)}
    gameplay_by_id = {
        int(t.get("taskmaster_id")): t for t in gameplay if isinstance(t, dict) and isinstance(t.get("taskmaster_id"), int)
    }

    task_ids: list[int] = []
    if args.task_id:
        task_ids = [int(str(args.task_id).split(".", 1)[0])]
    else:
        if not args.all:
            print("SC_LLM_ACCEPTANCE_REFS ERROR: specify --task-id <n> or --all")
            return 2
        task_ids = sorted(set(back_by_id.keys()) | set(gameplay_by_id.keys()))

    if args.max_tasks and args.max_tasks > 0:
        task_ids = task_ids[: int(args.max_tasks)]

    results: list[dict[str, Any]] = []
    hard_fail = False
    any_updates = 0

    for tid in task_ids:
        master = master_by_id.get(str(tid))
        back_task = back_by_id.get(tid)
        gameplay_task = gameplay_by_id.get(tid)

        missing: dict[ItemKey, str] = {}
        prefer_gd = False
        if isinstance(back_task, dict) and str(back_task.get("layer") or "").strip().lower() == "ui":
            prefer_gd = True
        if isinstance(gameplay_task, dict) and str(gameplay_task.get("layer") or "").strip().lower() == "ui":
            prefer_gd = True

        def _collect(view: str, entry: dict[str, Any] | None) -> None:
            if not isinstance(entry, dict):
                return
            acc = entry.get("acceptance")
            if not isinstance(acc, list):
                return
            for idx, a in enumerate(acc):
                s = str(a or "").strip()
                if not s:
                    continue
                if REFS_RE.search(s) and not args.overwrite_existing:
                    continue
                # In overwrite mode we still need LLM mapping for every item.
                missing[ItemKey(view=view, index=idx)] = _strip_refs_suffix(s) if args.overwrite_existing else s

        _collect("back", back_task)
        _collect("gameplay", gameplay_task)

        if not missing:
            results.append({"task_id": tid, "status": "skipped", "reason": "no_missing_refs"})
            continue

        title = str((master or {}).get("title") or "")
        existing_candidates = _pick_existing_candidates(
            all_tests=all_tests, task_id=tid, title=title, limit=int(args.candidate_limit)
        )
        existing_cs_hint = next((p for p in existing_candidates if p.endswith(".cs") and (root / p).exists()), None)
        existing_gd_hint = next((p for p in existing_candidates if p.endswith(".gd") and (root / p).exists()), None)

        prompt = _build_prompt(
            prd_excerpt=prd_excerpt,
            task_id=tid,
            master=master,
            back=back_task,
            gameplay=gameplay_task,
            missing_items=missing,
            existing_candidates=existing_candidates,
            max_refs_per_item=int(args.max_refs_per_item),
        )

        prompt_path = out_dir / f"prompt-{tid}.txt"
        last_msg_path = out_dir / f"codex-last-{tid}.txt"
        trace_path = out_dir / f"codex-trace-{tid}.log"
        write_text(prompt_path, prompt)

        rc, trace_out, cmd = _run_codex_exec(prompt=prompt, out_last_message=last_msg_path, timeout_sec=int(args.timeout_sec))
        write_text(trace_path, trace_out)
        last_msg = _read_text(last_msg_path) if last_msg_path.exists() else ""

        task_result: dict[str, Any] = {
            "task_id": tid,
            "status": "ok",
            "rc": rc,
            "cmd": cmd,
            "prompt": str(prompt_path.relative_to(root)).replace("\\", "/"),
            "trace": str(trace_path.relative_to(root)).replace("\\", "/"),
            "output": str(last_msg_path.relative_to(root)).replace("\\", "/"),
            "missing_items": len(missing),
        }

        if rc != 0 or not last_msg.strip():
            task_result["status"] = "fail"
            task_result["error"] = "codex exec failed/empty output"
            results.append(task_result)
            hard_fail = True
            continue

        try:
            obj = _extract_json_object(last_msg)
            items = obj.get("items")
            if not isinstance(items, list):
                raise ValueError("items must be a list")

            by_view_index: dict[str, dict[int, list[str]]] = {"back": {}, "gameplay": {}}
            for it in items:
                if not isinstance(it, dict):
                    continue
                view = str(it.get("view") or "").strip().lower()
                if view not in ("back", "gameplay"):
                    continue
                idx = it.get("index")
                if not isinstance(idx, int):
                    continue
                paths = it.get("paths")
                if not isinstance(paths, list):
                    continue
                cleaned = [str(p).strip().replace("\\", "/") for p in paths if str(p).strip()]
                cleaned = [p for p in cleaned if _is_allowed_test_path(p)]
                if not cleaned:
                    continue
                by_view_index[view][idx] = cleaned[: int(args.max_refs_per_item)]

            # Ensure every missing item has at least one mapping (fallback).
            for k in missing:
                if k.view not in by_view_index:
                    by_view_index[k.view] = {}
                if k.index not in by_view_index[k.view]:
                    by_view_index[k.view][k.index] = [_default_ref_for(task_id=tid, prefer_gd=prefer_gd)]

            if args.write:
                if isinstance(back_task, dict):
                    applied = _apply_paths_to_view_entry(
                        root=root,
                        entry=back_task,
                        view_label="back",
                        task_id=tid,
                        overwrite_existing=bool(args.overwrite_existing),
                        paths_by_index=by_view_index["back"],
                        prefer_gd=prefer_gd,
                        existing_cs_hint=existing_cs_hint,
                        existing_gd_hint=existing_gd_hint,
                    )
                    any_updates += int(applied.get("updated") or 0)
                if isinstance(gameplay_task, dict):
                    applied = _apply_paths_to_view_entry(
                        root=root,
                        entry=gameplay_task,
                        view_label="gameplay",
                        task_id=tid,
                        overwrite_existing=bool(args.overwrite_existing),
                        paths_by_index=by_view_index["gameplay"],
                        prefer_gd=prefer_gd,
                        existing_cs_hint=existing_cs_hint,
                        existing_gd_hint=existing_gd_hint,
                    )
                    any_updates += int(applied.get("updated") or 0)

            task_result["mapped_items"] = sum(len(v) for v in by_view_index.values())
            results.append(task_result)
        except Exception as exc:  # noqa: BLE001
            task_result["status"] = "fail"
            task_result["error"] = str(exc)
            results.append(task_result)
            hard_fail = True

    if args.write and any_updates > 0:
        # Write JSON views back only when there were actual updates to avoid noisy rewrites.
        back_p.write_text(json.dumps(back, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        gameplay_p.write_text(json.dumps(gameplay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    # Final deterministic sanity check: all acceptance items have Refs: now (for the processed tasks).
    missing_after = 0
    if args.write and any_updates > 0:
        for tid in task_ids:
            for view_label, entry in [("back", back_by_id.get(tid)), ("gameplay", gameplay_by_id.get(tid))]:
                if not isinstance(entry, dict):
                    continue
                for a in entry.get("acceptance") or []:
                    s = str(a or "").strip()
                    if s and not REFS_RE.search(s):
                        missing_after += 1

    summary = {
        "cmd": "sc-llm-fill-acceptance-refs",
        "date": today_str(),
        "write": bool(args.write),
        "overwrite_existing": bool(args.overwrite_existing),
        "tasks": len(task_ids),
        "any_updates": any_updates,
        "results": results,
        "missing_after_write": missing_after,
        "out_dir": str(out_dir),
    }
    write_json(out_dir / "summary.json", summary)

    status = "fail" if hard_fail or (args.write and missing_after) else "ok"
    print(f"SC_LLM_ACCEPTANCE_REFS status={status} tasks={len(task_ids)} out={out_dir}")
    return 1 if status == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
