using Godot;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;

namespace Game.Godot.Scripts.Config;

public partial class FeatureFlags : Node
{
    private readonly Dictionary<string, bool> _flags = new(StringComparer.OrdinalIgnoreCase);

    private static string ConfigDir() => ProjectSettings.GlobalizePath("user://config");
    private static string ConfigPath() => ProjectSettings.GlobalizePath("user://config/features.json");

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
            Directory.CreateDirectory(ConfigDir());
            var json = JsonSerializer.Serialize(_flags, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(ConfigPath(), json);
        }
        catch { /* best-effort; avoid crashing template */ }
    }

    private void LoadFromDisk()
    {
        try
        {
            var path = ConfigPath();
            if (File.Exists(path))
            {
                var json = File.ReadAllText(path);
                var map = JsonSerializer.Deserialize<Dictionary<string, bool>>(json);
                if (map != null)
                {
                    _flags.Clear();
                    foreach (var kv in map)
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
