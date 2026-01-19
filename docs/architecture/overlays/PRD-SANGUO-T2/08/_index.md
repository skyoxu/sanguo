---
PRD-ID: PRD-SANGUO-T2
Title: 08 章功能纵切索引（契约与测试对齐）
Status: Accepted
Updated: true
ADR-Refs:
  - ADR-0004
  - ADR-0005
Arch-Refs:
  - CH01
  - CH03
---

# PRD-SANGUO-T2 功能纵切索引

本目录聚合 T2 功能纵切页面与对应测试引用（仅引用 01/02/03 章口径，不在此复制阈值/策略）。

## Contracts（SSoT）

- `Game.Core/Contracts/Sanguo/GameStartConfig.cs`
- `Game.Core/Contracts/Sanguo/SanguoMapsCatalog.cs`
- `Game.Core/Contracts/Sanguo/SanguoMapDefinitionV2.cs`
- `Game.Core/Contracts/Sanguo/SanguoMapDefinitionV2Validator.cs`
- `Game.Core/Contracts/Sanguo/SanguoRandomEventsCatalog.cs`
- `Game.Core/Contracts/Sanguo/SanguoActionCardsCatalog.cs`
- `Game.Core/Contracts/Sanguo/SanguoCharactersCatalog.cs`
- `Game.Core/Contracts/Sanguo/SanguoBuildingsCatalog.cs`

- 资源加载与外链白名单（Whitelist）— 见 `08-Contracts-Preload-Whitelist.md`
- DomainEvent（CloudEvents-like）— 见 `08-Contracts-CloudEvent.md`
- CloudEvents Core（EventType/关联字段）— 见 `08-Contracts-CloudEvents-Core.md`
- 三国大富翁闭环事件（Sanguo GameLoop Events）— 见 `08-Contracts-Sanguo-GameLoop-Events.md`
- 安全口径引用（Security Contracts）— 见 `08-Contracts-Security.md`
- 质量指标与门禁引用（Quality Metrics）— 见 `08-Contracts-Quality-Metrics.md`
- T50–T65 契约映射（Events/DTO/Interfaces）— 见 `08-contracts-taskmap-t50-t65.md`

- 验收清单（Acceptance Checklist）— 见 `ACCEPTANCE_CHECKLIST.md`
- 玩法闭环（功能纵切）— 见 `08-feature-slice-t2-monopoly-loop.md`
- 开局配置与模块骨架（T50–T60 概览）— 见 `08-feature-slice-t2-setup-map-character-events-cards-buildings-combat-gameend.md`
- T50–T60 多页（按任务拆分）：
  - T50 GameStartConfig（唯一开局输入）— 见 `08-t50-game-start-config.md`
  - T51 倍率合成与 applied_multipliers — 见 `08-t51-economy-multipliers-and-applied-multipliers.md`
  - T52 回合窗口（BeforeRoll）与事件顺序 — 见 `08-t52-turn-window-and-event-ordering.md`
  - T53 地图配置（多文件）与 Tile 语义 — 见 `08-t53-map-config.md`
  - T54 新游戏配置界面（地图/人数/资金档/间隔/选角）— 见 `08-t54-new-game-menu.md`
  - T55 角色（≥8 角色）与初始资金口径 — 见 `08-t55-characters.md`
  - T56 随机事件池（事件格 + 每N回合全局事件）— 见 `08-t56-random-events.md`
  - T57 行动卡（BeforeRoll，止损版）— 见 `08-t57-action-cards.md`
  - T58 建筑扩展（买地后建造类型）— 见 `08-t58-buildings.md`
  - T59 战斗（PVE）触发与回主循环 — 见 `08-t59-combat-pve.md`
  - T60 每局胜利与结算界面 — 见 `08-t60-game-end-and-settlement.md`
- T61–T65 多页（按任务拆分）：
  - T61 AI 最小确定性策略（止损层）— 见 `08-t61-ai-minimal-deterministic.md`
  - T62 宝物系统（Relics）— 见 `08-t62-relics.md`
  - T63 全局事件触发机制（RoundNumber）— 见 `08-t63-global-events.md`
  - T64 州郡数据模型（Regions）— 见 `08-t64-regions.md`
  - T65 州郡机制（全占增益 + 连协收费）— 见 `08-t65-regions-mechanics.md`
- 城池所有权模型（功能纵切）— 见 `08-t2-city-ownership-model.md`

> 关联 PRD：`.taskmaster/docs/prd.txt` 中 T2 阶段「最小可玩闭环」描述  
> 关联 ADR：ADR-0018、ADR-0005、ADR-0006、ADR-0015、ADR-0019、ADR-0020、ADR-0021、ADR-0024、ADR-0025  
> 关联章节：CH01、CH02、CH04、CH05、CH06、CH07、CH09、CH10

  - T61–T65 多页（按任务拆分）：
  - T61 … 见 `08-t61-ai-minimal-deterministic.md`
  - T62 … 见 `08-t62-relics.md`
  - T63 … 见 `08-t63-global-events.md`
  - T64 … 见 `08-t64-regions.md`
  - T65 … 见 `08-t65-regions-mechanics.md`
