using System;
using System.Text.Json;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Game.Core.Repositories;
using Game.Core.Ports;

namespace Game.Godot.Adapters.Db;

public class SqlInventoryRepository : IInventoryRepository
{
    private readonly ISqlDatabase _db;
    private const string UserId = "default";
    private const int Slot = 90; // transitional snapshot slot

    public SqlInventoryRepository(ISqlDatabase db) => _db = db;

    public Task<InventoryItem> AddAsync(string itemId, int qty)
    {
        EnsureMigratedFromSnapshot();
        var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        // Upsert into dedicated table
        var current = GetQty(itemId);
        var next = current + Math.Max(0, qty);
        _db.Execute("INSERT INTO inventory_items(user_id,item_id,qty,updated_at) VALUES(@0,@1,@2,@3) " +
                    "ON CONFLICT(user_id,item_id) DO UPDATE SET qty=@2, updated_at=@3;",
            UserId, itemId, next, now);
        return Task.FromResult(new InventoryItem(itemId, next));
    }

    public Task<InventoryItem?> GetAsync(string itemId)
    {
        EnsureMigratedFromSnapshot();
        var qty = GetQty(itemId);
        if (qty <= 0) return Task.FromResult<InventoryItem?>(null);
        return Task.FromResult<InventoryItem?>(new InventoryItem(itemId, qty));
    }

    public Task<IReadOnlyList<InventoryItem>> AllAsync()
    {
        EnsureMigratedFromSnapshot();
        var rows = _db.Query("SELECT item_id, qty FROM inventory_items WHERE user_id=@0 ORDER BY item_id;", UserId);
        var list = rows.Select(r => new InventoryItem(r["item_id"]?.ToString() ?? string.Empty, Convert.ToInt32(r["qty"] ?? 0))).ToList();
        return Task.FromResult<IReadOnlyList<InventoryItem>>(list);
    }
    
    // Non-interface convenience: replace entire snapshot for current user
    public Task ReplaceAllAsync(Dictionary<string,int> items)
    {
        EnsureMigratedFromSnapshot();
        _db.BeginTransaction();
        try
        {
            _db.Execute("DELETE FROM inventory_items WHERE user_id=@0;", UserId);
            var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            foreach (var kv in items)
            {
                _db.Execute("INSERT INTO inventory_items(user_id,item_id,qty,updated_at) VALUES(@0,@1,@2,@3);",
                    UserId, kv.Key, Math.Max(0, kv.Value), now);
                // Test-only: allow simulating an error to verify rollback
                if ((System.Environment.GetEnvironmentVariable("DB_SIMULATE_REPLACEALL_ERROR") ?? "0") == "1")
                    throw new InvalidOperationException("Simulated ReplaceAll error");
            }
            _db.CommitTransaction();
        }
        catch
        {
            _db.RollbackTransaction();
            throw;
        }
        return Task.CompletedTask;
    }
    
    private int GetQty(string itemId)
    {
        var rows = _db.Query("SELECT qty FROM inventory_items WHERE user_id=@0 AND item_id=@1;", UserId, itemId);
        if (rows.Count == 0) return 0;
        return Convert.ToInt32(rows[0]["qty"] ?? 0);
    }

    private void EnsureMigratedFromSnapshot()
    {
        // If dedicated table empty but snapshot exists, migrate
        var countRows = _db.Query("SELECT COUNT(1) AS cnt FROM inventory_items WHERE user_id=@0;", UserId);
        var cnt = countRows.Count > 0 ? Convert.ToInt32(countRows[0]["cnt"] ?? 0) : 0;
        if (cnt > 0) return;
        var rows = _db.Query("SELECT data FROM saves WHERE user_id=@0 AND slot_number=@1 LIMIT 1;", UserId, Slot);
        if (rows.Count == 0) return;
        var json = rows[0]["data"]?.ToString() ?? string.Empty;
        if (string.IsNullOrWhiteSpace(json)) return;
        try
        {
            var doc = JsonDocument.Parse(json);
            if (!doc.RootElement.TryGetProperty("items", out var items)) return;
            var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            foreach (var prop in items.EnumerateObject())
            {
                var itemId = prop.Name;
                var qty = prop.Value.GetInt32();
                _db.Execute("INSERT INTO inventory_items(user_id,item_id,qty,updated_at) VALUES(@0,@1,@2,@3) " +
                            "ON CONFLICT(user_id,item_id) DO UPDATE SET qty=@2, updated_at=@3;",
                    UserId, itemId, qty, now);
            }
        }
        catch { }
    }
}
