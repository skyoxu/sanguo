using System;
using System.Collections.Generic;
using System.Text.Json;

namespace Game.Godot.Scripts.UI;

public sealed class HudEventHandlersController
{
    private readonly Dictionary<string, Action<JsonElement>> _handlers = new(StringComparer.Ordinal);
    private readonly Action<string, string, string, string, JsonElement> _recordEvent;
    private readonly Action<string> _warn;
    private readonly JsonDocumentOptions _jsonOptions;

    public HudEventHandlersController(
        Action<string, string, string, string, JsonElement> recordEvent,
        Action<string> warn,
        JsonDocumentOptions jsonOptions)
    {
        _recordEvent = recordEvent ?? throw new ArgumentNullException(nameof(recordEvent));
        _warn = warn ?? throw new ArgumentNullException(nameof(warn));
        _jsonOptions = jsonOptions;
    }

    public void Register(string type, Action<JsonElement> handler)
    {
        if (string.IsNullOrWhiteSpace(type) || handler is null)
        {
            return;
        }

        _handlers[type] = handler;
    }

    public void HandleDomainEvent(string type, string source, string dataJson, string id, string timestampIso)
    {
        if (string.IsNullOrWhiteSpace(source) || source.Length > 64)
        {
            return;
        }

        if (!_handlers.TryGetValue(type, out var handler))
        {
            return;
        }

        var json = string.IsNullOrWhiteSpace(dataJson) ? "{}" : dataJson;
        if (json.Length > 65536)
        {
            _warn($"HUD ignored over-sized event payload (type='{type}', length={json.Length}).");
            return;
        }

        try
        {
            using var doc = JsonDocument.Parse(json, _jsonOptions);
            handler(doc.RootElement);
            try
            {
                _recordEvent(type, source, id, timestampIso, doc.RootElement);
            }
            catch (Exception ex)
            {
                _warn($"HUD record-only event processing failed for '{type}': {ex.Message}");
            }
        }
        catch (Exception ex)
        {
            _warn($"HUD failed to handle event '{type}': {ex.Message}");
        }
    }
}
