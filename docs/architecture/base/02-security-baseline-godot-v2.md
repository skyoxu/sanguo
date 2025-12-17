---
title: 02 security baseline v2 (godot)
status: base-SSoT
adr_refs: [ADR-0019, ADR-0011, ADR-0003, ADR-0020]
placeholders: unknown-app, Unknown Product, ${DOMAIN_PREFIX}, dev-team, production
---

# 02 安全基线（Godot 4.5 + C#，Windows-only）

> 本章正文以 **Godot 运行时安全基线** 为准（见 ADR-0019）。

## 0. 章节定位（与 arc42 §2 对齐）

- 本章定义 **默认拒绝** 的防御性基线：文件系统、外链/网络、权限、插件/动态执行、遥测隐私。
- 具体阈值/开关口径以 ADR-0019 为准；本章不重复阈值表，仅给出可执行的策略边界与验收形态。
- 所有安全相关失败必须产生审计工件（JSONL）并落盘到 `logs/**`（见 `docs/testing-framework.md` 的“日志与工件”）。

## 1) 文件系统与资源（res:// / user://）

### 规则

- 仅允许 `res://`（只读资源）与 `user://`（读写存档/配置/日志）。
- 拒绝绝对路径、盘符路径、UNC 路径、`..` 越权、`:`/`\0` 等危险片段。
- 对写入路径做扩展名与大小白名单校验（策略由 ADR-0019 统一定义）。

### 审计（必须）

- 任何拒绝的访问必须写入 `security-audit.jsonl`，至少包含 `{ts, action, reason, target, caller}`。

示例（JSONL 单行）：

```json
{"ts":"2025-12-16T12:00:00Z","action":"fs.write","reason":"path_traversal","target":"C:\\Windows\\system32\\x","caller":"SaveService"}
```

## 2) 外链与网络（HTTPS + 主机白名单）

### 规则

- 仅允许 `https://`；拒绝 `http://`、`file://`、`javascript:`、`data:` 等。
- 仅允许 `ALLOWED_EXTERNAL_HOSTS` 白名单内的主机；`GD_OFFLINE_MODE=1` 时拒绝所有出网。
- 对外链打开/网络请求都必须产生日志与审计（allow/deny/invalid 三态）。

## 3) OS.execute 与权限（默认禁用）

### 规则

- 默认禁止 `OS.execute`（或仅开发态显式开启并强审计）。
- CI/headless 环境下：摄像头/麦克风/文件选择等权限默认拒绝。

## 4) 代码与插件（禁止动态加载）

- 禁止运行期动态加载外部程序集/脚本（例如从 `user://`/网络拉取并执行）。
- 插件白名单：导出/发布时剔除 dev-only 插件；禁止远程调试与编辑器残留配置进入发布包。

## 5) 遥测与隐私（最小合规）

- 在最早 Autoload 初始化 Sentry（见 03 章与 ADR-0003）。
- 发送前进行敏感字段脱敏；结构化日志采样（避免高频洪峰）。

## 6) 安全烟测（CI 最小集）

### 必须覆盖的三态

- allow：合法 `https://` + 白名单主机
- deny：合法格式但不在白名单（或 offline 模式）
- invalid：非法 scheme/格式/越权路径

### 推荐执行入口（Windows）

- 场景/引擎侧（headless，含安全小集）：`py -3 scripts/python/quality_gates.py all --godot-bin "$env:GODOT_BIN" --gdunit-hard`
- 聚合门禁：`pwsh -File scripts/ci/quality_gate.ps1`
