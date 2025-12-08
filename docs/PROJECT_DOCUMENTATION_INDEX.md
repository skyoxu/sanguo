# 项目完整文档索引

> 最后更新: 2025-11-06
> 项目: vitegame — Phaser 3 + React 19 + Electron 桌面游戏框架
> 核心理念: AI 优先 + arc42/C4 规范 + 不可回退基座（Base/Overlay 分离）

---

## 0. 项目整体说明

### 核心指导文档
- [CLAUDE.md](../CLAUDE.md) — 单一真相（SSoT），AI 助手工作规则
  - AI 优先开发流程；arc42/C4 架构规范
  - Base/Overlay 文档结构
  - 4 段式契约模板
  - 质量门禁要求

### AI 助手协作规范
- [AGENTS.md](../AGENTS.md) — 多助手协作指南
- [ai-assistants.policies.md](ai-assistants.policies.md) — AI 助手行为准则
- [thinking-modes-guide.md](thinking-modes-guide.md) — 思维模式使用指南

### 项目概览
- [README.md](../README.md) — 项目快速入门
- [README.md](README.md) — 文档导航中心
- [CONTRIBUTING.md](../CONTRIBUTING.md) — 贡献指南

### Release / Sentry / CI 流水线
- [WINDOWS_MANUAL_RELEASE.md](release/WINDOWS_MANUAL_RELEASE.md) — Windows 手动发布与导出指引
- [GM-NG-T2-playable-guide.md](workflows/GM-NG-T2-playable-guide.md) — sanguo 可玩度 / Release 工作流与 Sentry 软门禁说明
- [serena-mcp-command-reference.md](workflows/serena-mcp-command-reference.md) — Serena / Codex CLI 命令与常用任务入口
- [superclaude-command-reference.md](workflows/superclaude-command-reference.md) — SuperClaude 工作流与常见命令说明
- [task-master-superclaude-integration.md](workflows/task-master-superclaude-integration.md) — Taskmaster + SuperClaude 集成与任务回链规范

### Release / Sentry / CI 流水线
- [WINDOWS_MANUAL_RELEASE.md](release/WINDOWS_MANUAL_RELEASE.md) — Windows 手动发布与导出指引
- [PRD-NEWGUILD-VS-0001.md](prd/PRD-NEWGUILD-VS-0001.md) — 示例垂直切片 PRD（包含 Test-Refs 与 Release 约束）
- [GM-NG-T2-playable-guide.md](workflows/GM-NG-T2-playable-guide.md) — newguild 可玩度 T2 流水线说明
- [task-master-superclaude-integration.md](workflows/task-master-superclaude-integration.md) — Taskmaster + SuperClaude 集成与任务回链

---

## 1. ADR（架构决策记录）

说明: 以 `docs/adr/` 目录的实际文件为准（建议由 CI 自动统计并更新此节计数）。当前仓库计数: 15。

### 基础技术栈（ADR-0001 ~ 0010）
- [ADR-0001-tech-stack.md](adr/ADR-0001-tech-stack.md) — 技术栈选型（React 19 / Electron / Phaser 3 / TS / Vite）
- [ADR-0002-electron-security.md](adr/ADR-0002-electron-security.md) — Electron 安全基线（CSP、nodeIntegration=false、contextIsolation=true）
- [ADR-0003-observability-release-health.md](adr/ADR-0003-observability-release-health.md) — 可观测性与发布健康（Sentry 集成，崩溃率阈值 99.5%）
- [ADR-0004-event-bus-and-contracts.md](adr/ADR-0004-event-bus-and-contracts.md) — 事件总线与契约（CloudEvents 1.0，4 段式模板 + Godot 事件命名/适配变体）
- [ADR-0005-quality-gates.md](adr/ADR-0005-quality-gates.md) — 质量门禁（覆盖率、ESLint、性能、Bundle 大小）
- [ADR-0006-data-storage.md](adr/ADR-0006-data-storage.md) — 数据存储（Godot 变体：SQLite + ConfigFile，路径与事务口径）
- [ADR-0007-ports-adapters.md](adr/ADR-0007-ports-adapters.md) — 端口适配器模式
- [ADR-0008-deployment-release.md](adr/ADR-0008-deployment-release.md) — 部署与发布
- [ADR-0009-cross-platform.md](adr/ADR-0009-cross-platform.md) — 跨平台
- [ADR-0010-internationalization.md](adr/ADR-0010-internationalization.md) — 国际化
- [ADR-0023-settings-ssot-configfile.md](adr/ADR-0023-settings-ssot-configfile.md) — Settings 单一事实来源：ConfigFile（user://settings.cfg），与 Godot 数据存储口径收敛

