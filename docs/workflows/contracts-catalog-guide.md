# Contracts Catalog（契约目录）生成与使用指南

本模板允许用脚本生成一份“契约目录（Contracts Catalog）”，用于在开工前快速对齐以下几件事：

- 当前仓库 `Game.Core/Contracts/**` 中已落盘的 `EventType`（领域事件稳定标识）
- 任务视图（`.taskmaster/tasks/*.json`）中声明的 `contractRefs[]`
- Overlay（`docs/architecture/overlays/<PRD-ID>/08/**`）对契约文件的引用路径

重要：**契约的单一事实源（SSoT）永远是 `Game.Core/Contracts/**`。**  
契约目录是脚本生成的“对齐视图/审计材料”，推荐输出到 `logs/ci/<YYYY-MM-DD>/`，默认不入库。

## 推荐用法（Windows）

1) 生成契约目录（默认输出到 `logs/ci/<date>/contracts-catalog/`）：

```powershell
py -3 scripts/python/generate_contracts_catalog.py --prd-id <PRD-ID>
```

2) 仅检查契约命名与 `EventType` 规范（不生成目录也可）：

```powershell
py -3 scripts/python/check_domain_contracts.py
```

3) 校验 Overlay ↔ Contracts 回链（门禁脚本）：

```powershell
py -3 scripts/python/validate_contracts.py
```

## 生成产物与版本控制规则

- 生成产物默认写入 `logs/ci/<YYYY-MM-DD>/...`，作为 CI/本地审计证据。
- 如果你确实希望把“某个 PRD 的契约目录”放进 `docs/` 供团队查阅：
  - 建议写入 `docs/workflows/generated/`（默认被 `.gitignore` 忽略）。
  - 不建议把带业务项目名/事件列表的目录文档作为模板仓的长期文档入口，以免误导后续新项目。

