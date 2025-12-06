using System;
using System.Threading.Tasks;
using Game.Core.Domain.Entities;
using Game.Core.Ports;
using Game.Core.Repositories;
using Godot;

namespace Game.Godot.Adapters.Db;

public partial class RepositoryTestBridge : Node
{
    private ISqlDatabase GetDb()
    {
        var db = GetNodeOrNull<SqliteDataStore>("/root/SqlDb");
        if (db == null)
            throw new InvalidOperationException("SqlDb autoload not found");
        return db;
    }

    public bool UpsertUser(string username)
    {
        var repo = new UserRepository(GetDb());
        var u = new User { Username = username, CreatedAt = DateTimeOffset.UtcNow.ToUnixTimeSeconds() };
        repo.UpsertAsync(u).GetAwaiter().GetResult();
        return true;
    }

    public string? FindUser(string username)
    {
        var repo = new UserRepository(GetDb());
        var u = repo.FindByUsernameAsync(username).GetAwaiter().GetResult();
        return u?.Username;
    }

    public string? FindUserId(string username)
    {
        var rows = GetDb().Query("SELECT id FROM users WHERE username=@0 LIMIT 1;", username);
        if (rows.Count == 0) return null;
        return rows[0]["id"]?.ToString();
    }

    public bool UpsertSave(string userId, int slot, string data)
    {
        var repo = new SaveGameRepository(GetDb());
        var save = new SaveGame { UserId = userId, SlotNumber = slot, Data = data };
        repo.UpsertAsync(save).GetAwaiter().GetResult();
        return true;
    }

    public bool TryUpsertSave(string userId, int slot, string data)
    {
        try
        {
            var repo = new SaveGameRepository(GetDb());
            var save = new SaveGame { UserId = userId, SlotNumber = slot, Data = data };
            repo.UpsertAsync(save).GetAwaiter().GetResult();
            return true;
        }
        catch
        {
            return false;
        }
    }

    public string? GetSaveData(string userId, int slot)
    {
        var repo = new SaveGameRepository(GetDb());
        var s = repo.GetAsync(userId, slot).GetAwaiter().GetResult();
        return s?.Data;
    }

    public string[] ListSaveJsonByUser(string userId)
    {
        var repo = new SaveGameRepository(GetDb());
        var list = repo.ListByUserAsync(userId).GetAwaiter().GetResult();
        return list.ConvertAll(s => s.Data ?? string.Empty).ToArray();
    }
}
