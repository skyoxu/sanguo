from __future__ import annotations

from pathlib import Path


REQUIRED_CHECKLIST_HEADINGS = [
    "\u4e00\u3001\u6587\u6863\u5b8c\u6574\u6027\u9a8c\u6536",
    "\u4e8c\u3001\u67b6\u6784\u8bbe\u8ba1\u9a8c\u6536",
    "\u4e09\u3001\u4ee3\u7801\u5b9e\u73b0\u9a8c\u6536",
    "\u56db\u3001\u6d4b\u8bd5\u6846\u67b6\u9a8c\u6536",
]

REQUIRED_PRD_DOCS_BY_ID: dict[str, list[str]] = {
    "PRD-SANGUO-V3": [
        "PRD_V3_TRACEABILITY_MATRIX.md",
        "PRD_V3_RULES_FREEZE.md",
        "PRD_V3_ACCEPTANCE_ASSERTIONS.md",
    ]
}


def parse_prd_docs_csv(value: str | None) -> list[str]:
    if not str(value or "").strip():
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def validate_required_prd_docs(*, prd_id: str, companion_paths: list[Path]) -> list[str]:
    required = REQUIRED_PRD_DOCS_BY_ID.get(str(prd_id).strip(), [])
    if not required:
        return []
    present_names = {path.name for path in companion_paths}
    return [name for name in required if name not in present_names]