### 平台与质量约束（ADR-0011 ~ 0017）
- [ADR-0011-windows-only-platform-and-ci.md](adr/ADR-0011-windows-only-platform-and-ci.md) — Windows 平台策略
- [ADR-0012-pr-template-conditional-rendering.md](adr/ADR-0012-pr-template-conditional-rendering.md) — PR 模板动态渲染
- [ADR-0015-performance-budgets-and-gates.md](adr/ADR-0015-performance-budgets-and-gates.md) — 性能预算与门禁（P95 阈值、Bundle 限制、首屏优化）
- [ADR-0016-api-contracts-openapi.md](adr/ADR-0016-api-contracts-openapi.md) — API 契约（OpenAPI）
- [ADR-0017-quality-intelligence-dashboard-and-governance.md](adr/ADR-0017-quality-intelligence-dashboard-and-governance.md) — 质量智能看板

### ADR 管理
- [adr/guide.md](adr/guide.md) — ADR 编写指南

---

## 2. Base-Clean 架构文档（arc42 12 章）

目录: `docs/architecture/base/` — 无 PRD 痕迹的清洁基座

核心章节:
1. [01-introduction-and-goals-v2.md](architecture/base/01-introduction-and-goals-v2.md) — 项目目标、质量目标、利益相关方（引: ADR-0001/0002/0003）
2. [02-security-baseline-electron-v2.md](architecture/base/02-security-baseline-electron-v2.md) — Electron 安全基线（引: ADR-0002）
3. [03-observability-sentry-logging-v2.md](architecture/base/03-observability-sentry-logging-v2.md) — Sentry、结构化日志、Release Health（引: ADR-0003）
4. [04-system-context-c4-event-flows-v2.md](architecture/base/04-system-context-c4-event-flows-v2.md) — C4 上下文、事件流、CloudEvents（引: ADR-0004）
5. [05-data-models-and-storage-ports-v2.md](architecture/base/05-data-models-and-storage-ports-v2.md) — 数据模型与存储端口（Godot+C#：ConfigFile + SQLite，见 ADR-0006/0007/0023）
6. [06-runtime-view-loops-state-machines-error-paths-v2.md](architecture/base/06-runtime-view-loops-state-machines-error-paths-v2.md) — 运行时视图（Godot 场景/Autoload/事件总线/错误路径，含 Settings ConfigFile 流程）
7. [07-dev-build-and-gates-v2.md](architecture/base/07-dev-build-and-gates-v2.md) — 构建、CI/CD、质量门禁（引: ADR-0005）
8. [08-crosscutting-and-feature-slices.base.md](architecture/base/08-crosscutting-and-feature-slices.base.md) — 仅模板（功能纵切在 overlays）
9. [09-performance-and-capacity-v2.md](architecture/base/09-performance-and-capacity-v2.md) — 性能基准、容量、回归阈值（引: ADR-0015）
10. [10-i18n-ops-release-v2.md](architecture/base/10-i18n-ops-release-v2.md) — 国际化、运维、发布（引: ADR-0008/0010）
11. [11-risks-and-technical-debt-v2.md](architecture/base/11-risks-and-technical-debt-v2.md) — 风险与技术债务
12. [12-glossary-v2.md](architecture/base/12-glossary-v2.md) — 术语表

辅助文档:
- [architecture-completeness-checklist.md](architecture/base/architecture-completeness-checklist.md)
- [csp-policy-analysis.md](architecture/base/csp-policy-analysis.md)
- [front-matter-standardization-example.md](architecture/base/front-matter-standardization-example.md)
- [00-README.md](architecture/base/00-README.md) — Base 文档导航

---

## 3. PRD → Tasks 产出（可执行链路）

- 任务清单（Taskmaster）: `.taskmaster/tasks/tasks.json`
- Overlays 功能纵切索引: `docs/architecture/overlays/PRD-*/08/_index.md`
- 约束: 08 章只写功能纵切；跨切面规则仍在 Base/ADR；公共类型统一放在 `src/shared/contracts/**`。
- 命名规范: Overlay 目录使用英文/ASCII 路径（示例: `PRD-Guild-Manager/08/`），文件名与链接保持一致，避免 `-enhanced`、`-claude` 这类后缀导致 404；推荐统一使用 `-v2.md` 版本后缀。

