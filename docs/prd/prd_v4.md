# PRD v4（基于当前仓库的最小侵入战斗改造方案）

- 文档日期：2026-05-11
- 基线来源：`docs/prd/prd_v3.md`、当前已实现仓库代码与数据结构
- 适用目标：角色属性、敌方属性/Boss 属性、PVE 战斗逻辑、战斗场景 UI
- 约束原则：不平行新建第二套角色 schema、战斗事件、战斗场景或启动配置

配套文件：

- `docs/prd/PRD_V4_RULES_FREEZE.md`
- `docs/prd/PRD_V4_ACCEPTANCE_ASSERTIONS.md`
- `docs/prd/PRD_V4_TRACEABILITY_MATRIX.md`

---

## 1. 文档目标

本版本不是推翻当前系统重做战斗，而是在当前仓库能力基础上，对现有角色数据、战斗契约、战斗 resolver、战斗场景进行最小侵入扩展，使项目从当前“战力阈值比较”升级为“可进入独立战斗场景的自动战斗 PVE 系统”。

本版本明确要求：

1. 角色、敌方、Boss 统一进入同一套 PVE 战斗规则。
2. 继续复用当前 `GameStartConfig`、`SanguoCharacterDefinition`、`SanguoCombatStarted`、`SanguoCombatEnded`、`SanguoBattleView`。
3. 所有新增能力以“扩展现有契约/场景/数据文件”为准，不允许新建平行系统替代现有系统。

---

## 2. 当前基线与复用边界

以下是 v4 必须复用的现有资产：

- 角色定义契约：`Game.Core/Contracts/Sanguo/SanguoCharacterDefinition.cs`
- 角色数据入口：`Data/characters.json`
- 角色数据加载与校验：`Game.Core/Services/Sanguo/SanguoCharactersCatalogLoader.cs`
- 开局配置契约：`Game.Core/Contracts/Sanguo/GameStartConfig.cs`
- 战斗契约：`Game.Core/Contracts/Sanguo/SanguoCombatContracts.cs`
- 战斗求解入口：`Game.Core/Services/Sanguo/SanguoCombatResolver.cs`
- 战斗场景入口：`Game.Godot/Scenes/Sanguo/SanguoBattleView.tscn`
- 战斗场景脚本：`Game.Godot/Scripts/Sanguo/SanguoBattleView.cs`
- 宝物数据入口：`Data/relics.json`
- 随机事件战斗触发入口：`Data/random_events.json`

以下是 v4 不允许做的事情：

- 不新建第二个角色定义文件替代 `SanguoCharacterDefinition`
- 不新建新的战斗 started/ended 事件名
- 不新建 `BattleStartConfig` 之类的平行启动契约
- 不新建 `BattleViewV2`、`BattleViewV4` 一类平行场景
- 不把 `random_events.json` 直接伪装成正式敌方/Boss 配置表

---

## 3. v4 要解决的现状缺口

当前仓库战斗能力存在以下边界：

1. 角色只有 `CombatRating`，没有可展开的战斗属性。
2. 战斗结果只有 `Outcome`、`MoneyDelta`、`EncounterTarget`、`EffectiveCombatRating`，不足以承载真实战报与战后状态。
3. `SanguoCombatResolver.ResolvePveCombat(...)` 仍是“战力 >= 阈值即胜利”的一次性比较。
4. `SanguoBattleView` 只是事件监听后的结果弹窗，并非真正的战斗场景。
5. 宝物仅支持 `moneyDelta` 和 `economyStepDelta`，还没有战斗属性入口。
6. 随机事件只会触发 `encounterId + encounterTarget`，还没有正式敌人/Boss 定义来源。

---

## 4. v4 范围

### 4.1 In Scope

1. 扩展角色战斗属性 schema。
2. 新增敌方/Boss 配置 schema。
3. 新增技能配置 schema 的最小可落地结构。
4. 新增战斗初始化期运行时属性框架。
5. 实现自动攻击读条式 PVE 战斗逻辑。
6. 纳入召唤物、群攻、反伤、DoT 的 v4 规则。
7. 扩展战斗 started/ended 契约 payload。
8. 原地扩展 `SanguoBattleView.tscn` 与 `SanguoBattleView.cs` 为真实战斗场景。
9. 支持胜利奖励展示和失败后回主循环。

### 4.2 Out of Scope

