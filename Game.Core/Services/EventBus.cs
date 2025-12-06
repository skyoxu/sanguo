using Game.Core.Contracts;

namespace Game.Core.Services;

public interface IEventBus
{
    Task PublishAsync(DomainEvent evt);
    IDisposable Subscribe(Func<DomainEvent, Task> handler);
}

public class InMemoryEventBus : IEventBus
{
    private readonly List<Func<DomainEvent, Task>> _handlers = new();
    private readonly object _gate = new();

    public Task PublishAsync(DomainEvent evt)
    {
        List<Func<DomainEvent, Task>> snapshot;
        lock (_gate) snapshot = _handlers.ToList();
        return Task.WhenAll(snapshot.Select(h => SafeInvoke(h, evt)));
    }

    private static async Task SafeInvoke(Func<DomainEvent, Task> h, DomainEvent evt)
    {
        try { await h(evt); }
        catch { /* swallow to keep bus stable */ }
    }

    public IDisposable Subscribe(Func<DomainEvent, Task> handler)
    {
        lock (_gate) _handlers.Add(handler);
        return new Unsubscriber(_handlers, handler, _gate);
    }

    private sealed class Unsubscriber : IDisposable
    {
        private readonly List<Func<DomainEvent, Task>> _list;
        private readonly Func<DomainEvent, Task> _handler;
        private readonly object _gate;
        private bool _disposed;

        public Unsubscriber(List<Func<DomainEvent, Task>> list, Func<DomainEvent, Task> handler, object gate)
        { _list = list; _handler = handler; _gate = gate; }

        public void Dispose()
        {
            if (_disposed) return;
            lock (_gate) _list.Remove(_handler);
            _disposed = true;
        }
    }
}

