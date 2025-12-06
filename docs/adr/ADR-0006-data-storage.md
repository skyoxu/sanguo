---
ADR-ID: ADR-0006
title: Godot 数据存储与持久化（SQLite + ConfigFile）
status: Accepted
decision-time: '2025-08-17'
deciders: [架构小组, 游戏研发组]
archRefs: [CH05, CH06, CH11]
verification:
  - path: Game.Godot/Adapters/SqliteDataStore.cs
    assert: 仅允许 user:// 写入；拒绝绝对路径与路径穿越；LastError 语义清晰
  - path: Tests.Godot/tests/Adapters/Db
    assert: 跨重启持久化、事务回滚、路径安全均有 GdUnit4 用例覆盖
  - path: docs/adr/ADR-0023-settings-ssot-configfile.md
    assert: Settings SSoT 明确为 ConfigFile（user://settings.cfg）
impact-scope:
  - Game.Core/Ports/
  - Game.Godot/Adapters/Db/
  - Game.Godot/Adapters/Security/
  - Tests.Godot/tests/Adapters/Db/
tech-tags: [godot, sqlite, configfile, persistence, storage]
depends-on: [ADR-0002, ADR-0005]
depended-by: [ADR-0023]
test-coverage: Tests.Godot/tests/Adapters/Db/*.gd
monitoring-metrics: [implementation_coverage, db_path_security, persistence_stability]
executable-deliverables:
  - Game.Godot/Adapters/SqliteDataStore.cs
  - Game.Godot/Adapters/Db/DbTestHelper.cs
  - Tests.Godot/tests/Adapters/Db/
supersedes: []
---

# ADR-0006: Godot 数据存储与持久化（SQLite + ConfigFile）

## Context

本模板的运行时代码最初从 vitegame（Electron + React + SQLite + Node 脚本）迁移到通用模板仓库 godotgame（Godot 4.5 + C#），当前仓库 sanguo 则是在 godotgame 模板基础上派生的“三国”主题 Windows-only Godot + C# 变体。本 ADR 中提到的“本模板”均指 sanguo 仓库。原有 ADR‑0006 主要描述了 Node 侧 SQLite+WAL 策略，与当前 Godot 变体的实现存在以下差异：

- **平台差异**：现为 Windows-only，运行在 Godot 4.5 .NET runtime 上，不再依赖 Node/Electron 环境。
- **后端差异**：DB 访问通过 C# 适配器（`SqliteDataStore` + 具体仓储），测试中统一使用 `Microsoft.Data.Sqlite` 作为 managed provider；godot-sqlite 作为可选 GDExtension，而不是唯一实现。
- **路径与安全**：Godot 的安全基线（见 ADR‑0002、Godot 安全章节）要求：
  - 仅允许对 `user://` 写入；
  - 只从 `res://` 读取资源；
  - 严格禁止绝对路径与目录穿越；
  - 所有失败路径必须写入结构化审计日志（logs/ci/**/security-audit.jsonl）。
- **Settings 口径变化**：
  - 旧模板将用户设置（音量、画质、语言等）存入 DB 的 `settings` 表；
  - Godot 变体经 ADR‑0023 收束后，Settings 的 SSoT 为 ConfigFile（user://settings.cfg），DB 不再作为设置的权威来源。

本 ADR 在保留“SQLite 作为结构化数据存储”的前提下，重写 Godot 变体下的数据存储策略，明确 DB 与 ConfigFile 的职责边界，并支撑当前的测试与 CI 门禁设计。

## Decision

1. **数据源分工：ConfigFile 为 Settings SSoT，SQLite 承担领域数据**

- ConfigFile（user://settings.cfg）：
  - 作为 **Settings 的唯一单一事实来源（SSoT）**，用于存储玩家偏好：音量、画质、语言等；
  - 通过 `ConfigFile.Load/Save` 实现读写，路径固定为 `user://settings.cfg`；
  - SettingsPanel 在运行时直接读写 ConfigFile，并在保存时即时应用（音量、语言等）。
- SQLite：
  - 承担**领域数据**与**复杂状态**：用户档、存档槽、库存、统计等；
  - 通过 `SqliteDataStore` 适配器封装 C# 访问；
  - 统一使用 managed provider（`Microsoft.Data.Sqlite`）作为默认实现，godot-sqlite 仅作为可选插件。

2. **路径与安全约束（Godot 变体）**

- DB 仅允许写入 `user://` 空间：
  - `SqliteDataStore.TryOpen(path)` 会规范化路径并检查：
    - 拒绝绝对路径（如 `C:\` 开头）；
    - 拒绝 `..` 等目录穿越片段；
    - 仅允许以 `user://` 开头的逻辑路径，实际由 Godot 映射到本地目录；
  - 任意违规尝试均返回 false 并写入审计日志。
- 资源访问只允许 `res://`：
  - Schema 脚本、迁移脚本、测试用资源路径仅以 `res://` 引用，禁止 `file://`、绝对路径或混用；
  - 与 ADR‑0002 安全基线保持一致。
