using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;
using System;
using System.Text.Json;

namespace Game.Godot.Scripts.Sanguo;

/// <summary>
/// Test-project mirror of <see cref="Game.Godot.Scripts.Sanguo.SanguoMapConfigLoader"/>.
/// Keep this file in sync with the runtime project to ensure GdUnit4 can execute scene wiring.
/// </summary>
internal static class SanguoMapConfigLoader
{
    internal const string DefaultMapPath = "res://Game.Godot/Assets/Config/Sanguo/map-default.json";
    internal const string UserOverrideMapPath = "user://config/sanguo/map.json";

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
        MaxDepth = 64,
    };

    internal static bool TryLoadMap(
        IResourceLoader loader,
        string correlationId,
        out SanguoMapDefinition map,
        out string sourcePath,
        out string error
    )
    {
        ArgumentNullException.ThrowIfNull(loader);

        if (TryLoadFromPath(loader, UserOverrideMapPath, out map, out error))
        {
            sourcePath = UserOverrideMapPath;
            SanguoSecurityAuditWriter.TryAppendSecurityAudit(
                action: "SANGUO_MAP_CONFIG_LOADED",
                reason: "user_override",
                target: $"path={UserOverrideMapPath}",
                caller: "SanguoMapConfigLoader.TryLoadMap",
                eventType: "runtime.map.config.loaded",
                eventSource: nameof(SanguoMapConfigLoader),
                eventId: correlationId);
            return true;
        }

        if (!string.IsNullOrWhiteSpace(error))
        {
            SanguoSecurityAuditWriter.TryAppendSecurityAudit(
                action: "SANGUO_MAP_CONFIG_LOAD_FAILED",
                reason: "user_override_invalid_fallback_default",
                target: $"path={UserOverrideMapPath} error={error}",
                caller: "SanguoMapConfigLoader.TryLoadMap",
                eventType: "runtime.map.config.load.failed",
                eventSource: nameof(SanguoMapConfigLoader),
                eventId: correlationId);
        }
        else
        {
            SanguoSecurityAuditWriter.TryAppendSecurityAudit(
                action: "SANGUO_MAP_CONFIG_FALLBACK",
                reason: "user_override_missing",
                target: $"path={UserOverrideMapPath}",
                caller: "SanguoMapConfigLoader.TryLoadMap",
                eventType: "runtime.map.config.fallback",
                eventSource: nameof(SanguoMapConfigLoader),
                eventId: correlationId);
        }

        if (TryLoadFromPath(loader, DefaultMapPath, out map, out error))
        {
            sourcePath = DefaultMapPath;
            SanguoSecurityAuditWriter.TryAppendSecurityAudit(
                action: "SANGUO_MAP_CONFIG_LOADED",
                reason: "default",
                target: $"path={DefaultMapPath}",
                caller: "SanguoMapConfigLoader.TryLoadMap",
                eventType: "runtime.map.config.loaded",
                eventSource: nameof(SanguoMapConfigLoader),
                eventId: correlationId);
            return true;
        }

        sourcePath = DefaultMapPath;
        SanguoSecurityAuditWriter.TryAppendSecurityAudit(
            action: "SANGUO_MAP_CONFIG_LOAD_FAILED",
            reason: "default_failed",
            target: $"path={DefaultMapPath} error={error}",
            caller: "SanguoMapConfigLoader.TryLoadMap",
            eventType: "runtime.map.config.load.failed",
            eventSource: nameof(SanguoMapConfigLoader),
            eventId: correlationId);
        return false;
    }

    private static bool TryLoadFromPath(
        IResourceLoader loader,
        string path,
        out SanguoMapDefinition map,
        out string error
    )
    {
        map = new SanguoMapDefinition(MapId: "invalid", TileCount: 0, Tiles: Array.Empty<SanguoTileDefinition>());
        error = string.Empty;

        var json = loader.LoadText(path);
        if (string.IsNullOrWhiteSpace(json))
        {
            return false;
        }

        SanguoMapDefinition? parsed;
        try
        {
            parsed = JsonSerializer.Deserialize<SanguoMapDefinition>(json, JsonOptions);
        }
        catch (Exception ex)
        {
            error = $"json_parse_failed:{ex.GetType().Name}";
            return false;
        }

        if (!SanguoMapDefinitionValidator.TryValidate(parsed, out var errors))
        {
            error = "invalid_map:" + string.Join(" | ", errors);
            if (error.Length > 512)
            {
                error = error.Substring(0, 512);
            }
            return false;
        }

        map = parsed!;
        return true;
    }
}
