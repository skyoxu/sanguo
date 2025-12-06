# Phase 13-22 快速规划（骨架文档）

> 本文档为 Phase 13-22 的规划骨架，每个 Phase 均包含：目标、工作量估算、关键交付物、完成清单
> 详细文档将基于此骨架逐步展开

---

## Phase 13: 质量门禁脚本与自动化

**目标**: 统一 xUnit + GdUnit4 的质量门禁，建立 guard:ci 脚本入口  
**工作量**: 4-5 人天  
**依赖**: Phase 10-12（测试框架）
**详细规划**: [Phase-13-Quality-Gates-Script.md](Phase-13-Quality-Gates-Script.md) （850+ 行，含完整脚本示例与架构设计）

### 关键交付物
- Python 统一入口脚本 (`scripts/python/quality_gates.py`)
  - 覆盖率门禁（xUnit ≥90% 行）
  - GdUnit4 冒烟测试通过率检查
  - 重复率门禁（jscpd ≤2%）
  - 复杂度度量（Cyclomatic ≤10）
- PowerShell guard:ci 包装脚本
- GitHub Actions 工作流（CI 集成）
- 日志输出规范（logs/ci/YYYY-MM-DD/）

### 完成清单
- [ ] 实现 Python 质量门禁驱动（10 项门禁检查）
- [ ] 实现覆盖率合并与阈值检查
- [ ] 实现 GdUnit4 报告聚合
- [ ] 集成 jscpd（C#/GDScript）
- [ ] 集成 SonarQube 扫描
- [ ] 测试本地运行成功（<2min）
- [ ] GitHub Actions 集成与 PR 评论

---

## Phase 14: Godot 安全基线与审计

**目标**: 实现 Electron ADR-0002 等价的 Godot 安全基线  
**工作量**: 5-7 人天  
**依赖**: Phase 8（场景设计）、Phase 12（Headless 测试）
**详细规划**: [Phase-14-Godot-Security-Baseline.md](Phase-14-Godot-Security-Baseline.md) （1000+ 行，含完整 Security.cs 实现、20+ GdUnit4 测试套件、审计日志规范）

### 关键交付物
- Security.cs Autoload（完整实现）
  - URL 白名单验证
  - HTTPRequest 域/协议/路径限制
  - 文件系统 user:// 约束
  - 审计日志（JSONL）
- 安全 GdUnit4 测试套件
  - URL 允许/拒绝场景
  - 非 HTTPS 拒绝测试
  - 无白名单域拒绝测试
  - 审计文件结构验证
- ADR-0018-Godot-Security-Baseline 草案
- 安全烟测 CI 集成

### 完成清单
- [ ] 实现 Security.cs 核心功能
- [ ] 编写≥8 个安全 GdUnit4 测试
- [ ] 实现审计日志写入
- [ ] 集成到冒烟测试
- [ ] 生成安全审计报告（HTML）
- [ ] 文档化白名单管理流程

---

## Phase 15: 性能预算与门禁

**目标**: 建立 Godot 性能基准与自动化回归检测
**工作量**: 5-6 人天
**依赖**: Phase 12（PerformanceTracker.cs）
**详细规划**: [Phase-15-Performance-Budgets-and-Gates.md](Phase-15-Performance-Budgets-and-Gates.md) （1200+ 行，含 10 项性能指标、基准建立流程、CI 集成方案）

### 关键交付物
- PerformanceTracker.cs 核心库（C#）
  - 精确计时 API（微秒级）
  - 百分位数计算（P50/P95/P99）
  - JSON 报告生成
- TestRunner.cs 性能采集器
  - 启动时间采集（≤3s）
  - 帧时统计（P50/P95/P99）
  - 内存使用监控
- PerformanceGates.cs 门禁检查
  - 基准对比
  - Pass/Fail 判定
  - HTML 报告生成
- 性能基准基线文件 (`benchmarks/baseline.json`)
- 基准建立指南与脚本
- GitHub Actions 性能检测工作流

### 完成清单
- [ ] 实现 PerformanceTracker.cs（280+ 行）
- [ ] 实现 QueryPerformanceTracker.cs（100+ 行）
- [ ] 实现 TestRunner.cs 性能采集（180+ 行）
- [ ] 实现 PerformanceGates.cs 门禁检查（220+ 行）
- [ ] 编写 performance_gates.py 聚合脚本（150+ 行）
- [ ] 建立性能基准（10 项 KPI）
- [ ] 集成到 CI 流程（performance-gates.yml）
- [ ] 生成基准建立指南文档

---

## Phase 16: 可观测性与 Sentry 集成

**目标**: 完整集成 Sentry Godot SDK，实现发布健康门禁  
**工作量**: 4-5 人天  
**依赖**: Phase 8（场景设计）

### 关键交付物
- Observability.cs Autoload
  - Sentry 初始化（Release + Sessions）
  - 结构化日志集成
  - 错误捕捉与上报
  - 隐私脱敏配置
- 发布健康门禁脚本
  - 查询 Sentry API（Crash-Free Sessions）
  - 检查 24h Crash-Free ≥99.5%
  - CI 自动阻断（不达标）
- Sentry Release 标签化
- 日志审计与隐私合规文档

### 完成清单
- [ ] 配置 Sentry Godot SDK
- [ ] 实现 Observability.cs
- [ ] 集成结构化日志
- [ ] 实现发布健康门禁脚本
- [ ] 验证 Release 创建与上报
- [ ] 测试本地 CI 流程

---

## Phase 17: 构建系统与 Godot Export

**目标**: 自动化 Windows .exe 打包流程  
**工作量**: 3-4 人天  
**依赖**: Phase 1（Godot 安装）

