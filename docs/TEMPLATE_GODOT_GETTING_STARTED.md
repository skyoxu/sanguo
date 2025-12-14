# Godot+C# 模板：快速开始（Windows-only）
  > 本文件是 `sanguo` 仓库的通用「上手模板」，用于指导从本项目派生的新游戏在 Windows 上完成首次运行、测试与导出。
  > 所有中文内容均使用 UTF-8 编码；若在终端中出现乱码，请以 VS Code 等编辑器并显式选择 UTF-8 查看。

  ---

  ## 1. 适用范围与前提条件

  本模板面向 **Godot 4.5.1 + C#（.NET 8）+ Windows-only** 项目，默认目录结构与本仓一致：

  - `GodotGame.csproj` —— Godot .NET 主工程（场景 + Adapters 层）
  - `Game.Core/` —— 纯 C# 领域层（零 Godot 依赖）
  - `Game.Core.Tests/` —— xUnit 单元测试（覆盖率门禁）
  - `Tests.Godot/` —— GdUnit4 场景/Glue 测试
  - `scripts/ci/**`、`scripts/python/**` —— Windows 友好的 CI/测试脚本

  在开始之前，请在 Windows 上准备：

  - 安装 **.NET 8 SDK**（建议通过 `dotnet --version` 验证）
  - 安装 **Godot 4.5.1 .NET（mono）**，例如：
    - `C:\Godot\Godot_v4.5.1-stable_mono_win64.exe`
  - 安装 **Python 3** 并通过 `py -3` 可调用
  - 建议使用 **VS Code** 或 Rider 打开解决方案（UTF-8 编码）

  设置一个全局环境变量指向 Godot 可执行文件：

  ```powershell
  setx GODOT_BIN "C:\Godot\Godot_v4.5.1-stable_mono_win64.exe"

  重新打开终端后，$env:GODOT_BIN 应该可用。

  ———

  ## 2. 第一次打开与运行项目

  1. 克隆或复制本模板为新项目目录（例如 C:\buildgame\mygame）。
  2. 在 Godot Editor 中：
      - 启动 Godot_v4.5.1-stable_mono_win64.exe
      - 选择「导入项目」，指向 project.godot
  3. 等待 Godot 编译 C# 程序集（首次会稍慢）。
  4. 在 Editor 中按 F5 运行游戏主场景，确认能正常启动和退出。

  > 如需从命令行 headless 启动进行自检，可使用：
  >
  > & "$env:GODOT_BIN" --headless --path . --quit

  ———

  ## 3. 一键导出与 EXE 冒烟（Windows）

  本模板提供了最小导出与 EXE 冒烟脚本，适配 ADR-0011（Windows-only 平台）与 ADR-0005（质量门禁）：

  1. 在仓库根目录打开 PowerShell：

     cd C:\buildgame\sanguo  # 或你的派生项目路径
     $env:GODOT_BIN = "C:\Godot\Godot_v4.5.1-stable_mono_win64.exe"
  2. 使用内置导出脚本生成 EXE：

     ./scripts/ci/export_windows.ps1 -GodotBin "$env:GODOT_BIN" -Preset "Windows Desktop" -Output build\Game.exe
  3. 对导出的 EXE 做一次本地冒烟测试：

     ./scripts/ci/smoke_exe.ps1 -ExePath build\Game.exe
  4. 若希望在 CI 工作流中 dry-run 导出/冒烟，可参考：
      - .github/workflows/windows-export-slim.yml
      - .github/workflows/windows-release.yml
      - .github/workflows/windows-release-tag.yml

  这些工作流均假设：

  - Godot 可执行由 CI 任务下载到 GODOT_BIN
  - 导出产物落盘到 build/Game.exe
  - 日志与工件写入 logs/ci/**（见 AGENTS.md 6.3 日志规范）

  ———

  ## 4. 单元测试（Game.Core + Game.Core.Tests）

  领域层逻辑放在 Game.Core/，通过 Game.Core.Tests/ 做 xUnit 单元测试（ADR-0005/0006）：

  cd C:\buildgame\sanguo

  # 运行所有单元测试
  dotnet test --collect:"XPlat Code Coverage"

  建议：

  - 新增领域逻辑时，总是先在 Game.Core.Tests 写红灯测试，再在 Game.Core 实现。
  - 覆盖率门禁：lines ≥ 90%，branches ≥ 85%（约定见 docs/testing-framework.md 与 ADR-0005）。
  - 生成的覆盖率报告会落盘到 logs/unit/（或由 CI 脚本收敛）。

  ———

  ## 5. 场景与 Glue 测试（Tests.Godot + Python 包装）

  场景层与 Glue 测试集中在 Tests.Godot/，由 GdUnit4 驱动：

  - 场景烟囱用例：Tests.Godot/tests/Scenes/Smoke/**
  - UI/Glue 测试：Tests.Godot/tests/UI/**
  - DB/跨重启：Tests.Godot/tests/Adapters/Db/**

  本模板提供统一的 Python 封装脚本：

  cd C:\buildgame\sanguo

  # 准备 GdUnit4 测试工程（一次性或按需执行）
  py -3 scripts/python/prepare_gd_tests.py --project Tests.Godot --runtime Game.Godot

  # 运行场景 Smoke 测试（与 windows-smoke-dry-run.yml 一致）
  py -3 scripts/python/run_gdunit.py --prewarm --godot-bin "$env:GODOT_BIN" --project Tests.Godot `
    --add tests/Scenes/Smoke `
    --timeout-sec 300 --rd "logs/e2e/local/gdunit-reports/smoke-scenes"

  > 建议：在本地至少保证 Smoke 测试通过，再推送到远程，让 CI 的 Windows Smoke (Dry Run) 工作流复跑一遍。

  ———

  ## 6. Sentry 软门禁脚本与 Release Health（摘要）

  Release 工作流在 Job 末尾调用 scripts/python/check_sentry_secrets.py 进行 Sentry 环境软门禁（ADR-0003）：

  - 检查 Secrets：SENTRY_AUTH_TOKEN, SENTRY_ORG, SENTRY_PROJECT
  - 读取可选标记：SENTRY_UPLOAD_PERFORMED（由未来 sourcemap 上传步骤设置）
  - 输出一行摘要：

    Sentry: secrets_detected=<true|false> upload_executed=<true|false>
  - 如存在 GITHUB_STEP_SUMMARY，则以 UTF-8 追加写入 Step Summary，用于 PR/Release 审查。
  - 该脚本始终返回 0，不会阻断构建，只用于审计与可见性。

  派生项目只需：

  1. 复用本模板的 check_sentry_secrets.py 与 Release 工作流末尾步骤；
  2. 在 GitHub 仓库 Secrets 中配置 Sentry 相关变量；
  3. 在需要真正上传 sourcemap 的步骤里设置 SENTRY_UPLOAD_PERFORMED=1。

  ———

  ## 7. 深入阅读与后续步骤

  - 整体文档索引：docs/PROJECT_DOCUMENTATION_INDEX.md
  - 测试框架与金字塔：docs/testing-framework.md
  - Windows-only 快速指引：docs/migration/Phase-17-Windows-Only-Quickstart.md
  - 安全基线：docs/migration/Phase-14-Godot-Security-Baseline.md
  - Release / Sentry / 工作流说明：docs/workflows/GM-NG-T2-playable-guide.md

  > 派生新项目时，可以直接复制本文件并按实际仓库名、主工程名（例如 sanguo）做极少量替换，即可获得一份完整的「Godot+C# Windows-only 快速开始」文档。