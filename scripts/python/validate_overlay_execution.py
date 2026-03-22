#!/usr/bin/env python3
"""Validate overlay execution readiness in a template-safe way.

Compared with project-specific variants, this validator avoids fixed PRD names
and fixed T2 page file names. It validates a chosen overlay folder by:
1) checking required base files exist (`_index.md`, `ACCEPTANCE_CHECKLIST.md`);
2) checking front matter essentials for non-checklist pages (`PRD-ID`, `Title`);
3) checking optional required headings when passed via CLI;
4) checking concrete backtick path refs resolve on disk.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


VALID_PRD_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
OVERLAY_PRD_RE = re.compile(r"^docs/architecture/overlays/([^/]+)/08(?:/|$)")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def ci_out_dir() -> Path:
    out = repo_root() / "logs" / "ci" / today_str() / "overlay-lint"
    out.mkdir(parents=True, exist_ok=True)
    return out


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.replace("\r\n", "\n").rstrip("\n") + "\n", encoding="utf-8", newline="\n")


def to_posix(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def parse_front_matter(md: str) -> dict[str, Any]:
    lines = md.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {}

    block = lines[1:end_idx]
    result: dict[str, Any] = {}
    current_key: str | None = None

    for raw in block:
        line = raw.rstrip()
        if not line.strip():
            continue

        if re.match(r"^\s*-\s+", line) and current_key:
            result.setdefault(current_key, [])
            if isinstance(result[current_key], list):
                result[current_key].append(re.sub(r"^\s*-\s+", "", line).strip())
            continue

        match = re.match(r"^([A-Za-z0-9_\-]+)\s*:\s*(.*)$", line)
        if not match:
            continue

        key = match.group(1).strip()
        value = match.group(2).strip()
        current_key = key

        if value.startswith("[") and value.endswith("]"):
            body = value[1:-1].strip()
            result[key] = [x.strip() for x in body.split(",") if x.strip()] if body else []
        elif value == "":
            result[key] = []
        else:
            result[key] = value

    return result


def has_markdown_heading(md: str, heading: str) -> bool:
    pattern = rf"^##\s+{re.escape(heading)}\s*$"
    return re.search(pattern, md, flags=re.MULTILINE) is not None


def extract_backtick_paths(md: str) -> list[str]:
    refs = re.findall(r"`([^`]+)`", md)
    out: list[str] = []
    for ref in refs:
        text = ref.strip()
        if not text:
            continue
        if text.startswith("py -3 ") or text.startswith("dotnet ") or text.startswith("pwsh "):
            continue
        if "/" not in text and "\\" not in text:
            continue
        out.append(text.replace("\\", "/"))
    return out


def should_check_path(path: str) -> bool:
    if "<" in path or ">" in path:
        return False
    if path.startswith("logs/"):
        return False
    prefixes = (
        "docs/",
        "scripts/",
        "Game.Core/",
        "Game.Core.Tests/",
        "Game.Godot/",
        "Tests.Godot/",
        ".taskmaster/",
        "examples/",
    )
    return path.startswith(prefixes)


def validate_file_paths(root: Path, md_text: str, rel: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    refs = extract_backtick_paths(md_text)

    for ref in refs:
        if not should_check_path(ref):
            continue
        if not (root / ref).exists():
            errors.append(f"{rel}: missing referenced path: {ref}")

    if not refs:
        warnings.append(f"{rel}: no backtick references found")
    return errors, warnings


def find_overlay_pages(overlay_dir: Path) -> list[Path]:
    pages = [p for p in overlay_dir.glob("*.md") if p.is_file()]
    pages.sort(key=lambda p: p.name.lower())
    return pages


def auto_detect_prd_id(root: Path) -> str:
    task_files = [
        root / ".taskmaster" / "tasks" / "tasks.json",
        root / "examples" / "taskmaster" / "tasks.json",
    ]
    candidates: set[str] = set()
    for path in task_files:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        tasks = (payload.get("master") or {}).get("tasks") if isinstance(payload, dict) else None
        if not isinstance(tasks, list):
            continue
        for task in tasks:
            if not isinstance(task, dict):
                continue
            overlay = str(task.get("overlay", "")).strip()
            match = OVERLAY_PRD_RE.match(overlay.replace("\\", "/"))
            if match:
                candidates.add(match.group(1))
    if len(candidates) == 1:
        return next(iter(candidates))
    if len(candidates) > 1:
        ordered = sorted(candidates)
        raise ValueError(f"Auto-detect found multiple PRD IDs in task files: {ordered}. Use --prd-id.")

    overlays_root = root / "docs" / "architecture" / "overlays"
    fs_candidates = [p.name for p in overlays_root.iterdir() if p.is_dir() and (p / "08").exists()] if overlays_root.exists() else []
    if len(fs_candidates) == 1:
        return fs_candidates[0]
    if len(fs_candidates) > 1:
        ordered = sorted(fs_candidates)
        raise ValueError(f"Auto-detect found multiple PRD IDs in overlays: {ordered}. Use --prd-id.")
    raise ValueError("Cannot auto-detect PRD ID. Use --prd-id.")


def validate_overlay(prd_id: str, overlay_dir: Path, required_headings: list[str]) -> dict[str, Any]:
    root = repo_root()
    errors: list[str] = []
    warnings: list[str] = []

    if not VALID_PRD_ID_RE.fullmatch(prd_id.strip()):
        errors.append(f"invalid PRD ID: {prd_id}")
        return {
            "prd_id": prd_id,
            "overlay_dir": str(overlay_dir),
            "errors": errors,
            "warnings": warnings,
            "status": "fail",
        }

    required_core = ["_index.md", "ACCEPTANCE_CHECKLIST.md"]
    for name in required_core:
        if not (overlay_dir / name).exists():
            errors.append(f"missing required overlay file: {to_posix(overlay_dir / name, root)}")

    pages = find_overlay_pages(overlay_dir)
    if not pages:
        errors.append(f"no markdown pages found in overlay dir: {to_posix(overlay_dir, root)}")
    else:
        feature_count = len([p for p in pages if p.name.lower().startswith("08-") and p.name.lower() not in {"_index.md"}])
        if feature_count == 0:
            warnings.append(f"{to_posix(overlay_dir, root)}: no 08-*.md pages found")

    for page in pages:
        rel = to_posix(page, root)
        text = read_text(page)
        fm = parse_front_matter(text)

        if page.name != "ACCEPTANCE_CHECKLIST.md":
            if not fm:
                errors.append(f"{rel}: missing front matter block")
            else:
                if str(fm.get("PRD-ID", "")).strip() != prd_id:
                    errors.append(f"{rel}: PRD-ID mismatch, expected {prd_id}")
                if not str(fm.get("Title", "")).strip():
                    errors.append(f"{rel}: missing Title in front matter")
                if page.name != "_index.md" and not fm.get("Arch-Refs"):
                    warnings.append(f"{rel}: missing Arch-Refs in front matter")
                if page.name != "_index.md" and not fm.get("ADRs"):
                    warnings.append(f"{rel}: missing ADRs in front matter")
                if page.name not in {"_index.md", "ACCEPTANCE_CHECKLIST.md"} and not fm.get("Test-Refs"):
                    warnings.append(f"{rel}: missing Test-Refs in front matter")

        for heading in required_headings:
            if not has_markdown_heading(text, heading):
                errors.append(f"{rel}: missing section heading '## {heading}'")

        e2, w2 = validate_file_paths(root, text, rel)
        errors.extend(e2)
        warnings.extend(w2)

    checklist = overlay_dir / "ACCEPTANCE_CHECKLIST.md"
    if checklist.exists():
        body = read_text(checklist)
        if "| Check ID |" not in body and "- [ ]" not in body and "- [x]" not in body:
            warnings.append(f"{to_posix(checklist, root)}: no checklist table/checkbox markers found")

    return {
        "prd_id": prd_id,
        "overlay_dir": to_posix(overlay_dir, root),
        "required_headings": required_headings,
        "errors": errors,
        "warnings": warnings,
        "status": "ok" if not errors else "fail",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate overlay execution readiness (template-safe).")
    ap.add_argument("--prd-id", default="", help="PRD ID under docs/architecture/overlays/<PRD-ID>/08")
    ap.add_argument("--overlay-dir", default="", help="Explicit overlay 08 directory (optional).")
    ap.add_argument(
        "--require-heading",
        action="append",
        default=[],
        help="Require each page to contain a heading, e.g. --require-heading \"Task Mapping\"",
    )
    args = ap.parse_args()

    root = repo_root()
    try:
        prd_id = args.prd_id.strip() if args.prd_id.strip() else auto_detect_prd_id(root)
    except ValueError as exc:
        out_dir = ci_out_dir()
        report = {
            "prd_id": args.prd_id,
            "overlay_dir": args.overlay_dir,
            "errors": [str(exc)],
            "warnings": [],
            "status": "fail",
        }
        write_json(out_dir / "report.json", report)
        write_text(out_dir / "report.md", f"# Overlay Execution Validation\n\n- status: fail\n- error: {exc}\n")
        print(f"OVERLAY_EXEC_VALIDATION status=fail errors=1 warnings=0 out={out_dir}")
        return 2

    overlay_dir = (root / args.overlay_dir).resolve() if args.overlay_dir else (root / "docs" / "architecture" / "overlays" / prd_id / "08")
    report = validate_overlay(prd_id, overlay_dir, args.require_heading)
    out_dir = ci_out_dir()

    report_json = out_dir / "report.json"
    report_md = out_dir / "report.md"
    write_json(report_json, report)

    lines = [
        "# Overlay Execution Validation",
        "",
        f"- prd_id: {report['prd_id']}",
        f"- overlay_dir: {report['overlay_dir']}",
        f"- status: {report['status']}",
        f"- errors: {len(report['errors'])}",
        f"- warnings: {len(report['warnings'])}",
        "",
    ]
    if report["errors"]:
        lines.append("## Errors")
        for err in report["errors"]:
            lines.append(f"- {err}")
        lines.append("")
    if report["warnings"]:
        lines.append("## Warnings")
        for warn in report["warnings"]:
            lines.append(f"- {warn}")
        lines.append("")
    write_text(report_md, "\n".join(lines))

    print(
        f"OVERLAY_EXEC_VALIDATION status={report['status']} errors={len(report['errors'])} "
        f"warnings={len(report['warnings'])} out={out_dir}"
    )
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())

