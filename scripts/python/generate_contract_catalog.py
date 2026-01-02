from __future__ import annotations

import argparse
from pathlib import Path

from contract_catalog_lib import generate_contract_catalog


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a contracts catalog markdown from repo state.")
    parser.add_argument("--repo-root", default=".", help="Repository root (default: .)")
    parser.add_argument(
        "--out-doc",
        default="docs/workflows/contracts-catalog-prd-sanguo-t2.md",
        help="Output markdown path",
    )
    parser.add_argument(
        "--out-json",
        default="",
        help="Optional output JSON path (for CI/audit artifacts)",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    out_doc = repo_root / args.out_doc
    out_json = (repo_root / args.out_json) if args.out_json else None

    doc_path, json_path = generate_contract_catalog(repo_root, out_doc, out_json)
    print(f"WROTE_DOC={doc_path}")
    if json_path:
        print(f"WROTE_JSON={json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

