## 任务说明（必填）

- 任务 ID（NG/GM）：`<TASK_IDS>` <!-- 例如：NG-0040, GM-0103；需来自 .taskmaster/tasks/*.json -->
- 关联 ADR：`<ADR_REFS>` <!-- 例如：ADR-0018, ADR-0019, ADR-0004 -->
- 关联 C4 组件/上下文：`<C4_COMPONENTS>` <!-- 例如：Game.Core/Engine, Game.Godot/Adapters, Scenes/Main -->

### 变更摘要

<!-- 简要描述本 PR 做了什么；建议与 Conventional Commits 中的 summary 保持一致 -->

### 提交信息规范

- [ ] 本次提交信息遵循 **Conventional Commits**，示例：
  - `feat(core): add T2 game loop SaveId validation`
  - `fix(adapter): harden SqliteDataStore path validation`
  - `refactor(ci): add gameloop quality guard step summary`

---

## ADR / 架构引用

- [ ] PR 描述中已引用本次变更涉及的 ADR（例如：`ADR-0018`, `ADR-0019`, `ADR-0004`, `ADR-0005`）
- [ ] 如涉及 C4 结构/组件调整，已同步更新：
  - [ ] `docs/architecture/base/04-system-context-c4-event-flows-v2.md` 或相关 C4 章节
  - [ ] `docs/architecture/overlays/PRD-*/08/` 下的功能纵切文档（仅在需要时）

---

## 契约与文档（Contracts / Overlays）

- [ ] 本次改动未修改领域契约（Contracts），或：
  - [ ] 已更新 `Game.Core/Contracts/**` 中的 C# 契约文件
  - [ ] 已更新对应 Overlay 08 文档（例如：`08-Contracts-*.md` / `08-功能纵切-*.md`），记录事件/DTO/文件路径
  - [ ] 已更新/新增对应测试：
    - [ ] `Game.Core.Tests/Domain/*ContractsTests.cs`
    - [ ] （如适用）`Tests.Godot/tests/**`
  - [ ] 本地运行 `py -3 scripts/python/validate_contracts.py` 通过

---

## 测试与质量门禁

- [ ] dotnet 单元测试：`dotnet test` 通过（或 `py -3 scripts/python/run_dotnet.py`）
- [ ] GdUnit4 集成/场景测试：`py -3 scripts/python/run_gdunit.py ...` 通过（如本次改动涉及 Godot 脚本/场景）
- [ ] Headless smoke（如适用）：`py -3 scripts/python/smoke_headless.py ...` 通过
- [ ] 覆盖率门禁（如适用）：已检查 `logs/unit/**/coverage.json`，新代码不低于项目约定阈值
- [ ] 任务回链校验（如适用）：`py -3 scripts/python/task_links_validate.py` 通过

---

## Sentry / Release / Sourcemaps

- [ ] 如本 PR 预期合并到 main 后触发 **Windows Release + Sentry 源图上传**，已确认：
  - [ ] 相关 Sentry Secrets 已在仓库/环境中配置（`SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT`）
  - [ ] 需要上传的调试符号/源图已在构建产物中生成（按项目约定路径）
- [ ] 已在最近一次 CI 运行的 **Step Summary** 中看到类似行：
  - `Sentry: secrets_detected=<true|false> upload_executed=<true|false>`
  - 若 `upload_executed=false` 但预期上传，请在 PR 中说明原因或后续计划

> 说明：当前 Sentry 源图上传仍处于逐步接入阶段；本 PR 模板中的勾选项用于提醒与审计，
> 实际上传行为由 CI 工作流和相关脚本（Python/PowerShell）共同决定。

---

## 其他检查项

- [ ] 如改动涉及 `.taskmaster/tasks/*.json`，已同步更新：
  - [ ] `owner`, `labels`, `test_refs`, `acceptance` 等字段与实际实现一致
  - [ ] 对应任务状态（`status`）合理更新（`pending` / `in-progress` / `done`）
- [ ] 如改动涉及 Observability / Release Health：
  - [ ] 已确认 `release-health` / Sentry 相关脚本在本分支 CI 中运行正常

