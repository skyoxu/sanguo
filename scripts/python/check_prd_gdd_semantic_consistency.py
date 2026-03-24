#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hard semantic consistency gate for PRD/GDD documents.

Template-safe behavior:
- If the config file is missing, this script reports "skipped" and exits 0.
- If the config file exists, the script enforces configured required clauses
  and contradiction scans across the PRD/GDD corpus.

Config example:
{
  "core_files": [
    "docs/prd/PRD-EXAMPLE.md",
    "docs/gdd/GDD-EXAMPLE.md"
  ],
  "scan_globs": [
    "docs/prd/*.md",
    "docs/gdd/*.md"
  ],
  "required_rules": {
    "rule_name": {
      "patterns": ["regex1", "regex2"]
    }
  },
  "contradiction_rules": [
    {
      "rule": "rule_id",
      "all_terms": ["token1", "token2"],
      "exclude_terms": ["must not", "forbidden"],
      "context_exclude_terms": ["anti-pattern", "example"],
      "window_radius": 3
    }
  ]
}

Output:
  logs/ci/<YYYY-MM-DD>/prd-gdd-consistency/summary.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path("scripts/python/config/prd-gdd-consistency-rules.json")
DEFAULT_SCAN_GLOBS = ["docs/prd/*.md", "docs/gdd/*.md"]


