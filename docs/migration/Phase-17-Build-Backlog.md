# Phase 17 Backlog — 构建系统与导出管道增强

> 状态：Backlog（非当前模板 DoD，按需渐进启用）
> 目的：承接 Phase-17-Build-System-and-Godot-Export.md 中尚未在当前 Godot+C# 模板落地的构建/导出蓝图，避免“文档超前、实现滞后”，同时为后续项目提供发布管道演进路线图。
> 相关 ADR：ADR‑0003（Release Health）、ADR‑0005（质量门禁）、ADR‑0015（性能预算）

---

## B1：Python 构建驱动脚本（scripts/build_windows.py）

- 现状：
  - 模板当前仅提供 `scripts/ci/export_windows.ps1`（导出）与 `scripts/ci/smoke_exe.ps1`（EXE 冒烟），通过 `quality_gate.ps1` 可在 CI 中选择性启用；
  - Phase‑17 文档中多处引用 `scripts/build_windows.py`，但该脚本尚未在仓库中实现。
- 蓝图目标：
  - 提供一个跨平台的 Python 构建驱动脚本 `scripts/build_windows.py`，统一完成：
    - 环境验证（Godot .NET、Export Templates、SignTool 等）；
    - 清理旧构建产物（`build/` 与临时目录）；
    - 调用 Godot headless 导出（Release/Debug/Pack 回退逻辑）；
    - 可选代码签名（使用 Windows SignTool）；
    - 生成版本元数据（版本号、git commit、CI run ID、构建时间等）；
    - 生成校验和（SHA256）和构建摘要 JSON。
- 建议实现方式：
  - 先在本地用 Python 脚本封装 `export_windows.ps1` 的核心逻辑，仅作为 CLI 工具使用；
  - 在后续项目中根据需要逐步扩展签名与元数据注入能力；
  - 在 package.json 或 README 中提供 `py -3 scripts/build_windows.py release` 的使用示例。
- 优先级：P2（适合有正式发布需求的项目，模板阶段可继续使用 PowerShell 版本）。

---

## B2：版本元数据与构建信息注入

- 现状：
  - 当前导出流程只生成 `build/Game.exe` + `.pck` 与导出日志/summary.json，未对 EXE 内嵌版本信息或生成统一的 `build-info.json`；
  - Phase‑17 文档中提到“版本号（git tag）、Build Number（CI run ID）、Commit SHA、Build Timestamp”等元数据由构建脚本注入。
- 蓝图目标：
  - 为发布产物建立一份统一的版本信息：
    - 例如 `build/build-info.json` 或 `build/version.json`，包含 {version, commit, run_id, built_at}；
    - 在 Godot 场景或 About 对话框中展示版本信息；
    - 与 Sentry Release/Release Health 门禁联动（Phase‑16 ADR‑0003）。
- 建议实现方式：
  - 在 B1 的 Python 脚本中读取 git/tag/CI 环境变量，生成版本信息 JSON；
  - 在 Godot 侧提供一个简单的 VersionProvider（从该 JSON 读取信息）或通过编译常量注入；
  - 将版本信息路径写入导出 summary.json，便于 CI/调试使用。
- 优先级：P2–P3（对发布追踪有价值，但不影响模板级导出能力）。

---

## B3：独立 Release 工作流（release-windows.yml）

- 现状：
  - Windows CI / Windows Quality Gate 工作流主要关注测试与质量门禁，导出由 `quality_gate.ps1` 可选控制；
  - Phase‑17 文档中提到的“GitHub Actions Release Trigger”与专门的 Release 工作流尚未创建，例如 `.github/workflows/release-windows.yml`。
- 蓝图目标：
  - 提供一条专门用于发布的 CI 工作流：
    - 触发条件：git tag push 或手动 dispatch；
    - 步骤：生成版本元数据 → 调用 `scripts/build_windows.py` 导出/签名 → 上传 `Game.exe/.pck` 与版本信息到 GitHub Release；
    - 可选：在发布前调用 Release Health Gate（Phase‑16）与性能门禁（Phase‑15）。
- 建议实现方式：
  - 新增 `.github/workflows/release-windows.yml`，只在 tag 分支上运行；
  - 将现有导出脚本整合为 workflow 的一个步骤，避免重复实施；
  - 在 Phase‑17 文档中补充该工作流的 YAML 片段与使用说明。
- 优先级：P3（适合有正式发布流需求的项目，模板阶段不必强制）。

---

## B4：代码签名与安全分发

- 现状：
  - 当前导出流程不包含代码签名；
  - Phase‑17 文档中提到使用 PowerShell SignTool 集成实现 Windows 代码签名，但仓库中尚未引入证书/签名脚本。
- 蓝图目标：
  - 为带签名要求的项目提供一条可配置的签名步骤：
    - 使用 SignTool 对 `build/Game.exe` （以及安装包，如存在）进行签名；
    - 通过环境变量提供证书路径/密码，而非硬编码；
    - 在导出 summary 或 Release 说明中记录签名状态。
- 建议实现方式：
  - 在 B1 的构建脚本中增加可选的签名步骤，仅在检测到相关环境变量时启用；
  - 在 README/Phase‑17 文档中说明签名配置方式和注意事项。
- 优先级：P3（安全与分发层面增强，不影响模板基本使用）。

---

## B5：导出预设与多配置支持

- 现状：
  - 模板当前主要依赖单一 “Windows Desktop” 导出预设，输出 `build/Game.exe`；
  - Phase‑17 文档中提到 Debug/Release 多配置、带/不带 Demo 的多种导出场景，但尚未在 export_presets.cfg 与脚本中实现完整支持。
- 蓝图目标：
  - 提供多种导出配置以适应不同场景：
    - Debug 版本（额外日志、无压缩）；
    - Release 版本（优化/压缩、去除测试资源）；
    - Demo 版本（仅包含部分关卡或内容）。
- 建议实现方式：
  - 在 Godot 的 export_presets.cfg 中定义多条预设，并在导出脚本中增加对应参数；
  - 在 Phase‑17 文档中记录各预设的差异与推荐使用场景。
- 优先级：P3（模板阶段可保持单一预设，有实际需求时再扩展）。

---

## 使用说明

- 对于基于本模板创建的新项目：
  - 模板提供的 `export_windows.ps1` + `smoke_exe.ps1` 已能满足“导出可运行 EXE + 基本冒烟”的最小需求；
  - 当项目需要正式发布管道时，可按 B1→B3→B4/B2/B5 的顺序逐步启用 Python 构建脚本、Release 工作流与签名/多配置支持。

- 对于模板本身：
  - 当前 Phase 17 仅要求导出脚本与冒烟脚本在本地/CI 中可用，并在 Quickstart/Checklist 文档中提供清晰指引；
  - 本 Backlog 文件用于记录构建/发布蓝图，避免在模板阶段就强行引入复杂发布系统和签名流程。