本地校验（Windows，使用 Node/Python）:
- 列出 overlays: `node scripts/build-overlay-map.mjs`
- 任务-文档反链校验: `node scripts/ci/check-adr-refs.mjs`

---

## 4. 工作流清单（.github/workflows）

- 主 CI/CD: `ci.yml` — 含 T2 Gate（Playable Smoke）、质量门禁、构建与工件归档
- PR 门禁: `pr-gatekeeper.yml`、`pr-performance-check.yml`、`pr-performance-lighthouse.yml`、`pr-performance-bundle.yml`、`pr-security-audit.yml`、`pr-template-conditional-render.yml`、`pr-template-validation.yml`、`pr-metrics.yml`、`pr-ai-code-review.yml`、`pr-doc-sync.yml`、`pr-fast-chain.yml`
- 发布与回滚: `release.yml`、`release-prepare.yml`、`release-ramp.yml`、`release-emergency-rollback.yml`、`release-monitor.yml`、`release-health-monitor.yml`
- 安全/观测: `security-unified.yml`、`observability-gate.yml`
- 其他管控: `build-and-test.yml`、`ai-code-review.yml`、`main-deep-chain.yml`、`nightly-quality-rollup.yml`、`nightly-scene-transition.yml`、`staged-release.yml`、`soft-gates.yml`、`validate-workflows.yml`、`branch-protection-encoding-guard.yml`、`config-management.yml`、`docs-governance.yml`、`fetch-run-logs.yml`、`tasks-governance.yml`、`taskmaster-pr-link.yml`

说明: 上述为关键工作流编目，具体触发条件与产物请参见各 yml 内注释。

---

## 5. 质量门禁清单（阈值/脚本/本地复现）

- 覆盖率门禁（ADR-0005）
  - 阈值: lines ≥ 90%、branches ≥ 85%
  - 本地: `npm run test:coverage:gate`
  - 脚本: `scripts/ci/coverage-gate.cjs`
- 性能预算（ADR-0015）
  - 指标: P95（FCP/场景切换）、Bundle 大小限制
  - 本地: `node scripts/ci/bundle-budget-gate.mjs`、`node scripts/ci/compare-playwright-perf.mjs`
- Electron 安全基线（ADR-0002）
  - 基线: CSP、`nodeIntegration=false`、`contextIsolation=true`、预加载白名单
  - 本地: `node scripts/comprehensive-security-validation.mjs`
- 契约/文档一致性（ADR-0004）
  - 本地: `node scripts/ci/check-adr-refs.mjs`、`node scripts/ci/check-contract-docs.mjs`
- TestID 覆盖率
  - 本地: `node scripts/ci/check-testid-coverage.mjs`

日志与工件: 统一写入 `logs/YYYY-MM-DD/<模块>/...`，CI 会以工作流名与用例名称分目录归档以便排障。

---

## 6. Implementation 与 Plans（现存与模板）

### 该功能的大致描述
本节用于将 PRD/Overlay 的业务目标落地为“可执行的实现计划”，并与 ADR 与 arc42 基座形成闭环。它强调“计划可验证、实现可回溯、失败可回滚”的工程化约束，确保每一阶段（Stage）都有清晰目标、测试与门禁。

- 定位：连接 PRD → ADR/arc42 → Implementation Plan → 代码/测试 的执行链路。
- 产出：`docs/implementation-plans/**`（阶段性计划）与 `docs/implementation/**`（实施记录/迁移笔记）。
- 关联：每个阶段应在 Front‑Matter 反链 ADR（至少 ADR‑0004/0005，可按需补充 ADR‑0008/0015），并引用 Base 第 01/02/03 章口径而不复制阈值。
- 质量：以 `npm run guard:ci` 为最小门禁；覆盖率、复杂度、重复率与依赖健康均需过线（详见 ADR‑0005）。
- 日志：本地与 CI 的执行与构建日志统一落盘 `logs/YYYY‑MM‑DD/implementation/<stage>/`，便于回溯与审计。
- 平台：Windows 优先（ADR‑0011）；示例脚本与命令须提供 Windows 兼容用法，避免依赖特定 Shell。

