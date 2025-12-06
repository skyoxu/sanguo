---
title: 05 data models and storage ports v2 (Godot + C#)
status: base-SSoT
adr_refs: [ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0006, ADR-0023]
placeholders: unknown-app, Unknown Product, gamedev, ${ENTITY_A}, ${ENTITY_B}, ${AGGREGATE_A}, production, dev, 0.0.0
derived_from: 05-data-models-and-storage-ports-v2.godot.md
last_adjusted: 2025-11-17
---

## C4：数据模型与存储端口（Godot 变体）

> 本章是数据模型与存储端口的 **SSoT**，以 Godot 4.5 + C# 为基线，解释领域聚合、仓储端口、SQLite/ConfigFile 的分工。运行时视图与状态机见 CH06，安全与质量门禁见 ADR‑0002/0005/0006/0023。

```mermaid
C4Container
title Data Ports & Adapters (Godot 4.5 + C#)
Person(user, "玩家")
System_Boundary(godot, "unknown-app (Godot)") {
  Container(core, "Game.Core", "C# Class Library", "领域模型 + 服务")
  Container(ports, "Storage Ports", "Interfaces", "IDataStore/ISaveGameRepository/...")
  Container(adapters, "Db/Config Adapters", "C# + Godot", "SqliteDataStore / ConfigFile / Repositories")
}
Rel(user, core, "通过 UI 间接使用")
Rel(core, ports, "依赖端口")
Rel(ports, adapters, "由适配器实现")
```

> 目标：在 **端口-适配器（Hexagonal）** 思路下，清晰区分领域模型、存储端口与适配器，让 Game.Core 保持“不依赖 Godot 引擎”，同时又能通过 Db/Config 适配层持久化数据。

---

## 1) 存储端口契约（Game.Core）

> 端口接口放置在 Game.Core/Ports，不依赖 Godot 类型，便于 xUnit 单元测试与覆盖率门禁（见 6.2）。

```csharp
// Game.Core/Ports/IDataStore.cs
namespace Game.Core.Ports;

public interface IDataStore
{
    bool TryOpen(string logicalPath);
    void Close();
    int Execute(string sql, params object[] args);
    IReadOnlyList<IReadOnlyDictionary<string, object?>> Query(string sql, params object[] args);
    string? LastError { get; }
}

// Game.Core/Ports/ISaveGameRepository.cs
namespace Game.Core.Ports;

public interface ISaveGameRepository
{
    Task UpsertAsync(SaveGame save, CancellationToken ct = default);
    Task<SaveGame?> FindBySlotAsync(string userId, int slot, CancellationToken ct = default);
}

// Game.Core/Ports/IInventoryRepository.cs
namespace Game.Core.Ports;

public interface IInventoryRepository
{
    Task ReplaceAllAsync(string userId, IReadOnlyCollection<InventoryItem> items, CancellationToken ct = default);
    Task<IReadOnlyCollection<InventoryItem>> GetAllAsync(string userId, CancellationToken ct = default);
}
```

> Settings 不通过 DB 端口暴露，而是走 ConfigFile（见 ADR‑0023）。领域层只关心“当前设置”的值，不关心它来自哪个介质。

---

## 2) 数据模型与聚合（示例）

```csharp
// Game.Core/Domain/SaveGame.cs
namespace Game.Core.Domain;

public sealed class SaveGame
{
    public string UserId { get; }
    public int Slot { get; }
    public byte[] Blob { get; }
    public DateTimeOffset UpdatedAt { get; }

    public SaveGame(string userId, int slot, byte[] blob, DateTimeOffset updatedAt)
    {
        UserId = userId;
        Slot = slot;
        Blob = blob;
        UpdatedAt = updatedAt;
    }
}

// Game.Core/Domain/InventoryItem.cs
namespace Game.Core.Domain;

public sealed class InventoryItem
{
    public string UserId { get; }
    public string ItemId { get; }
    public int Quantity { get; }

    public InventoryItem(string userId, string itemId, int quantity)
    {
        UserId = userId;
        ItemId = itemId;
        Quantity = quantity;
    }
}
```

> 聚合与值对象只依赖 .NET 标准库；Godot 相关 API 仅出现在 Adapters/Scenes 层，符合“Contracts 不依赖引擎”的约束（见 AGENTS 6.7）。

---

## 3) SQLite 适配层（Game.Godot/Adapters/Db）

> 适配层为 Game.Core 提供 IDataStore 等端口的具体实现，统一处理路径、安全与事务逻辑。

```csharp
// Game.Godot/Adapters/SqliteDataStore.cs
using System;
using System.Collections.Generic;
using Game.Core.Ports;
using Microsoft.Data.Sqlite;

namespace Game.Godot.Adapters;

public sealed class SqliteDataStore : Node, IDataStore
{
    private SqliteConnection? _connection;
    public string? LastError { get; private set; }

    public bool TryOpen(string logicalPath)
    {
        LastError = null;
        var normalized = DbPathNormalizer.NormalizeUserPath(logicalPath);
        if (normalized == null)
        {
            LastError = "Path not allowed";
            DbAudit.LogOpenFail(logicalPath, LastError);
            return false;
        }

        try
        {
            _connection = new SqliteConnection($"Data Source={normalized}");
            _connection.Open();
            DbPragmas.ApplyDefaultPragmas(_connection);
            return true;
        }
        catch (Exception ex)
        {
            LastError = ex.Message;
            DbAudit.LogOpenFail(normalized, LastError);
            _connection = null;
            return false;
        }
    }

    public void Close()
    {
        _connection?.Dispose();
        _connection = null;
    }

    public int Execute(string sql, params object[] args)
    {
        // ... 省略：使用参数化命令并记录失败审计
    }

    public IReadOnlyList<IReadOnlyDictionary<string, object?>> Query(string sql, params object[] args)
    {
        // ... 省略：使用 reader 填充行数据
    }
}
```

> 具体 SqliteDataStore 实现细节在代码中；本章只规定“必须统一走 IDataStore 端口，并在适配层集中处理安全与日志”。

---

## 4) Settings：ConfigFile 作为 SSoT

> 参见 ADR‑0023。本节只给出端口层面的结论，不在 Base 文档复制所有细节。

- Settings 的持久化 SSoT：`ConfigFile`（`user://settings.cfg`）；
- DB 中的 `settings` 表为历史兼容保留，不作为权威来源；
- SettingsPanel 在 Godot 运行时：
  - Save：收集 UI 控件值 → 写 ConfigFile → 即时应用音量/语言等；
  - Load：优先从 ConfigFile 读；如首次运行且 ConfigFile 不存在，则尝试从 DB 读一次，再写入 ConfigFile；
- 相关实现由 Game.Godot/Scripts/UI/SettingsPanel.cs 与 UI 测试负责，本章不展开。

---

## 5) Test-Refs（端口与存储）

- 领域与端口：
  - Game.Core/Ports/IDataStore.cs
  - Game.Core/Ports/ISaveGameRepository.cs
  - Game.Core/Ports/IInventoryRepository.cs
- Adapters/Db：
  - Game.Godot/Adapters/SqliteDataStore.cs
  - Game.Godot/Adapters/Db/DbTestHelper.cs
- Tests.Godot：
  - Tests.Godot/tests/Adapters/Db/test_db_path_security.gd
  - Tests.Godot/tests/Adapters/Db/test_db_persistence_cross_restart.gd
  - Tests.Godot/tests/Adapters/Db/test_savegame_persistence_cross_restart.gd
  - Tests.Godot/tests/Adapters/Db/test_inventory_persistence_cross_restart.gd
- Settings（ConfigFile）：
  - Tests.Godot/tests/UI/test_settings_panel_logic.gd
  - Tests.Godot/tests/UI/test_settings_locale_persist.gd