### 关键交付物
- export_presets.cfg 完整配置
  - Windows Desktop 导出参数
  - 资源优化（纹理压缩、音频）
  - 调试/发布两套配置
- Python 构建驱动脚本
  - Godot headless 导出
  - .pck 与 .exe 分离
  - 签名（可选）
  - 工件上传
- GitHub Actions 构建工作流
- 版本管理与标签化

### 完成清单
- [ ] 完善 export_presets.cfg
- [ ] 实现 Python 构建脚本
- [ ] 本地测试 export 成功
- [ ] 集成 CI 构建流程
- [ ] 验证 .exe 可独立运行

---

## Phase 18: 分阶段发布与 Canary 策略

**目标**: 实现 Canary/Beta/Stable 分阶段发布  
**工作量**: 3-4 人天  
**依赖**: Phase 16（发布健康）、Phase 17（构建）

### 关键交付物
- Release 工作流 (release.yml)
  - 版本碰撞（自动或手动）
  - Changelog 生成
  - GitHub Release 创建
  - Sentry Release 标签
- Canary 部署脚本
  - 内部 Beta 版本发布
  - 限制用户 ID 范围
  - 独立 Sentry 标签
- Beta 到 Stable 晋升规则
  - 24h Crash-Free ≥99.5%
  - 无高优先级 bug
  - 自动或手动审批

### 完成清单
- [ ] 实现 Release 工作流
- [ ] 设计版本控制策略
- [ ] 实现 Canary 隔离
- [ ] 配置发布健康自动门禁
- [ ] 文档化发布流程

---

## Phase 19: 应急回滚与监控

**目标**: 自动化回滚机制与发布监控  
**工作量**: 2-3 人天  
**依赖**: Phase 16（发布健康）

### 关键交付物
- 紧急回滚工作流 (release-emergency-rollback.yml)
  - 一键回滚至前一个稳定版本
  - Sentry Release 标记 revoked
  - 用户通知（可选）
- 发布监控 Dashboard（Sentry 自定义查询）
  - 实时 Crash-Free Session 统计
  - 错误趋势图
  - 关键指标告警

### 完成清单
- [ ] 实现回滚脚本
- [ ] 配置 Sentry 自定义查询
- [ ] 本地模拟回滚流程
- [ ] 文档化应急预案

---

## Phase 20: 功能验收与测试清单

**目标**: 逐功能模块验收，确保 Godot 版本与原版功能对齐  
**工作量**: 5-8 人天  
**依赖**: Phase 8-12（功能实现与测试）

### 关键交付物
- 功能验收矩阵 (acceptance_matrix.md)
  - 原 vitegame 功能清单
  - Godot 版本实现状态
  - 测试覆盖标记
- 竖切玩法测试脚本
  - 启用 GD_ENABLE_PLAYABLE=1 后的完整关卡玩法
  - 记录运行时异常
  - 生成玩法验收报告
- 用户验收测试 (UAT) 指南

### 完成清单
- [ ] 列出 vitegame 核心功能清单（≥30 项）
- [ ] 逐项对应 Godot 实现状态
- [ ] 执行功能验收测试
- [ ] 修复缺失或错误的功能
- [ ] 生成验收签字报告

---

## Phase 21: 性能优化与微调

**目标**: 达到 or 超过原版性能基准  
**工作量**: 5-7 人天  
**依赖**: Phase 15（性能基准）、Phase 20（功能完成）

### 关键交付物
- 性能瓶颈分析报告
  - Godot Profiler 截图
  - 启动时间分解
  - 内存占用统计
  - GC 暂停分析
- 优化方案清单
  - 资源预加载
  - 场景流式加载
  - 脚本优化（算法/数据结构）
  - Godot 引擎参数调优
- 优化前后对比报告

### 完成清单
- [ ] 用 Godot Profiler 采集基准数据
- [ ] 识别 top 3 瓶颈
- [ ] 实施优化方案
- [ ] 验证改进（P95 帧时、启动时间）
- [ ] 确保 Performance gate 通过

---

## Phase 22: 文档更新与最终清单

**目标**: 完成迁移文档，生成 Godot 版本开发指南  
**工作量**: 3-5 人天  
**依赖**: Phase 1-21（所有）

### 关键交付物
- 项目文档索引（Godot 版）
  - 更新 PROJECT_DOCUMENTATION_INDEX.md
  - Godot 特定 ADR 链接
  - 新增 Godot 开发指南
- Godot 开发快速指南 (README-GODOT.md)
  - 项目结构导览
  - 常用命令（编辑/测试/构建）
  - 调试技巧
  - 性能优化最佳实践
- 迁移完成报告
  - 功能完整性对标
  - 性能对比
  - 质量指标（覆盖率/复杂度）
  - 已知限制与后续改进方向
- CHANGELOG 与发布说明

### 完成清单
- [ ] 更新 CLAUDE.md（Godot 特定规范）
- [ ] 更新 ADR 索引（新增 ADR-0018~0022）
- [ ] 编写 README-GODOT.md
- [ ] 生成最终迁移报告
- [ ] 整理测试报告与性能数据

---

## 迁移完成标志

完成标志：
- 所有 Phase 1-22 文档完成  
- xUnit 单元测试 ≥90% 覆盖率  
- GdUnit4 冒烟测试 100% 通过  
- 性能基准达到或超越原版  
- 安全审计完全通过  
- Sentry Crash-Free Sessions ≥99.5%  
- Windows .exe 可独立分发  
- 功能验收清单 100% 完成  
- 文档完整更新  

---

## 后续工作（Post-Migration）

- **维护与迭代**: 定期性能基准与安全审计
- **功能增强**: 基于用户反馈的新增功能开发
- **跨平台扩展**: 如需 macOS/Linux，从 ADR-0011 开始评估
- **性能持续优化**: 基于实际用户数据的优化
