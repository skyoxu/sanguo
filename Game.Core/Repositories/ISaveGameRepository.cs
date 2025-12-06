using System.Collections.Generic;
using System.Threading.Tasks;
using Game.Core.Domain.Entities;

namespace Game.Core.Repositories;

public interface ISaveGameRepository
{
    Task UpsertAsync(SaveGame save);
    Task<SaveGame?> GetAsync(string userId, int slot);
    Task<List<SaveGame>> ListByUserAsync(string userId);
}

