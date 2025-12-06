# Windows 手动发布指引（模板最小集）

> 目标：在 GitHub Actions 中手动触发 Windows‑only 导出与产物上传，适合模板首次验证或临时分发。

## 前置 / Prerequisites
- 仓库已启用 GitHub Actions。
- 分支包含工作流：`.github/workflows/windows-release.yml`（本模板已提供）。

## 操作步骤 / Steps
1) 打开仓库 → Actions → 选择 “Windows Release (Manual)”。
2) 点击 “Run workflow”。无需参数（默认使用 Godot 4.5.1‑mono）。
3) 等待 Job 完成（约 1–3 分钟，视机器与网络）。
4) 在工作流页面底部 “Artifacts” 下载 `windows-release` 压缩包：
   - 含导出产物：`build/Game.exe`
   - 含日志：`logs/ci/YYYYMMDD-HHMMSS/**`

## 验证 / Verify
- 打开 `logs/ci/**/smoke/exe.log`，优先寻找：`[TEMPLATE_SMOKE_READY]`（模板就绪标记）。
- 备选信号：`[DB] opened`（数据库就绪）。
- 无日志输出时视为 INCONCLUSIVE，但产物仍可手动运行验证。

## 说明 / Notes
- 工作流会自动：
  - 下载 Godot .NET（mono）；
  - 安装 Export Templates；
  - 调用脚本导出（`scripts/ci/export_windows.ps1`）。
- 代码签名与商店分发不在本模板范围，可在产物生成后按需接入签名工具链。
- 若需更严格门禁（包含测试与导出），优先使用 “Windows Quality Gate”。

## 常见问题 / FAQ
- 无法导出：通常是 Export Templates 未安装；本工作流已安装，若本地导出失败请先在 Editor 中安装模板。
- Godot 版本：如需更新，修改工作流中的 `GODOT_VERSION` 环境变量并同步本地 `GODOT_BIN`。

