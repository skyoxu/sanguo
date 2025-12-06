using Godot;
using System;
using Game.Godot.Adapters;

namespace Game.Godot.Scripts.UI;

public partial class SettingsLoader : Node
{
    private const string UserId = "default";

    public override void _Ready()
    {
        var db = GetNodeOrNull<SqliteDataStore>("/root/SqlDb");
        if (db == null) return;
        try
        {
            var rows = db.Query("SELECT audio_volume, graphics_quality, language FROM settings WHERE user_id=@0;", UserId);
            if (rows.Count == 0) return;
            var r = rows[0];
            if (r.TryGetValue("audio_volume", out var v) && v != null)
            {
                ApplyVolume((float)Convert.ToSingle(v));
            }
            if (r.TryGetValue("language", out var l) && l != null)
            {
                ApplyLanguage(l.ToString() ?? "");
            }
            if (r.TryGetValue("graphics_quality", out var g) && g != null)
            {
                ApplyGraphicsQuality(g.ToString() ?? "medium");
            }
        }
        catch { }
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
        try { DisplayServer.WindowSetVsyncMode(q == "low" ? DisplayServer.VSyncMode.Disabled : DisplayServer.VSyncMode.Enabled); } catch { }
        var vp = GetViewport();
        if (vp != null)
        {
            int msaa = q == "low" ? 0 : q == "medium" ? 1 : 2;
            try { vp.Set("msaa_2d", msaa); } catch { }
            try { vp.Set("msaa_3d", msaa); } catch { }
        }
    }
}
