---
adr: ADR-0006
title: Addendum — Data Storage for Godot (SQLite + ConfigFile)
date: 2025-11-08
status: Active
scope: Windows-only runtime, Godot 4.5 (.NET)
---

# ADR-0006 补充：Godot 数据存储对齐（SQLite + ConfigFile）

## Context

Godot+C# 变体需要同时满足：

- 复杂结构化数据（存档/进度/状态）可用 SQLite 持久化；
- 轻量设置（Settings）使用 `ConfigFile` 持久化；
- 所有写入必须落在 `user://`，符合安全基线（见 ADR-0019）。

## Decisions

- 数据库：优先使用 `godot-sqlite`（GDExtension）承载结构化数据；重操作应避免阻塞主线程。
- 路径：仅允许写入 `user://`；禁止绝对路径与目录穿越。
- Settings：Settings 的 SSoT 为 `ConfigFile`（见 ADR-0023）。

## Verification

- 场景测试（GdUnit4）：在 `user://` 下创建临时 DB/配置文件并做读写断言；产出日志/摘要到 `logs/e2e/**`。
- CI 工件：最小 DB/设置一致性日志写入 `logs/ci/**` 便于排障。

