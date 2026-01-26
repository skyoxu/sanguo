#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import datetime as dt
import json
import re
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
    return Path("logs") / "ci" / date / "sync-t65-overlay-from-views"


def _read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_utf8_crlf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = text.replace("\r\n", "\n").replace("\n", "\r\n")
    path.write_bytes(normalized.encode("utf-8"))


def _upsert_file(path: Path, new_text: str) -> WriteResult:
    before = _read_utf8(path) if path.exists() else ""
    after = new_text
    changed = before != after
    if changed:
        _write_utf8_crlf(path, after)
    return WriteResult(
        path=str(path).replace("\\", "/"),
        changed=changed,
        bytes_before=len(before.encode("utf-8")),
        bytes_after=len(after.encode("utf-8")),
    )


def _yaml_list(items: list[str]) -> str:
    return "\n".join([f"  - {x}" for x in items])


def _strip_module_prefix(title: str) -> str:
    t = title.strip()
    if t.startswith("模块:"):
        return t[len("模块:") :].strip()
    return t


def _build_t65_page(task: dict) -> str:
    short = _strip_module_prefix(str(task.get("title", "")).strip())
    adr_refs = list(task.get("adr_refs", []))
    ch_refs = list(task.get("chapter_refs", []))
    acceptance = list(task.get("acceptance", []))
    test_refs = list(task.get("test_refs", []))

    acceptance_block = "\n".join([f"- {a}" for a in acceptance]).strip()
    tests_block = "\n".join([f"- `{t}`" for t in test_refs]).strip()

    return (
        "---\n"
        "PRD-ID: PRD-SANGUO-T2\n"
        f"Title: 08-T65 {short}\n"
        "Status: Draft\n"
        "ADR-Refs:\n"
        f"{_yaml_list(adr_refs)}\n"
        "Arch-Refs:\n"
        f"{_yaml_list(ch_refs)}\n"
        "---\n\n"
        f"# T65：{short}\n\n"
        "## 范围\n"
        "- 连协收费（经济型止损版）：当角色落到州郡内的城市 A（owner=X）时，支付金额 = 该州郡内 owner=X 的全部城市“最终过路费”求和；支付对象始终为落点城市 owner。\n\n"
        "## 非目标\n"
        "- 不实现“全占增益/非经济型增益”。\n"
        "- 不在本任务引入卡牌/宝物对连协收费的实际规避效果（仅预留扩展入口）。\n\n"
        "## 口径冻结\n"
        "- 适用范围：仅当落点城存在 owner，且 owner 不是路过方/自身，并且 owner 在该州郡存在“已拥有城市集合”时才产生连协收费。\n"
        "- 计算方式：逐城先计算“最终过路费”，再求和；返回 total 与 breakdown，且 total 必须等于 breakdown 金额之和。\n"
        "- 止损与输入校验：必要数据缺失/不一致/越界时必须拒绝开始或立即 fail-fast（不得静默降级为 0 或部分结果）。\n"
        "- 规避扩展：允许后续通过“明确的机制能力”对连协收费进行规避扩展；默认实现必须不规避。\n\n"
        "## 契约（EventType + 触发点）\n"
        "- 逐城扣费（经济记账/破产判定的事实来源）：`core.sanguo.city.toll.paid`\n"
        "  - 含 `AppliedMultipliers`（用于 UI/复盘快照）。\n"
        "- 连协收费汇总（UI 分组/复盘语义）：`core.sanguo.city.toll.synergy.paid`\n"
        "  - 仅当本次实际发生 ≥2 次逐城扣费时发布 1 次汇总事件（避免单城时“重复记账”）。\n"
        "  - `Breakdown[]` 必须覆盖本次实际逐城扣费（至少 `CityId/Amount/AppliedMultipliers`），并包含 expected/paid 的总额与计数字段用于复盘。\n\n"
        "## 止损提醒（避免未来返工）\n"
        "- UI/主日志优先以 `core.sanguo.city.toll.synergy.paid` 作为“本次连协收费”的唯一入口；逐城 `core.sanguo.city.toll.paid` 仅作为明细或审计展示。\n"
        "- 逐城扣费的 `CityId` 代表“被计费的城市”，不代表路过方的落点；任何基于落点的展示/判定不得从 `core.sanguo.city.toll.paid.CityId` 反推。\n"
        "- 若发生部分支付（如中途破产），必须使用 `PaidCitiesCount < ExpectedCitiesCount` 与 `PaidTotalAmount != ExpectedTotalAmount` 进行显式标记，避免把“未支付部分”误当作漏事件。\n\n"
        "## 验收条款（ACC）\n"
        f"{acceptance_block}\n\n"
        "## Test-Refs\n"
        f"{tests_block}\n"
    )


def _patch_index_t65_title(index_text: str, new_short_title: str) -> str:
    # Update both the detailed and the ellipsis bullet lines if present.
    # Example lines:
    # - T65 州郡机制（全占增益 + 连协收费）— 见 `08-t65-regions-mechanics.md`
    # - T65 … 见 `08-t65-regions-mechanics.md`
    t1 = re.sub(
        r"(T65)\s+[^—\r\n]+(—\s+见\s+`08-t65-regions-mechanics\.md`)",
        rf"\1 {new_short_title} \2",
        index_text,
    )
    return t1


def main() -> int:
    out_dir = _today_ci_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    views_back = Path(".taskmaster/tasks/tasks_back.json")
    data = json.loads(_read_utf8(views_back))
    t65 = next(x for x in data if x.get("taskmaster_id") == 65)

    overlay_dir = Path("docs/architecture/overlays/PRD-SANGUO-T2/08")
    page_path = overlay_dir / "08-t65-regions-mechanics.md"
    index_path = overlay_dir / "_index.md"

    new_short = _strip_module_prefix(str(t65.get("title", "")).strip())

    results: list[WriteResult] = []
    results.append(_upsert_file(page_path, _build_t65_page(t65)))

    before_index = _read_utf8(index_path)
    after_index = _patch_index_t65_title(before_index, new_short)
    results.append(_upsert_file(index_path, after_index))

    changed = [r.path for r in results if r.changed]
    report = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "operation": "sync_t65_overlay_from_views",
        "changed_paths": changed,
        "results": [r.__dict__ for r in results],
    }
    (out_dir / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"SYNC_T65_OVERLAY status=ok changed={len(changed)} out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
