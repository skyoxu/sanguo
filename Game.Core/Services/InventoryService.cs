using Game.Core.Domain;

namespace Game.Core.Services;

public class InventoryService
{
    private readonly Inventory _inventory;
    private readonly int _maxSlots;

    public InventoryService(Inventory inventory, int maxSlots = 30)
    {
        _inventory = inventory;
        _maxSlots = maxSlots;
    }

    public int CountDistinct() => _inventory.Items.Count;
    public int CountItem(string id) => _inventory.CountItem(id);
    public bool HasItem(string id, int atLeast = 1) => _inventory.HasItem(id, atLeast);

    /// <summary>
    /// Adds item stacks subject to distinct slot capacity.
    /// Returns actual added count.
    /// </summary>
    public int Add(string id, int count = 1, int maxStack = 99)
    {
        var isNew = !_inventory.Items.ContainsKey(id);
        if (isNew && CountDistinct() >= _maxSlots) return 0;
        return _inventory.Add(id, count, maxStack);
    }

    public int Remove(string id, int count = 1) => _inventory.Remove(id, count);
}
