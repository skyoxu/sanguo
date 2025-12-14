# ADR-0023: Settings SSoT = ConfigFile (user://)

- Status: Accepted
- Context: 现状中 SettingsPanel 曾将设置写入 SQLite（DB）中的 `settings` 表，而 Base 文档与 ADR-0006 Godot 附录都推荐“轻量设置使用 ConfigFile（user://）”。这导致“设置的单一事实来源（SSoT）”口径不一致：一部分实现/文档以 DB 为准，一部分以 ConfigFile 为准，测试也分别覆盖了两种路径，缺少统一结论与迁移策略。
- Decision: 在 Godot+C# 变体中，规范层明确“Settings 的 SSoT 为 ConfigFile（user://settings.cfg）”；DB 仅用于领域数据（存档、进度、复杂状态），不再作为 Settings 的权威来源。SettingsPanel 在运行时读写 ConfigFile；如检测到旧版 DB 中存在 settings 记录，则在首次运行时一次性迁移到 ConfigFile 并以后以 ConfigFile 为准。
- Consequences:
  - Settings 读取/写入的唯一权威来源为 ConfigFile（user://settings.cfg）。DB 中的 `settings` 表仅作为历史兼容，不再在文档中被当作 SSoT 引用。
  - Base 文档 CH05/CH06 以及迁移文档中，所有“Settings → DB” 的描述需要标注为 Deprecated，并补充新路径：“SettingsPanel → ConfigFile（参见本 ADR）”。
  - 在测试与 CI 中，保留 DB 相关的 Schema/兼容测试，但新增并以 ConfigFile 场景为主：包括 SettingsPanel 保存/加载、语言持久化、跨“重启”的 ConfigFile 一致性。DB 相关 Settings 测试退居历史兼容场景（如存在）。
  - 安全与路径口径保持与 ADR-0002、ADR-0006 Godot 附录一致：所有 Settings 持久化仅写入 user://，路径需规范化，不允许绝对路径与目录穿越。
  - 迁移策略：在 SettingsPanel 实现中，如果检测到 ConfigFile 不存在但 DB 中存在该用户的 settings 记录，则一次性读取 DB 值写入 ConfigFile；迁移完成后仍保留 DB 表结构（便于历史数据排查），但新代码不得再以其为权威来源。
- Supersedes: 本 ADR 不整体 Supersede ADR-0006，而是对其中“Settings 使用 DB 持久化”的早期口径做精细化收束——在 Settings 场景上，以本 ADR 与《ADR-0006 Godot Data Storage Addendum》中“Preferences: use ConfigFile for player settings”为准；如存在冲突，以本 ADR 为最终口径。
- References: ADR-0002（安全基线）、ADR-0005（质量门禁）、ADR-0006（数据存储）及其 Godot 附录、ADR-0010（国际化）、ADR-0025（测试策略）、Base CH05/CH06（数据模型与运行时视图）。

## Test-Refs

- Tests.Godot/tests/UI/test_settings_panel_logic.gd
- Tests.Godot/tests/UI/test_settings_locale_persist.gd
- Tests.Godot/tests/Adapters/Db/test_savegame_persistence_cross_restart.gd
- Tests.Godot/tests/Adapters/Db/test_inventory_persistence_cross_restart.gd

