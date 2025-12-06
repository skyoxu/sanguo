using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Godot;
using Game.Core.Contracts;
using Game.Core.Services;

namespace Game.Godot.Adapters;

public partial class EventBusAdapter : Node, IEventBus
{
    [Signal]
    public delegate void DomainEventEmittedEventHandler(string type, string source, string dataJson, string id, string specVersion, string dataContentType, string timestampIso);

    private readonly List<Func<DomainEvent, Task>> _handlers = new();
    private readonly object _gate = new();

    public Task PublishAsync(DomainEvent evt)
    {
        // Emit Godot signal for scene-level listeners
        var dataJson = evt.Data is string s ? (string.IsNullOrWhiteSpace(s) ? "{}" : s)
                                            : System.Text.Json.JsonSerializer.Serialize(evt.Data);
        EmitSignal(SignalName.DomainEventEmitted, evt.Type, evt.Source, dataJson, evt.Id, evt.SpecVersion, evt.DataContentType, evt.Timestamp.ToString("o"));

        // Notify in-process subscribers
        List<Func<DomainEvent, Task>> snapshot;
        lock (_gate) snapshot = _handlers.ToList();
        return Task.WhenAll(snapshot.Select(h => SafeInvoke(h, evt)));
    }

    private static async Task SafeInvoke(Func<DomainEvent, Task> h, DomainEvent evt)
    {
        try { await h(evt); }
        catch { /* ignore to keep bus stable */ }
    }

    public IDisposable Subscribe(Func<DomainEvent, Task> handler)
    {
        lock (_gate) _handlers.Add(handler);
        return new Unsubscriber(_handlers, handler, _gate);
    }

    // Simple publish for GDScript tests without needing DomainEvent construction
    public void PublishSimple(string type, string source, string data_json)
    {
        var evt = new DomainEvent(type, source, data_json, DateTime.UtcNow, Guid.NewGuid().ToString("N"));
        _ = PublishAsync(evt);
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
