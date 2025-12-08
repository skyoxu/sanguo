# Godot 4.5 + C# 技术栈迁移计划索引



> 项目: vitegame → godotgame

> 迁移类型: 完整技术栈替换（运行时 + UI + 渲染 + 测试）

> 目标平台: Windows Desktop

> 最后更新: 2025-12-21



---



## 迁移概览



### 核心变化对照表



| 层次 | 原技术栈 (vitegame) | 新技术栈 (godotgame) | 迁移复杂度 |

|------|-------------------|-------------------|----------|

| 桌面容器 | Electron | Godot 4.5 | ★★★★★ |

| 游戏引擎 | Phaser 3 | Godot 4.5 (Scene Tree) | ★★★★☆ |

| UI框架 | React 19 | Godot Control | ★★★★★ |

| 样式 | Tailwind CSS v4 | Godot Theme/Skin | ★★★☆☆ |

| 开发语言 | TypeScript | C# (.NET 8) | ★★★★☆ |

| 构建工具 | Vite | Godot Export Templates | ★★★☆☆ |

| 单元测试 | Vitest | xUnit + FluentAssertions | ★★★☆☆ |

| 场景测试 | - | GdUnit4 (Godot Unit Test) | ★★☆☆☆ |

| E2E测试 | Playwright (Electron) | Godot Headless + 自建Runner | ★★★★☆ |

| 覆盖率 | Vitest Coverage | coverlet | ★★☆☆☆ |

| 数据库 | SQLite (better-sqlite3) | godot-sqlite | ★★☆☆☆ |

