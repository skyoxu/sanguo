using System.Threading.Tasks;
using Godot;
using Game.Core.Ports;
using Game.Godot.Scripts.Security;

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
        var path = PathFor(key);
        SecurityFileAdapter.TryWriteText(path, json, caller: nameof(DataStoreAdapter), out _);
        return Task.CompletedTask;
    }

    public Task<string?> LoadAsync(string key)
    {
        var path = PathFor(key);
        if (!SecurityFileAdapter.TryReadText(path, caller: nameof(DataStoreAdapter), out var text, out _))
        {
            return Task.FromResult<string?>(null);
        }

        return Task.FromResult<string?>(text);
    }

    public Task DeleteAsync(string key)
    {
        var path = PathFor(key);
        SecurityFileAdapter.TryDeleteFile(path, caller: nameof(DataStoreAdapter), out _);
        return Task.CompletedTask;
    }

    // Synchronous helpers for GDScript tests
    public void SaveSync(string key, string json) => SaveAsync(key, json).Wait();
    public string? LoadSync(string key) => LoadAsync(key).Result;
    public void DeleteSync(string key) => DeleteAsync(key).Wait();
}