def _today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _to_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _load_config(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _expand_globs(repo_root: Path, patterns: list[str]) -> list[Path]:
    files: dict[str, Path] = {}
    for pattern in patterns:
        for item in repo_root.glob(pattern):
            if item.is_file():
                rel = _to_posix(item.relative_to(repo_root))
                files[rel] = item.resolve()
    return [files[key] for key in sorted(files)]


def _resolve_core_files(repo_root: Path, config: dict[str, Any]) -> list[Path]:
    raw_core = config.get("core_files") or []
    if isinstance(raw_core, list) and raw_core:
        files: list[Path] = []
        for item in raw_core:
            rel = str(item or "").strip()
            if not rel:
                continue
            files.append((repo_root / rel).resolve())
        return files
    scan_globs = config.get("scan_globs") or DEFAULT_SCAN_GLOBS
    if not isinstance(scan_globs, list):
        scan_globs = DEFAULT_SCAN_GLOBS
    return _expand_globs(repo_root, [str(x) for x in scan_globs])


def _iter_scope_files(repo_root: Path, config: dict[str, Any]) -> list[Path]:
    scan_globs = config.get("scan_globs") or DEFAULT_SCAN_GLOBS
    if not isinstance(scan_globs, list):
        scan_globs = DEFAULT_SCAN_GLOBS
    return _expand_globs(repo_root, [str(x) for x in scan_globs])


def _required_rules_check(repo_root: Path, core_files: list[Path], required_rules: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    normalized_rules: dict[str, list[str]] = {}
    for rule_name, rule_config in required_rules.items():
        if isinstance(rule_config, dict):
            patterns = rule_config.get("patterns") or []
        else:
            patterns = rule_config or []
        normalized_rules[str(rule_name)] = [str(x) for x in patterns if str(x).strip()]

    for file_path in core_files:
        rel = _to_posix(file_path.relative_to(repo_root)) if file_path.exists() and str(file_path).startswith(str(repo_root)) else _to_posix(file_path)
        if not file_path.exists():
            checks.append(
                {
                    "file": rel,
                    "status": "fail",
                    "reason": "missing_core_file",
                    "rules": {},
                }
            )
            continue
        text = file_path.read_text(encoding="utf-8")
        file_rules: dict[str, bool] = {}
        for rule_name, patterns in normalized_rules.items():
            file_rules[rule_name] = any(re.search(pattern, text, re.IGNORECASE | re.MULTILINE) for pattern in patterns)
        checks.append(
            {
                "file": rel,
                "status": "ok" if all(file_rules.values()) else "fail",
                "reason": "" if all(file_rules.values()) else "missing_required_rule_clause",
                "rules": file_rules,
            }
        )
    return checks


def _contains_any(text: str, tokens: list[str]) -> bool:
    lowered = text.lower()
    return any(str(token).lower() in lowered for token in tokens)


def _window_has_any(lines: list[str], index: int, tokens: list[str], radius: int) -> bool:
    start = max(0, index - radius)
    end = min(len(lines), index + radius + 1)
    window = "\n".join(lines[start:end]).lower()
    return any(str(token).lower() in window for token in tokens)


def _contradiction_hits(repo_root: Path, scope_files: list[Path], contradiction_rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    normalized_rules: list[dict[str, Any]] = []
    for item in contradiction_rules:
        if not isinstance(item, dict):
            continue
        normalized_rules.append(
            {
                "rule": str(item.get("rule") or "unnamed_rule"),
                "all_terms": [str(x) for x in (item.get("all_terms") or []) if str(x).strip()],
                "exclude_terms": [str(x) for x in (item.get("exclude_terms") or []) if str(x).strip()],
                "context_exclude_terms": [str(x) for x in (item.get("context_exclude_terms") or []) if str(x).strip()],
                "window_radius": max(0, int(item.get("window_radius") or 0)),
            }
        )

    for file_path in scope_files:
        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        in_code_block = False
        for line_number, raw_line in enumerate(lines, 1):
            line = raw_line.strip()
            if line.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block or not line:
                continue
            for rule in normalized_rules:
                if not rule["all_terms"]:
                    continue
                lowered = line.lower()
                if any(term.lower() not in lowered for term in rule["all_terms"]):
                    continue
                if rule["exclude_terms"] and _contains_any(line, rule["exclude_terms"]):
                    continue
                if rule["context_exclude_terms"] and _window_has_any(lines, line_number - 1, rule["context_exclude_terms"], rule["window_radius"]):
                    continue
                hits.append(
                    {
                        "rule": rule["rule"],
                        "file": _to_posix(file_path.relative_to(repo_root)),
                        "line": line_number,
                        "text": line,
                    }
                )
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="Hard semantic consistency gate for PRD/GDD documents.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG).replace("\\", "/"), help="JSON config path.")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    input_config = Path(args.config)
    config_path = (repo_root / input_config).resolve() if not input_config.is_absolute() else input_config
    out_dir = repo_root / "logs" / "ci" / _today_str() / "prd-gdd-consistency"
    out_path = out_dir / "summary.json"

    config = _load_config(config_path)
    if config is None:
        summary = {
            "status": "skipped",
            "reason": "missing_config",
            "config": _to_posix(config_path.relative_to(repo_root)) if str(config_path).startswith(str(repo_root)) else _to_posix(config_path),
            "required_checks": [],
            "contradiction_hits": [],
        }
        _write_json(out_path, summary)
        print(f"PRD_GDD_CONSISTENCY status=skipped reason=missing_config out={_to_posix(out_path.relative_to(repo_root))}")
        return 0

    try:
        core_files = _resolve_core_files(repo_root, config)
        scope_files = _iter_scope_files(repo_root, config)
        required_rules = config.get("required_rules") or {}
        contradiction_rules = config.get("contradiction_rules") or []
        required_checks = _required_rules_check(repo_root, core_files, required_rules if isinstance(required_rules, dict) else {})
        contradiction_hits = _contradiction_hits(repo_root, scope_files, contradiction_rules if isinstance(contradiction_rules, list) else [])
        failed_required = sum(1 for item in required_checks if item.get("status") == "fail")
        status = "ok" if failed_required == 0 and not contradiction_hits else "fail"
        summary = {
            "status": status,
            "config": _to_posix(config_path.relative_to(repo_root)) if str(config_path).startswith(str(repo_root)) else _to_posix(config_path),
            "core_files": [
                _to_posix(path.relative_to(repo_root)) if path.exists() and str(path).startswith(str(repo_root)) else _to_posix(path)
                for path in core_files
            ],
            "scan_files": [_to_posix(path.relative_to(repo_root)) for path in scope_files],
            "required_checks": required_checks,
            "contradiction_hits": contradiction_hits,
            "summary": {
                "failed_required": failed_required,
                "contradiction_hits": len(contradiction_hits),
            },
        }
        _write_json(out_path, summary)
        print(
            "PRD_GDD_CONSISTENCY "
            f"status={status} failed_required={failed_required} contradiction_hits={len(contradiction_hits)} "
            f"out={_to_posix(out_path.relative_to(repo_root))}"
        )
        return 0 if status == "ok" else 1
    except Exception as exc:
        summary = {
            "status": "error",
            "reason": str(exc),
            "config": _to_posix(config_path.relative_to(repo_root)) if str(config_path).startswith(str(repo_root)) else _to_posix(config_path),
        }
        _write_json(out_path, summary)
        print(f"PRD_GDD_CONSISTENCY status=error reason={exc} out={_to_posix(out_path.relative_to(repo_root))}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