- 审计与日志：
  - `SqliteDataStore` 在 Open/Execute/Query 失败时写入 `logs/ci/YYYY-MM-DD/security-audit.jsonl`；
  - 日志字段至少包含 `{ ts, action, reason, target, caller }`，便于 CI 与本地排查。

3. **事务与跨重启持久化策略**

- 核心仓储（如 SaveGame/Inventory/User）通过显式事务保护批量写入：
  - `DbTestHelper` 提供 `Begin/Commit/Rollback` 帮助方法；
  - 测试用桥接类（`RepositoryTestBridge`, `InventoryRepoBridge` 等）用于在 GdUnit4 用例中验证“抛错 → 事务回滚，数据不被污染”。
- 跨重启场景：
  - SaveGame：写入后关闭 DB，再用新连接打开，验证存档仍可读；
  - Inventory：批量替换和增删操作后，关闭再打开，验证集合内容一致；
  - 相关用例在 Tests.Godot 中作为 DB 持久化的软门禁。

4. **Settings 迁移策略（DB → ConfigFile，一次性）**

- 为了与旧 schema 兼容，`settings` 表仍保留，但仅用于“迁移源”：
  - SettingsPanel 在加载时先尝试从 ConfigFile 读取；
  - 如 ConfigFile 不存在或缺少 Settings 字段，则尝试从 DB `settings` 表读取一次，并写回 ConfigFile；
  - 迁移成功后，后续运行均以 ConfigFile 为准，不再回写 DB。
- 文档层面：
  - CH05/CH06 与迁移文档中，所有“Settings → DB”的旧描述标记为 Deprecated，并指向本 ADR；
  - 新增 Settings 相关用例与代码一律以 ConfigFile 方案为主线。

5. **WAL / 日志模式选择（管理化简版）**

- 在 Godot 变体中，不再强制追求 Node 脚本中的 WAL 细节，而是采用更简单、便于移植的策略：
  - 测试环境：
    - 使用 `DELETE` 日志模式，避免 WAL sidecar 文件，为 CI 中的复制/备份脚本简化操作；
    - 通过 GdUnit 用例验证 PRAGMA 设置与事务行为（提交/回滚）。
  - 运行环境：
    - 默认维持 SQLite 的 WAL 建议（具体 PRAGMA 可在 `SqliteDataStore` 内集中配置）；
    - 预留环境变量/配置项覆盖 PRAGMA（如需要深度调优时）。

## Consequences

- **对实现的影响**：
  - SettingsPanel 与 DB 仓储职责分离：Settings 始终走 ConfigFile，仓储仅负责领域数据；
  - `SqliteDataStore` 成为 DB 安全与路径约束的集中入口，便于测试与审计；
  - DB 相关代码不再依赖 Node 脚本，而是完全在 C# + GdUnit4 测试下演进。
- **对测试与 CI 的影响**：
  - Tests.Godot 中 DB 用例聚焦“跨重启/事务/路径安全”；
  - Settings 相关测试切换到 ConfigFile 场景，并通过 ADR‑0023 的 Test‑Refs 与文档对齐；
  - CI 的 DB 相关软门禁可读取 schema dump 与 security-audit.jsonl，确保实现遵守本 ADR 约束。
- **对文档的影响**：
  - Base 章节 CH05/CH06 需更新：Settings SSoT 表述改为 ConfigFile，并引用本 ADR；
  - 迁移文档中的 `CREATE TABLE settings` 片段应标注 Deprecated，并注明仅作为历史 schema 兼容保留。

## Verification

- GdUnit4 用例：
  - `Tests.Godot/tests/Adapters/Db/test_db_path_security.gd`
  - `Tests.Godot/tests/Adapters/Db/test_db_persistence_cross_restart.gd`
  - `Tests.Godot/tests/Adapters/Db/test_savegame_persistence_cross_restart.gd`
  - `Tests.Godot/tests/Adapters/Db/test_inventory_persistence_cross_restart.gd`
- UI/Settings 用例：
  - `Tests.Godot/tests/UI/test_settings_panel_logic.gd`
  - `Tests.Godot/tests/UI/test_settings_locale_persist.gd`
- CI 工具链：
  - `scripts/python/run_gdunit.py` + `ci-windows.yml` / `windows-quality-gate.yml` 中的 Adapters/Db 集合；
  - 审计与 schema dump：logs/ci/**/security-audit.jsonl、schema-dump.json。

## References

- CH 章节：CH05、CH06、CH11（数据模型、运行时视图、技术债）
- 相关 ADR：
  - ADR-0002（安全基线）
  - ADR-0005（质量门禁）
  - ADR-0006 Godot Data Storage Addendum（偏好设置使用 ConfigFile）
  - ADR-0023（Settings SSoT = ConfigFile）
  - Phase-14 Godot 安全基线（SqliteDataStore 与 SecurityAudit/SecurityHttpClient 的 DB/HTTP 审计约束）
- 外部文档：SQLite 官方文档（WAL / VACUUM / PRAGMA），Godot ConfigFile / FileAccess / DirAccess API 文档