快速使用（Windows，示例）
```python
# 复制模板生成一个新的实施计划文件（需 Python ≥3.9）
import os, shutil
src = 'docs/implementation-plans/_TEMPLATE.md'
dst = 'docs/implementation-plans/Phase-10-Sample-Implementation-Plan.md'
os.makedirs(os.path.dirname(dst), exist_ok=True)
shutil.copyfile(src, dst)
print(f'Created: {dst}')
```

注意事项
- 08 章功能纵切仅写在 overlays 下；本节只索引/描述计划与实施，不落入具体业务阈值。
- 若计划引入或调整跨切面口径（安全/可观测性/门禁/发布阈值），需新增或 Supersede 对应 ADR，并在计划文档中明确标注。
- 计划状态必须保持最新（Not Started/In Progress/Complete），并在 PR 描述中对齐验收标准与 Test‑Refs。

### 本章定义与功能（基于现存文档）
本章汇集“质量与变更工作流”的实施计划与实施记录，不承载具体业务功能设计。其职责是以 ADR 为口径（主要引用 ADR‑0002/0003/0005/0015/0011），将 PR 生命周期与发布后健康度的门禁与自动化落地为可运行的 CI/CD 与开发者工作流。

- 范围：PR 模板与度量、任务反链、AI 审查、性能回归、依赖安全、发布健康、静态质量门禁、T2/T3 门禁实现与文档同步等。
- 输出目录：`docs/implementation-plans/**`（阶段/系统性计划与总纲）与 `docs/implementation/**`（就地实施记录）。
- 门禁策略：影子/软门禁（PR 期给出预警）与硬门禁（main 上严格阻断）并行推进，所有报告与工件统一落盘 `logs/YYYY-MM-DD/ci/**`。
- 平台约束：Windows‑only 运行环境（ADR‑0011），工作流与脚本均需验证 Windows 兼容。

所含模块/工作流（代表性文件）
- PR 质量系统总纲：`docs/implementation-plans/PR-Quality-System-Overview.md`（Phase 1–6 全景；阻塞策略与集成点）
- 必选检查与顺序：`docs/implementation-plans/required-checks.md`（lint/typecheck/unit/e2e/coverage/bundle/release health）
- 静态质量门禁：`docs/implementation-plans/static-quality-gates.md`（重复度 ≤2%、圈复杂度 CC≤10/均值≤5；影子 vs 硬门）
- 发布健康与回滚：`docs/implementation-plans/Phase-6-Release-Health-and-Auto-Rollback.md`（Sentry Release Health + GitHub Deployments + 自动回滚）
- 性能回归检测：`docs/implementation-plans/Phase-8-Performance-Regression-Implementation-Plan.md`（Lighthouse/Bundle/Playwright；阈值引自 ADR‑0015）
- 依赖安全审计：`docs/implementation-plans/Phase-9-Dependency-Security-Implementation-Plan.md`（npm audit + license-checker；GPL/AGPL 禁止；阻塞合并）
- AI 审查工作流：`docs/implementation-plans/Phase-7.2-AI-Developer-Review-Workflow.md`（规范实现；交互式深度审查）；`Phase-7-*.md` 为历史/已废弃说明
- 任务反链与 Schema：`docs/implementation-plans/taskmaster-pr-backlinking.md`、`taskmaster-pr-schema.md`（PR ↔ Task 反链契约）
- T2/T3 门禁实现：`docs/implementation/T2-T3-quality-gates-implementation.md`（可玩度冒烟与“必须包含测试变更”）
- 集成点验证：`docs/implementation-plans/Integration-Points-Verification-Summary.md`（Phase 7/8/9 的 PR 集成与 shouldBlock 计算）
- 其它阶段性文档：`P0‑P2‑consolidated‑plan.md`、阶段总结与开发者指南（Phase‑4 Developer Guide/条件模板渲染计划等）

一致性与状态
- Phase 7 以“7.2 工作流”为当前口径；`Phase-7-AI-Code-Review-Implementation-Plan.md` 标注为已废弃，仅供参考。
- 所有阈值与策略以 ADR 为准；实施计划不得复制阈值，应引用 ADR‑0002/0003/0005/0015 的条款编号。
- 报告与工件路径应与计划一致（统一 `logs/YYYY-MM-DD/ci/<module>/`），避免口径漂移。

