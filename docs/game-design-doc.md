# Game Design Document (Minimal)

## 可解释性闭环（UI 解释链）

### 目标
- 玩家在 HUD/日志中能理解：为什么扣钱、为什么涨钱、为什么触发事件、为什么进入战斗、为什么结算。
- 解释输出不出现原始事件码或内部字段名，避免信息噪声。
- 同一事件在摘要与详情中保持口径一致。

### 口径
- 解释对象：乘法/加法/判定/触发/结算的结果。
- 展示位置：HUD 事件日志（摘要 + 详情面板）。
- 语言：支持 zh/en，本地化键缺失时允许回退为可读文本。

### 覆盖范围
- 经济变动：钱变动与倍率快照（AppliedMultipliers），包含加法与乘法来源。
- 事件触发：随机/全局/地块事件的来源与触发回合。
- 战斗触发：进入战斗的原因与下一步提示。
- 宝物/卡牌/州郡：获得/失去/生效/协同结算。
- 结算与周期：月结/年结的时间与核心结果。

### 不在范围
- 玩法数值平衡与经济参数设计。
- 叙事剧情与对白文本。

### 解释输出规则
- 不直接输出 eventType、实体 id 或内部字段名。
- 使用本地化键生成标签与值，缺失时回退为可读文本。
- 详情区块固定包含：deltas、facts、multipliers（additive/multiplicative）。

### 依赖与实现入口
- EventExplainService：统一生成摘要与详情。
- LocalizationBootstrap：加载 ui_event_log 与 i18n JSON。
- Data/i18n/zh_cn.json 与 Data/i18n/en_us.json：实体名称与说明。
- Game.Godot/Translations/ui_event_log.*.csv：解释标签与值域翻译。

### 验证与测试（示例）
- Tests.Godot/tests/UI/test_event_log_summary_localized.gd
- Tests.Godot/tests/UI/test_event_log_details_panel.gd
- Tests.Godot/tests/UI/test_hud_event_log_applied_multipliers.gd
- Tests.Godot/tests/UI/test_task51_year_price_adjusted_event_log.gd
- Tests.Godot/tests/UI/test_task56_hud_event_prompt_uses_payload.gd

### ADR 引用
- ADR-0004 事件总线与契约（事件命名与结构）。
- ADR-0003 可观测性与发布健康（日志与可解释性口径）。

## 事件说明字典（解释链）

> 仅用于 UI 解释链口径，对应 HUD 事件日志的摘要/详情展示。

### 经济与结算
- `core.sanguo.economy.year.price.adjusted`
  - 摘要字段：年份、城池、旧价→新价、倍率快照。
  - 详情字段：AppliedMultipliers（加法/乘法来源）。
- `core.sanguo.economy.month.settled`
  - 摘要字段：年份、月份、结算总览。
  - 详情字段：玩家结算列表、AppliedMultipliers。
- `core.sanguo.economy.season.event.applied`
  - 摘要字段：年份、季节、影响范围。
  - 详情字段：受影响州郡、收益倍率、AppliedMultipliers。
- `core.sanguo.city.toll.paid`
  - 摘要字段：付款方、城池、金额。
  - 详情字段：付款/入账/国库溢出、AppliedMultipliers。
- `core.sanguo.city.toll.synergy.paid`
  - 摘要字段：付款方、州郡、总金额。
  - 详情字段：分城池明细、各城池 AppliedMultipliers。

### 事件触发与战斗
- `core.sanguo.random_event.applied`
  - 摘要字段：事件名称、触发来源、回合数。
  - 详情字段：金钱/步数变化、AppliedMultipliers、下一步提示。
- `core.sanguo.combat.started`
  - 摘要字段：遭遇来源、目标强度。
  - 详情字段：遭遇 id、随机种子、下一步提示。
- `core.sanguo.combat.ended`
  - 摘要字段：结果、金钱变化。
  - 详情字段：战斗结果明细。

### 宝物、卡牌与掉落
- `core.sanguo.loot.granted`
  - 摘要字段：掉落类型、来源、关键实体（卡牌/宝物/金钱）。
  - 详情字段：来源类型/来源 id。
- `core.sanguo.relic.applied`
  - 摘要字段：宝物名称、效果类型。
  - 详情字段：金钱/步数变化。
- `core.sanguo.card.lost`
  - 摘要字段：卡牌名称、丢失原因。
  - 详情字段：来源类型/来源 id。
- `core.sanguo.action_card.played`
  - 摘要字段：卡牌名称、效果类型、持续回合。
  - 详情字段：步数变化、AppliedMultipliers（如有）。
- `core.sanguo.action_card.play.rejected`
  - 摘要字段：卡牌名称、拒绝原因。
  - 详情字段：阶段、原因码。

### 州郡与所有权
- `core.sanguo.region.captured`
  - 摘要字段：州郡、拥有者、原因。
  - 详情字段：涉及城池数量。
- `core.sanguo.region.lost`
  - 摘要字段：州郡、拥有者、原因。
  - 详情字段：触发城池。
- `core.sanguo.city.owner.changed`
  - 摘要字段：城池、旧主→新主、原因。
  - 详情字段：仅所有权变化（不解释经济计算）。

### 回合与结局
- `core.sanguo.game.turn.started`
  - 摘要字段：回合、当前玩家、年月日。
- `core.sanguo.game.turn.advanced`
  - 摘要字段：回合、年月日。
- `core.sanguo.game.ended`
  - 摘要字段：结束原因、胜者。
  - 详情字段：终局统计（若有）。
- `core.sanguo.game.turn.ended`
  - 摘要字段：回合、当前玩家。
  - 解释输出：可选（用于回合收束提示）。
- `core.sanguo.game.started`
  - 摘要字段：地图、玩家数、初始资金预设。
  - 解释输出：可选（用于开局说明）。
- `core.sanguo.player.eliminated`
  - 摘要字段：玩家、原因、资金变化。
  - 解释输出：需要（用于淘汰提示）。
- `core.sanguo.game.saved`
  - 摘要字段：存档位。
  - 解释输出：可选（用于保存提示）。
- `core.sanguo.game.loaded`
  - 摘要字段：存档位。
  - 解释输出：可选（用于加载提示）。