1. 完整技能引擎正式版。
2. 战斗中动态 buff/debuff 引擎。
3. 多种敌方 AI 行为树或复杂站位系统。
4. PvP 战斗。
5. 重新设计主循环、HUD 总体框架、EventBus 总线机制。

---

## 5. 角色与敌方属性模型

### 5.1 角色基础属性

角色基础属性通过扩展现有 `SanguoCharacterDefinition` 承载，保留现有 `CombatRating` 字段，不删除。

角色基础属性包含：

- `MaxHP`
- `Attack`
- `CritRate`
- `CritMultiplier`
- `LifeStealRate`
- `DodgeRate`
- `AttackSpeed`
- `DamageReductionRate`
- `ReflectRate`
- `AoEEnabled`

说明：

1. `CombatRating` 在 v4 中保留为兼容字段，可继续用于旧 UI、旧任务、旧数据验证或临时回退路径。
2. `AttackSpeed` 表示“每次攻击需要的秒数”，数值越小越快，下限为 `0.5s`。
3. `AoEEnabled` 为布尔语义，表示常驻群攻属性是否生效。

### 5.2 敌方 / Boss 基础属性

敌方与 Boss 使用同一套战斗属性结构，但不包含暴击体系。

敌方 / Boss 属性包含：

- `MaxHP`
- `Attack`
- `LifeStealRate`
- `DodgeRate`
- `AttackSpeed`
- `DamageReductionRate`
- `ReflectRate`
- `AoEEnabled`

说明：

1. 敌方 / Boss 未来默认不接入暴击体系。
2. Boss 不单独发明另一套战斗公式，仅在配置、展示和奖励层面与普通敌方区分。

### 5.3 运行时属性框架

战斗真正消费的不是“初始化属性”，而是“运行时属性”。

运行时属性在进入战斗场景时一次性结算，来源按叠加顺序组成：

1. Base：角色 / 敌方 / Boss 基础属性
2. Growth：成长提供的固定加值
3. PassiveSkill：被动技能提供的常驻修正
4. Treasure：宝物提供的常驻修正
5. Event：事件提供的战前修正
6. PreBattleBuff：战前 Buff 修正
7. PreBattleDebuff：战前 Debuff 修正
8. Environment：环境修正

规则：

1. 成长属性只做加法叠加。
2. 百分比变化主要通过 buff/debuff、宝物、技能等来源进入最终运行时属性。
3. v4 中 buff/debuff 只在战斗开始前参与一次性计算，战斗过程中不再动态变化。
4. 战斗场景 UI 展示的属性应为最终运行时属性。

---

## 6. 战斗核心规则

### 6.1 战斗流程

1. 地图或事件触发战斗后，进入 `SanguoBattleView`。
2. 双方基于最终运行时属性创建主战单位。
3. 若有召唤物，则在战斗初始化时或技能效果中加入战场。
4. 双方按各自 `AttackSpeed` 进行自动攻击读条。
5. 任一主单位 `CurrentHP <= 0` 时立即判定战斗结束。
6. 我方主单位死亡则失败；敌方 / Boss 主单位死亡则胜利。

### 6.2 攻击触发与优先级

1. 攻击不是回合制，而是基于读条完成触发。
2. 每次单位获得一次攻击机会时，按技能优先级从高到低检测。
3. `Priority` 数值越大，优先级越高。
4. 每个技能按自己的触发概率判定是否触发。
5. 首个成功触发的技能会直接消耗本次攻击机会。
6. 如果所有技能都未触发，则进入普通攻击。
7. 普通攻击视为最后一个 100% 触发的保底技能。

### 6.3 同时触发时的行动优先级

同一时刻若多个单位同时满足行动条件，按以下优先级决定出手顺序：

1. 我方主单位
2. 敌方 / Boss 主单位
3. 召唤物

若优先级完全相同且攻击条件完全一致，则随机决定。

### 6.4 普通攻击与直接伤害

1. 普通攻击基础伤害公式固定为 `Attack`。
2. 技能伤害不硬编码固定值，需以 `Attack` 作为入参。
3. 直接伤害受闪避、免伤、反伤、吸血等规则影响。
4. 最终直接伤害最小为 `1`。

### 6.5 胜负与战后处理

1. 我方主单位死亡：
   - 战斗失败
   - 点击统一战报确认按钮后返回地图主循环
   - 我方 HP 恢复到 `50% MaxHP`
2. 敌方 / Boss 主单位死亡：
   - 战斗胜利
   - 展示战报与奖励
   - 点击确认后返回地图主循环
   - 我方保留战斗结束瞬间 HP，不恢复