### 实现规划文档（模板）
- 建议新增 `docs/implementation-plans/_TEMPLATE.md`，推荐结构:
  ```markdown
  ## Stage N: [Name]
  **Goal**: [Specific deliverable]
  **Success Criteria**: [Testable outcomes]
  **Tests**: [Specific test cases]
  **Risks/Mitigations**: [Known risks + rollback]
  **Status**: [Not Started|In Progress|Complete]
  ```

### 现存实现与计划（实际文档）
- `docs/implementation/T2-T3-quality-gates-implementation.md`
- `docs/implementation-plans/Phase-8-Performance-Regression-Implementation-Plan.md`
- `docs/implementation-plans/Phase-7-AI-Code-Review-Implementation-Plan.md`
- `docs/implementation-plans/Phase-9-Dependency-Security-Implementation-Plan.md`
- `docs/implementation-plans/Phase-6-Implementation-Summary.md`

### 历史文档（只读参考）
`docs/architecture/back/` — 早期架构文档（已被 Base 替代），不建议继续维护。

### 实现文档
- [automation-guides.md](automation-guides.md) — 自动化指引
- [VERTICAL_SLICE.md](../VERTICAL_SLICE.md) — 垂直切片开发指引

---

## 7. 本项目独特功能与框架

### AI 优先开发框架
- CLAUDE.md 规则引擎: AI 助手行为准则与工作流
- SuperClaude 框架: FLAGS.md / PRINCIPLES.md / RULES.md / MODE_*.md

### Base/Overlay 架构模式
- Base（清洁基座）: 无 PRD 痕迹，占位符 `${DOMAIN_*}`、`${PRODUCT_*}`
- Overlay（业务叠加）: 包含 PRD-ID，具体业务逻辑
- 08 章分工: Base 仅模板；Overlay 存储功能纵切
  
 文档状态标识（建议）: `Active`（当前口径） / `Design`（设计中） / `Template`（模板/占位）。索引应只将 `Active` 作为默认阅读入口，其余标注状态避免读者混淆。

### 契约驱动开发
- 4 段式契约模板: 声明 / 类型 / 工厂 / 测试
- CloudEvents 1.0: `app.<entity>.<action>` 命名规范
- 契约合规校验: `node scripts/ci/check-contract-docs.mjs`

### 不可回退基座设计
- ADR 驱动: 所有架构决策必须引用 ≥1 个 ADR
- 反向链接验证: Task ↔ ADR/CH 校验（Ajv）
- Base Clean 检查: 自动化脚本验证基座清洁度

### 多 AI 助手协作
- AGENTS.md: 多助手协作规范
- Zen MCP: 多模型验证
- Taskmaster: PRD → Task 自动化
- Serena MCP: 符号级重构与 TDD 编辑

### 质量智能看板（ADR-0017）
- 指标: 覆盖率、复杂度、重复率
- 能力: 趋势分析、门禁状态统一面板

### Windows 平台优先（ADR-0011）
- 单平台策略: 降低跨平台复杂度
- CI 优化: Windows 缓存与优先级
- 脚本兼容: 优先 Node.js/（可选）Python；避免依赖特定 Shell

### 渐进发布与回滚（ADR-0008）
- 分阶段发布: Canary/Beta/Stable
- 自动回滚: Release Health 低于阈值自动回滚
- 紧急回滚工作流: `release-emergency-rollback.yml`

---

## 8. 附加资源

### 开发工具配置
- [ZEN_SETUP_GUIDE.md](../ZEN_SETUP_GUIDE.md) — Zen MCP 设置指南
- [ZEN_USAGE.md](../ZEN_USAGE.md) — Zen MCP 使用说明
- [mcpsetup.md](../mcpsetup.md) — MCP 服务器配置

### 测试与调试
- [playwright-config-analysis.md](playwright-config-analysis.md) — Playwright 配置分析
- [e2e-test-failure-root-cause-analysis.md](e2e-test-failure-root-cause-analysis.md) — E2E 失败根因分析
- [individual-test-results.md](individual-test-results.md) — 独立测试结果

### AI 助手索引（自动更新与校验）
- 本地自动触发（Husky）
  - 正常 `git commit` 时会执行 `.husky/pre-commit`，其中包含 `node scripts/ci/update-ai-index.mjs --write || true`（非阻断）。
  - 如未生效，请先执行一次 `npm run prepare` 确保 Husky 安装。
