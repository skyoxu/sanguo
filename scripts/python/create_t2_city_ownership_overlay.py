#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate PRD-SANGUO-T2 overlay doc for city ownership model.

This script writes Markdown under:
  docs/architecture/overlays/PRD-SANGUO-T2/08/

Design goals:
- Deterministic content (UTF-8).
- Avoid toolchain drift by keeping acceptance + Test-Refs close to tasks and code.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path


PRD_ID = "PRD-SANGUO-T2"
OVERLAY_DIR = Path("docs/architecture/overlays") / PRD_ID / "08"
DOC_PATH = OVERLAY_DIR / "08-t2-city-ownership-model.md"
INDEX_PATH = OVERLAY_DIR / "_index.md"


LINK_LINE = "- [08-功能纵切-T2-城池所有权模型](08-t2-city-ownership-model.md)"


def _write_utf8(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def build_doc() -> str:
    return """# 08-功能纵切-T2-城池所有权模型

## 8.x 范围与目标

- 本文档定义 T2 阶段的「城池所有权/出局释放」领域规则与验收口径，避免 PRD、任务与实现之间口径漂移。
- 关联任务：Task 12（购买城池）、Task 13（过路费支付）、Task 17（回合循环）。
- 关联 ADR（引用，不复制阈值）：ADR-0018、ADR-0020、ADR-0004、ADR-0005、ADR-0015、ADR-0024。
- 关联章节：CH05、CH06、CH07、CH09。

## 8.x.1 模型定义（领域层）

### 1) 所有权表示（SSoT）

- 领域层 `City` 为不可变记录，不持有 `Owner` 字段；所有权由 `SanguoPlayer.OwnedCityIds` 表示。
- “无人占领”定义：任意玩家的 `OwnedCityIds` 均不包含该 `CityId`。
- “拥有”定义：恰好一个未出局玩家的 `OwnedCityIds` 包含该 `CityId`。

> 说明：PRD 文本中曾描述 `City.Owner`（引用 Player 或 null），但本仓库实现选择“所有权在 Player 侧集中表示”，以减少双向引用与可变状态分散。若未来要回归 `City.Owner`，应以新增/替代 ADR 的方式显式迁移。

### 2) 出局状态（锁定态）

- `SanguoPlayer.IsEliminated=true` 表示该玩家出局，领域对象进入锁定态：
  - 不允许再购买（`TryBuyCity` 返回 `false`）。
  - 不允许再支付过路费（`TryPayTollTo` 返回 `false`）。
- 出局后的回合轮转/游戏结束由 `TurnManager` 负责：
  - 玩家出局 → 触发 GameOver（前台表现由后续任务实现）。
  - NPC 出局 → 退出本局剩余回合。

## 8.x.2 触发时机与状态转移

### A. 购买城池（Task 12）

- 触发：玩家停留在无人占领城池并选择购买。
- 领域调用：`SanguoPlayer.TryBuyCity(city, priceMultiplier)`。
- 状态变化：
  - 资金减少：`city.GetPrice(priceMultiplier, rules)`。
- `OwnedCityIds` 增加 `CityId`。

### B. 支付过路费（Task 13）

- 触发：玩家停留在他人拥有城池。
- 领域调用：`SanguoPlayer.TryPayTollTo(owner, city, tollMultiplier, treasury)`。

**正常支付（资金足够）**

- 支付方资金减少 `toll`。
- 收款方资金增加 `toll`；若超过资金上限，则：
  - 收款方资金封顶；
  - 溢出金额归集到 `SanguoTreasury`（默认视作进入“国库/丢弃”，具体落地在回合/事件系统任务中实现）。

**资金不足（破产/出局分支）**

- 支付方剩余资金全额转给债权人（收款方），支付方资金归零。
- 支付方标记出局：`IsEliminated=true`。
- 支付方释放全部城池：清空 `OwnedCityIds` → 原持有城池回到“无人占领”。

> 说明：PRD 对 T2 的原始建议是“资金不足时支付所有剩余资金，后续阶段再引入破产判定”。本仓库按任务强化口径，
> 在“支付剩余资金”之后立即进入出局锁定（不可再交易/释放城池），以避免负资金传播并简化回合推进；整局胜负与 UI 表现
> 仍由回合管理与结算相关任务落地。

## 8.x.3 字段与不变式（实现对齐）

- `SanguoPlayer.PlayerId`：唯一标识。
- `SanguoPlayer.Money`：非负，且不超过资金上限（上限由 `Money` 值对象定义）。
- `SanguoPlayer.OwnedCityIds`：去重集合；出局时必须清空。
- `SanguoPlayer.IsEliminated`：出局锁定开关。
- `SanguoEconomyRules.MaxPriceMultiplier/MaxTollMultiplier`：价格/过路费倍数上限（可配置）。
- `SanguoTreasury`：资金上限导致的溢出金额归集点（后续由回合系统决定如何落盘与展示）。

## 8.x.4 验收标准（就地验收）

- 购买成功：资金扣减正确且 `OwnedCityIds` 增加。
- 已出局玩家：购买/付费均不得改变任何状态（返回 `false`）。
- 过路费（资金足够）：支付方资金不为负，收款方增加正确。
- 过路费（资金不足）：剩余资金全额转给债权人；支付方资金归零、出局、释放全部城池；之后不得再交易。
- 收款方达到资金上限：收款方封顶，溢出金额正确归集到 treasury。

> 可选加固（不属于本节验收的硬门禁）：审计追踪/事件溯源/最大拥有城池数上限等，见 Task 13 的 details/testStrategy 描述。

## Test-Refs

- `Game.Core.Tests/Domain/SanguoPlayerTests.cs`
  - `SanguoPlayer_TryBuyCity_WhenEnoughMoney_ShouldDeductMoneyAndAddCity`
  - `SanguoPlayer_TryPayTollTo_WhenInsufficientFunds_TransfersRemainingMoney_EliminatesAndReleasesCities`
  - `SanguoPlayer_TryPayTollTo_WhenPayerEliminated_ReturnsFalse`
  - `SanguoPlayer_TryPayTollTo_WhenOwnerEliminated_ReturnsFalse`
  - `SanguoPlayer_TryPayTollTo_WhenCreditorWouldExceedMax_ShouldCapCreditorAndDepositOverflowToTreasury`
"""


def update_index(existing: str) -> str:
    if "08-t2-city-ownership-model.md" in existing:
        return existing

    lines = existing.splitlines()
    inserted = False
    for i, line in enumerate(lines):
        if "08-功能纵切-T2-三国大富翁闭环" in line:
            lines.insert(i + 1, LINK_LINE)
            inserted = True
            break
    if not inserted:
        if lines and lines[0].startswith("#"):
            lines.insert(1, "")
            lines.insert(2, LINK_LINE)
        else:
            lines.append(LINK_LINE)
    return "\n".join(lines).rstrip("\n") + "\n"


def write_logs(root: Path, doc_path: Path, index_path: Path) -> None:
    now = _dt.datetime.now().astimezone()
    date_dir = now.strftime("%Y-%m-%d")
    out_dir = root / "logs" / "ci" / date_dir / "overlay-gen"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "ts": now.isoformat(timespec="seconds"),
        "action": "create_t2_city_ownership_overlay",
        "output": {
            "doc": str(doc_path.as_posix()),
            "index": str(index_path.as_posix()),
        },
    }
    _write_utf8(out_dir / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    root = Path(__file__).resolve().parents[2]

    OVERLAY_DIR.mkdir(parents=True, exist_ok=True)

    _write_utf8(DOC_PATH, build_doc())

    if INDEX_PATH.exists():
        existing = INDEX_PATH.read_text(encoding="utf-8")
    else:
        existing = "# PRD-SANGUO-T2 功能纵切索引\n\n"
    _write_utf8(INDEX_PATH, update_index(existing))

    write_logs(root, DOC_PATH, INDEX_PATH)
    print(f"Wrote: {DOC_PATH}")
    print(f"Updated: {INDEX_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
