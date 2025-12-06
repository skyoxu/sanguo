# Phase 22 Backlog — 文档整合与发布说明增强

> 状态：Backlog（非当前模板 DoD，按需在实际项目中启用）
> 目的：承接 Phase-22-Documentation-and-Release-Notes.md 中与具体产品/游戏相关的文档与发布说明蓝图，避免在模板阶段虚构项目文档，同时为后续团队提供一套可复用的文档结构与自动化思路。
> 相关 Phase：Phase 1–21（迁移与架构）、Phase 13（质量门禁）、Phase 17–19（构建/发布/回滚）

---

## B1：Executive Summary 与 Migration Report（项目级）

- 现状：
  - 模板仓库提供了完整的 Phase 1–21 迁移蓝图与 ADR 体系，但没有针对某个具体产品/游戏的高管摘要或迁移完成报告；
  - Phase‑22 文档中的 Executive Summary/Migration Report 更适合作为项目级交付物，而非模板内容。
- 蓝图目标：
  - 在项目仓库中提供：
    - 简洁的 Executive Summary（迁移/构建成果、ROI、风险与缓解）；
    - 迁移完成报告，汇总 Phase 1–21 的关键决策与验收结果（功能/性能/安全等）。
- 建议实现方式：
  - 在项目私有仓库中创建 `docs/release/EXECUTIVE_SUMMARY.md` 与 `docs/release/MIGRATION_REPORT.md`，参考 Phase‑22 的分层设计填入实际内容；
  - 模板仓库仅保留 Phase 1–22 文档与 ADR 作为“架构与迁移蓝图”的示例，不承载具体业务结论。
- 优先级：项目级 P0（正式发布前的必备材料）。

---

## B2：Operations Manual / User Manual / FAQ（项目级）

- 现状：
  - 模板提供了开发者视角的 AGENTS/CLAUDE/Quickstart 文档，但没有面向最终用户或运维团队的完整用户手册与运维手册；
  - Phase‑22 分层架构中的 Operations Manual/User Manual/FAQ 尚未在模板中具体化。
- 蓝图目标：
  - 在实际游戏项目中，根据目标用户与运维需求编写：
    - Operations Manual：部署流程、环境要求、监控检查点、常见故障排除；
    - User Manual：功能说明、操作指南、注意事项；
    - FAQ：常见问题与解决方案（支持团队视角）。
- 建议实现方式：
  - 以模板仓库的 Quickstart/Export Checklist 为参考，在项目仓库中扩展对应的用户/运维文档；
  - 在 README 或 docs 索引中显式标记这些文档路径，方便导航；
  - 模板仓库只保留分层架构与示例，不强制提供通用用户手册。
- 优先级：项目级 P1。

---

## B3：Release Notes 自动化填充与文档完整性检查

- 现状：
  - 模板提供了 `scripts/ci/generate_release_notes.ps1` 与 `docs/release/RELEASE_NOTES_TEMPLATE.md`，但生成内容主要是骨架占位，尚未自动从 CI 汇总 JSON（ci-pipeline-summary/export summary/release profile）中提取实际结果；
  - CI 中尚未实现“文档完整性/链接检查”的自动门禁（如 Phase 文档是否齐全、索引是否覆盖关键文档）。
- 蓝图目标：
  - 为项目提供一个更自动化的文档更新流程：
    - 从 `logs/ci/<date>/ci-pipeline-summary.json`、`logs/ci/<date>/export/summary.json` 等文件中读取测试/门禁/导出结果；
    - 将这些结果填入 Release Notes 的相应段落（Quality Gate、Perf、Artifacts 等）；
    - 在 CI 中增加简单的文档完整性检查（例如：Phase 1–22 文档存在性、索引覆盖率、关键链接可解析）。
- 建议实现方式：
  - 在项目仓库中扩展 PowerShell/Python 脚本，对现有 `generate_release_notes.ps1` 进行增强或包装；
  - 新增文档检查脚本（如 `scripts/python/check_docs_integrity.py`），在 CI 中作为软/硬门禁；
  - 模板仓库只在 Backlog 中描述这些增强，不在当前阶段实现，以避免对通用模板造成过多耦合。
- 优先级：项目级 P1–P2。

---

## 使用说明

- 对于基于本模板创建的新项目：
  - Phase‑22 提供的是“文档分层架构 + 发布说明脚手架”，具体内容需要结合项目 PRD 与实际实现自行填充；
  - 可按 B1→B2→B3 的顺序逐步补齐高管报告、运维/用户文档与 Release Notes 自动化。

- 对于模板本身：
  - 当前 Phase 22 仅要求核心技术文档（Phase 文档、ADR、测试/质量规范）完整，并提供最小 Release Notes 模板与生成脚本；
  - 本 Backlog 文件用于记录模板视角下的“项目级文档与发布说明增强”蓝图，避免在模板阶段就强行引入具体业务内容或复杂文档门禁。

