from __future__ import annotations

from pathlib import Path


REQUIRED_CHECKLIST_HEADINGS = [
    "一、文档完整性验收",
    "二、架构设计验收",
    "三、代码实现验收",
    "四、测试框架验收",
]


def parse_prd_docs_csv(value: str | None) -> list[str]:
    if not str(value or "").strip():
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def validate_required_prd_docs(
    *,
    prd_id: str,
    companion_paths: list[Path],
    expected_doc_names: list[str] | None = None,
) -> list[str]:
    _ = prd_id
    required = [name.strip() for name in expected_doc_names or [] if str(name).strip()]
    if not required:
        return []
    present_names = {path.name for path in companion_paths}
    return [name for name in required if name not in present_names]
