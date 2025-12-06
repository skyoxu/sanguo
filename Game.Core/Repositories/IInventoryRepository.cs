using Game.Core.Domain;

namespace Game.Core.Repositories;

public interface IInventoryRepository
{
    Task<InventoryItem> AddAsync(string itemId, int qty);
    Task<InventoryItem?> GetAsync(string itemId);
    Task<IReadOnlyList<InventoryItem>> AllAsync();
}

public record InventoryItem(string ItemId, int Qty);

