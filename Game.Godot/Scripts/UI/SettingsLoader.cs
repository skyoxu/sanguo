using Godot;
using System;
using Game.Godot.Adapters;

namespace Game.Godot.Scripts.UI;

public partial class SettingsLoader : Node
{
    private const string UserId = "default";
    private const string ConfigPath = "user://settings.cfg";
    private const string ConfigSection = "settings";
    private const string KeyVolume = "vol";
    private const string KeyGraphics = "gfx";
    private const string KeyLanguage = "lang";
    private const string KeyResolution = "resolution";
    private const string KeyWindowMode = "window_mode";

    public override void _Ready()
    {
        if (!TryLoadFromConfig(out var vol, out var gfx, out var lang, out var resolution, out var windowMode))
        {
            return;
        }

        ApplyLanguage(lang);
        ApplyVolume(vol);
        ApplyGraphicsQuality(gfx);
        ApplyResolution(resolution);
        ApplyWindowMode(windowMode);
    }

    private static bool TryLoadFromConfig(out float vol, out string gfx, out string lang, out string resolution, out string windowMode)
    {
        vol = 0.5f; gfx = "medium"; lang = "en"; resolution = string.Empty; windowMode = string.Empty;
        var cfg = new ConfigFile();
        var err = cfg.Load(ConfigPath);
        if (err != Error.Ok)
        {
            return false;
        }

        try
        {
            Variant v = cfg.GetValue(ConfigSection, KeyVolume, 0.5f);
            Variant g = cfg.GetValue(ConfigSection, KeyGraphics, "medium");
            Variant l = cfg.GetValue(ConfigSection, KeyLanguage, "en");
            Variant r = cfg.GetValue(ConfigSection, KeyResolution, string.Empty);
            Variant m = cfg.GetValue(ConfigSection, KeyWindowMode, string.Empty);
            vol = v.VariantType == Variant.Type.Nil ? 0.5f : (float)v.AsDouble();
            gfx = g.VariantType == Variant.Type.Nil ? "medium" : g.AsString();
            lang = l.VariantType == Variant.Type.Nil ? "en" : l.AsString();
            resolution = r.VariantType == Variant.Type.Nil ? string.Empty : r.AsString();
            windowMode = m.VariantType == Variant.Type.Nil ? string.Empty : m.AsString();
            return true;
        }
        catch (Exception ex)
        {
            GD.PushWarning($"SettingsLoader: failed to parse ConfigFile: {ex.GetType().Name}: {ex.Message}");
            return false;
        }
    }

    private void ApplyVolume(float vol)
    {
        int bus = AudioServer.GetBusIndex("Master");
        if (bus >= 0) AudioServer.SetBusVolumeDb(bus, Mathf.LinearToDb(Mathf.Clamp(vol,0,1)));
    }

    private void ApplyLanguage(string lang)
    {
        if (!string.IsNullOrEmpty(lang)) TranslationServer.SetLocale(lang);
    }

    private void ApplyGraphicsQuality(string q)
    {
        q = (q ?? "medium").ToLowerInvariant();
        try { DisplayServer.WindowSetVsyncMode(q == "low" ? DisplayServer.VSyncMode.Disabled : DisplayServer.VSyncMode.Enabled); } catch (Exception ex) { GD.PushWarning($"SettingsLoader: failed to apply vsync: {ex.GetType().Name}: {ex.Message}"); }
        var vp = GetViewport();
        if (vp != null)
        {
            int msaa = q == "low" ? 0 : q == "medium" ? 1 : 2;
            try { vp.Set("msaa_2d", msaa); } catch (Exception ex) { GD.PushWarning($"SettingsLoader: failed to apply msaa_2d: {ex.GetType().Name}: {ex.Message}"); }
            try { vp.Set("msaa_3d", msaa); } catch (Exception ex) { GD.PushWarning($"SettingsLoader: failed to apply msaa_3d: {ex.GetType().Name}: {ex.Message}"); }
        }
    }

    private static bool TryParseResolution(string text, out Vector2I res)
    {
        res = new Vector2I(0, 0);
        if (string.IsNullOrWhiteSpace(text))
            return false;
        var cleaned = text.Trim().ToLowerInvariant().Replace(" ", "");
        var idx = cleaned.IndexOf('x');
        if (idx <= 0 || idx >= cleaned.Length - 1)
            return false;
        if (!int.TryParse(cleaned[..idx], out var w))
            return false;
        if (!int.TryParse(cleaned[(idx + 1)..], out var h))
            return false;
        res = new Vector2I(w, h);
        return true;
    }

    private void ApplyResolution(string resolution)
    {
        if (!TryParseResolution(resolution, out var res))
            return;
        if (res.X <= 0 || res.Y <= 0)
            return;
        try { DisplayServer.WindowSetSize(res); } catch (Exception ex) { GD.PushWarning($"SettingsLoader: failed to apply resolution: {ex.GetType().Name}: {ex.Message}"); }
    }

    private void ApplyWindowMode(string windowMode)
    {
        var t = (windowMode ?? string.Empty).Trim().ToLowerInvariant();
        var mode = t switch
        {
            "fullscreen" => DisplayServer.WindowMode.Fullscreen,
            "exclusive_fullscreen" => DisplayServer.WindowMode.ExclusiveFullscreen,
            "exclusivefullscreen" => DisplayServer.WindowMode.ExclusiveFullscreen,
            "windowed" => DisplayServer.WindowMode.Windowed,
            _ => (DisplayServer.WindowMode?)null,
        };
        if (mode == null)
            return;
        try { DisplayServer.WindowSetMode(mode.Value); } catch (Exception ex) { GD.PushWarning($"SettingsLoader: failed to apply window mode: {ex.GetType().Name}: {ex.Message}"); }
    }
}
