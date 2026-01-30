# 内容包 Manifest 规范（pack.json）

本规范定义内容包的**最小、可校验、可扩展**的 Manifest 结构，用于在**不扫描目录**的前提下完成内容加载与质量门禁。
本阶段仅设计规范与最小落地路径，不要求引入热更新与工具链。

## 目标

- 明确内容包版本、依赖与适配范围。
- 明确内容文件清单（按类型显式列出，禁止目录扫描）。
- 提供统一的硬门禁规则（版本、i18n、路径、安全、引用一致性）。

## 文件位置（建议）

- 内容包索引：`res://Data/packs/_index.json`
- 内容包目录：`res://Data/packs/<pack_id>/`
- 内容包清单：`res://Data/packs/<pack_id>/pack.json`

> 说明：索引文件用于**显式列出可加载的包**，避免扫描目录。

## pack.json（字段定义）

顶层字段（必填）：
- `schemaVersion`：整数，固定为 `1`。
- `version`：整数，内容包版本（>=1）。
- `packId`：字符串，`^[a-z0-9_]{1,32}$`。
- `nameKey`：i18n key（需同时存在于 zh/en）。
- `descriptionKey`：i18n key（需同时存在于 zh/en）。
- `enabledByDefault`：布尔，默认是否启用。
- `compatibility`：对象，适配范围（见下）。
- `content`：对象，内容文件清单（见下）。

可选字段：
- `dependencies`：数组，包依赖（见下）。
- `tags`：字符串数组，用于筛选与调试（例如 `["core","t2"]`）。

`compatibility`：
- `minGameVersion`：字符串（例如 `"0.2.0"`）。
- `maxGameVersion`：字符串或 `null`（上限可空）。

`dependencies[]`：
- `packId`：字符串（依赖包 id）。
- `minVersion`：整数（依赖包最低版本）。

`content`：
> 每个类型必须为**数组**，可为空；**必须显式列出文件路径**。
- `maps`：`res://.../_index.json`
- `characters`：`res://.../characters.json`
- `events`：`res://.../random_events.json`
- `cards`：`res://.../action_cards.json`
- `buildings`：`res://.../buildings.json`
- `relics`：`res://.../relics.json`
- `regions`：`res://.../regions.json`
- `facilities`：`res://.../facilities.json`
- `i18n`：对象，必须包含 `zh-CN` 与 `en-US` 两个键
  - `zh-CN`：`res://.../zh_cn.json`
  - `en-US`：`res://.../en_us.json`

## 规范化与安全要求（硬门禁）

- **路径安全**：所有路径必须以 `res://Data/packs/<pack_id>/` 开头；禁止 `..` 与 `%2e` 绕过。
- **版本门禁**：`pack.json` 和所有内容文件必须包含 `version`；变更时必须递增。
- **i18n 完整性**：`nameKey/descriptionKey` 必须同时存在于 `zh-CN` 与 `en-US`。
- **ID 规范**：所有 id 使用 `^[a-z0-9_]{1,32}$`，且在各自表内唯一。
- **引用一致性**：跨表引用（例如 map→region/building/facility/eventPool）必须存在。
- **effectKind 白名单**：仅允许当前阶段白名单（与 Core/ADR-0004 对齐）。
- **资源安全**：asset 必须位于 `res://Assets/`，扩展名白名单与大小上限保持不变（ADR-0019）。

## 加载顺序（建议）

1. 读取 `res://Data/packs/_index.json` 获取启用包列表（按 `order` 排序）。
2. 依次加载每个 `pack.json` 并校验 `compatibility/dependencies`。
3. 按 `content` 中的显式文件列表加载内容。
4. 发现冲突（同类 ID 重复）即失败并阻止开始。

## 示例（最小包）

```json
{
  "schemaVersion": 1,
  "version": 1,
  "packId": "core_t2",
  "nameKey": "pack.core_t2.name",
  "descriptionKey": "pack.core_t2.desc",
  "enabledByDefault": true,
  "compatibility": { "minGameVersion": "0.2.0", "maxGameVersion": null },
  "dependencies": [],
  "tags": ["core","t2"],
  "content": {
    "maps": ["res://Data/packs/core_t2/maps/_index.json"],
    "characters": ["res://Data/packs/core_t2/characters.json"],
    "events": ["res://Data/packs/core_t2/random_events.json"],
    "cards": ["res://Data/packs/core_t2/action_cards.json"],
    "buildings": ["res://Data/packs/core_t2/buildings.json"],
    "relics": ["res://Data/packs/core_t2/relics.json"],
    "regions": ["res://Data/packs/core_t2/regions.json"],
    "facilities": ["res://Data/packs/core_t2/facilities.json"],
    "i18n": {
      "zh-CN": "res://Data/packs/core_t2/i18n/zh_cn.json",
      "en-US": "res://Data/packs/core_t2/i18n/en_us.json"
    }
  }
}
```

## 引用与口径

- ADR-0004：事件命名与契约口径（CloudEvents-like type）。
- ADR-0005：质量门禁与 CI 约束（硬门禁）。
- ADR-0019：资源与路径安全基线。
