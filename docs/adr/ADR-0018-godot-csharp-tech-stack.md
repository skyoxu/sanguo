# ADR-0018: 技术栈切换至 Godot 4.5 + C# (.NET 8)

- Status: Accepted
- Context: 原项目 vitegame 采用 Electron + React + Phaser + TypeScript 技术栈；当前仓库为迁移后的 Windows only Godot + C# 模板。为统一口径与后续实现/测试/门禁脚本，本 ADR 明确以 Godot 4.5 + C# (.NET 8) 为主技术栈。
- Decision: 采用 Godot 4.5（Forward+ 渲染），C# 为主语言（.NET 8），场景与 UI 使用 Godot Scene/Control 体系；测试体系为 xUnit（领域层）+ GdUnit4（场景/集成），覆盖率使用 coverlet；质量门禁与可观测性沿用 ADR-0005/ADR-0003 的统一口径。
- Consequences: 
  - 前端/Electron 相关实现与门禁迁出运行时关键路径；相应基线由“Electron 安全”切换为“Godot 安全”（见 ADR-0019）。
  - 领域层以纯 C# 为 SSoT（不依赖 Godot），适配层封装 Godot API 通过接口注入；三层可测结构成为强制约束（见 docs/architecture/base/06 与 6.2 测试门禁）。
  - CI/CD 流程转为 Windows 优先（见 ADR-0011），E2E 测试改为 Godot Headless 方案；导出与发布使用 Godot Export Templates。
  - 文档与 Overlay 的 08 章仅引用 01/02/03 口径；事件命名转为 Signals/Contracts 常量化，不再使用 Electron/Playwright 相关术语。
- Supersedes: ADR-0001-tech-stack
- References: ADR-0011-windows-only-platform-and-ci, ADR-0005-quality-gates, ADR-0003-observability-release-health, docs/migration/MIGRATION_INDEX.md

