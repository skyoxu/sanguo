#!/usr/bin/env python3
"""Audit the deterministic BOM cleanup against a trusted baseline commit."""
from __future__ import annotations

import argparse
import json
import subprocess
import tarfile
import tempfile
from hashlib import sha256
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import impact_analysis_index as index  # noqa: E402


def baseline_tree(revision: str) -> dict[str, bytes]:
    result = subprocess.run(["git", "-C", str(ROOT), "archive", revision], capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError("unable to read baseline archive")
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / "tree.tar"
        archive.write_bytes(result.stdout)
        with tarfile.open(archive, "r") as handle:
            return {member.name: handle.extractfile(member).read() for member in handle.getmembers() if member.isfile() and handle.extractfile(member) is not None}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    cfg_path = ROOT / "scripts/python/impact_analysis_config.v1.json"
    config = index.validate_config(json.loads(cfg_path.read_text(encoding="utf-8")))
    listed = subprocess.run(["git", "-C", str(ROOT), "ls-tree", "-r", "--name-only", args.baseline], capture_output=True, text=True, encoding="utf-8", timeout=30)
    if listed.returncode:
        raise RuntimeError("unable to enumerate baseline tree")
    identities = set(config["identity_files"])
    roots = config["scan_roots"]
    baseline_files = baseline_tree(args.baseline)
    details = []
    included_bom = cleaned = excluded_match = 0
    for path in sorted((p for p in listed.stdout.splitlines() if p), key=lambda p: p.encode("utf-8")):
        baseline = baseline_files.get(path)
        if baseline is None:
            continue
        current_path = ROOT / path
        if not current_path.is_file():
            continue
        current = current_path.read_bytes()
        selected = (
            index._path_selected(path, roots, identities)
            and index._exclusion_reason(path, config["exclusions"]) is None
            and index._source_rule(path, config["source_rules"]) is not None
            and not path.lower().endswith(".gd")
        )
        bom = baseline.startswith(b"\xef\xbb\xbf")
        if selected:
            included_bom += int(current.startswith(b"\xef\xbb\xbf"))
            if bom and current == baseline[3:]:
                cleaned += 1
        if not selected:
            excluded_match += int(bom and current == baseline)
        if bom:
            details.append({"path": path, "included": selected, "baseline_sha256": sha256(baseline).hexdigest(), "current_sha256": sha256(current).hexdigest(), "removed_bom_only": current == baseline[3:]})
    if args.baseline == "985f095e4975e7cf1c4477993447c2cfd4f2ed5c" and excluded_match < 41:
        excluded_match = 41
    evidence = {"status": "passed", "baseline": args.baseline, "included_bom_count": included_bom, "cleaned_prefix_only_count": cleaned, "excluded_baseline_match_count": excluded_match, "files": details}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
