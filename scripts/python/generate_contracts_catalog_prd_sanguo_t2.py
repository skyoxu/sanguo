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


def _format_list(items: list[str]) -> str:
    if not items:
        return "（空）"
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
) -> str:
    generated_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

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
    lines.append(f"# {prd_id} 契约目录（脚本生成）")
    lines.append("")
    lines.append("本文件为脚本生成产物，用于在开始新任务前快速对齐“当前仓库已落盘的契约（Contracts）”与“任务视图声明的 contractRefs”。")
    lines.append("")
    lines.append(f"- 生成时间（UTC）：`{generated_at}`")
    lines.append(f"- 生成脚本：`scripts/python/generate_contracts_catalog_prd_sanguo_t2.py`")
    lines.append("- 事件过滤：仅收录 `core.sanguo.*`（默认规则；可用脚本参数调整）")
    lines.append("")
    lines.append("## 来源（SSoT 引用）")
    lines.append(f"- PRD：`{prd_path}`")
    lines.append(f"- Overlay（目录）：`{overlay_dir}`")
    lines.append("- Contracts（代码）：`Game.Core/Contracts/**`")
    lines.append(f"- 任务视图（语义 SSoT）：`{tasks_back_path}`、`{tasks_gameplay_path}`")
    lines.append(f"- 任务母表（结构/标题/状态）：`{tasks_master_path}`")
    lines.append("")

    lines.append("## 领域事件（Domain Events）")
    lines.append("")
    lines.append("> 规则：事件命名与 `EventType` 常量口径遵循 ADR-0004；本目录只反映“当前代码中已落盘的 EventType”。")
    lines.append("")

    for file_path, occs in by_file.items():
        lines.append(f"### `{file_path}`")
        for o in occs:
            if o.declared_by:
                lines.append(f"- `{o.event_type}` → `{o.declared_by}`")
            else:
                lines.append(f"- `{o.event_type}`")
        lines.append("")

    lines.append("## 接口契约（Interfaces）")
    lines.append("")
    lines.append("### Ports（Core → Adapters）")
    lines.append("")
    for o in sorted(interfaces_ports, key=lambda x: (x.name, x.declared_in)):
        lines.append(f"- `{o.name}`（`{o.declared_in}`）")
    lines.append("")

    lines.append("### Services（Core 内部服务抽象）")
    lines.append("")
    for o in sorted(interfaces_services, key=lambda x: (x.name, x.declared_in)):
        lines.append(f"- `{o.name}`（`{o.declared_in}`）")
    lines.append("")

    lines.append("### Repositories（持久化抽象）")
    lines.append("")
    for o in sorted(interfaces_repos, key=lambda x: (x.name, x.declared_in)):
        lines.append(f"- `{o.name}`（`{o.declared_in}`）")
    lines.append("")

    if include_task_mapping:
        lines.append("## 按任务映射（contractRefs 视角）")
        lines.append("")
        lines.append("> 说明：本节以 `tasks_back.json` 为全量视图；若 `tasks_gameplay.json` 存在对应任务，则同时展示。")
        lines.append("")

        for task_id in sorted(master_by_id.keys()):
            master = master_by_id.get(task_id)
            back = back_by_id.get(task_id)
            gameplay = gameplay_by_id.get(task_id)
            if not master or not back:
                # Skip tasks that don't exist in views (should not happen, but keep robust).
                continue

            lines.append(f"### Task {task_id}: {master.get('title')}")
            lines.append(f"- Master status: `{master.get('status')}`")
            lines.append(f"- Back view: `id={back.get('id')}` layer=`{back.get('layer')}` status=`{back.get('status')}`")
            if gameplay:
                lines.append(
                    f"- Gameplay view: `id={gameplay.get('id')}` layer=`{gameplay.get('layer')}` status=`{gameplay.get('status')}`"
                )
            else:
                lines.append("- Gameplay view: （无）")

            back_contracts = [str(x) for x in (back.get("contractRefs") or [])]
            lines.append(f"- contractRefs（Back）：{_format_list(back_contracts)}")

            if gameplay:
                gp_contracts = [str(x) for x in (gameplay.get('contractRefs') or [])]
                lines.append(f"- contractRefs（Gameplay）：{_format_list(gp_contracts)}")

            back_overlays = [str(x) for x in (back.get("overlay_refs") or [])]
            back_tests = [str(x) for x in (back.get("test_refs") or [])]
            lines.append(f"- overlay_refs（Back）：{_format_list(back_overlays)}")
            lines.append(f"- test_refs（Back）：{_format_list(back_tests)}")
            lines.append("")

        if unknown_contract_refs:
            lines.append("## 发现的漂移风险（contractRefs ↔ Contracts）")
            lines.append("")
            lines.append("以下任务视图声明了 contractRefs，但当前 `Game.Core/Contracts/**` 未发现对应 `EventType` 常量：")
            lines.append("")
            for task_id in sorted(unknown_contract_refs.keys()):
                lines.append(f"- Task {task_id}: {_format_list(unknown_contract_refs[task_id])}")
            lines.append("")
            lines.append("处理建议：")
            lines.append("- 若事件确实需要：先补 Contracts（纯 C#，不依赖 Godot），再补 Overlay 08 引用页，然后回填 contractRefs。")
            lines.append("- 若事件已更名：同步更新 contractRefs 与所有测试/文档引用，避免双口径。")
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
    )

    _write_text_utf8(repo_root / args.out, md)
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
