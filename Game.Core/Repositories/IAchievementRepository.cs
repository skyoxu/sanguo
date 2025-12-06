using System.Collections.Generic;
using System.Threading.Tasks;
using Game.Core.Domain.Entities;

namespace Game.Core.Repositories;

public interface IAchievementRepository
{
    Task UnlockAsync(Achievement achievement);
    Task<bool> HasAsync(string userId, string key);
    Task<List<Achievement>> ListByUserAsync(string userId);
}

