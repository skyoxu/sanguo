from __future__ import annotations

import datetime as dt
from pathlib import Path


def _detect_newline(raw: bytes) -> str:
    if b"\r\n" in raw:
        return "\r\n"
    return "\n"


def _replace_once(text: str, old: str, new: str) -> str:
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise ValueError(f"expected text to contain replacement target: {old!r}")


def _insert_after(text: str, marker: str, insertion: str) -> str:
    idx = text.find(marker)
    if idx < 0:
        raise ValueError(f"marker not found: {marker!r}")
    if text.find(marker, idx + 1) >= 0:
        raise ValueError(f"marker not unique: {marker!r}")
    return text[: idx + len(marker)] + insertion + text[idx + len(marker) :]


def main() -> int:
    repo_root = Path(".")
    prd_path = repo_root / ".taskmaster" / "docs" / "prd.txt"
    raw = prd_path.read_bytes()
    newline = _detect_newline(raw)
    # Normalize to LF for editing to avoid accidental CRCRLF corruption.
    text = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")

    # Update scope/goal to match the current planned feature set (cards/combat/relics/etc.).
    text = _replace_once(
        text,
        "范围：在该阶段，游戏包含玩家与至少一个AI对手，支持轮流掷骰前进、购买城池、收取过路费、定期结算收益及触发环境事件等核心机制。战斗、装备、道具、卡片等高级元素暂不引入，仅保留金钱和城池所有权作为主要变量。游戏为单机离线模式，平台限定为Windows（Godot Mono版本）",
        "范围：在该阶段，游戏包含玩家与AI对手（总人数 4–8），支持新游戏配置（地图/人数/起始资金档位/选角与AI补位）、回合制掷骰移动、落地动作（买地/收租/建造/触发事件/设施动作）、周期性收益结算、行动卡（BeforeRoll 0/1）、PVE 战斗（可快速结算）与掉落（含宝物/卡牌/金钱）、以及明确的破产出局与结算界面。时间“日/月/年/季度/年度”仅作为 UI 投影显示，不参与任何逻辑计算；季度/年度事件在本阶段已弃用，由 RoundNumber 驱动的全局事件机制替代。游戏为单机离线模式，平台限定为 Windows（Godot Mono 版本）。",
    )

    text = _replace_once(
        text,
        "目标：实现完整的玩法闭环：玩家掷骰子→按点数移动→停留格子判断购买或付费→月末结算收益→季度环境事件→年初地价调整→下一轮循环。确保这一循环可以周而复始进行，形成基本的玩法体验。该阶段侧重验证核心机制，无明确胜负条件（可在后续阶段添加例如破产判负等规则）。",
        "目标：实现“可复现开局 → 回合循环（BeforeRoll→掷骰→移动→落地动作）→ 经济结算/全局事件/战斗（可选）→ 胜负判定 → 结算界面 → 回主菜单”的完整可玩闭环。保证同一输入（配置+random_seed+状态）可复现同一输出；所有经济数值计算仅在 Core 发生，UI 只展示事件/投影字段；事件命名遵循 ADR-0004（CloudEvents-like type）。",
    )

    # Refresh user stories that were previously describing deprecated quarter/year mechanics.
    text = _replace_once(
        text,
        "收益结算：作为玩家，我希望每月最后一天自动结算我所拥有城池的收益，使我的资金随着时间增长，增加经营管理的维度。",
        "收益结算：作为玩家，我希望按固定轮次周期自动结算我所拥有城池的收益（例如每 15 轮一次；UI 可投影为“月末”），使我的资金随着进程增长，增加经营管理的维度。",
    )
    text = _replace_once(
        text,
        "环境事件：作为玩家，我希望每季度开始时出现随机的环境事件影响某些区域（州郡）的土地收益，这会带来正负不定的效果，为游戏增加变化和策略性。",
        "全局事件：作为玩家，我希望每轮开始前触发全局事件检查，并可能对特定区域或经济/战斗产生影响，为游戏增加变化与策略性（同输入可复现）。",
    )
    text = _replace_once(
        text,
        "地价变动：作为玩家，我希望每年年初进行一次全国性的地价调整，使所有城池的价值发生变化，从而影响我未来的投资和资金策略。",
        "终局与结算：作为玩家，我希望当资金降为 0（或以下）时出局；当只剩 1 个未出局角色时判定胜利，并进入结算界面查看结果与统计快照。",
    )

    # Mark quarter/year sections as deprecated (kept as historical reference).
    dep_q = f"\n季度环境事件\n\n"
    if dep_q in text:
        text = text.replace(
            dep_q,
            "\n季度环境事件（已弃用）\n\n"
            "本阶段不实现季度/年度事件；统一由 T63「全局事件触发机制（RoundNumber）」替代。以下内容仅保留为历史参考。\n\n",
            1,
        )
    dep_y = f"\n年度地价调整\n\n"
    if dep_y in text:
        text = text.replace(
            dep_y,
            "\n年度地价调整（已弃用）\n\n"
            "本阶段不实现年度地价调整；统一由 T63「全局事件触发机制（RoundNumber）」替代或延后到后续阶段。以下内容仅保留为历史参考。\n\n",
            1,
        )

    # Replace the deprecated time-check bullets with RoundNumber global-event checks.
    old_time_block = (
        "收益结算：如果 `RoundNumber` 达到收益结算周期边界（本阶段：每 15 轮一次），则执行一次收益结算并入账。\n"
        "\n"
        "季度首日（显示层投影）：若 UI 投影的日期进入新季度（例如1/4/7/10月首日），则按概率触发环境事件并应用其效果。\n"
        "\n"
        "年初（显示层投影）：若 UI 投影的年份发生变化，则执行一次年初地价调整（然后同样按季度规则处理Q1的环境事件）。\n"
        "\n"
        "执行次序：当年初与季度重合时（1月1日），应先执行地价调整，再执行该季度的环境事件，以免事件影响前后不一致；月末结算总是在月最后一天当晚进行（在日期推进到下月之前）。时间管理模块确保以上事件按顺序触发。\n"
    )
    new_time_block = (
        "收益结算：如果 `RoundNumber` 达到收益结算周期边界（本阶段：每 15 轮一次），则执行一次收益结算并入账。\n"
        "\n"
        "全局事件（T63）：在每轮开始前（发布 `core.sanguo.game.turn.started` 之前）进行一次全局事件检查；若命中则应用并发布 `core.sanguo.global_event.triggered`（同输入可复现）。\n"
        "\n"
        "执行次序（止损）：全局事件检查 → turn.started → 回合内行动（含落地动作/战斗可选）→ turn.advanced → 胜负检查/结算界面（若触发）。\n"
    )
    if old_time_block in text:
        text = _replace_once(text, old_time_block, new_time_block)

    # Character module: align with 4–8 players by requiring >=8 unique characters and add combat_rating.
    text = _replace_once(
        text,
        "- 角色数量：6 个（全局唯一，不可重复选择）",
        "- 角色数量：至少 8 个（全局唯一，不可重复选择；满足总人数 4–8 的补位约束）",
    )
    text = _replace_once(
        text,
        "- 非范围：技能池、体力系统、战斗/装备/道具、角色进度成长（除经济系数快照外）。",
        "- 非范围：技能池、体力系统、装备/道具、角色进度成长（除经济系数/战斗基线快照外）。",
    )
    if "\n- portrait_path: string（res://...）\n" in text and (
        "\n- combat_rating:" not in text
    ):
        text = text.replace(
            "\n- portrait_path: string（res://...）\n",
            "\n- portrait_path: string（res://...）\n"
            "- combat_rating: int（静态战斗强度基线，>=0；供 PVE 判定与事件快照使用）\n",
            1,
        )
    text = _replace_once(
        text,
        "- 选角界面：能加载 res://Data/characters.json 并展示 6 个角色的 name/description/portrait_path/四个 multiplier 字段。",
        "- 选角界面：能加载 res://Data/characters.json 并展示至少 8 个角色的 name/description/portrait_path/combat_rating/四个 multiplier 字段。",
    )

    # Remove remaining references to deprecated quarter/year mechanics outside the deprecated sections.
    text = _replace_once(
        text,
        "城池属性：每个城池有名称（可取三国时期真实城池名）、所属州郡（用于区域事件）、基础价格和基础过路费。",
        "城池属性：每个城池有名称（可取三国时期真实城池名）、所属州郡（用于州郡机制/全局事件）、基础价格和基础过路费。",
    )
    text = _replace_once(
        text,
        "州郡结构：城池按历史上的州/郡划分区域，每个城池记录所属的州郡名称。季度环境事件将以此为单位影响区域内城池的收益。",
        "州郡结构：城池按历史上的州/郡划分区域，每个城池记录所属的州郡名称；全局事件与州郡机制可能以此为单位影响区域内城池的经济点。",
    )
    text = _replace_once(
        text,
        "回合循环：在处理完当前回合的一切事务（包括上述时间事件）后，游戏进入下一回合，如此循环往复，直到出现游戏终局条件（T2阶段暂未定义终局，可无限循环）。",
        "回合循环：在处理完当前回合的一切事务（包括上述时间事件）后，游戏进入下一回合，如此循环往复，直到出现终局条件（破产出局/仅剩 1 个未出局角色/玩家控制角色出局）。终局触发后进入结算界面并返回主菜单。",
    )

    # Insert T61–T65 draft modules after T60 placeholder test ref.
    marker = "  - `Tests.Godot/tests/UI/test_task60_game_end_screen.gd`"
    insertion = """

T61 模块: AI 最小确定性策略（止损层）
- 范围：AI 行为与玩家同规则、同约束；所有决策点（buy/skip、build/skip、choose_building_type、discard_cards、teleport_target、facility_action 等）均采用“总是选择第一个合法选项”的确定性策略；本阶段 AI 不使用额外随机。
  - 可观测性：每次 AI 做出选择必须发布 `core.sanguo.ai.decision.made`（原因/决策点/候选数量等，便于复盘）。
- 验收：
  - ACC:T61.1 同一输入（game_start_config + random_seed + state + TurnNumber/RoundNumber）下，AI 选择结果 100% 可复现。
  - ACC:T61.2 关键决策点均走统一策略与统一审计事件（不得出现“未审计的隐式选择”）。
  - ACC:T61.3 AI 决策事件包含足够信息复盘“为何该选择合法/为何被选中”。
- Test-Refs（占位）：
  - `Game.Core.Tests/Tasks/Task61AiDeterminismTests.cs`

T62 模块: 宝物系统（Relics）
- 范围：宝物掉落来源包含战斗/事件格/设施；同一局内 relic_id 全局唯一不重复；宝物效果覆盖经济/战斗/全局事件三类；每个宝物在配置中声明 effect 为“加/乘”，多宝物叠加按 relic_id 升序应用（稳定性优先）。
- 验收：
  - ACC:T62.1 宝物掉落能被记录并立刻生效，且同局内不重复。
  - ACC:T62.2 同一输入下宝物应用顺序与最终效果可复现。
  - ACC:T62.3 掉落与生效产生可审计的域事件（建议 `core.sanguo.loot.granted` 与/或 `core.sanguo.relic.applied`，最终以 Contracts 为准）。
- Test-Refs（占位）：
  - `Game.Core.Tests/Tasks/Task62RelicsTests.cs`

T63 模块: 全局事件触发机制（RoundNumber，替代季度/年度）
- 范围：第二套事件池（建议 `res://Data/global_events.json`）；每轮只检查一次全局事件（RoundNumber 边界）；事件在 turn.started 之前触发并发布审计事件；显示层按“每 30 轮=1月、每 360 轮=1年”投影，仅展示不计算。
- 验收：
  - ACC:T63.1 每轮最多触发一次全局事件检查与应用（同轮内不重复触发）。
  - ACC:T63.2 全局事件选择与效果应用在同一 random_seed 下可复现（均匀抽样/冷却规则以配置为准）。
  - ACC:T63.3 触发后发布 `core.sanguo.global_event.triggered` 以供 UI 展示与复盘。
- Test-Refs（占位）：
  - `Game.Core.Tests/Tasks/Task63GlobalEventsTests.cs`

T64 模块: 州郡数据模型（Regions）
- 范围：随地图定义 regions；每个 city tile 必须包含 region_id；region 可跨地图复用同一 region_id；region 字段最小集：region_id/name_key/bonus_kind/bonus_params。
- 验收：
  - ACC:T64.1 地图加载时校验 region 定义与 tile.region_id 引用完整性；缺失/越界 fail-fast。
  - ACC:T64.2 name/description 走 i18n key（地图索引与 region 均用 key，不直接写展示文本）。
- Test-Refs（占位）：
  - `Game.Core.Tests/Tasks/Task64RegionsDataModelTests.cs`

T65 模块: 州郡机制（全占增益 + 连协收费）
- 范围：当某州郡内所有城市归属同一角色时，立即生效州郡增益（不可选择、不可取消；买下最后一城生效，出局释放资产立即失效）；连协收费：落到他人 city 时，按“该 owner 在该州郡拥有的所有城市的最终过路费之和”收费（先算每城最终过路费，再求和）。
  - 止损：同回合 teleport 最多一次；teleport 落点结算只一次；落点不得再次 teleport/战斗（避免连锁不可控）。
- 验收：
  - ACC:T65.1 全占增益的生效/失效时点正确，且只影响本州郡城市的经济点（buy/toll/settlement）。
  - ACC:T65.2 连协收费按 owner 在 region 内的占有城市集合求和；缺失 region 数据 fail-fast。
  - ACC:T65.3 连协收费可被卡牌/宝物机制规避（规避作为机制能力，不是规则例外）。
- Test-Refs（占位）：
  - `Game.Core.Tests/Tasks/Task65RegionSynergyTollTests.cs`
""".lstrip("\n")
    if marker in text and "T61 模块:" not in text:
        text = _insert_after(text, marker, insertion)

    # Write updated PRD preserving original newline style.
    normalized_lines = text.split("\n")
    out_text = newline.join(normalized_lines)
    if not out_text.endswith(newline):
        out_text += newline
    out_bytes = out_text.encode("utf-8")
    prd_path.write_bytes(out_bytes)

    # Log a minimal audit trail.
    today = dt.date.today().strftime("%Y-%m-%d")
    out_dir = repo_root / "logs" / "ci" / today
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "prd-update-t61-t65.log"
    u_fffd = text.count("\ufffd")
    log_path.write_text(
        "\n".join(
            [
                "Updated .taskmaster/docs/prd.txt",
                f"newline={repr(newline)}",
                f"contains_uFFFD={u_fffd}",
                "applied_changes=scope,goal,user_stories,deprecated_sections,time_block,character_module,insert_t61_t65",
            ]
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(f"Wrote PRD: {prd_path.as_posix()}")
    print(f"Wrote log: {log_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
