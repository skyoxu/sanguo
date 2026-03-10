#!/usr/bin/env python3
import argparse
import datetime as dt
import io
import json
import os
import re
import sys


METHOD_RE = re.compile(
    r"^\s*(public|private|protected|internal)\s+(?:static\s+)?(?:async\s+)?[\w<>\[\],\.\?]+\s+\w+\s*\(")


def _read_json(path: str) -> dict:
    with io.open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    return obj if isinstance(obj, dict) else {}


def _write_json(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _to_rel(path: str, root: str) -> str:
    rel = os.path.relpath(path, root).replace("\\", "/")
    return rel


def _collect_metrics(abs_path: str) -> tuple[int, int]:
    with io.open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.read().splitlines()
    method_count = sum(1 for line in lines if METHOD_RE.search(line))
    return len(lines), method_count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="scripts/python/architecture_hotspots_budget.json")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    root = os.path.abspath(os.getcwd())
    date = dt.date.today().strftime("%Y-%m-%d")
    out_path = args.out or os.path.join(root, "logs", "ci", date, "architecture-hotspots", "summary.json")
    config_path = args.config
    if not os.path.isabs(config_path):
        config_path = os.path.join(root, config_path)

    if not os.path.isfile(config_path):
        summary = {
            "status": "fail",
            "reason": "config_missing",
            "config_path": _to_rel(config_path, root),
            "hotspots": [],
            "violations": [{"type": "config_missing", "config_path": _to_rel(config_path, root)}],
        }
        _write_json(out_path, summary)
        print(f"ARCH_HOTSPOTS status=fail out={out_path} reason=config_missing")
        return 1

    cfg = _read_json(config_path)
    hotspots = cfg.get("hotspots")
    if not isinstance(hotspots, list):
        summary = {
            "status": "fail",
            "reason": "invalid_config",
            "config_path": _to_rel(config_path, root),
            "hotspots": [],
            "violations": [{"type": "invalid_config", "field": "hotspots"}],
        }
        _write_json(out_path, summary)
        print(f"ARCH_HOTSPOTS status=fail out={out_path} reason=invalid_config")
        return 1

    measured: list[dict] = []
    violations: list[dict] = []

    for item in hotspots:
        if not isinstance(item, dict):
            violations.append({"type": "invalid_item"})
            continue
        raw_path = str(item.get("path") or "").strip()
        max_lines = int(item.get("max_lines") or 0)
        max_methods = int(item.get("max_methods") or 0)
        if not raw_path or max_lines <= 0 or max_methods <= 0:
            violations.append({"type": "invalid_item", "path": raw_path, "max_lines": max_lines, "max_methods": max_methods})
            continue

        abs_path = raw_path if os.path.isabs(raw_path) else os.path.join(root, raw_path)
        rel_path = _to_rel(abs_path, root)
        if not os.path.isfile(abs_path):
            violations.append({"type": "file_missing", "path": rel_path})
            measured.append({"path": rel_path, "exists": False, "max_lines": max_lines, "max_methods": max_methods})
            continue

        lines, methods = _collect_metrics(abs_path)
        measured.append(
            {
                "path": rel_path,
                "exists": True,
                "lines": lines,
                "methods": methods,
                "max_lines": max_lines,
                "max_methods": max_methods,
            }
        )
        if lines > max_lines:
            violations.append({"type": "lines_exceeded", "path": rel_path, "actual": lines, "max": max_lines})
        if methods > max_methods:
            violations.append({"type": "methods_exceeded", "path": rel_path, "actual": methods, "max": max_methods})

    status = "ok" if not violations else "fail"
    summary = {
        "status": status,
        "config_path": _to_rel(config_path, root),
        "hotspots": measured,
        "violations": violations,
    }
    _write_json(out_path, summary)
    print(f"ARCH_HOTSPOTS status={status} out={out_path} violations={len(violations)}")
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
