# 架构完整性检查清单

## 实施状态检查

### ADR-0002 Electron安全基线

- [ ] contextIsolation = true
- [ ] nodeIntegration = false
- [ ] sandbox = true
- [ ] 严格CSP策略已配置
- [ ] preload脚本使用contextBridge白名单API

### ADR-0003 可观测性系统

- [ ] Sentry集成已配置
- [ ] Release Health监控已启用
- [ ] 结构化日志系统已实施
- [ ] 错误边界已配置

### ADR-0004 事件总线契约

- [ ] CloudEvents格式事件定义
- [ ] 类型安全的事件系统
- [ ] IPC通信契约已定义
- [ ] 事件版本化策略已实施

### ADR-0005 质量门禁

- [ ] E2E测试覆盖率达标
- [ ] 单元测试覆盖率≥90%
- [ ] 安全测试自动化
- [ ] 质量门禁脚本已配置

## 文档完整性检查

### Base文档 (docs/architecture/base/)

- [ ] 01-约束与目标-增强版.md
- [ ] 02-安全基线(Electron).md
- [ ] 03-可观测性(Sentry+日志)增强版.md
- [ ] 04-系统上下文与C4+事件流.md
- [ ] 05-数据模型与存储端口.md
- [ ] 06-运行时视图(循环+状态机+错误路径).md
- [ ] 07-开发与构建+质量门禁.md
- [ ] 08-功能纵切-template.md
- [ ] 09-性能与容量规划.md
- [ ] 10-国际化·运维·发布.md

### ADR文档 (docs/adr/)

- [ ] 所有ADR包含必需章节 (Status, Context, Decision, Consequences)
- [ ] ADR状态与实际实施一致
- [ ] ADR间依赖关系已明确定义

## 配置一致性检查

- [ ] 安全策略在下游ADR中正确继承
- [ ] 质量门禁阈值在所有相关组件中一致
- [ ] 技术版本在所有ADR中保持同步
- [ ] 数据一致性策略在相关ADR中对齐

## 自动化检查

- [ ] scripts/arch-governance.mjs 脚本可执行
- [ ] scripts/adr-config-linker.mjs 报告无Critical问题
- [ ] npm run guard:ci 全部通过
- [ ] 架构优化分析器报告健康分数≥80

---

_此检查清单应定期更新并与架构演进保持同步_