- CI 触发
  - 推送到 PR 或 `main` 后，Build & Test 工作流会在构建阶段执行 “Update AI assistants index (non-blocking)”。
- 日志工件
  - 工件名: `docs-encoding-and-ai-index-logs`（包含 `logs/**/ai-index/**`）。
  - 结果文件随工作区产物可下载。
- 校验方式
  - 本地: `git diff docs/ai-assistants.index.md docs/ai-assistants.state.json`。
  - CI: 查看工件 `docs-encoding-and-ai-index-logs`，或直接查看构建产物中的上述文件。

### 问题排查
- [test-failure-analysis.md](test-failure-analysis.md) — 测试失败分析
- [fix-verification-results.md](fix-verification-results.md) — 修复验证结果

### 编码与文本清洁（UTF-8）
- 检查 BOM/非 ASCII: `node scripts/ci/check-bom.mjs`、`node scripts/ci/clean-non-ascii.mjs`
- 报告输出目录: `logs/YYYY-MM-DD/encoding/`

### 变更日志与发布
- [CHANGELOG.md](../CHANGELOG.md) — 变更日志
- [RELEASE_NOTES.md](../RELEASE_NOTES.md) — 发布说明

### 质量报告
- [QUALITY_REPORT.md](../QUALITY_REPORT.md) — 质量报告
- [quality-check-report.md](../quality-check-report.md) — 质量检查报告

---

## 9. 文档索引与导航

### 索引文件
- `architecture_base.index` — Base 文档索引（如未生成，可用 `node scripts/rebuild_architecture_index.mjs` 生成）
- `prd_chunks.index` — PRD 分片索引（如未生成，可用 `node scripts/rebuild_indexes.mjs` 生成）
- `@shards/flattened-prd.xml` — PRD 扁平化 XML（外部输入，勿手改）
- `@shards/flattened-adr.xml` — ADR 扁平化 XML（外部输入，勿手改）

### 导航入口
- [README.md](README.md) — 文档导航中心
- [architecture/base/00-README.md](architecture/base/00-README.md) — Base 文档导航

### 快速查找（Windows，使用 Node/Python）
```bash
# 列出 ADR
node -e "require('fs').readdirSync('docs/adr').filter(f=>f.startsWith('ADR-')).forEach(f=>console.log(f))"

# 列出 Base 文档
node -e "require('fs').readdirSync('docs/architecture/base').forEach(f=>console.log(f))"

# 列出工作流
node -e "require('fs').readdirSync('.github/workflows').forEach(f=>console.log(f))"

# 列出 CI 脚本
node -e "require('fs').readdirSync('scripts/ci').forEach(f=>console.log(f))"
```

---

## 10. 使用建议

### 新手入门
1. 阅读 [CLAUDE.md](../CLAUDE.md) 了解整体框架
2. 查看 [README.md](../README.md) 快速启动项目
3. 学习 [ADR-0001](adr/ADR-0001-tech-stack.md)、[ADR-0005](adr/ADR-0005-quality-gates.md) 核心决策

### 架构理解
1. 阅读 [docs/architecture/base/](architecture/base/) 12 章 arc42 文档
2. 理解 Base/Overlay 分离模式
3. 学习 [ADR-0004](adr/ADR-0004-event-bus-and-contracts.md) 契约驱动开发

### AI 协作开发
1. 配置 [AGENTS.md](../AGENTS.md) 规范的 AI 助手
2. 使用 Taskmaster（`.taskmaster/`）管理任务与反链
3. 遵循 [CLAUDE.md](../CLAUDE.md) 4 段式契约模板

### 质量保障
1. 本地运行 `npm run guard:ci` 进行质量门禁检查
2. 确保 ADR 反向链接: `node scripts/ci/check-adr-refs.mjs`
3. 验证 Base 清洁度: `node scripts/verify_base_clean.mjs`
4. 链接与命名自检: 确认索引中的文件名与仓库真实文件一致（统一 `-v2.md` 后缀；避免 `-enhanced`、`-claude` 等历史命名），Overlay 与 GDD 文档使用英文/ASCII 路径，避免中文路径在 GitHub 上无法直开。

---

## 更新历史

- 2025-11-06: 初始版本整理，去重并清理旧口径；修正 ADR 数量口径；补充工作流与质量门禁清单；直链 Implementation/Plans；统一 UTF-8 中文表述；新增 AI 助手索引说明
