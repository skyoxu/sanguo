#!/usr/bin/env python3
"""Initialize the project-owned resource knowledge catalog under docs/."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

FILES = {
    "README.md": "# 项目资源知识目录\n\nChapter 6 发现的配置、素材、场景、代码和测试关联。运行日志仍只写入 logs/**。\n",
    "schema/resource-link.schema.json": {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object", "required": ["id", "path", "kind", "confidence", "source_revision", "evidence"]},
    "catalog/knowledge-catalog.json": {"schema_version": "1.0", "project": "newrouge", "entries": [], "last_scan_revision": None},
    "catalog/config-catalog.json": {"schema_version": "1.0", "entries": []},
    "catalog/asset-catalog.json": {"schema_version": "1.0", "entries": []},
    "generated/task-resource-links.json": {"schema_version": "1.0", "generated": [], "source_revision": None},
    "generated/code-resource-links.json": {"schema_version": "1.0", "generated": [], "source_revision": None},
    "indexes/manifest.json": {"schema_version": "1.0", "current_generation": None, "source_revision": None},
}

def initialize(root: Path, force: bool = False, validate: bool = False) -> dict:
    base = root / "docs" / "knowledge"
    created, skipped = [], []
    for relative, value in FILES.items():
        path = base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not force:
            skipped.append(relative); continue
        path.write_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        created.append(relative)
    result = {"status": "ok", "root": "docs/knowledge", "created": created, "skipped": skipped, "validated": validate, "generated_at": datetime.now(timezone.utc).isoformat()}
    if validate:
        result["valid"] = all((base / relative).exists() for relative in FILES)
        issues = []
        catalog = base / "catalog/knowledge-catalog.json"
        if catalog.exists():
            try:
                payload = json.loads(catalog.read_text(encoding="utf-8"))
                entries = payload.get("entries", [])
                ids = [item.get("id") for item in entries]
                if len(ids) != len(set(ids)):
                    issues.append("duplicate_entry_id")
                for item in entries:
                    if not all(item.get(key) for key in ("id", "path", "kind", "confidence", "source_revision")):
                        issues.append("entry_missing_required_field")
            except (OSError, json.JSONDecodeError):
                issues.append("invalid_catalog_json")
        result["issues"] = issues
        result["valid"] = result["valid"] and not issues
        if not result["valid"]: result["status"] = "failed"
    return result

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--repo-root", type=Path, default=Path.cwd()); parser.add_argument("--force", action="store_true"); parser.add_argument("--validate", action="store_true")
    args = parser.parse_args(argv); print(json.dumps(initialize(args.repo_root.resolve(), args.force, args.validate), ensure_ascii=False)); return 0

if __name__ == "__main__": raise SystemExit(main())
