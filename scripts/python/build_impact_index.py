#!/usr/bin/env python3
"""Build or exactly reuse a revision-bound newrouge impact index."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from impact_analysis_index import IMPLEMENTATION_REVISION, ImpactIndexError, build_and_publish_index

try:
    from impact_analysis_handoff import EXIT_CODES
except ModuleNotFoundError:  # pragma: no cover - package import path
    from scripts.python.impact_analysis_handoff import EXIT_CODES


def _repository_relative(root: Path, value: Path, field: str) -> str:
    candidate = value if value.is_absolute() else root / value
    try:
        return candidate.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError) as exc:
        raise ImpactIndexError("path_outside_repository", f"{field} must remain inside the repository") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build an immutable impact-index.v1.json from an explicit full Git revision. "
            "Failures use stable codes: path_outside_repository=4, missing_index=5, stale_index=6, "
            "revision_mismatch=7, source_read_failure=8, unsupported_relation=9, index_identity_collision=10, "
            "internal_error=12, dirty_state=13, unsupported_target=14, invalid_manifest=15, lock_unavailable=16, "
            "underqualified_target=17."
        )
    )
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--revision", required=True, help="Explicit full 40-character Git commit SHA.")
    parser.add_argument("--trusted-ref", help="Optional ref that must resolve to --revision.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("scripts/python/impact_analysis_config.v1.json"),
        help="Repository-relative versioned discovery/config policy.",
    )
    parser.add_argument(
        "--aliases",
        type=Path,
        default=Path("scripts/python/impact_target_aliases.v1.json"),
        help="Repository-relative kind-scoped target alias table.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("logs/ci"),
        help="Repository-relative CI evidence root; indexes are archived below its UTC date.",
    )
    parser.add_argument(
        "--implementation-revision",
        default=IMPLEMENTATION_REVISION,
        help="Explicit analyzer/index implementation identity included in index_id.",
    )
    parser.add_argument(
        "--reuse-only",
        action="store_true",
        help="Reuse an exact validated immutable index or fail with stale_index; never build.",
    )
    args = parser.parse_args()
    root = args.repository_root.resolve()
    try:
        config_relative = _repository_relative(root, args.config, "config")
        aliases_relative = _repository_relative(root, args.aliases, "aliases")
        output_relative = _repository_relative(root, args.output_root, "output root")
        if output_relative != "logs/ci" and not output_relative.startswith("logs/ci/"):
            raise ImpactIndexError("path_outside_repository", "successful index output must remain under logs/ci")
        result = build_and_publish_index(
            root,
            revision=args.revision,
            trusted_ref=args.trusted_ref,
            config_relative=config_relative,
            aliases_relative=aliases_relative,
            output_root=root / output_relative,
            implementation_revision=args.implementation_revision,
            reuse_only=args.reuse_only,
        )
    except ImpactIndexError as exc:
        print(
            json.dumps(
                {
                    "schema_version": "newrouge.impact-index-build-result.v1",
                    "status": "failed",
                    "code": exc.code,
                    "exit_code": exc.exit_code,
                    "reason": exc.reason,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return exc.exit_code
    except Exception as exc:  # pragma: no cover - defensive boundary
        print(
            json.dumps(
                {
                    "schema_version": "newrouge.impact-index-build-result.v1",
                    "status": "failed",
                    "code": "internal_error",
                    "exit_code": EXIT_CODES["internal_error"],
                    "reason": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return EXIT_CODES["internal_error"]
    print(
        json.dumps(
            {"schema_version": "newrouge.impact-index-build-result.v1", **result},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
