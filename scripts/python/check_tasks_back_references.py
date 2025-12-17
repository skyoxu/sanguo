import json
import re
from pathlib import Path

import check_tasks_all_refs


# Keep ADR->CH mapping consistent with the main checker.
ADR_FOR_CH = check_tasks_all_refs.ADR_FOR_CH


def load_tasks_back(root: Path) -> list[dict]:
    path = root / ".taskmaster" / "tasks" / "tasks_back.json"
    return json.loads(path.read_text(encoding="utf-8"))


def collect_adr_ids(root: Path) -> set[str]:
    adr_dir = root / "docs" / "adr"
    ids: set[str] = set()
    if not adr_dir.exists():
        return ids
    for f in adr_dir.glob("ADR-*.md"):
        m = re.match(r"ADR-(\d{4})", f.stem)
        if m:
            ids.add(f"ADR-{m.group(1)}")
    return ids


def collect_overlay_paths(root: Path) -> set[str]:
    overlay_paths: set[str] = set()

    overlays_root = root / "docs" / "architecture" / "overlays"
    if not overlays_root.exists():
        return overlay_paths

    for prd_dir in overlays_root.iterdir():
        if not prd_dir.is_dir():
            continue
        chapter_dir = prd_dir / "08"
        if not chapter_dir.exists():
            continue
        for p in chapter_dir.glob("*"):
            rel = p.relative_to(root)
            overlay_paths.add(str(rel).replace("\\", "/"))

    return overlay_paths


def run_check(root: Path) -> bool:
    """Validate backlog (non-exported) tasks in tasks_back.json.

    This is an incremental check that focuses on tasks that are NOT exported to
    tasks.json (i.e., taskmaster_exported != true). The full check still lives in
    check_tasks_all_refs.py.

    Returns True if everything is consistent, False otherwise.
    """

    tasks = load_tasks_back(root)
    adr_ids = collect_adr_ids(root)
    overlay_paths = collect_overlay_paths(root)

    backlog_tasks = [t for t in tasks if not t.get("taskmaster_exported")]

    print(f"backlog_tasks_count: {len(backlog_tasks)}")
    print(f"known ADR ids (sample): {sorted(adr_ids)[:10]} ...")
    print(f"overlay files: {sorted(overlay_paths)}")

    has_error = False

    for t in sorted(backlog_tasks, key=lambda x: str(x.get("id", ""))):
        tid = t["id"]
        story_id = t.get("story_id")
        print(f"\n== {tid} ==")
        print(f"story_id: {story_id}")

        # ADR refs
        missing_adrs = [a for a in t.get("adr_refs", []) if a not in adr_ids]
        if missing_adrs:
            print(f"  missing ADRs: {missing_adrs}")
            has_error = True
        else:
            print("  adr_refs OK")

        # chapter_refs vs ADR_FOR_CH
        expected_ch: set[str] = set()
        for adr in t.get("adr_refs", []):
            expected_ch.update(ADR_FOR_CH.get(adr, []))
        current_ch = set(t.get("chapter_refs", []))
        missing_ch = expected_ch - current_ch
        extra_ch = current_ch - expected_ch
        if missing_ch:
            print(f"  missing chapter_refs (from ADR): {sorted(missing_ch)}")
            has_error = True
        if extra_ch:
            # Optional improvement (A+B): allow extra chapters as warnings.
            print(f"  WARN extra chapter_refs (not implied by ADR map): {sorted(extra_ch)}")
        if not missing_ch and not extra_ch:
            print("  chapter_refs consistent with ADR map")

        # overlay refs (if present)
        refs = [p.replace("\\", "/") for p in t.get("overlay_refs", [])]
        if refs:
            missing_overlays = [p for p in refs if p not in overlay_paths]
            if missing_overlays:
                print(f"  missing overlays: {missing_overlays}")
                has_error = True
            else:
                print("  overlay_refs OK")
        else:
            print("  overlay_refs: (none)")

        # depends_on refs must exist within tasks_back.json (local sanity)
        known_ids = {str(x.get("id")) for x in tasks if x.get("id")}
        deps = [str(d) for d in t.get("depends_on") or []]
        missing_deps = [d for d in deps if d not in known_ids]
        if missing_deps:
            print(f"  missing depends_on ids: {missing_deps}")
            has_error = True

    return not has_error


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    ok = run_check(root)
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
