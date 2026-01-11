using Godot;
using System;
using System.Collections.Generic;
using System.Text.Json;
using Game.Godot.Scripts.Security;

namespace Game.Godot.Scripts.Config;

public partial class FeatureFlags : Node
{
    private readonly Dictionary<string, bool> _flags = new(StringComparer.OrdinalIgnoreCase);

    private const string ConfigPath = "user://config/features.json";

    public override void _Ready()
    {
        LoadFromDisk();
        ApplyEnvOverrides();
    }

    public bool IsEnabled(string name)
    {
        if (string.IsNullOrWhiteSpace(name)) return false;
        // Immediate env override takes precedence (FEATURE_<NAME>)
        var envKey = $"FEATURE_{name}".ToUpperInvariant();
        var envVal = System.Environment.GetEnvironmentVariable(envKey);
        if (!string.IsNullOrEmpty(envVal))
            return ParseBool(envVal);

        return _flags.TryGetValue(name, out var on) && on;
    }

    public void Enable(string name) => Set(name, true);
    public void Disable(string name) => Set(name, false);

    public void Set(string name, bool enabled)
    {
        if (string.IsNullOrWhiteSpace(name)) return;
        _flags[name] = enabled;
        Save();
    }

    public void Save()
    {
        try
        {
            var json = JsonSerializer.Serialize(_flags, new JsonSerializerOptions { WriteIndented = true });
            SecurityFileAdapter.TryWriteText(ConfigPath, json, caller: "FeatureFlags.Save", out _);
        }
        catch { /* best-effort; avoid crashing template */ }
    }

    private void LoadFromDisk()
    {
        try
        {
            if (!SecurityFileAdapter.TryReadText(ConfigPath, caller: "FeatureFlags.LoadFromDisk", out var json, out var readReason))
            {
                if (string.Equals(readReason, "deny:file_missing", StringComparison.Ordinal))
                {
                    return;
                }
                return;
            }

            var map = JsonSerializer.Deserialize<Dictionary<string, bool>>(json);
            if (map != null)
            {
                _flags.Clear();
                foreach (var kv in map)
                {
                    _flags[kv.Key] = kv.Value;
                }
            }
        }
        catch { /* ignore parse errors */ }
    }

    private void ApplyEnvOverrides()
    {
        try
        {
            // GAME_FEATURES=name1,name2 => enable listed flags
            var list = System.Environment.GetEnvironmentVariable("GAME_FEATURES");
            if (!string.IsNullOrWhiteSpace(list))
            {
                foreach (var raw in list.Split(',', StringSplitOptions.RemoveEmptyEntries))
                {
                    var name = raw.Trim();
                    if (name.Length > 0) _flags[name] = true;
                }
            }

            // FEATURE_<NAME>=1|0|true|false to force a value
            foreach (System.Collections.DictionaryEntry e in System.Environment.GetEnvironmentVariables())
            {
                var key = e.Key?.ToString() ?? string.Empty;
                if (key.StartsWith("FEATURE_", StringComparison.OrdinalIgnoreCase))
                {
                    var name = key.Substring("FEATURE_".Length);
                    var value = e.Value?.ToString() ?? string.Empty;
                    _flags[name] = ParseBool(value);
                }
            }
        }
        catch { }
    }

    private static bool ParseBool(string value)
    {
        if (string.IsNullOrWhiteSpace(value)) return false;
        var v = value.Trim().ToLowerInvariant();
        return v is "1" or "true" or "on" or "yes";
    }
}
