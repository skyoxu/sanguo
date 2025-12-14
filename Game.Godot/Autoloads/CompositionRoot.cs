using Game.Core.Ports;
using Game.Core.Services;
using System;
using System.Collections.Generic;
using Godot;
using Game.Godot.Scripts.Obs;

namespace Game.Godot.Autoloads;

/// <summary>
/// Composition root for adapter layer. Provides port implementations
/// backed by Godot APIs and wires global event bus/logging.
/// Configure this class as an Autoload (Singleton) in project.godot.
/// </summary>
public partial class CompositionRoot : Node
{
    public static CompositionRoot? Instance { get; private set; }

    public ITime Time { get; private set; } = default!;
    public IInput Input { get; private set; } = default!;
    public IResourceLoader ResourceLoader { get; private set; } = default!;
    public IDataStore DataStore { get; private set; } = default!;
    public ILogger Logger { get; private set; } = default!;
    public IErrorReporter ErrorReporter { get; private set; } = default!;
    public IEventBus EventBus { get; private set; } = default!;

    private bool _initialized;

    public override void _EnterTree()
    {
        Instance = this;
    }

    public override void _Ready()
    {
        if (_initialized) return;
        InitializePorts();
        _initialized = true;
    }

    private void InitializePorts()
    {
        // Bind required Autoload singletons (configured in project.godot).
        var time = RequireAutoload<Adapters.TimeAdapter>("/root/Time", "Time");
        var input = RequireAutoload<Adapters.InputAdapter>("/root/Input", "Input");
        var store = RequireAutoload<Adapters.DataStoreAdapter>("/root/DataStore", "DataStore");
        var logger = RequireAutoload<Adapters.LoggerAdapter>("/root/Logger", "Logger");
        var bus = RequireAutoload<Adapters.EventBusAdapter>("/root/EventBus", "EventBus");
        var sentry = RequireAutoload<SentryClient>("/root/SentryClient", "SentryClient");

        // Ports not configured as Autoloads to avoid global-name collisions (e.g., ResourceLoader).
        var loader = new Adapters.ResourceLoaderAdapter { Name = "ResourceLoaderPort" };
        var reporter = new Adapters.ErrorReporterAdapter { Name = "ErrorReporter", Sentry = sentry };
        AddChild(loader);
        AddChild(reporter);

        Time = time;
        Input = input;
        ResourceLoader = loader;
        DataStore = store;
        Logger = logger;
        ErrorReporter = reporter;
        EventBus = bus;

        bus.Logger = logger;
        bus.ErrorReporter = reporter;
    }

    private T RequireAutoload<T>(NodePath path, string name) where T : Node
    {
        var node = GetNodeOrNull<T>(path);
        if (node is null)
            FailFast($"Required autoload '{name}' not found.", path.ToString());
        return node!;
    }

    private void FailFast(string reason, string? path = null)
    {
        var msg = path is null ? reason : $"{reason} path={path}";
        GD.PushError($"[CompositionRoot] {msg}");
        try
        {
            var ctx = new Dictionary<string, object>
            {
                ["reason"] = reason,
                ["path"] = path ?? string.Empty,
            };
            GetNodeOrNull<SentryClient>("/root/SentryClient")?.CaptureException("composition_root.fail_fast", ctx);
        }
        catch
        {
        }
        throw new InvalidOperationException(msg);
    }

    // Expose a simple status map for GDScript without accessing C# properties directly
    public global::Godot.Collections.Dictionary PortsStatus()
    {
        var d = new global::Godot.Collections.Dictionary
        {
            { "time", Time != null },
            { "input", Input != null },
            { "resourceLoader", ResourceLoader != null },
            { "dataStore", DataStore != null },
            { "logger", Logger != null },
            { "errorReporter", ErrorReporter != null },
            { "eventBus", EventBus != null },
        };
        return d;
    }
}
