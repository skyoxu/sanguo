---
title: 10 i18n ops release v2
status: base-SSoT
adr_refs: [ADR-0010, ADR-0011, ADR-0018, ADR-0003, ADR-0019]
placeholders: Unknown Product, ${ORG}, ${REPO}, ${PRODUCT_DOWNLOAD_URL}
derived_from: 10-i18n-ops-release-v2.md
last_generated: 2025-12-16
---

# 10 i18n 与发布运维（Windows-only，Godot）

本章收敛两类跨切面能力：i18n（文本资源管理）与发布运维（Windows 导出、版本策略、Release Health 取证）。具体阈值与安全口径分别引用 ADR-0010/ADR-0003/ADR-0019。

## 1) i18n（最小流程）

- 资源形态：使用 Godot 的翻译资源（如 `.translation`/`.po`），由 `TranslationServer` 加载与切换。
- 约束：
  - 文本 key 稳定、可回溯；避免将 UI 文本硬编码在脚本中。
  - 新增 key 必须补齐默认语言，并在 CI 侧提供缺失 key 的软检查（作为后续增强项）。

## 2) 发布（Windows Desktop）

- 导出依赖：安装 Godot Export Templates（Windows Desktop）。
- 导出产物：
  - `build/Game.exe`（以及可选的 `build/Game.pck`）
- 推荐入口：
  - 手动导出：`docs/release/WINDOWS_MANUAL_RELEASE.md`
  - 脚本导出：`scripts/ci/export_windows.ps1`

## 3) CI/Release 工作流（仓库内）

- 手动触发 Release：`.github/workflows/windows-release.yml`
- Tag 触发 Release：`.github/workflows/windows-release-tag.yml`（`v*`）
- 导出（轻量）：`.github/workflows/windows-export-slim.yml`

## 4) Release Health（Sentry，软门禁）

- Release job 末尾执行：`py -3 scripts/python/check_sentry_secrets.py`
- 输出 Step Summary 行：`Sentry: secrets_detected=<true|false> upload_executed=<true|false>`
- 说明：当前为软门禁，不阻断构建；用于确认 Secrets 是否存在以及上传逻辑是否真正执行过（由未来上传步骤写入 `SENTRY_UPLOAD_PERFORMED=1`）。

