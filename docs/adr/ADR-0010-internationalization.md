---
ADR-ID: ADR-0010
title: 国际化策略（Godot）- TranslationServer + ConfigFile 持久化
status: Accepted
decision-time: '2025-12-16'
deciders: [架构团队, UX团队]
archRefs: [CH10]
verification:
  - path: Game.Godot/Scripts/UI/SettingsPanel.cs
    assert: Language selection persists to user://settings.cfg and applies via TranslationServer.SetLocale
  - path: Tests.Godot/tests/UI/test_settings_locale_persist.gd
    assert: Locale persists across restart via ConfigFile
impact-scope: [Game.Godot/Translations/, Game.Godot/Scripts/UI/, Tests.Godot/tests/UI/]
tech-tags: [i18n, localization, godot, translationserver]
depends-on: [ADR-0023, ADR-0019]
depended-by: []
supersedes: []
---

# ADR-0010: 国际化策略（Godot）

## Context

模板需要支持多语言，并保证语言选择可持久化、可在运行时切换、可在 headless 下验收。Godot 运行时不使用 Web 前端 i18n 生态（如 i18next），因此需要以 Godot 原生国际化能力为基线口径。

## Decision

### 1) 翻译资源（Translation Resources）

- 翻译资源放置目录：`Game.Godot/Translations/`
- 使用 Godot 支持的格式（如 `.translation`/`.po`/`.csv`），并在项目设置中注册（导出时随包携带）。
- 默认语言与回退语言：`en`（可按项目需要调整）。

### 2) 语言选择与持久化（SSoT）

- Settings 的 SSoT 为 ConfigFile：`user://settings.cfg`（见 ADR-0023）。
- 语言切换：调用 `TranslationServer.SetLocale(<lang>)`，并立刻生效。

### 3) 验收与门禁

- 场景测试（GdUnit4）：至少覆盖
  - 语言设置写入 ConfigFile
  - 重启后语言仍然生效（跨重启）
- 所有测试工件统一落盘 `logs/**`（目录口径见 `docs/testing-framework.md`）。

## Consequences

- 正向：无额外依赖，直接使用 Godot 国际化能力；语言选择可回溯、可测试。
- 代价：翻译资源需要项目侧维护流程（新增 key、翻译同步与质量检查）。

