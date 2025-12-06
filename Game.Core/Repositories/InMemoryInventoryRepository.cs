using Game.Core.Domain;

namespace Game.Core.Repositories;

public class InMemoryInventoryRepository : IInventoryRepository
{
    private readonly Dictionary<string, int> _items = new();

    public Task<InventoryItem> AddAsync(string itemId, int qty)
    {
        _items.TryGetValue(itemId, out var existing);
        var next = existing + qty;
        _items[itemId] = next;
        return Task.FromResult(new InventoryItem(itemId, next));
    }

    public Task<InventoryItem?> GetAsync(string itemId)
    {
        return Task.FromResult(_items.TryGetValue(itemId, out var qty) ? new InventoryItem(itemId, qty) : null);
    }

    public Task<IReadOnlyList<InventoryItem>> AllAsync()
    {
        var list = _items.Select(kv => new InventoryItem(kv.Key, kv.Value)).ToList();
        return Task.FromResult<IReadOnlyList<InventoryItem>>(list);
    }
}

