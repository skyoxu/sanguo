from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Iterable

EVENT_TYPE_RE = re.compile(r'public\s+const\s+string\s+EventType\s*=\s*"([^"]+)"\s*;')
SEALED_RECORD_RE = re.compile(r"public\s+sealed\s+record\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
PUBLIC_RECORD_RE = re.compile(r"public\s+record\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
PUBLIC_INTERFACE_RE = re.compile(r"public\s+interface\s+([A-Za-z_][A-Za-z0-9_]*)\b")

def read_text_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="strict")

def posix(path: Path) -> str:
    return str(path).replace("\\", "/")

def load_json(path: Path) -> Any:
    return json.loads(read_text_utf8(path))

def iter_cs_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.cs"):
        if p.name.endswith(".g.cs"):
            continue
        yield p


def extract_domain_events_from_file(path: Path) -> list[dict[str, str]]:
    text = read_text_utf8(path)
    matches = list(EVENT_TYPE_RE.finditer(text))
    if not matches:
        return []

    record_decls: list[tuple[int, str]] = []
    for m in SEALED_RECORD_RE.finditer(text):
        record_decls.append((m.start(), m.group(1)))
    for m in PUBLIC_RECORD_RE.finditer(text):
        record_decls.append((m.start(), m.group(1)))
    record_decls.sort(key=lambda x: x[0])

    def find_record_name(before_index: int) -> str:
        names = [name for idx, name in record_decls if idx < before_index]
        return names[-1] if names else "UnknownRecord"

    rel = posix(path)
    out: list[dict[str, str]] = []
    for m in matches:
        out.append(
            {
                "event_type": m.group(1),
                "csharp_type": find_record_name(m.start()),
                "file": rel,
            }
        )
    return out

def extract_public_interfaces_from_file(path: Path) -> list[dict[str, str]]:
    text = read_text_utf8(path)
    rel = posix(path)
    return [{"name": m.group(1), "file": rel} for m in PUBLIC_INTERFACE_RE.finditer(text)]

def sorted_unique_str(items: Iterable[str]) -> list[str]:
    return sorted({i for i in items if i})

def index_tasks_master(tasks_json: dict[str, Any]) -> dict[int, dict[str, Any]]:
    master = tasks_json.get("master") or {}
    tasks = master.get("tasks") or []
    out: dict[int, dict[str, Any]] = {}
    for t in tasks:
        try:
            out[int(str(t.get("id")))] = t
        except Exception:
            continue
    return out


def index_view_tasks_by_taskmaster_id(view_tasks: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for t in view_tasks:
        tid = t.get("taskmaster_id")
        if isinstance(tid, int):
            out[tid] = t
    return out


def derive_needed_interfaces(events: list[str]) -> list[str]:
    if not events:
        return []
    needed = {"Game.Core.Services.IEventBus", "Game.Core.Contracts.DomainEvent"}
    if "core.sanguo.ai.decision.made" in events:
        needed |= {
            "Game.Core.Services.ISanguoAiDecisionPolicy",
            "Game.Core.Domain.ISanguoPlayerView",
            "Game.Core.Utilities.IRandomNumberGenerator",
        }
    if "core.sanguo.dice.rolled" in events:
        needed.add("Game.Core.Utilities.IRandomNumberGenerator")
    return sorted(needed)


def derive_needed_dtos(events: list[str]) -> list[str]:
    if not events:
        return []
    needed = {
        "Game.Core.Contracts.IEventData",
        "Game.Core.Contracts.JsonElementEventData",
        "Game.Core.Contracts.RawJsonEventData",
    }
    if "core.sanguo.economy.month.settled" in events:
        needed.add("Game.Core.Contracts.Sanguo.PlayerSettlement")
    return sorted(needed)


def generate_contract_catalog(
    repo_root: Path,
    out_doc: Path,
    out_json: Path | None,
) -> tuple[str, str | None]:
    prd_path = ".taskmaster/docs/prd.txt"
    overlay_dir = repo_root / "docs" / "architecture" / "overlays" / "PRD-SANGUO-T2" / "08"
    overlay_docs = [posix(overlay_dir / n) for n in (
        "08-Contracts-CloudEvent.md",
        "08-Contracts-CloudEvents-Core.md",
        "08-Contracts-Sanguo-GameLoop-Events.md",
        "08-feature-slice-t2-monopoly-loop.md",
        "08-t2-city-ownership-model.md",
    )]

    # Domain events (SSoT)
    contracts_root = repo_root / "Game.Core" / "Contracts"
    domain_events: list[dict[str, str]] = []
    for cs in iter_cs_files(contracts_root):
        domain_events.extend(extract_domain_events_from_file(cs))
    domain_events = sorted(domain_events, key=lambda e: (e["file"], e["event_type"]))
    event_record_names = sorted_unique_str(e["csharp_type"] for e in domain_events)

    events_by_file: dict[str, list[dict[str, str]]] = {}
    for e in domain_events:
        events_by_file.setdefault(Path(e["file"]).name, []).append(e)

    # Interfaces (contract-like boundaries)
    def scan_interfaces(roots: list[Path]) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for r in roots:
            if not r.exists():
                continue
            for cs in iter_cs_files(r):
                out.extend(extract_public_interfaces_from_file(cs))
        uniq: dict[tuple[str, str], dict[str, str]] = {}
        for i in out:
            uniq[(i["name"], i["file"])] = i
        return [uniq[k] for k in sorted(uniq.keys())]

    interfaces_core = scan_interfaces([repo_root / "Game.Core" / x for x in ("Services", "Domain", "Contracts", "Utilities")])
    interfaces_ports = scan_interfaces([repo_root / "Game.Core" / "Ports"])
    interfaces_repos = scan_interfaces([repo_root / "Game.Core" / "Repositories"])
    interface_index: dict[str, str] = {}
    for i in interfaces_core + interfaces_ports + interfaces_repos:
        interface_index[i["name"]] = i["file"]

    known_interface_names = sorted(interface_index.keys(), key=lambda x: (-len(x), x))
    known_dto_names = sorted_unique_str(["DomainEvent", "IEventData", "RawJsonEventData", "JsonElementEventData", "PlayerSettlement", *event_record_names])

    def scan_symbols_in_files(file_refs: list[str], symbols: list[str]) -> list[str]:
        if not file_refs or not symbols:
            return []
        found: set[str] = set()
        for ref in file_refs:
            p = repo_root / ref
            if not p.exists():
                continue
            try:
                text = read_text_utf8(p)
            except Exception:
                continue
            for s in symbols:
                if re.search(rf"\\b{re.escape(s)}\\b", text):
                    found.add(s)
        return sorted(found)

    def view_test_refs(v: dict[str, Any]) -> list[str]:
        tr = v.get("test_refs") or []
        if not isinstance(tr, list):
            return []
        return [str(x) for x in tr if isinstance(x, str) and x.strip()]

    # Tasks triplet
    tasks_json = load_json(repo_root / ".taskmaster" / "tasks" / "tasks.json")
    tasks_back = load_json(repo_root / ".taskmaster" / "tasks" / "tasks_back.json")
    tasks_gameplay = load_json(repo_root / ".taskmaster" / "tasks" / "tasks_gameplay.json")
    if not isinstance(tasks_back, list) or not isinstance(tasks_gameplay, list):
        raise SystemExit("Unexpected tasks_back/tasks_gameplay format: expected JSON arrays.")

    master_by_id = index_tasks_master(tasks_json)
    back_by_id = index_view_tasks_by_taskmaster_id(tasks_back)
    gameplay_by_id = index_view_tasks_by_taskmaster_id(tasks_gameplay)
    task_ids = sorted(set(master_by_id) | set(back_by_id) | set(gameplay_by_id))

    def count_contract_refs(view_tasks: list[dict[str, Any]]) -> int:
        c = 0
        for t in view_tasks:
            v = t.get("contractRefs")
            if isinstance(v, list) and any(isinstance(x, str) and x.strip() for x in v):
                c += 1
        return c

    heuristic_findings: list[dict[str, Any]] = []

    def flag_if_suspicious(view_id: str, taskmaster_id: int, title: str, refs: list[str]) -> None:
        tl = title.lower()
        if ("地图" in title or "map" in tl) and any("game.saved" in e or "game.loaded" in e for e in refs):
            heuristic_findings.append(
                {
                    "view_id": view_id,
                    "taskmaster_id": taskmaster_id,
                    "message": "map-related task references game.saved/game.loaded; verify relevance.",
                }
            )
        if ("事件" in title or "event" in tl) and not refs:
            heuristic_findings.append(
                {
                    "view_id": view_id,
                    "taskmaster_id": taskmaster_id,
                    "message": "event-related task has empty contractRefs; verify missing domain events.",
                }
            )

    for view in tasks_back + tasks_gameplay:
        tid = view.get("taskmaster_id")
        if not isinstance(tid, int):
            continue
        title = str(view.get("title") or "")
        refs = view.get("contractRefs")
        if not isinstance(refs, list):
            refs = []
        refs = [str(x) for x in refs if isinstance(x, str)]
        flag_if_suspicious(str(view.get("id")), tid, title, refs)

    # Markdown
    md: list[str] = []
    md += ["# T2 契约目录（按类别 + 按任务映射）", ""]
    md += ["本文件为派生文档：从现有代码与任务视图中提取“当前仓库已落盘的契约”，用于在开始新任务前快速对齐。", ""]
    md += ["## 来源（SSoT 引用）", f"- PRD：`{prd_path}`"]
    md += [f"- Overlay：`{x}`" for x in overlay_docs]
    md += [
        "- Contracts（代码）：`Game.Core/Contracts/**`",
        "- 任务视图（SSoT for contractRefs）：`.taskmaster/tasks/tasks_back.json`、`.taskmaster/tasks/tasks_gameplay.json`",
        "",
    ]
    md += [
        "## CloudEvents 对齐（最小子集）",
        "",
        "DomainEvent 字段映射：`SpecVersion→specversion`、`Type→type`、`Source→source`、`Id→id`、`Timestamp→time`、`DataContentType→datacontenttype`、`Data→data`（并用 `IEventData` 限制载荷类型面）。",
        "",
    ]

    md += ["## 领域事件（Domain Events）", "", "> 规则：每个事件必须包含 `public const string EventType`（见 Overlay：CloudEvents Core 口径）。", ""]
    for fname, items in events_by_file.items():
        md.append(f"### `{fname}`")
        for it in items:
            md.append(f"- `{it['event_type']}` → `{it['csharp_type']}`（`{it['file']}`）")
        md.append("")

    md += ["## 接口契约（Interfaces）", ""]
    md += ["### 事件与游戏闭环核心"] + [f"- `{i['name']}`（`{i['file']}`）" for i in interfaces_core] + [""]
    md += ["### Ports（Core→Adapters）"] + [f"- `{i['name']}`（`{i['file']}`）" for i in interfaces_ports] + [""]
    md += ["### Repositories（持久化抽象）"] + [f"- `{i['name']}`（`{i['file']}`）" for i in interfaces_repos] + [""]

    md += ["## 按任务映射（每个任务需要哪些事件/DTO/接口）", ""]
    md += ["> 说明：`contractRefs` 只记录“本任务关心的领域事件（EventType）”，DTO/接口为基于事件集的推导，用于开发时对齐依赖。", ""]

    def render_view(view_name: str, v: dict[str, Any] | None) -> None:
        if v is None:
            md.append(f"- {view_name}：缺失")
            return
        refs = v.get("contractRefs")
        if not isinstance(refs, list):
            refs = []
        refs = [str(x) for x in refs if isinstance(x, str)]
        adr = v.get("adrRefs") or v.get("adr_refs") or []
        if not isinstance(adr, list):
            adr = []
        adr = [str(x) for x in adr if isinstance(x, str)]
        overlay = str(v.get("overlay") or "")
        if not overlay:
            overlay_refs = v.get("overlay_refs") or []
            if isinstance(overlay_refs, list) and overlay_refs:
                overlay = str(overlay_refs[0])
        test_refs = v.get("test_refs") or []
        if not isinstance(test_refs, list):
            test_refs = []
        test_refs = [str(x) for x in test_refs if isinstance(x, str)]

        scanned_interfaces = scan_symbols_in_files(test_refs, known_interface_names)
        scanned_dtos = scan_symbols_in_files(test_refs, known_dto_names)
        md.append(f"- {view_name}：`{v.get('id')}` layer=`{v.get('layer')}` status=`{v.get('status')}`")
        md.append("  - 领域事件（contractRefs）：" + (", ".join(f"`{e}`" for e in refs) if refs else "(空)"))
        md.append(
            "  - DTO："
            + (
                ", ".join(f"`{d}`" for d in scanned_dtos)
                if scanned_dtos
                else (", ".join(f"`{d}`" for d in derive_needed_dtos(refs)) if refs else "(空)")
            )
        )
        md.append(
            "  - 接口："
            + (
                ", ".join(f"`{i}`" for i in scanned_interfaces)
                if scanned_interfaces
                else (", ".join(f"`{i}`" for i in derive_needed_interfaces(refs)) if refs else "(空)")
            )
        )
        md.append("  - ADR：" + (", ".join(f"`{a}`" for a in adr) if adr else "(空)"))
        md.append(f"  - Overlay：`{overlay}`" if overlay else "  - Overlay：(空)")
        md.append("  - Test-Refs：" + (", ".join(f"`{t}`" for t in test_refs) if test_refs else "(空)"))

    for tid in task_ids:
        master = master_by_id.get(tid)
        title = (master or {}).get("title") or "(unknown)"
        master_status = (master or {}).get("status") or ""
        master_adr = (master or {}).get("adrRefs") or []
        master_arch = (master or {}).get("archRefs") or []
        master_overlay = (master or {}).get("overlay") or ""
        if not isinstance(master_adr, list):
            master_adr = []
        if not isinstance(master_arch, list):
            master_arch = []
        md.append(f"### Task {tid}: {title}")
        if master:
            md.append(f"- Master(tasks.json)：status=`{master_status}`")
            md.append("  - ADR：" + (", ".join(f"`{a}`" for a in master_adr) if master_adr else "(空)"))
            md.append("  - Arch：" + (", ".join(f"`{c}`" for c in master_arch) if master_arch else "(空)"))
            md.append(f"  - Overlay：`{master_overlay}`" if master_overlay else "  - Overlay：(空)")
        render_view("SG(tasks_back)", back_by_id.get(tid))
        render_view("GM(tasks_gameplay)", gameplay_by_id.get(tid))
        md.append("")

    md += ["## contractRefs 现状检查与优化建议", ""]
    md.append(f"- tasks_back：{len(tasks_back)} 个任务，contractRefs 非空 {count_contract_refs(tasks_back)} 个")
    md.append(f"- tasks_gameplay：{len(tasks_gameplay)} 个任务，contractRefs 非空 {count_contract_refs(tasks_gameplay)} 个")
    md.append("")
    if heuristic_findings:
        md.append("### 需要人工复核的疑点（启发式）")
        md += [f"- Task {f['taskmaster_id']} {f['view_id']}: {f['message']}" for f in heuristic_findings]
        md.append("")
    md += [
        "### 建议口径（建议固化到工作流，而不是靠记忆）",
        "- `contractRefs` 只允许填 EventType（例如 `core.sanguo.*`），不要混入类名/文件名。",
        "- 优先从 `acceptance[].Refs:` 与 `test_refs` 的实际测试断言中反推该任务关心的事件集合，避免语义漂移。",
        "- 对 UI 任务：`contractRefs` 应覆盖 UI 订阅的事件（日志/提示/状态刷新），并与 GdUnit4 用例保持一致。",
        "",
    ]

    out_doc.parent.mkdir(parents=True, exist_ok=True)
    # Use UTF-8 with BOM for Windows tooling compatibility (avoids mojibake in legacy editors/PowerShell).
    out_doc.write_text("\n".join(md), encoding="utf-8-sig", newline="\n")

    out_json_path: str | None = None
    if out_json is not None:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(
            json.dumps(
                {
                    "generated_at": dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z"),
                    "prd": prd_path,
                    "overlay_docs": overlay_docs,
                    "contracts": {"domain_events_by_file": events_by_file},
                    "tasks": {
                        "stats": {
                            "back_total": len(tasks_back),
                            "back_with_contracts": count_contract_refs(tasks_back),
                            "gameplay_total": len(tasks_gameplay),
                            "gameplay_with_contracts": count_contract_refs(tasks_gameplay),
                        },
                        "contract_refs_findings": heuristic_findings,
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
            newline="\n",
        )
        out_json_path = posix(out_json)

    return posix(out_doc), out_json_path
