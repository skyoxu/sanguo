using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using Godot;
using Game.Core.Contracts;
using Game.Core.Ports;
using Game.Core.Services;

namespace Game.Godot.Adapters;

public partial class EventBusAdapter : Node, IEventBus
{
    [Signal]
    public delegate void DomainEventEmittedEventHandler(string type, string source, string dataJson, string id, string specVersion, string dataContentType, string timestampIso);

    private readonly List<Func<DomainEvent, Task>> _handlers = new();
    private readonly object _gate = new();
    private static readonly JsonSerializerOptions JsonSerializeOptions = new()
    {
        MaxDepth = 32,
    };

    public ILogger? Logger { get; set; }
    public IErrorReporter? ErrorReporter { get; set; }

    public Task PublishAsync(DomainEvent evt)
    {
        // Emit Godot signal for scene-level listeners
        var dataJson = evt.Data switch
        {
            null => "{}",
            RawJsonEventData raw => string.IsNullOrWhiteSpace(raw.Json) ? "{}" : raw.Json,
            JsonElementEventData element => element.Value.ValueKind == JsonValueKind.Undefined ? "{}" : element.Value.GetRawText(),
            _ => JsonSerializer.Serialize(evt.Data, JsonSerializeOptions),
        };
        EmitSignal(SignalName.DomainEventEmitted, evt.Type, evt.Source, dataJson, evt.Id, evt.SpecVersion, evt.DataContentType, evt.Timestamp.ToString("o"));

        // Notify in-process subscribers
        List<Func<DomainEvent, Task>> snapshot;
        lock (_gate) snapshot = _handlers.ToList();
        return Task.WhenAll(snapshot.Select(h => SafeInvoke(h, evt)));
    }

    private async Task SafeInvoke(Func<DomainEvent, Task> h, DomainEvent evt)
    {
        try
        {
            await h(evt);
        }
        catch (Exception ex)
        {
            try
            {
                Logger?.Error($"EventBusAdapter handler failed (type={evt.Type} source={evt.Source} id={evt.Id})", ex);
            }
            catch { }

            try
            {
                var ctx = new Dictionary<string, string>
                {
                    ["event_type"] = evt.Type,
                    ["event_source"] = evt.Source,
                    ["event_id"] = evt.Id,
                    ["handler"] = h.Method.Name,
                    ["handler_type"] = h.Method.DeclaringType?.FullName ?? "unknown",
                };
                ErrorReporter?.CaptureException("eventbus.adapter.handler.exception", ex, ctx);
            }
            catch { }
        }
    }

    public IDisposable Subscribe(Func<DomainEvent, Task> handler)
    {
        lock (_gate) _handlers.Add(handler);
        return new Unsubscriber(_handlers, handler, _gate);
    }

    // Simple publish for GDScript tests without needing DomainEvent construction
    public void PublishSimple(string type, string source, string data_json)
    {
        var evt = new DomainEvent(type, source, new RawJsonEventData(data_json), DateTime.UtcNow, Guid.NewGuid().ToString("N"));
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
