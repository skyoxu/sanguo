using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Game.Core.Domain.Entities;
using Game.Core.Ports;
using Game.Core.Repositories;

namespace Game.Godot.Adapters.Db;

public class AchievementRepository : IAchievementRepository
{
    private readonly ISqlDatabase _db;
    public AchievementRepository(ISqlDatabase db) => _db = db;

    public Task UnlockAsync(Achievement achievement)
    {
        if (string.IsNullOrEmpty(achievement.Id)) achievement.Id = Guid.NewGuid().ToString();
        if (achievement.UnlockedAt == 0) achievement.UnlockedAt = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        _db.Execute("INSERT INTO achievements(id,user_id,achievement_key,unlocked_at,progress) VALUES(@0,@1,@2,@3,@4) ON CONFLICT(id) DO UPDATE SET progress=@4;",
            achievement.Id, achievement.UserId, achievement.AchievementKey, achievement.UnlockedAt, achievement.Progress);
        return Task.CompletedTask;
    }

    public Task<bool> HasAsync(string userId, string key)
    {
        var rows = _db.Query("SELECT 1 FROM achievements WHERE user_id=@0 AND achievement_key=@1 LIMIT 1;", userId, key);
        return Task.FromResult(rows.Count > 0);
    }

    public Task<List<Achievement>> ListByUserAsync(string userId)
    {
        var rows = _db.Query("SELECT id,user_id,achievement_key,unlocked_at,progress FROM achievements WHERE user_id=@0 ORDER BY unlocked_at DESC;", userId);
        var list = new List<Achievement>(rows.Count);
        foreach (var r in rows)
        {
            list.Add(new Achievement
            {
                Id = r["id"]?.ToString() ?? string.Empty,
                UserId = r["user_id"]?.ToString() ?? string.Empty,
                AchievementKey = r["achievement_key"]?.ToString() ?? string.Empty,
                UnlockedAt = Convert.ToInt64(r["unlocked_at"] ?? 0),
                Progress = Convert.ToDouble(r["progress"] ?? 0)
            });
        }
        return Task.FromResult(list);
    }
}

