from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from _knowledge_catalog_builder import GitSnapshot, build_layers


OUTPUT_PATHS = {
    "snapshot": Path("knowledge/snapshots/repository-source-snapshot.v1.json"),
    "catalog": Path("knowledge/catalogs/repository-knowledge-catalog.v1.json"),
    "projections": Path("knowledge/projections/consumer-projections.v1.json"),
}


def _canonical_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _canonical_text(value)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        delete=False,
        dir=path.parent,
        suffix=".tmp",
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _check_outputs(root: Path, outputs: dict[Path, dict[str, Any]]) -> list[str]:
    stale: list[str] = []
    for relative, expected in outputs.items():
        path = root / relative
        if not path.is_file():
            stale.append(f"missing:{relative.as_posix()}")
            continue
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            stale.append(f"invalid:{relative.as_posix()}")
            continue
        if current != expected:
            stale.append(f"stale:{relative.as_posix()}")
    return stale


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build newrouge repository knowledge layers from a trusted git ref."
    )
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--authority-ref", default="refs/heads/main")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    root = args.repository_root.resolve()
    policies = json.loads(
        (root / "knowledge/policies/consumer-policies.v1.json").read_text(encoding="utf-8")
    )
    exclusions = json.loads(
        (root / "knowledge/policies/source-exclusions.v1.json").read_text(encoding="utf-8")
    )
    snapshot, catalog, projections = build_layers(
        GitSnapshot(root, args.authority_ref), exclusions, policies
    )
    outputs = {
        OUTPUT_PATHS["snapshot"]: snapshot,
        OUTPUT_PATHS["catalog"]: catalog,
        OUTPUT_PATHS["projections"]: projections,
    }

    if args.write:
        for relative, value in outputs.items():
            _atomic_json(root / relative, value)

    stale = _check_outputs(root, outputs) if args.check else []
    status = "stale" if stale else "ok"
    print(
        json.dumps(
            {
                "status": status,
                "authority_ref": args.authority_ref,
                "commit": snapshot["commit"],
                "sources": len(snapshot["sources"]),
                "modules": len(catalog["modules"]),
                "written": args.write,
                "checked": args.check,
                "issues": stale,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
