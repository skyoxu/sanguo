#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ensure PRD-SANGUO-T2 overlay 08 markdown files include CH01/CH03 references.

This is required by scripts/ci/verify_base_clean.ps1 (overlay CH reference guardrail).

We implement it in a deterministic, UTF-8 safe way:
- If a file has YAML front matter (--- ... ---), insert "Arch-Refs: [CH01, CH03]" list if missing.
- If a file does not have front matter, do not guess; fail with a clear message.

Logs:
  logs/ci/<YYYY-MM-DD>/overlay-arch-refs/changes.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import List


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OVERLAY_DIR = PROJECT_ROOT / "docs" / "architecture" / "overlays" / "PRD-SANGUO-T2" / "08"


@dataclass(frozen=True)
class Change:
    file: str
    action: str


ARCH_REFS_BLOCK = "Arch-Refs:\n  - CH01\n  - CH03\n"


def split_front_matter(text: str) -> tuple[str, str, str]:
    if not text.startswith("---\n"):
        raise ValueError("missing_front_matter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("unterminated_front_matter")
    fm = text[4:end + 1]  # include trailing newline
    rest = text[end + len("\n---\n") :]
    return "---\n", fm, "---\n" + rest


def ensure_arch_refs(text: str) -> tuple[str, bool]:
    start, fm, tail = split_front_matter(text)
    if "Arch-Refs:" in fm:
        return text, False

    # Insert after ADR-Refs block when present; otherwise append to front matter.
    insert_at = None
    if "ADR-Refs:" in fm:
        # After ADR-Refs list: find next top-level key (non-indented, contains ':')
        lines = fm.splitlines(keepends=True)
        idx = None
        for i, line in enumerate(lines):
            if line.startswith("ADR-Refs:"):
                idx = i
                break
        if idx is not None:
            j = idx + 1
            while j < len(lines):
                line = lines[j]
                if line.startswith("  - "):
                    j += 1
                    continue
                if line.strip() == "":
                    j += 1
                    continue
                if not line.startswith(" "):
                    insert_at = j
                break
            if insert_at is None:
                insert_at = len(lines)

            lines.insert(insert_at, ARCH_REFS_BLOCK)
            new_fm = "".join(lines)
            return start + new_fm + tail, True

    new_fm = fm
    if not new_fm.endswith("\n"):
        new_fm += "\n"
    new_fm += ARCH_REFS_BLOCK
    return start + new_fm + tail, True


def add_minimal_front_matter(text: str, title: str) -> str:
    header = (
        "---\n"
        "PRD-ID: PRD-SANGUO-T2\n"
        f"Title: {title}\n"
        "Arch-Refs:\n"
        "  - CH01\n"
        "  - CH03\n"
        "---\n\n"
    )
    return header + text


def guess_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip() or fallback
    return fallback


def write_audit(changes: List[Change]) -> Path:
    out_dir = PROJECT_ROOT / "logs" / "ci" / date.today().isoformat() / "overlay-arch-refs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "changes.json"
    payload = {
        "generated": datetime.now().isoformat(),
        "overlay_dir": str(OVERLAY_DIR),
        "changes": [c.__dict__ for c in changes],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def main() -> int:
    if not OVERLAY_DIR.exists():
        raise SystemExit(f"Missing overlay dir: {OVERLAY_DIR}")

    changes: List[Change] = []
    for path in sorted(OVERLAY_DIR.glob("*.md")):
        rel = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        text = path.read_text(encoding="utf-8")
        try:
            new_text, changed = ensure_arch_refs(text)
        except ValueError as e:
            if str(e) != "missing_front_matter":
                raise SystemExit(f"{rel}: {e}") from e
            title = guess_title(text, fallback=path.stem)
            new_text = add_minimal_front_matter(text, title=title)
            changed = True

        if changed:
            path.write_text(new_text, encoding="utf-8", newline="\n")
            changes.append(Change(file=rel, action="insert_arch_refs"))

    audit = write_audit(changes)
    print(f"[overlay-arch-refs] changed={len(changes)} audit={audit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
