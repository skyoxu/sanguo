#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REFS_RE = re.compile(r"\bRefs\s*:\s*(.+)$", flags=re.IGNORECASE)
ALLOWED_TEST_PREFIXES = ("Game.Core.Tests/", "Tests.Godot/tests/")


@dataclass(frozen=True)
class ItemKey:
    view: str
    index: int


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def truncate(text: str, *, max_chars: int) -> str:
    value = str(text or "")
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3] + "..."


def run_codex_exec(*, root: Path, prompt: str, out_last_message: Path, timeout_sec: int) -> tuple[int, str, list[str]]:
    exe = shutil.which("codex")
    if not exe:
        return 127, "codex executable not found in PATH\n", ["codex"]
    cmd = [
        exe,
        "exec",
        "-s",
        "read-only",
        "-C",
        str(root),
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
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return 124, "codex exec timeout\n", cmd
    except Exception as exc:  # noqa: BLE001
        return 1, f"codex exec failed to start: {exc}\n", cmd
    return proc.returncode or 0, proc.stdout or "", cmd


def extract_json_object(text: str) -> dict[str, Any]:
    payload = str(text or "").strip()
    try:
        obj = json.loads(payload)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    m = re.search(r"\{.*\}", payload, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON object found in model output.")
    obj = json.loads(m.group(0))
    if not isinstance(obj, dict):
        raise ValueError("Model output JSON is not an object.")
    return obj


def is_abs_path(path: str) -> bool:
    s = str(path or "").strip()
    if not s:
        return False
    if os.path.isabs(s):
        return True
    return bool(len(s) >= 2 and s[1] == ":")


def is_allowed_test_path(path: str) -> bool:
    s = str(path or "").strip().replace("\\", "/")
    if not s or is_abs_path(s):
        return False
    if not (s.endswith(".cs") or s.endswith(".gd")):
        return False
    return s.startswith(ALLOWED_TEST_PREFIXES)


def is_evidence_path(path: str) -> bool:
    s = str(path or "").strip().replace("\\", "/")
    return s.startswith("logs/") or s.startswith("docs/")


def extend_unique(dst: list[str], items: list[str]) -> None:
    seen = set(dst)
    for raw in items:
        s = str(raw or "").strip().replace("\\", "/")
        if not s or s in seen:
            continue
        dst.append(s)
        seen.add(s)


def strip_refs_suffix(text: str) -> str:
    return REFS_RE.sub("", str(text or "")).rstrip()


def split_refs_blob(blob: str) -> list[str]:
    s = str(blob or "").strip().replace("`", "").replace(",", " ").replace(";", " ")
    return [p.strip().replace("\\", "/") for p in s.split() if p.strip()]


def extract_refs_from_acceptance_item(text: str) -> list[str]:
    m = REFS_RE.search(str(text or "").strip())
    if not m:
        return []
    return split_refs_blob(m.group(1))


def extract_prd_excerpt(*, root: Path) -> tuple[str, str]:
    ordered = [
        root / ".taskmaster" / "docs" / "prd.txt",
        root / "prd.txt",
        root / "prd_yuan.md",
    ]
    for path in ordered:
        if path.exists():
            return truncate(read_text(path), max_chars=10_000), str(path.relative_to(root)).replace("\\", "/")
    return "", ""


def list_existing_tests(*, root: Path) -> list[str]:
    out: list[str] = []
    for base, ext in [("Game.Core.Tests", ".cs"), ("Tests.Godot/tests", ".gd")]:
        p = root / base
        if not p.exists():
            continue
        for f in p.rglob(f"*{ext}"):
            if not f.is_file():
                continue
            rel = str(f.relative_to(root)).replace("\\", "/")
            if is_allowed_test_path(rel):
                out.append(rel)
    out.sort()
    return out


def pick_existing_candidates(*, all_tests: list[str], task_id: int, title: str, limit: int) -> list[str]:
    tid = str(task_id)
    by_tid = [p for p in all_tests if re.search(rf"\bTask{re.escape(tid)}\b", p, flags=re.IGNORECASE)]
    if by_tid:
        return by_tid[:limit]
    tokens = [t for t in re.split(r"[^A-Za-z0-9]+", str(title or "")) if t][:6]
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


def default_ref_for(*, task_id: int, prefer_gd: bool) -> str:
    if prefer_gd:
        return f"Tests.Godot/tests/UI/test_task{task_id}_acceptance.gd"
    return f"Game.Core.Tests/Tasks/Task{task_id}AcceptanceTests.cs"


def infer_preferred_kind(*, acceptance_text: str, prefer_gd_by_layer: bool) -> str:
    t = str(acceptance_text or "").lower()
    gd_hits = ["gdunit", "godot", "headless", "scene", ".tscn", "hud", "toast", "ui", "control", "node", "signal", "input"]
    cs_hits = ["xunit", "fluentassertions", "game.core", "domain", "service", "contracts", "dto", "eventtype", "money", "economy", "turn"]
    if any(k in t for k in gd_hits):
        return "gd"
    if any(k in t for k in cs_hits):
        return "cs"
    return "gd" if prefer_gd_by_layer else "either"


def is_placeholder_ref(*, task_id: int, path: str) -> bool:
    p = str(path or "").strip().replace("\\", "/")
    if not p:
        return False
    if p.lower().endswith(".cs"):
        return p == f"Game.Core.Tests/Tasks/Task{task_id}RequirementsTests.cs"
    if p.lower().endswith(".gd"):
        name = Path(p).name
        return re.search(rf"(?i)(?<!\\d)task{task_id}(?!\\d)", name) is not None
    return False


def is_a11y_task(*, master: dict[str, Any] | None) -> bool:
    title = str((master or {}).get("title") or "").strip().lower()
    desc = str((master or {}).get("description") or "").strip().lower()
    body = title + "\n" + desc
    return any(k in body for k in ("a11y", "accessibility", "wcag", "screen reader", "accessible"))


def collect_missing_for_entry(
    *,
    view: str,
    entry: dict[str, Any] | None,
    task_id: int,
    master: dict[str, Any] | None,
    overwrite_existing: bool,
    rewrite_placeholders: bool,
) -> tuple[dict[ItemKey, str], set[int]]:
    missing: dict[ItemKey, str] = {}
    overwrite_indices: set[int] = set()
    if not isinstance(entry, dict):
        return missing, overwrite_indices
    acc = entry.get("acceptance")
    if not isinstance(acc, list):
        return missing, overwrite_indices
    a11y_task = is_a11y_task(master=master)
    for idx, raw in enumerate(acc):
        s = str(raw or "").strip()
        if not s:
            continue
        if REFS_RE.search(s) and not overwrite_existing:
            refs = extract_refs_from_acceptance_item(s)
            if not refs:
                if not rewrite_placeholders:
                    continue
            has_non_test_ref = any(not is_allowed_test_path(p) for p in refs)
            if has_non_test_ref:
                overwrite_indices.add(idx)
            if not rewrite_placeholders and idx not in overwrite_indices:
                continue
            if (not a11y_task) and refs and all(str(p).replace("\\", "/").startswith("Tests.Godot/tests/UI/A11y/") for p in refs):
                overwrite_indices.add(idx)
                missing[ItemKey(view=view, index=idx)] = strip_refs_suffix(s)
                continue
            if refs and not all(is_placeholder_ref(task_id=task_id, path=p) for p in refs):
                continue
            overwrite_indices.add(idx)
        missing[ItemKey(view=view, index=idx)] = strip_refs_suffix(s) if (overwrite_existing or idx in overwrite_indices) else s
    return missing, overwrite_indices


def parse_model_items_to_paths(*, items: Any, max_refs_per_item: int) -> dict[str, dict[int, list[str]]]:
    by_view_index: dict[str, dict[int, list[str]]] = {"back": {}, "gameplay": {}}
    if not isinstance(items, list):
        return by_view_index
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
        cleaned = [p for p in cleaned if is_allowed_test_path(p)]
        if cleaned:
            by_view_index[view][idx] = cleaned[: int(max_refs_per_item)]
    return by_view_index


def apply_paths_to_view_entry(
    *,
    root: Path,
    entry: dict[str, Any],
    task_id: int,
    a11y_task: bool,
    overwrite_existing: bool,
    overwrite_indices: set[int] | None,
    paths_by_index: dict[int, list[str]],
    prefer_gd: bool,
) -> int:
    acceptance = entry.get("acceptance")
    if not isinstance(acceptance, list):
        return 0
    evidence_refs = entry.get("evidence_refs")
    if not isinstance(evidence_refs, list):
        evidence_refs = []
    evidence_refs = [str(x).strip().replace("\\", "/") for x in evidence_refs if str(x).strip()]
    test_refs = entry.get("test_refs")
    if not isinstance(test_refs, list):
        test_refs = []
    norm_test_refs: list[str] = []
    for raw_ref in test_refs:
        ref = str(raw_ref).strip().replace("\\", "/")
        if not ref:
            continue
        if is_allowed_test_path(ref):
            extend_unique(norm_test_refs, [ref])
        elif is_evidence_path(ref):
            extend_unique(evidence_refs, [ref])

    updated = 0
    new_acceptance: list[str] = []
    for idx, raw in enumerate(acceptance):
        text = str(raw or "").strip()
        if not text:
            new_acceptance.append(text)
            continue
        had_refs = bool(REFS_RE.search(text))
        existing_refs = extract_refs_from_acceptance_item(text) if had_refs else []
        existing_evidence_refs = [p for p in existing_refs if is_evidence_path(p)]
        if existing_evidence_refs:
            extend_unique(evidence_refs, existing_evidence_refs)
        should_overwrite = bool(overwrite_existing) or (overwrite_indices is not None and idx in overwrite_indices) or bool(existing_evidence_refs)
        if had_refs and not should_overwrite:
            new_acceptance.append(text)
            continue
        candidate = [p.replace("\\", "/") for p in (paths_by_index.get(idx) or []) if str(p).strip()]
        valid = [p for p in candidate if is_allowed_test_path(p)]
        if not a11y_task:
            valid = [p for p in valid if "/UI/A11y/" not in p.replace("\\", "/")]
        existing = [p for p in valid if (root / p).exists()]
        chosen = existing if existing else valid
        preferred = infer_preferred_kind(acceptance_text=text, prefer_gd_by_layer=prefer_gd)
        if preferred == "cs" and len(chosen) > 1:
            cs_only = [p for p in chosen if p.lower().endswith(".cs")]
            if cs_only:
                chosen = cs_only
        if preferred == "gd" and len(chosen) > 1:
            gd_only = [p for p in chosen if p.lower().endswith(".gd")]
            if gd_only:
                chosen = gd_only
        if not chosen:
            chosen = [p for p in existing_refs if is_allowed_test_path(p)]
        if not chosen:
            chosen = [default_ref_for(task_id=task_id, prefer_gd=prefer_gd)]
        chosen = chosen[: max(1, min(len(chosen), 5))]
        base = strip_refs_suffix(text) if had_refs else text
        new_acceptance.append(f"{base} Refs: {' '.join(chosen)}")
        updated += 1
        extend_unique(norm_test_refs, chosen)

    entry["acceptance"] = new_acceptance
    entry["test_refs"] = norm_test_refs
    entry["evidence_refs"] = evidence_refs
    return updated
