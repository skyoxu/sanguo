#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WriteResult:
    path: str
    changed: bool
    bytes_before: int
    bytes_after: int


def _today_ci_dir() -> Path:
    date = dt.date.today().strftime("%Y-%m-%d")
    return Path("logs") / "ci" / date / "overlays-t61-t65-freeze"


def _read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_utf8(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Repo enforces CRLF in working tree via .gitattributes; write CRLF to avoid churn/warnings.
    normalized = text.replace("\r\n", "\n").replace("\n", "\r\n")
    path.write_bytes(normalized.encode("utf-8"))


def _upsert_file(path: Path, new_text: str) -> WriteResult:
    before = _read_utf8(path) if path.exists() else ""
    after = new_text
    changed = before != after
    if changed:
        _write_utf8(path, after)
    return WriteResult(
        path=str(path).replace("\\", "/"),
        changed=changed,
        bytes_before=len(before.encode("utf-8")),
        bytes_after=len(after.encode("utf-8")),
    )


def _build_page(title: str, t_id: int, adr_refs: list[str], ch_refs: list[str], body: str) -> str:
    adr_block = "\n".join([f"  - {a}" for a in adr_refs])
    ch_block = "\n".join([f"  - {c}" for c in ch_refs])
    return (
        "---\n"
        f"PRD-ID: PRD-SANGUO-T2\n"
        f"Title: {title}\n"
        "Status: Draft\n"
        "ADR-Refs:\n"
        f"{adr_block}\n"
        "Arch-Refs:\n"
        f"{ch_block}\n"
        "---\n\n"
        f"# T{t_id}：{title.split(' ', 1)[1] if ' ' in title else title}\n\n"
        f"{body.strip()}\n"
    )


def _page_t61() -> str:
    body = """
## 范围
- AI 最小确定性决策：在买地/跳过、建造/跳过、弃牌等需要选择时给出确定性选择。
- 统一审计：AI 的关键选择必须发布 `core.sanguo.ai.decision.made`（ADR-0004）。

## 非目标
- 不做复杂 AI 状态机、评分模型与学习机制（后续任务）。

## 口径冻结
- 确定性：同一输入（GameStartConfig + random_seed + state + TurnNumber/RoundNumber）下，AI 选择结果 100% 可复现。
- 选择策略（止损）：总是选择“第一个合法选项”（按候选列表稳定排序）。
- RNG：允许使用随机，但必须绑定统一 `rng_context_id = "<stream>:<turn>:<round>:<sourceId>"` 并记录候选集证据（候选 id 升序、picked_index/picked_id/hash）。
- 审计：不得出现“未审计的隐式选择”；审计事件必须包含足够信息复盘“为何合法/为何被选中”。

## 契约（EventType + 触发点）
- `core.sanguo.ai.decision.made`：当 AI 在当前情境做出一个会影响游戏状态推进的选择后。

## 验收条款（ACC）
- ACC:T61.1 同一输入下 AI 选择结果可复现。
- ACC:T61.2 关键决策点均走统一策略与统一审计事件。
- ACC:T61.3 AI 决策事件包含足够信息复盘选择过程。

## Test-Refs（占位）
- TODO: `Game.Core.Tests/Tasks/Task61AiDeterminismTests.cs`
"""
    return _build_page(
        title="08-T61 AI 最小确定性策略（止损层）",
        t_id=61,
        adr_refs=["ADR-0004", "ADR-0005"],
        ch_refs=["CH06"],
        body=body,
    )


def _page_t62() -> str:
    body = """
## 范围
- 宝物（Relics）在战斗/事件/设施掉落后立刻生效；效果为永久有效。
- 同局唯一：`relic_id` 同一局内不得重复；重复则重抽，耗尽候选则返回 null 并写入审计。
- 稳定应用顺序：多宝物同时生效时按 `relic_id` 升序应用（保证同输入复现同输出）。

## 非目标
- 不实现宝物的 UI 详情面板与复杂联动（后续任务）。

## 口径冻结
- 掉落：允许来自 event tile、facility 与 PVE 掉落。
- 叠加：宝物效果与事件/卡牌效果可叠加生效；宝物本身永久有效。
- 审计：掉落结果（含“空掉落”）必须写入审计；主日志是否展示由 UI 策略决定。
- 不使用“max_id 兜底”：候选耗尽即返回 null。

## 契约（EventType + 触发点）
- 当前阶段优先复用“经济事件倍率快照（applied_multipliers）”来体现宝物对经济的影响；如需显式掉落事件，后续补充 Contracts（最终以 Contracts 为准）。

## 验收条款（ACC）
- ACC:T62.1 宝物掉落能被记录并立刻生效，且同局内不重复。
- ACC:T62.2 同一输入下宝物应用顺序与最终效果可复现。
- ACC:T62.3 掉落与生效产生可审计的域事件（以 Contracts 为准）。

## Test-Refs（占位）
- TODO: `Game.Core.Tests/Tasks/Task62RelicsTests.cs`
"""
    return _build_page(
        title="08-T62 宝物系统（Relics）",
        t_id=62,
        adr_refs=["ADR-0004", "ADR-0005", "ADR-0019"],
        ch_refs=["CH05", "CH06"],
        body=body,
    )


def _page_t63() -> str:
    body = """
## 范围
- 全局事件由 `RoundNumber` 驱动（替代季度/年度），每轮最多检查与触发一次。
- 触发点：在每轮开始前（发布 `core.sanguo.game.turn.started` 之前）检查并应用。

## 非目标
- 不实现季度/年度事件（本阶段已弃用）。

## 口径冻结
- 触发频率：每轮最多触发一次（同轮内不重复触发）。
- 复现：同一 random_seed 下事件选择与应用结果可复现（候选 id 升序、picked_index/picked_id/hash）。
- 契约：使用 `core.sanguo.random_event.applied` 表达“事件格/全局事件”的统一应用（Contracts 已定义）。
- 归属：全局事件的 `PlayerId` 绑定为该轮的“首个行动者”（用于事件归属与审计一致性）。
- 兜底：如因冷却/唯一性过滤导致候选为空，则使用兜底事件（冷却为 0 的小收益事件）保证流程可继续。

## 契约（EventType + 触发点）
- `core.sanguo.random_event.applied`：当全局事件被选中并成功应用后（source=global）。

## 验收条款（ACC）
- ACC:T63.1 每轮最多触发一次全局事件检查与应用（同轮内不重复触发）。
- ACC:T63.2 选择与效果应用在同一 random_seed 下可复现。
- ACC:T63.3 触发后发布事件供 UI 展示与复盘（以 `core.sanguo.random_event.applied` 为准）。

## Test-Refs（占位）
- TODO: `Game.Core.Tests/Tasks/Task63GlobalEventTests.cs`
"""
    return _build_page(
        title="08-T63 全局事件触发机制（RoundNumber）",
        t_id=63,
        adr_refs=["ADR-0004", "ADR-0005"],
        ch_refs=["CH06"],
        body=body,
    )


def _page_t64() -> str:
    body = """
## 范围
- 州郡（Regions）为配置数据模型：用于表达“州郡全占增益”与“州郡连协收费”的边界。
- region_id 跨地图复用：同一 region_id 可以在不同地图出现（用于复用增益配置）。

## 非目标
- 不实现地图编辑器与运行时热更新。

## 口径冻结
- 数据来源：配置只读，路径与白名单约束遵循 ADR-0019。
- 校验：地图加载时校验 region 定义与 tile.region_id 引用完整性；缺失/越界 fail-fast。
- i18n：region 的 name/description 一律使用 i18n key，不直接写展示文本。

## 契约（EventType + 触发点）
- 当前阶段优先在加载校验失败时走错误上报/审计；显式事件待后续任务补充（以 Contracts 为准）。

## 验收条款（ACC）
- ACC:T64.1 地图加载时校验 region 定义与引用完整性；缺失/越界 fail-fast。
- ACC:T64.2 name/description 走 i18n key（地图索引与 region 均用 key）。

## Test-Refs（占位）
- TODO: `Game.Core.Tests/Tasks/Task64RegionsConfigTests.cs`
"""
    return _build_page(
        title="08-T64 州郡数据模型（Regions）",
        t_id=64,
        adr_refs=["ADR-0019", "ADR-0005"],
        ch_refs=["CH05"],
        body=body,
    )


def _page_t65() -> str:
    body = """
## 范围
- 州郡机制包含两部分：
  - 全占增益：某州郡内所有城市归属同一角色时立即生效；当城市释放为无主或被夺取导致不再全占时立即失效。
  - 连协收费：当角色落到州郡内的城市 A（owner=X）时，支付金额 = 该州郡内 owner=X 的全部城市的“最终过路费”求和；支付对象始终为落点城市 owner。

## 非目标
- 不实现非经济型州郡增益（后续可扩展）。

## 口径冻结
- 生效/失效：买下最后一座 city 时立即生效；出局释放资产为无主时立即失效；卡牌/宝物夺取城市同样触发生效/失效。
- 影响面：本阶段只做经济型影响（buy/toll/settlement 两类），且全部来自 Core 计算；UI 只展示。
- 连协收费：按 owner 在 region 内的占有城市集合求和；缺失 region 数据 fail-fast。
- 规避：连协收费可被机制（卡牌/宝物）规避，但规避必须通过明确机制能力实现，不是规则例外。

## 契约（EventType + 触发点）
- 连协收费与全占增益对经济的影响必须通过“经济事件倍率快照（applied_multipliers）”体现；如需显式审计事件，后续补充 Contracts（最终以 Contracts 为准）。

## 验收条款（ACC）
- ACC:T65.1 全占增益生效/失效时点正确，且只影响本州郡城市的经济点（buy/toll/settlement）。
- ACC:T65.2 连协收费按 owner 在 region 内的占有城市集合求和；缺失 region 数据 fail-fast。
- ACC:T65.3 连协收费可被卡牌/宝物机制规避（规避作为机制能力，不是规则例外）。

## Test-Refs（占位）
- TODO: `Game.Core.Tests/Tasks/Task65RegionsMechanicsTests.cs`
"""
    return _build_page(
        title="08-T65 州郡机制（全占增益 + 连协收费）",
        t_id=65,
        adr_refs=["ADR-0004", "ADR-0005"],
        ch_refs=["CH05", "CH06"],
        body=body,
    )


def _update_index(index_path: Path, add_files: list[str]) -> WriteResult:
    before = _read_utf8(index_path)
    lines = before.splitlines()

    # Insert under the T50-T60 list; add a new T61-T65 subsection if missing.
    marker = "  - T60"
    insert_after = None
    for i, line in enumerate(lines):
        if line.strip().startswith(marker):
            insert_after = i
    # Fallback: insert near the end of list block
    if insert_after is None:
        insert_after = len(lines) - 1

    block = [
        "  - T61–T65 多页（按任务拆分）：",
    ] + [f"  - T{n} … 见 `{name}`" for n, name in add_files]

    # Ensure we don't insert duplicates.
    joined = "\n".join(lines)
    if all(name in joined for _, name in add_files):
        return WriteResult(
            path=str(index_path).replace("\\", "/"),
            changed=False,
            bytes_before=len(before.encode("utf-8")),
            bytes_after=len(before.encode("utf-8")),
        )

    new_lines = lines[: insert_after + 1] + [""] + block + lines[insert_after + 1 :]
    after = "\n".join(new_lines).rstrip() + "\n"
    _write_utf8(index_path, after)
    return WriteResult(
        path=str(index_path).replace("\\", "/"),
        changed=True,
        bytes_before=len(before.encode("utf-8")),
        bytes_after=len(after.encode("utf-8")),
    )


def main() -> int:
    out_dir = _today_ci_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    base = Path("docs/architecture/overlays/PRD-SANGUO-T2/08")
    pages: list[tuple[int, str, str]] = [
        (61, "08-t61-ai-minimal-deterministic.md", _page_t61()),
        (62, "08-t62-relics.md", _page_t62()),
        (63, "08-t63-global-events.md", _page_t63()),
        (64, "08-t64-regions.md", _page_t64()),
        (65, "08-t65-regions-mechanics.md", _page_t65()),
    ]

    results: list[WriteResult] = []
    changed: list[str] = []

    for _, filename, content in pages:
        p = base / filename
        r = _upsert_file(p, content)
        results.append(r)
        if r.changed:
            changed.append(r.path)

    index_path = base / "_index.md"
    add_files = [(t_id, fname) for t_id, fname, _ in pages]
    r_index = _update_index(index_path, add_files)
    results.append(r_index)
    if r_index.changed:
        changed.append(r_index.path)

    report = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "operation": "update_overlays_t61_t65_freeze",
        "changed_paths": changed,
        "results": [r.__dict__ for r in results],
    }
    (out_dir / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"OVERLAYS_T61_T65 status=ok changed={len(changed)} out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
