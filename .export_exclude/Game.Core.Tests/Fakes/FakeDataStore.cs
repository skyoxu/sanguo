using System.Collections.Concurrent;
using Game.Core.Ports;

namespace Game.Core.Tests.Fakes;

public class FakeDataStore : IDataStore
{
    private readonly ConcurrentDictionary<string, string> _store = new();

    public Task SaveAsync(string key, string json)
    {
        _store[key] = json;
        return Task.CompletedTask;
    }

    public Task<string?> LoadAsync(string key)
    {
        _store.TryGetValue(key, out var value);
        return Task.FromResult<string?>(value);
    }

    // Test helper
    public string? Peek(string key)
        => _store.TryGetValue(key, out var v) ? v : null;

    public Task DeleteAsync(string key)
    {
        _store.TryRemove(key, out _);
        return Task.CompletedTask;
    }
}