| 配置存储 | Local JSON | ConfigFile (user://) | ★★☆☆☆ |

| 事件通信 | EventBus (CloudEvents) | Signals + Autoload | ★★★★☆ |

| 多线程 | Web Worker | WorkerThreadPool / Thread | ★★★☆☆ |

| 静态分析 | ESLint + TypeScript | Roslyn + StyleCop + SonarQube | ★★★☆☆ |

| 错误追踪 | Sentry (Electron SDK) | Sentry (Godot SDK) | ★★☆☆☆ |



### 关键风险评估



**[高风险] 需要完全重写**

- Electron 安全基线 → Godot 安全基线（外链/网络/文件系统白名单）

- React 组件 → Godot Control 节点（UI 架构完全不同）

- Playwright E2E → Godot Headless 测试（测试框架完全替换）

- CloudEvents 契约 → Godot Signals 契约（事件系统重设计）



**[中风险] 需要适配改造**

- TypeScript 业务逻辑 → C# 领域层（可部分机翻 + 人工校验）

- Vitest 单元测试 → xUnit 单元测试（测试框架迁移）

- Vite 构建流程 → Godot Export 流程（构建工具替换）

- Sentry 集成 → Sentry Godot SDK（观测性迁移）



**[低风险] 可复用经验**

- SQLite 数据模型（Schema 可复用，API 需适配）

- 质量门禁思路（覆盖率/重复率/复杂度阈值可沿用）

- ADR/Base/Overlay 文档结构（框架可完整保留）

- 日志输出规范（logs/ 目录结构可保持）



---



## 迁移文档结构



### 第一阶段：准备与基座设计

- [Phase-1-Prerequisites.md](Phase-1-Prerequisites.md) — 环境准备与工具安装

- [Phase-2-ADR-Updates.md](Phase-2-ADR-Updates.md) — ADR 更新与新增（ADR-0018~0022）

- [Phase-3-Project-Structure.md](Phase-3-Project-Structure.md) — Godot 项目结构设计



### 第二阶段：核心层迁移

- [Phase-4-Domain-Layer.md](Phase-4-Domain-Layer.md) — 纯 C# 领域层迁移（Game.Core）

- [Phase-5-Adapter-Layer.md](Phase-5-Adapter-Layer.md) — Godot 适配层设计

- [Phase-6-Data-Storage.md](Phase-6-Data-Storage.md) — SQLite 数据层迁移



### 第三阶段：UI 与场景迁移

- [Phase-7-UI-Migration.md](Phase-7-UI-Migration.md) — React → Godot Control 迁移

- [Phase-8-Scene-Design.md](Phase-8-Scene-Design.md) — 场景树与节点设计

- [Phase-9-Signal-System.md](Phase-9-Signal-System.md) — CloudEvents → Signals 迁移



### 第四阶段：测试体系重建

- [GdUnit4 C# Runner 接入指南](gdunit4-csharp-runner-integration.md) — C# 场景测试命令行、报告命名、CI 工件收集



- [Phase-10-Unit-Tests.md](Phase-10-Unit-Tests.md) — xUnit 单元测试迁移

- [Phase-11-Scene-Integration-Tests-REVISED.md](Phase-11-Scene-Integration-Tests-REVISED.md) — **GdUnit4 + xUnit 双轨场景测试**（已改进：采用 GdUnit4 而非 GdUnit4，Headless 一等公民）

- [Phase-12-Headless-Smoke-Tests.md](Phase-12-Headless-Smoke-Tests.md) — **Godot Headless 冒烟测试与性能采集**（启动/菜单/信号/白名单验证）

- [VERIFICATION_REPORT_Phase11-12.md](VERIFICATION_REPORT_Phase11-12.md) — [OK] 可行性验证报告（Phase 11-12 技术可行性评估，综合评分 91/100，推荐实施）

- [CODE_EXAMPLES_VERIFICATION_Phase1-12.md](CODE_EXAMPLES_VERIFICATION_Phase1-12.md) — [OK] Phase 1-12 代码示例验证（代码完整性检查，91% 完整度，补充建议清单）



### 第五阶段：质量门禁迁移

- [Phase-13-22-Planning.md](Phase-13-22-Planning.md) — **Phase 13-22 规划骨架**（详见下方展开）

- [Phase-13-Quality-Gates-Script.md](Phase-13-Quality-Gates-Script.md) — [OK] Phase 13 详细规划（质量门禁脚本设计，10项强制门禁，完整脚本示例）

- [Phase-14-Godot-Security-Baseline.md](Phase-14-Godot-Security-Baseline.md) — [OK] Phase 14 详细规划（Godot 安全基线设计，5个防御域，Security.cs Autoload，20+ GdUnit4测试）

- [VERIFICATION_REPORT_Phase13-14.md](VERIFICATION_REPORT_Phase13-14.md) — [OK] Phase 13-14 综合验证报告（整体架构评估，综合评分 94/100，质量门禁验证）

- [MIGRATION_FEASIBILITY_SUMMARY.md](MIGRATION_FEASIBILITY_SUMMARY.md) — **💯 整体迁移可行性综合汇总**（完整项目评分 92/100、综合验证、实施路线图）

- [Phase-15-Performance-Budgets-and-Gates.md](Phase-15-Performance-Budgets-and-Gates.md) — [OK] Phase 15 详细规划（性能预算与门禁体系，10项KPI，基准建立指南）

- [Phase-16-Observability-Sentry-Integration.md](Phase-16-Observability-Sentry-Integration.md) — [OK] Phase 16 详细规划（可观测性与Sentry集成，3层架构，Release Health门禁，隐私合规）

- [Phase-17-Build-System-and-Godot-Export.md](Phase-17-Build-System-and-Godot-Export.md) — [OK] Phase 17 详细规划（构建系统与Godot导出，export_presets.cfg配置，Python构建驱动，GitHub Actions工作流）

- [Phase-18-Staged-Release-and-Canary-Strategy.md](Phase-18-Staged-Release-and-Canary-Strategy.md) — [OK] Phase 18 详细规划（分阶段发布与Canary策略，Release工作流，自动晋升规则，CI集成）

- [Phase-19-Emergency-Rollback-and-Monitoring.md](Phase-19-Emergency-Rollback-and-Monitoring.md) — [OK] Phase 19 详细规划（应急回滚与监控，自动触发机制，RollbackTrigger评估，版本安全链，发布健康门禁）

- [Phase-20-Functional-Acceptance-Testing.md](Phase-20-Functional-Acceptance-Testing.md) — [OK] Phase 20 详细规划（功能验收测试，四维对标，五阶段工作流，P0/P1/P2分级）

- [Phase-21-Performance-Optimization.md](Phase-21-Performance-Optimization.md) — [OK] Phase 21 详细规划（性能优化，5步工作流，Profiler集成，4类优化策略，Before/After验证）

  - **Phase 13**: 质量门禁脚本（xUnit + GdUnit4 + SonarQube）

  - **Phase 14**: Godot 安全基线（Security.cs + 审计）

  - **Phase 15**: 性能预算与门禁（PerformanceTracker + 基准回归）

  - **Phase 16**: 可观测性与 Sentry（Observability.cs + Release Health）

  - **Phase 17**: 构建系统（Godot Export + .exe 打包）

  - **Phase 18**: 分阶段发布（Canary/Beta/Stable）

  - **Phase 19**: 应急回滚（自动回滚 + 监控）

  - **Phase 20**: 功能验收（逐功能对标验证）

  - **Phase 21**: 性能优化（Profiler 分析 + 优化方案）

  - **Phase 22**: 文档更新（最终清单与发布说明）



---



## 迁移原则



### 不可回退基座保护

1. **ADR 驱动**：所有架构决策必须新增/更新 ADR

2. **Base/Overlay 分离**：Base 文档保持清洁（无 PRD 痕迹）

3. **反向链接验证**：Task ↔ ADR/CH 校验必须通过

4. **质量门禁不降级**：覆盖率/重复率/复杂度阈值保持或提高



### TDD 优先策略

1. **分层隔离**：Game.Core（纯 C#）与 Godot 依赖完全分离

2. **红绿灯循环**：先写 xUnit 测试（红）→ 实现（绿）→ 重构

3. **接口注入**：所有 Godot API 通过接口（ITime/IInput/IResourceLoader）隔离

4. **场景测试后置**：核心逻辑达到 80% 覆盖率后再补充 GdUnit4 测试



### 渐进式迁移路径

1. **先纯后混**：优先迁移不依赖 Godot 的纯逻辑（Game.Core）

2. **先测后功能**：测试框架与门禁先搭建，再迁移业务功能

3. **先冒烟后全量**：E2E 只先做启动/退出/关键信号冒烟测试

4. **分支并行**：保留 vitegame 主分支，godotgame 在独立分支开发



### Windows 平台优先

1. **脚本工具**：优先使用 Python 3（py -3）和 .NET CLI（dotnet）

2. **路径处理**：统一使用绝对路径，避免 Shell 特定语法

3. **CI 缓存**：优化 Windows Runner 缓存策略（Godot Export Templates）

4. **兼容性测试**：所有脚本在 Windows 11 + PowerShell 验证



---



## 关键决策点



### 已确定决策

[OK] 运行时：Godot 4.5（Scene Tree + Node 系统）

[OK] 主语言：C# (.NET 8) — 强类型 + 成熟工具链

[OK] 单元测试：xUnit + FluentAssertions + NSubstitute

[OK] 场景测试：GdUnit4（Headless 原生）

[OK] 覆盖率：coverlet（集成到 dotnet test）

[OK] 平台：Windows Desktop（单平台降低复杂度）

[OK] 数据库：godot-sqlite（SQLite wrapper）

[OK] 观测性：Sentry Godot SDK + 结构化日志



### 待确认决策

⏳ E2E 框架：GdUnit4 headless vs 自建 TestRunner？

⏳ 静态分析：SonarQube Community vs Cloud？

⏳ 性能分析：Godot Profiler vs 自建计时统计？

⏳ 资源管理：StreamTexture vs 预加载池策略？

⏳ 多线程：WorkerThreadPool（推荐）vs Thread（手动管理）？



---



## 时间估算（按阶段）



| 阶段 | 工作量（人天） | 关键里程碑 | 风险等级 |

|------|-------------|-----------|---------|

| Phase 1-3: 准备与基座 | 3-5 | ADR 完成 + 项目初始化 | 低 |

| Phase 4-6: 核心层迁移 | 10-15 | Game.Core + 80% 单元测试 | 中 |

| Phase 7-9: UI/场景迁移 | 15-20 | 主场景可运行 + 基础 UI | 高 |

| Phase 10-12: 测试重建 | 8-12 | 单元/场景/E2E 冒烟通过 | 中 |

| Phase 13: 质量门禁脚本 | 4-5 | 10 项门禁自动化 + CI 集成 | 中 |

| Phase 14: Godot 安全基线 | 5-7 | Security.cs + 审计日志 + 20+ 测试 | 中 |

| Phase 15: 性能预算与门禁 | 5-6 | 10 项 KPI + 基准建立 + 回归检测 | 中 |

| Phase 16: 可观测性与 Sentry | 4-5 | Release Health 门禁 + 结构化日志 | 低 |

| Phase 17-19: 构建发布 | 3-5 | Windows .exe 可打包 + 分阶段发布 | 低 |

| Phase 20-22: 验收优化 | 5-7 | 功能对齐 + 性能达标 | 低 |

| **总计** | **52-80 天** | **完整功能迁移 + 质量保障** | 中 |



注：上述为单人全职工作量估算；实际可能因团队规模/并行度/风险事件而调整。



---



## 后续步骤

- 将 Taskmaster 任务链校验与 C# 契约校验纳入 Phase-13 门禁（guard_ci.py → quality_gates.py），报告统一落盘 logs/ci/YYYY-MM-DD/（如 taskmaster-report.json、contracts-report.json）；

- 将 GdUnit4 场景测试报告（gdunit4-report.xml/json）与性能报告（perf.json）一并作为可选输入传入聚合脚本；

- 按 Godot + C# 目录约定组织 Contracts（如 Game.Core/Contracts/**），并在 CI 中以 dotnet/Python 驱动校验与汇总。





1. **阅读各阶段详细文档**：按 Phase-1 到 Phase-22 顺序执行

2. **创建 ADR 草案**：参考 [Phase-2-ADR-Updates.md](Phase-2-ADR-Updates.md)

3. **搭建 Godot 项目骨架**：参考 [Phase-3-Project-Structure.md](Phase-3-Project-Structure.md)

4. **建立最小 CI 管道**：参考 [Phase-13-Quality-Gates-Script.md](Phase-13-Quality-Gates-Script.md)



---



## 参考资源



### 原项目文档

- [PROJECT_DOCUMENTATION_INDEX.md](../PROJECT_DOCUMENTATION_INDEX.md) — vitegame 完整文档索引

- [CLAUDE.md](../../CLAUDE.md) — AI 优先开发规范

- [docs/adr/](../adr/) — 现有 ADR 记录（ADR-0001~0017）



### Godot 官方资源

- [Godot 4.5 文档](https://docs.godotengine.org/en/stable/)

- [C# 开发指南](https://docs.godotengine.org/en/stable/tutorials/scripting/c_sharp/index.html)

- [GdUnit4 文档](https://github.com/MikeSchulze/gdUnit4)



### 工具链文档

- [xUnit 文档](https://xunit.net/)

- [coverlet 文档](https://github.com/coverlet-coverage/coverlet)

- [SonarQube C# 规则](https://rules.sonarsource.com/csharp/)

- [Sentry Godot SDK](https://docs.sentry.io/platforms/godot/)



---



> **重要提示**：本迁移计划假定你已熟悉 Godot 4.5 基础操作与 C# 开发。如需入门培训，建议先完成官方教程后再启动迁移。

