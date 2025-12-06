using Godot;
using Game.Godot.Adapters;
using Game.Godot.Adapters.Db;
using System.Collections.Generic;
using System;
using System.Text.Json;

namespace Game.Godot.Scripts.UI;

public partial class InventoryPanel : Control
{
    private ItemList _list = default!;
    private Button _btnAdd = default!;
    private Button _btnRemove = default!;
    private Button _btnSave = default!;
    private Button _btnLoad = default!;

    private const string SaveKey = "ui_inventory";
    [Export] public bool UseRepository { get; set; } = true;

    public override void _Ready()
    {
        _list = GetNode<ItemList>("VBox/Items");
        _btnAdd = GetNode<Button>("VBox/Buttons/AddBtn");
        _btnRemove = GetNode<Button>("VBox/Buttons/RemoveBtn");
        _btnSave = GetNode<Button>("VBox/Buttons/SaveBtn");
        _btnLoad = GetNode<Button>("VBox/Buttons/LoadBtn");

        _btnAdd.Pressed += OnAdd;
        _btnRemove.Pressed += OnRemove;
        _btnSave.Pressed += OnSave;
        _btnLoad.Pressed += OnLoad;
    }

    private void OnAdd()
    {
        var name = $"Item_{Time.GetUnixTimeFromSystem()}";
        _list.AddItem(name);
    }

    private void OnRemove()
    {
        var sel = _list.GetSelectedItems();
        foreach (int i in sel)
            _list.RemoveItem(i);
    }

    private void OnSave()
    {
        // Build counts
        var counts = new Dictionary<string,int>();
        for (int i = 0; i < _list.ItemCount; i++)
        {
            var name = _list.GetItemText(i);
            counts.TryGetValue(name, out var c);
            counts[name] = c + 1;
        }
        if (UseRepository)
        {
            var db = GetNodeOrNull<SqliteDataStore>("/root/SqlDb");
            if (db != null)
            {
                var repo = new SqlInventoryRepository(db);
                repo.ReplaceAllAsync(counts).GetAwaiter().GetResult();
                return;
            }
        }
        // Fallback to DataStore JSON
        var json = JsonSerializer.Serialize(new { items = counts });
        GetNodeOrNull<DataStoreAdapter>("/root/DataStore")?.SaveSync(SaveKey, json);
    }

    private void OnLoad()
    {
        _list.Clear();
        if (UseRepository)
        {
            var db = GetNodeOrNull<SqliteDataStore>("/root/SqlDb");
            if (db != null)
            {
                var repo = new SqlInventoryRepository(db);
                var list = repo.AllAsync().GetAwaiter().GetResult();
                foreach (var it in list)
                {
                    for (int i = 0; i < it.Qty; i++) _list.AddItem(it.ItemId);
                }
                return;
            }
        }
        // Fallback to DataStore JSON array (legacy)
        var ds = GetNodeOrNull<DataStoreAdapter>("/root/DataStore");
        var json = ds?.LoadSync(SaveKey);
        if (string.IsNullOrEmpty(json)) return;
        try
        {
            var doc = JsonDocument.Parse(json!);
            if (doc.RootElement.TryGetProperty("items", out var obj))
            {
                foreach (var prop in obj.EnumerateObject())
                {
                    var name = prop.Name;
                    var qty = prop.Value.GetInt32();
                    for (int i = 0; i < qty; i++) _list.AddItem(name);
                }
                return;
            }
            if (doc.RootElement.ValueKind == JsonValueKind.Array)
            {
                foreach (var el in doc.RootElement.EnumerateArray()) _list.AddItem(el.GetString() ?? "");
            }
        }
        catch (Exception ex)
        {
            GD.PushError($"Inventory load failed: {ex.Message}");
        }
    }
}

