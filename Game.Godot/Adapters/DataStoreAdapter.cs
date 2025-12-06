using System.Threading.Tasks;
using Godot;
using Game.Core.Ports;

namespace Game.Godot.Adapters;

public partial class DataStoreAdapter : Node, IDataStore
{
    private static string MakeSafe(string key)
    {
        foreach (var c in System.IO.Path.GetInvalidFileNameChars())
            key = key.Replace(c, '_');
        return key;
    }

    private static string GetSavePath() => "user://saves";
    private static string PathFor(string key) => $"{GetSavePath()}/{MakeSafe(key)}.json";

    public Task SaveAsync(string key, string json)
    {
        DirAccess.MakeDirRecursiveAbsolute(GetSavePath());
        var path = PathFor(key);
        using var f = FileAccess.Open(path, FileAccess.ModeFlags.Write);
        if (f != null)
        {
            f.StoreString(json);
            f.Flush();
        }
        return Task.CompletedTask;
    }

    public Task<string?> LoadAsync(string key)
    {
        var path = PathFor(key);
        if (!FileAccess.FileExists(path))
            return Task.FromResult<string?>(null);
        using var f = FileAccess.Open(path, FileAccess.ModeFlags.Read);
        if (f == null) return Task.FromResult<string?>(null);
        return Task.FromResult<string?>(f.GetAsText());
    }

    public Task DeleteAsync(string key)
    {
        var path = PathFor(key);
        if (FileAccess.FileExists(path))
        {
            DirAccess.RemoveAbsolute(path);
        }
        return Task.CompletedTask;
    }

    // Synchronous helpers for GDScript tests
    public void SaveSync(string key, string json) => SaveAsync(key, json).Wait();
    public string? LoadSync(string key) => LoadAsync(key).Result;
    public void DeleteSync(string key) => DeleteAsync(key).Wait();
}
