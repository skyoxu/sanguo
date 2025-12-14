# ADR-0019: Godot 4.5 安全基线（Windows Only）

- Status: Accepted
- Context: 原 ADR-0002 针对 Electron 的安全基线（CSP、contextIsolation 等）已不再适用。Godot 运行时与文件系统/外链策略、插件与执行模型与 Electron 存在根本差异，需建立新的防御性基线并与质量门禁脚本协同。
- Decision:
  - 文件系统与资源：仅允许 `res://`（只读）与 `user://`（读写）；拒绝绝对路径与越权访问（路径规范化 + 扩展名/大小白名单）；失败统一审计（见 6.3 日志与工件）。
  - 外链与网络：仅 HTTPS；主机白名单 `ALLOWED_EXTERNAL_HOSTS`；`GD_OFFLINE_MODE=1` 时拒绝所有出网并审计。
  - 代码与插件：禁止运行期动态加载外部程序集/脚本；插件白名单（导出/发布剔除 dev-only 插件）；禁用远程调试与编辑器残留。
  - OS.execute 与权限：默认禁用 OS.execute（或仅开发态开启并严审计）；CI/headless 下摄像头/麦克风/文件选择默认拒绝。
  - 遥测与隐私：最早 Autoload 初始化 Sentry Godot SDK；开启 Releases + Sessions 计算 Crash‑Free；敏感字段 SDK 端脱敏；结构化日志采样。
  - 配置开关：`GD_SECURE_MODE=1`、`ALLOWED_EXTERNAL_HOSTS=<csv>`、`GD_OFFLINE_MODE=0/1`、`SECURITY_TEST_MODE=1`。
  - 安全烟测（CI 最小集）：外链 allow/deny/invalid 三态 + 审计文件存在；网络白名单验证；user:// 写入成功、绝对/越权写入拒绝；权限在 headless 下默认拒绝。
- Consequences:
  - 安全相关改动必须附带就地验收（xUnit/GdUnit4）与审计产物（logs/ 路径见 6.3）。
  - Overlay 的 08 章仅引用本基线，不复制阈值；契约与事件统一落盘 Game.Core/Contracts/**
  - CI 中新增/保留安全作业 `godot-e2e --suite security`；release‑health 门禁保持不变（ADR‑0003）。
- Supersedes: ADR-0002-electron-security
- References: ADR-0011-windows-only-platform-and-ci, ADR-0003-observability-release-health, docs/architecture/base/02-security-baseline-electron-v2.md（后续将以 Godot 版本替换）