---

## 7. 召唤物规则

1. 召唤物是独立战斗单位。
2. 默认继承本体 50% 的可继承属性，且按 `50% MaxHP` 满血生成。
3. 默认 `AttackSpeed = 2.0s`，不直接继承本体攻击速度。
4. 召唤物攻击速度可被技能或宝物修正，但 v4 不在战斗中动态变化。
5. 召唤物只有普通攻击，没有技能链判定。
6. 召唤物不继承本体常驻群攻、反伤、暴击属性。
7. 敌我双方默认单体攻击优先攻击对方召唤物。
8. 若目标侧有多个召唤物，则随机选择一个。
9. 召唤物可被群攻命中，也可承受 DoT。
10. 主单位死亡立即结束战斗，不等待召唤物全部清空。

---

## 8. 群攻、反伤、DoT 规则

### 8.1 群攻

1. 群攻没有数量系数，也没有 `AoEValue`。
2. 群攻定义为“攻击对方所有存活单位”。
3. 常驻群攻可由被动技能或宝物赋予。
4. 技能触发时，也可由技能配置决定该技能为单体或群攻。
5. 群攻可命中主单位与全部召唤物。
6. 群攻吸血按总最终直接伤害汇总后结算。

### 8.2 反伤

1. 反伤是特殊伤害类型，不属于直接伤害。
2. `ReflectRate = 0` 时不触发反伤。
3. 反伤不受闪避、免伤、吸血影响。
4. 反伤不连锁触发新的反伤。
5. 若目标已被该次攻击击杀，则不再对攻击者回弹反伤。
6. 反伤允许击杀攻击者。
7. 群攻命中多个存活目标时，反伤按目标逐个结算。

### 8.3 DoT

1. DoT 是独立伤害类型。
2. DoT 每 `1s` 结算一次。
3. DoT 伤害与 `Attack` 无关，使用独立配置值。
4. DoT 无法闪避、无法暴击、无法吸血、无法反伤。
5. DoT 受到免伤率影响。
6. DoT 最小伤害为 `1`。
7. 同源 DoT 使用 `SourceUnitId + DotEffectId` 作为简单覆盖键。
8. 同源 DoT 刷新时，重置持续时间并覆盖伤害值。
9. 不同来源 DoT 可并存。
10. 若 DoT 结算与攻击同时到点，则先结算 DoT。
11. 若单位被 DoT 击杀，则其本次待执行攻击取消。

---

## 9. 数值边界与取整规则

1. `AttackSpeed` 下限为 `0.5s`
2. `DamageReductionRate` 上限为 `0.90`
3. `DodgeRate` 上限为 `0.90`
4. 直接伤害最小值为 `1`
5. DoT 伤害最小值为 `1`
6. 反伤最小值按实现统一向下取整后再判定是否为 0
7. 百分比派生数值统一优先采用向下取整，保证实现简单可预测

---

## 10. 战斗场景 UI 要求

v4 不新建新战斗场景，直接扩展现有 `Game.Godot/Scenes/Sanguo/SanguoBattleView.tscn`。

战斗场景至少需要以下元素：

1. 我方建模占位
2. 敌方 / Boss 建模占位
3. 我方名称
4. 敌方 / Boss 名称
5. 我方宝物展示区
6. 我方被动技能展示区
7. 敌方 / Boss 被动技能展示区
8. 双方属性面板
9. 双方技能列表面板
10. Buff / Debuff UI 占位区
11. 战斗日志区域，仅滚动显示最近 15 条
12. 暂停 / 继续按钮
13. 2 倍速按钮
14. 胜利 / 失败统一结果弹窗
15. 奖励列表展示区，支持多奖励项滚动显示

行为要求：

1. 暂停时冻结攻击读条、DoT 计时、技能判定、动画和日志滚动。
2. 继续时从暂停状态继续，不重置时间轴。
3. 2 倍速只改变时间流速，不改变随机顺序和概率结果。

---

## 11. 数据与契约扩展方案

### 11.1 角色 schema 扩展

扩展现有 `SanguoCharacterDefinition`，保留原字段并新增战斗属性字段。

要求：

1. `CombatRating` 不删除。
2. 旧角色数据可通过默认值或迁移补齐新字段。
3. `SanguoCharactersCatalogLoader` 需要同步增加新字段校验。
4. 主菜单角色信息区可逐步从只展示 `CombatRating` 升级为展示核心战斗属性摘要。

