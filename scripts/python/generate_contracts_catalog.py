from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    # scripts/python/<this>.py -> scripts/python -> scripts -> repo root
    return Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a contracts catalog markdown for a PRD overlay using the project generator. "
            "This wrapper exists to provide a stable entrypoint name."
        )
    )
    parser.add_argument("--prd-id", default="PRD-SANGUO-T2", help="PRD id (e.g. PRD-SANGUO-T2).")
    parser.add_argument(
        "--out",
        default="docs/workflows/contracts-catalog-prd-sanguo-t2.md",
        help="Output markdown path (repo-relative).",
    )
    parser.add_argument("--prd-path", default=".taskmaster/docs/prd.txt", help="PRD path (repo-relative).")
    parser.add_argument(
        "--overlay-dir",
        default="docs/architecture/overlays/PRD-SANGUO-T2/08",
        help="Overlay directory path (repo-relative).",
    )
    parser.add_argument("--tasks-master", default=".taskmaster/tasks/tasks.json")
    parser.add_argument("--tasks-back", default=".taskmaster/tasks/tasks_back.json")
    parser.add_argument("--tasks-gameplay", default=".taskmaster/tasks/tasks_gameplay.json")
    parser.add_argument("--event-type-regex", default=r"^core\.sanguo\.")
    parser.add_argument(
        "--strings",
        default="docs/workflows/templates/contracts_catalog_strings.zh-CN.json",
        help="Path to a UTF-8 JSON file containing localized markdown strings (repo-relative).",
    )
    parser.add_argument("--no-task-mapping", action="store_true")

    args = parser.parse_args()
    repo_root = _repo_root()

    generator = repo_root / "scripts" / "python" / "generate_contracts_catalog_prd_sanguo_t2.py"
    if not generator.exists():
        raise SystemExit(f"Generator not found: {generator.as_posix()}")

    cmd = [
        sys.executable,
        str(generator),
        "--prd-id",
        args.prd_id,
        "--out",
        args.out,
        "--prd-path",
        args.prd_path,
        "--overlay-dir",
        args.overlay_dir,
        "--tasks-master",
        args.tasks_master,
        "--tasks-back",
        args.tasks_back,
        "--tasks-gameplay",
        args.tasks_gameplay,
        "--event-type-regex",
        args.event_type_regex,
        "--strings",
        args.strings,
    ]
    if args.no_task_mapping:
        cmd.append("--no-task-mapping")

    completed = subprocess.run(cmd, cwd=str(repo_root), check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())

