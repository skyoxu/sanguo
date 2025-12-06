namespace Game.Core.Domain;

/// <summary>
/// Simple stack-based inventory keyed by item id.
/// </summary>
public class Inventory
{
    private readonly Dictionary<string, int> _items = new();

    public IReadOnlyDictionary<string, int> Items => _items;

    public int CountItem(string id) => _items.TryGetValue(id, out var c) ? c : 0;
    public bool HasItem(string id, int atLeast = 1) => CountItem(id) >= atLeast;

    /// <summary>
    /// Adds up to <paramref name="count"/> items, capping at <paramref name="maxStack"/> per id.
    /// Returns actual added.
    /// </summary>
    public int Add(string id, int count = 1, int maxStack = 99)
    {
        if (count <= 0) return 0;
        _items.TryGetValue(id, out var existing);
        var canAdd = Math.Max(0, maxStack - existing);
        var added = Math.Min(canAdd, count);
        if (added > 0) _items[id] = existing + added;
        return added;
    }

    /// <summary>
    /// Removes up to <paramref name="count"/> items.
    /// Returns actual removed.
    /// </summary>
    public int Remove(string id, int count = 1)
    {
        if (count <= 0) return 0;
        if (!_items.TryGetValue(id, out var existing) || existing <= 0) return 0;
        var removed = Math.Min(existing, count);
        var left = existing - removed;
        if (left > 0) _items[id] = left; else _items.Remove(id);
        return removed;
    }
}

