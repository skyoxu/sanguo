from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class EventTypeOccurrence:
    event_type: str
    declared_in: str  # relative path
    declared_by: str | None  # C# type name (best-effort)


@dataclass(frozen=True)
class InterfaceOccurrence:
    name: str
    declared_in: str  # relative path


def _repo_root() -> Path:
    # scripts/python/<this>.py -> scripts/python -> scripts -> repo root
    return Path(__file__).resolve().parents[2]


def _read_text_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text_utf8(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _load_strings(path: Path) -> dict[str, str]:
    data = json.loads(_read_text_utf8(path))
    if not isinstance(data, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in data.items()):
        raise ValueError(f"Invalid strings file format: {path.as_posix()}")
    return data


def _scan_event_types(contracts_root: Path, repo_root: Path) -> list[EventTypeOccurrence]:
    # Best-effort: find `public const string EventType = "..."` and the closest preceding type name.
    event_type_re = re.compile(
        r"public\s+const\s+string\s+EventType\s*=\s*\"([^\"]+)\"\s*;",
        re.MULTILINE,
    )
    type_name_re = re.compile(r"\b(record|class|struct)\s+([A-Za-z_][A-Za-z0-9_]*)\b")

    occurrences: list[EventTypeOccurrence] = []

    for cs_path in sorted(contracts_root.rglob("*.cs")):
        text = _read_text_utf8(cs_path)
        for match in event_type_re.finditer(text):
            event_type = match.group(1).strip()
            declared_by: str | None = None

            # Walk backward and take the nearest type declaration name (heuristic).
            prefix = text[: match.start()]
            type_matches = list(type_name_re.finditer(prefix))
            if type_matches:
                declared_by = type_matches[-1].group(2)

            occurrences.append(
                EventTypeOccurrence(
                    event_type=event_type,
                    declared_in=_rel(cs_path, repo_root),
                    declared_by=declared_by,
                )
            )

    # Keep stable order and remove exact duplicates.
    dedup: dict[tuple[str, str, str | None], EventTypeOccurrence] = {}
    for o in occurrences:
        dedup[(o.event_type, o.declared_in, o.declared_by)] = o
    return list(dedup.values())


def _scan_interfaces(interface_roots: Iterable[Path], repo_root: Path) -> list[InterfaceOccurrence]:
    interface_re = re.compile(r"\binterface\s+([A-Za-z_][A-Za-z0-9_]*)\b")
    occurrences: list[InterfaceOccurrence] = []

    for root in interface_roots:
        if not root.exists():
            continue
        for cs_path in sorted(root.rglob("*.cs")):
            text = _read_text_utf8(cs_path)
            for match in interface_re.finditer(text):
                occurrences.append(
                    InterfaceOccurrence(
                        name=match.group(1),
                        declared_in=_rel(cs_path, repo_root),
                    )
                )

    dedup: dict[tuple[str, str], InterfaceOccurrence] = {}
    for o in occurrences:
        dedup[(o.name, o.declared_in)] = o
    return list(dedup.values())


def _load_tasks_view(path: Path) -> list[dict]:
    # View files are lists of dicts (tasks_back/tasks_gameplay).
    return json.loads(_read_text_utf8(path))


def _load_master_tasks(path: Path) -> list[dict]:
    obj = json.loads(_read_text_utf8(path))
    tasks = obj.get("master", {}).get("tasks")
    if not isinstance(tasks, list):
        raise ValueError(f"Unexpected tasks.json format: {path.as_posix()}")
    return tasks


def _format_list(items: list[str], *, empty_text: str) -> str:
    if not items:
        return empty_text
    return ", ".join(f"`{x}`" for x in items)


def _build_markdown(
    *,
    prd_id: str,
    repo_root: Path,
    prd_path: str,
    overlay_dir: str,
    tasks_master_path: str,
    tasks_back_path: str,
    tasks_gameplay_path: str,
    event_types: list[EventTypeOccurrence],
    interfaces_ports: list[InterfaceOccurrence],
    interfaces_services: list[InterfaceOccurrence],
    interfaces_repos: list[InterfaceOccurrence],
    master_tasks: list[dict],
    back_tasks: list[dict],
    gameplay_tasks: list[dict],
    include_task_mapping: bool,
    strings: dict[str, str],
) -> str:
    generated_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    arrow = strings["arrow"]
    empty_list_text = strings["empty_list"]

    event_types_sorted = sorted(event_types, key=lambda x: (x.event_type, x.declared_in))
    by_file: dict[str, list[EventTypeOccurrence]] = {}
    for o in event_types_sorted:
        by_file.setdefault(o.declared_in, []).append(o)

    known_event_types = {o.event_type for o in event_types_sorted}

    # Build quick index for views
    back_by_id = {int(t["taskmaster_id"]): t for t in back_tasks}
    gameplay_by_id = {int(t["taskmaster_id"]): t for t in gameplay_tasks}
    master_by_id = {int(t["id"]): t for t in master_tasks}

    # Find contractRefs that don't exist in code (useful to catch drift).
    unknown_contract_refs: dict[int, list[str]] = {}
    for task_id, t in back_by_id.items():
        refs = [str(x) for x in (t.get("contractRefs") or [])]
        missing = sorted(set(r for r in refs if r not in known_event_types))
        if missing:
            unknown_contract_refs[task_id] = missing

    lines: list[str] = []
    lines.append(f"# {prd_id} {strings['title_suffix']}")
    lines.append("")
    lines.append(strings["intro"])
    lines.append("")
    lines.append(f"- {strings['generated_at_label']}: `{generated_at}`")
    lines.append(f"- {strings['generator_label']}: `scripts/python/generate_contracts_catalog_prd_sanguo_t2.py`")
    lines.append(f"- {strings['event_filter_label']}: {strings['event_filter_default']}")
    lines.append("")
    lines.append(f"## {strings['sources_title']}")
    lines.append(f"- {strings['source_prd']}: `{prd_path}`")
    lines.append(f"- {strings['source_overlay_dir']}: `{overlay_dir}`")
    lines.append(f"- {strings['source_contracts']}: `Game.Core/Contracts/**`")
    lines.append(f"- {strings['source_task_views']}: `{tasks_back_path}`, `{tasks_gameplay_path}`")
    lines.append(f"- {strings['source_tasks_master']}: `{tasks_master_path}`")
    lines.append("")

    lines.append(f"## {strings['domain_events_title']}")
    lines.append("")
    lines.append(f"> {strings['domain_events_rule']}")
    lines.append("")

    for file_path, occs in by_file.items():
        lines.append(f"### `{file_path}`")
        for o in occs:
            if o.declared_by:
                lines.append(f"- `{o.event_type}`{arrow}`{o.declared_by}`")
            else:
                lines.append(f"- `{o.event_type}`")
        lines.append("")

    lines.append(f"## {strings['interfaces_title']}")
    lines.append("")
    lines.append(f"### {strings['ports_title']}")
    lines.append("")
    for o in sorted(interfaces_ports, key=lambda x: (x.name, x.declared_in)):
        lines.append(f"- `{o.name}` (`{o.declared_in}`)")
    lines.append("")

    lines.append(f"### {strings['services_title']}")
    lines.append("")
    for o in sorted(interfaces_services, key=lambda x: (x.name, x.declared_in)):
        lines.append(f"- `{o.name}` (`{o.declared_in}`)")
    lines.append("")

    lines.append(f"### {strings['repositories_title']}")
    lines.append("")
    for o in sorted(interfaces_repos, key=lambda x: (x.name, x.declared_in)):
        lines.append(f"- `{o.name}` (`{o.declared_in}`)")
    lines.append("")

    if include_task_mapping:
        lines.append(f"## {strings['task_mapping_title']}")
        lines.append("")
        lines.append(f"> {strings['task_mapping_note']}")
        lines.append("")

        for task_id in sorted(master_by_id.keys()):
            master = master_by_id.get(task_id)
            back = back_by_id.get(task_id)
            gameplay = gameplay_by_id.get(task_id)
            if not master or not back:
                # Skip tasks that don't exist in views (should not happen, but keep robust).
                continue

            lines.append(f"### {strings['task_heading_prefix']} {task_id}: {master.get('title')}")
            lines.append(f"- {strings['master_status_label']}: `{master.get('status')}`")
            lines.append(
                f"- {strings['back_view_label']}: `id={back.get('id')}` layer=`{back.get('layer')}` status=`{back.get('status')}`"
            )
            if gameplay:
                lines.append(
                    f"- {strings['gameplay_view_label']}: `id={gameplay.get('id')}` layer=`{gameplay.get('layer')}` status=`{gameplay.get('status')}`"
                )
            else:
                lines.append(f"- {strings['gameplay_view_label']}: {strings['gameplay_view_none']}")

            back_contracts = [str(x) for x in (back.get("contractRefs") or [])]
            lines.append(
                f"- {strings['contract_refs_back_label']}: {_format_list(back_contracts, empty_text=empty_list_text)}"
            )

            if gameplay:
                gp_contracts = [str(x) for x in (gameplay.get('contractRefs') or [])]
                lines.append(
                    f"- {strings['contract_refs_gameplay_label']}: {_format_list(gp_contracts, empty_text=empty_list_text)}"
                )

            back_overlays = [str(x) for x in (back.get("overlay_refs") or [])]
            back_tests = [str(x) for x in (back.get("test_refs") or [])]
            lines.append(
                f"- {strings['overlay_refs_back_label']}: {_format_list(back_overlays, empty_text=empty_list_text)}"
            )
            lines.append(f"- {strings['test_refs_back_label']}: {_format_list(back_tests, empty_text=empty_list_text)}")
            lines.append("")

        if unknown_contract_refs:
            lines.append(f"## {strings['drift_title']}")
            lines.append("")
            lines.append(strings["drift_intro"])
            lines.append("")
            for task_id in sorted(unknown_contract_refs.keys()):
                lines.append(
                    f"- {strings['task_heading_prefix']} {task_id}: {_format_list(unknown_contract_refs[task_id], empty_text=empty_list_text)}"
                )
            lines.append("")
            lines.append(strings["drift_actions_title"])
            lines.append(f"- {strings['drift_action_add']}")
            lines.append(f"- {strings['drift_action_rename']}")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate docs/workflows/contracts-catalog-prd-sanguo-t2.md from Contracts + task views (UTF-8)."
    )
    parser.add_argument("--prd-id", default="PRD-SANGUO-T2")
    parser.add_argument(
        "--out",
        default="docs/workflows/contracts-catalog-prd-sanguo-t2.md",
        help="Output markdown path (repo-relative).",
    )
    parser.add_argument("--prd-path", default=".taskmaster/docs/prd.txt")
    parser.add_argument(
        "--overlay-dir",
        default="docs/architecture/overlays/PRD-SANGUO-T2/08",
    )
    parser.add_argument("--tasks-master", default=".taskmaster/tasks/tasks.json")
    parser.add_argument("--tasks-back", default=".taskmaster/tasks/tasks_back.json")
    parser.add_argument("--tasks-gameplay", default=".taskmaster/tasks/tasks_gameplay.json")
    parser.add_argument("--no-task-mapping", action="store_true")
    parser.add_argument(
        "--strings",
        default="docs/workflows/templates/contracts_catalog_strings.zh-CN.json",
        help="Path to a UTF-8 JSON file containing localized markdown strings (repo-relative).",
    )
    parser.add_argument(
        "--event-type-regex",
        default=r"^core\.sanguo\.",
        help="Only include EventType values matching this regex (default: only core.sanguo.*).",
    )

    args = parser.parse_args()
    repo_root = _repo_root()

    contracts_root = repo_root / "Game.Core" / "Contracts"
    if not contracts_root.exists():
        raise SystemExit(f"Contracts root not found: {contracts_root.as_posix()}")

    event_types_all = _scan_event_types(contracts_root, repo_root)
    event_type_filter = re.compile(args.event_type_regex)
    event_types = [e for e in event_types_all if event_type_filter.search(e.event_type)]

    ports = _scan_interfaces([repo_root / "Game.Core" / "Ports"], repo_root)
    services = _scan_interfaces([repo_root / "Game.Core" / "Services"], repo_root)
    repos = _scan_interfaces([repo_root / "Game.Core" / "Repositories"], repo_root)

    master_tasks = _load_master_tasks(repo_root / args.tasks_master)
    back_tasks = _load_tasks_view(repo_root / args.tasks_back)
    gameplay_tasks = _load_tasks_view(repo_root / args.tasks_gameplay)

    strings = _load_strings(repo_root / args.strings)

    md = _build_markdown(
        prd_id=args.prd_id,
        repo_root=repo_root,
        prd_path=args.prd_path,
        overlay_dir=args.overlay_dir,
        tasks_master_path=args.tasks_master,
        tasks_back_path=args.tasks_back,
        tasks_gameplay_path=args.tasks_gameplay,
        event_types=event_types,
        interfaces_ports=ports,
        interfaces_services=services,
        interfaces_repos=repos,
        master_tasks=master_tasks,
        back_tasks=back_tasks,
        gameplay_tasks=gameplay_tasks,
        include_task_mapping=not args.no_task_mapping,
        strings=strings,
    )

    _write_text_utf8(repo_root / args.out, md)
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
