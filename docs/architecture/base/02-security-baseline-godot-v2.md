# 02 — 安全基线（Godot 4.5 + C# / Windows Only）

状态：Active（与 ADR-0019 一致）；覆盖运行时与 CI 的最小可执行基线。

参考：ADR-0019-godot-security-baseline.md、ADR-0011-windows-only-platform-and-ci.md、ADR-0003-observability-release-health.md

核心口径（SSoT，不在 08 章复制阈值）
- 资源与文件系统
  - 仅允许 `res://`（只读）与 `user://`（读写）。
  - 拒绝绝对路径与越权访问（路径规范化 + 扩展名/大小白名单）。
  - 失败统一审计（路径规范见“6.3 日志与工件”）。
- 外链与网络
  - 仅 HTTPS；主机白名单 `ALLOWED_EXTERNAL_HOSTS`。
  - `GD_OFFLINE_MODE=1` 时拒绝所有出网并审计。
- 代码与插件
  - 禁止运行期动态加载外部程序集/脚本。
  - 插件白名单；导出/发布剔除 dev-only 插件；禁用远程调试与编辑器残留。
- OS.execute 与权限
  - 默认禁用 OS.execute（或仅开发态开启并严审计）。
  - CI/headless 下摄像头/麦克风/文件选择默认拒绝。
- 遥测与隐私
  - 最早 Autoload 初始化 Sentry Godot SDK；开启 Releases + Sessions 统计 Crash‑Free。
  - 敏感字段 SDK 端脱敏；结构化日志采样。
- 配置开关
  - `GD_SECURE_MODE=1`、`ALLOWED_EXTERNAL_HOSTS=<csv>`、`GD_OFFLINE_MODE=0/1`、`SECURITY_TEST_MODE=1`。
- 安全烟测（CI 最小集）
  - 外链 allow/deny/invalid 三态 + 审计文件存在。
  - 网络白名单验证；`user://` 写入成功、绝对/越权写入拒绝；权限在 headless 下默认拒绝。

落地与验证
- 质量门禁脚本：`py -3 scripts/python/godot_tests.py --headless --suite security`（输出见 6.3）。
- Overlay 的 08 章仅“引用”本页与 ADR-0019，不复制阈值；契约与事件统一落盘 `Scripts/Core/Contracts/**`。