### 11.2 敌方 / Boss schema

新增正式敌方数据文件，而不是继续把 `random_events.json` 当正式敌人库。

建议新增独立数据文件：

- `Data/enemies.json`
- `Data/bosses.json`

职责：

1. `random_events.json` 继续只负责“触发哪场战斗”。
2. 敌方 / Boss 正式属性、技能列表、奖励掉落改由专用数据表承载。
3. `encounterId` 继续作为事件到战斗配置的桥接键。

### 11.3 技能 schema

v4 仅做最小技能配置结构，为后续技能引擎留接口，不要求这一版完成完整技能引擎。

建议新增：

- `Data/skills.json`

单技能至少需要：

- `SkillId`
- `NameKey`
- `DescriptionKey`
- `Priority`
- `TriggerChance`
- `TargetType`
- `DamageCoefficient`
- `CanApplyDot`
- `DotEffectId`
- `SummonConfigId`

### 11.4 宝物 schema 扩展

扩展现有 `Data/relics.json`，在当前 `moneyDelta` / `economyStepDelta` 基础上新增可选战斗修正字段。

要求：

1. 兼容旧宝物配置。
2. 新增字段只做增量，不重构旧 effectKind 体系。
3. 战斗属性修正、被动群攻、被动 DoT、召唤修正等应优先走可选扩展字段。

### 11.5 战斗契约扩展

扩展现有 `SanguoCombatResult`、`SanguoCombatStarted`、`SanguoCombatEnded`，不改事件名。

至少需要支持：

1. 参战双方基础展示数据
2. 参战双方最终运行时属性快照
3. 技能列表 / 被动技能列表 / 宝物列表
4. 战斗日志
5. 战斗奖励
6. 战斗结束时双方剩余状态
7. `DeathCauseType`

原则：

1. 事件名保持：
   - `core.sanguo.combat.started`
   - `core.sanguo.combat.ended`
2. 契约只加字段，不另起新事件族。

### 11.6 字段级最小 schema 草案

以下字段定义是 v4 的最小落地骨架，目的是让实现时能直接对齐字段来源与消费位置。

#### 11.6.1 `characters.json`

在现有角色字段基础上新增战斗字段：

- `maxHp`
- `attack`
- `critRate`
- `critMultiplier`
- `lifeStealRate`
- `dodgeRate`
- `attackSpeed`
- `damageReductionRate`
- `reflectRate`
- `aoeEnabled`

兼容要求：

1. 旧 `combatRating` 保留。
2. 旧角色条目可先补默认值。
3. `SanguoCharactersCatalogLoader` 需要校验数值范围与默认兜底。

#### 11.6.2 `enemies.json`

建议最小结构：

- `enemyId`
- `nameKey`
- `descriptionKey`
- `maxHp`
- `attack`
- `lifeStealRate`
- `dodgeRate`
- `attackSpeed`
- `damageReductionRate`
- `reflectRate`
- `aoeEnabled`
- `passiveSkillIds`
- `skillIds`
- `rewardId`

#### 11.6.3 `bosses.json`

建议最小结构与普通敌方一致，但增加 Boss 专属字段：

- `bossId`
- `phaseId`
- `rewardId`
- `pressureConfigId`
- `passiveSkillIds`
- `skillIds`

Boss 仍然复用同一套战斗规则，只在配置层区分权重、奖励、压力或阶段演出。

#### 11.6.4 `skills.json`

建议最小结构：

- `skillId`
- `nameKey`
- `descriptionKey`
- `priority`
- `triggerChance`
- `targetType`
- `damageCoefficient`
- `canCrit`
- `canApplyDot`
- `dotEffectId`
- `summonConfigId`
- `aoeEnabled`
- `cooldownTurns`

说明：

1. `priority` 数值越大越先检测。
2. `triggerChance` 为 0..1 或 0..100 需在实现期统一一种口径。
3. `targetType` 至少支持 `single` / `allEnemies` / `self` / `randomEnemySummon`。
4. `canCrit` 只对角色技能有意义，敌方/Boss 默认可不开放。

#### 11.6.5 `relics.json`

在原有经济类字段外新增可选战斗字段：

- `maxHpDelta`
- `attackDelta`
- `critRateDelta`
- `critMultiplierDelta`
- `lifeStealRateDelta`
- `dodgeRateDelta`
- `attackSpeedDelta`
- `damageReductionRateDelta`
- `reflectRateDelta`
- `aoeEnabledDelta`
- `passiveSkillIds`
- `skillIds`
- `dotEffectIds`
- `summonConfigIds`

