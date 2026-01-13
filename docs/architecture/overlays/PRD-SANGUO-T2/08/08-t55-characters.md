---
PRD-ID: PRD-SANGUO-T2
Title: 08-T55 角色（6 角色）与初始资金口径
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0019
Arch-Refs:
  - CH05
  - CH06
---

# T55：角色（6 角色）与初始资金口径

本页为 T55 的功能纵切拆页。角色数据配置为只读；经济系数只在 Core 计算点应用，UI 只展示（ADR-0004）。

## 范围
- 角色配置：`res://Data/characters.json`（6 角色，全局唯一不可重复）。
- 初始资金：`money0 = StartingMoneyPreset * starting_money_multiplier`。

## 非目标
- 不实现体力/技能池/装备/成长系统。

## 验收条款（ACC）
- ACC:T55.1 角色配置可加载且 6 角色可展示（name/description/portrait_path/经济系数）。
- ACC:T55.2 初始资金 = StartingMoneyPreset * starting_money_multiplier。

## Test-Refs
- `Game.Core.Tests/Tasks/Task55CharacterConfigTests.cs`
- `Tests.Godot/tests/UI/test_task55_character_select_ui.gd`

