---
ADR-ID: ADR-0008
title: 部署与发布策略（Windows-only）- Godot 导出 + GitHub Releases
status: Accepted
decision-time: '2025-12-16'
deciders: [架构团队, DevOps团队]
archRefs: [CH07, CH10]
verification:
  - path: .github/workflows/windows-release.yml
    assert: Manual workflow exports build/Game.exe and uploads logs/ci/**
  - path: .github/workflows/windows-release-tag.yml
    assert: Tag workflow attaches build/Game.exe to GitHub Release
  - path: scripts/ci/export_windows.ps1
    assert: Exports Windows Desktop preset and writes export logs under logs/ci/**
tech-tags: [release, windows, godot, export, github-actions]
depends-on: [ADR-0011, ADR-0018, ADR-0003]
depended-by: []
supersedes: []
---

# ADR-0008: 部署与发布策略（Windows-only）

## Context

模板需要一个“复制即可发布”的最小发布链路：在 GitHub Actions 上下载 Godot .NET、安装 Export Templates、导出 Windows EXE，并将产物与日志工件归档。该链路不引入额外签名/商店分发复杂度，保持模板开箱即用。

## Decision

### 1) 发布触发方式

- 手动发布（验证模板/临时分发）：`.github/workflows/windows-release.yml`
- Tag 发布（正式版本）：`.github/workflows/windows-release-tag.yml`（触发条件：`v*`）

### 2) 产物与工件

- 导出产物：`build/Game.exe`（Windows Desktop）
- 日志/工件：`logs/ci/**`（包含导出日志、门禁摘要等）

### 3) Release Health（软门禁取证）

- Release job 末尾总是运行：`py -3 scripts/python/check_sentry_secrets.py`
- Step Summary 输出：`Sentry: secrets_detected=<true|false> upload_executed=<true|false>`
- 说明：该步骤不阻断构建，用于确认 Sentry Secrets 是否配置以及上传逻辑是否真正执行过（由未来上传步骤写入 `SENTRY_UPLOAD_PERFORMED=1`）。

## Consequences

- 正向：Windows-only 链路清晰；导出与工件可回溯；模板无需额外环境即可在 CI 导出与发版。
- 代价：不包含代码签名与自动更新等高级能力（可在项目落地后按需接入）。