说明：

1. 仍保留现有 `effectKind` 分流。
2. 战斗字段全部是可选扩展，不影响经济宝物。
3. 百分比字段建议统一使用小数值表达，避免双重百分比换算。

#### 11.6.6 战斗结束结果

建议 `SanguoCombatResult` 至少补充：

- `battleId`
- `battleType`
- `winnerSide`
- `deathCauseType`
- `playerFinalHp`
- `enemyFinalHp`
- `rewardItems`
- `combatLog`
- `runtimePlayerStats`
- `runtimeEnemyStats`

这样 `SanguoBattleView` 可以直接显示战报、奖励和运行时属性摘要，而不必再反查其他模块。

---

## 12. 与现有系统的迁移关系

### 12.1 对 `CombatRating` 的态度

`CombatRating` 在 v4 中变为兼容字段，不再是正式 PVE 战斗唯一胜负依据。

推荐处理：

1. 旧逻辑回退路径仍可读取 `CombatRating`
2. 新战斗逻辑主路径读取完整运行时属性
3. 如需保留旧 UI 展示，可把 `CombatRating` 视为角色“综合战力摘要值”

### 12.2 对 `SanguoCombatResolver` 的演进

`SanguoCombatResolver` 不应被废弃，而应从“单次比较器”演进为“战斗模拟入口”。

要求：

1. 保留入口命名与调用主链位置
2. 内部从一次性阈值判定升级为战斗模拟
3. 旧单元测试需要按新契约重写或拆层

### 12.3 对 `SanguoBattleView` 的演进

`SanguoBattleView` 不再只是 started/ended 结果显示层，而是正式战斗场景入口。

要求：

1. 仍监听现有战斗 started/ended 事件
2. started 后进入战斗初始化和演出
3. ended 后显示统一结果弹窗
4. 不新建平行战斗场景替代它

---

## 13. 验收标准

### 13.1 业务验收

1. 地图/事件触发战斗后，可进入正式战斗场景。
2. 双方按攻击速度自动读条攻击，而不是一次性比战力。
3. 我方和敌方均可按技能优先级做技能触发判定。
4. 可正确处理普通攻击、群攻、召唤物、反伤、DoT。
5. 我方死亡后返回地图并恢复至 50% 上限 HP。
6. 敌方死亡后显示奖励并返回地图，保留我方剩余 HP。
7. 战斗日志最多显示最近 15 条。
8. 暂停与 2 倍速逻辑符合预期。

### 13.2 技术验收

1. 不新增平行角色 schema、战斗事件、战斗场景。
2. `Game.Core/Contracts/**` 继续保持 BCL-only。
3. 角色、敌方、技能、宝物数据文件具备明确 loader 与校验。
4. Core 领域战斗逻辑具备 xUnit 覆盖。
5. 战斗场景 UI 与事件胶水具备 GdUnit / 场景测试覆盖。

---

## 14. 建议实施顺序

### M1：契约与数据面

1. 扩展 `SanguoCharacterDefinition`
2. 扩展 `characters.json`
3. 新增 `enemies.json`、`bosses.json`、`skills.json`
4. 扩展 `relics.json`
5. 扩展战斗 contracts

### M2：Core 战斗模拟

1. 建立运行时属性聚合模型
2. 重写 `SanguoCombatResolver` 为真实战斗模拟入口
3. 落地普通攻击、技能优先级、群攻、召唤物、反伤、DoT
4. 输出战斗日志与奖励结果

### M3：战斗场景 UI

1. 扩展 `SanguoBattleView.tscn`
2. 扩展 `SanguoBattleView.cs`
3. 接入 started/ended 契约 payload
4. 接入暂停、继续、2 倍速、结果弹窗

### M4：主循环接入

1. 将 `random_events.json` 的战斗触发接到正式敌方/Boss 配置
2. 战后状态回写主循环
3. 奖励接回现有经济/物品主链

---

## 15. 一句话结论

v4 的正确做法不是重建一套新战斗系统，而是以 `SanguoCharacterDefinition + SanguoCombatContracts + SanguoCombatResolver + SanguoBattleView` 为主轴，在现有仓库上做增量扩展，把当前“战力阈值战斗”升级为“可演出、可配置、可扩展的自动战斗场景”。
