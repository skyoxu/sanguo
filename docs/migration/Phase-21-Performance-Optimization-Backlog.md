# Phase 21 Backlog — 性能优化蓝图（项目级）

> 状态：Backlog（非当前模板 DoD，按需在实际游戏项目中启用）
> 目的：承接 Phase-21-Performance-Optimization.md 中与具体玩法/资源相关的性能优化蓝图，避免在模板阶段虚构热点或强行加入项目特定优化，同时为后续项目提供可参考的优化路线。
> 相关 Phase：Phase 12（Smoke）、Phase 15（性能预算）、Phase 16（可观测性）、Phase 20（功能验收）

---

## B1：项目级性能基线与热点扫描

- 现状：
  - 模板提供了帧时间采集器（PerformanceTracker Autoload）与 P95 门禁脚本（check_perf_budget.ps1），但未在具体关卡/玩法场景中进行系统性 Profiler 分析；
  - Phase‑21 文档中的 CPU 热点、内存泄漏、渲染瓶颈、I/O 延迟等分析步骤尚未在模板层执行。
- 蓝图目标：
  - 在实际游戏项目中，选取代表性场景（主菜单、核心关卡、压力测试场景）进行性能基线采集：
    - 使用 Godot Profiler / VisualProfiler / Performance monitor 收集 CPU/渲染/内存指标；
    - 使用 PerfTracker 记录帧时间分布；
    - 记录采集环境与硬件配置，生成 `perf-baseline.md` 或 JSON 报告。
- 建议实现方式：
  - 在项目仓库中新增“性能测试场景”（如 `res://Scenes/Perf/PerfTest_Main.tscn` 等）；
  - 使用 Git 分支或独立 CI Job 跑这些场景，并将 Profiler 截图/JSON 导出保存到 `logs/perf/<date>/`；
  - 模板仓库仅保留 PerfTracker 和门禁脚本，不包含项目特定场景。
- 优先级：项目级 P0–P1。

---

## B2：算法和数据结构优化（核心玩法路径）

- 现状：
  - 模板中的 Core/Adapters 主要提供结构和简单演示逻辑，没有复杂 AI、路径规划、经济模拟等高复杂度算法；
  - Phase‑21 文档中提到的 O(n²)→O(n log n) 优化等更适合在具体玩法逻辑中应用。
- 蓝图目标：
  - 在项目中识别热点算法（例如：敌人 AI 更新、寻路、战斗计算、经济 tick），并针对这些路径进行：
    - 算法复杂度分析（从 O(n²) 降到 O(n log n) 或更好）；
    - 数据结构优化（例如从 List 变到 Dictionary/SpatialHash 等）。
- 建议实现方式：
  - 使用 Profiler 标记热点函数/调用栈，定位算法瓶颈；
  - 在 Game.Core 项目中专门为这些模块添加性能相关测试或基准（基于 xUnit + Stopwatch），验证优化前后差异；
  - 将优化实践记入项目的 `docs/perf/optimization-notes.md`，而不是模板文档。
- 优先级：项目级 P1–P2。

---

## B3：资源与渲染优化（纹理/音频/特效）

- 现状：
  - 模板仅带有非常轻量的 UI 与演示资源，没有大规模纹理/动画/粒子；
  - Phase‑21 文档中的纹理压缩、Mipmaps、Batching、Culling 等优化策略尚未在模板资源层面应用。
- 蓝图目标：
  - 在资源较多的项目中，为纹理/音频/特效等内容制定优化策略：
    - 统一纹理分辨率与压缩格式（ASTC/ETC2 等）；
    - 为关键粒子/特效设置合理的 LOD 和可见性判断；
    - 使用 Culling/Batching/实例化等降低渲染开销。
- 建议实现方式：
  - 利用 Godot 的 Import 设置与 Rendering 菜单进行资源级调优；
  - 在项目文档中记录针对不同平台（PC、移动）的资源配置方案；
  - 模板仓库只保留最简演示资源，不主动引入复杂优化。
- 优先级：项目级 P1–P3。

---

## B4：GC 与内存管理优化

- 现状：
  - 模板目前没有对 .NET GC 模式、对象池策略等做专门配置；
  - Phase‑21 文档中的 GC 暂停时间优化与内存泄漏排查尚未在模板级别执行。
- 蓝图目标：
  - 在实际项目中：
    - 识别频繁分配/回收的对象类型并引入对象池或结构化缓冲；
    - 根据场景特点调整 GC 设置（如 Server/Workstation 模式、LatencyMode）；
    - 使用内存 Profiler 发现并修复长生命周期泄漏。
- 建议实现方式：
  - 在 Game.Core 中抽象高频对象创建路径，便于替换为池化实现；
  - 使用 dotnet/gcprofiler 或第三方工具配合 Godot Profiler 分析 GC 行为；
  - 在项目文档中记录 GC 配置与调优经验。
- 优先级：项目级 P2–P3。

---

## 使用说明

- 对于基于本模板创建的新项目：
  - 建议在功能与稳定性（Phase 20）基本确认后，再启动 Phase‑21 类型的性能优化工作；
  - 优先从 B1 的基线采集与热点扫描开始，再按需要逐步切入算法、资源与 GC 优化。

- 对于模板本身：
  - 当前 Phase 21 不要求在模板级别实现具体性能优化，只需提供 PerfTracker + 性能门禁等基础设施；
  - 本 Backlog 文件用于记录“项目级性能优化任务”，帮助后续团队基于本模板制定符合自身游戏特性的优化计划。

