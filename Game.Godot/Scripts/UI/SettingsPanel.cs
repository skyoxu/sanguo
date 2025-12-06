using Godot;
using System;
using Game.Godot.Adapters;

namespace Game.Godot.Scripts.UI;

public partial class SettingsPanel : Control
{
    private HSlider _volume = default!;
    private OptionButton _graphics = default!;
    private OptionButton _language = default!;
    private Button _save = default!;
    private Button _load = default!;
    private Button _close = default!;

    private const string UserId = "default";
    private const string ConfigPath = "user://settings.cfg";
    private const string ConfigSection = "settings";

    public override void _Ready()
    {
        _volume = GetNode<HSlider>("VBox/VolRow/VolSlider");
        _graphics = GetNode<OptionButton>("VBox/GraphicsRow/GraphicsOpt");
        _language = GetNode<OptionButton>("VBox/LangRow/LangOpt");
        _save = GetNode<Button>("VBox/Buttons/SaveBtn");
        _load = GetNode<Button>("VBox/Buttons/LoadBtn");
        _close = GetNode<Button>("VBox/Buttons/CloseBtn");

        _save.Pressed += OnSave;
        _load.Pressed += OnLoad;
        _close.Pressed += () => Visible = false;

        if (_graphics.ItemCount == 0)
        {
            _graphics.AddItem("low");
            _graphics.AddItem("medium");
            _graphics.AddItem("high");
            _graphics.Selected = 1;
        }
        if (_language.ItemCount == 0)
        {
            _language.AddItem("en");
            _language.AddItem("zh");
            _language.AddItem("ja");
            _language.Selected = 0;
        }

        // Realtime apply handlers
        _volume.ValueChanged += OnVolumeChanged;
        _graphics.ItemSelected += OnGraphicsChanged;
        _language.ItemSelected += OnLanguageChanged;

        Visible = false;
    }

    private SqliteDataStore? Db() => GetNodeOrNull<SqliteDataStore>("/root/SqlDb");

    private void SaveToConfig(float vol, string gfx, string lang)
    {
        var cfg = new ConfigFile();
        // Load existing to preserve unrelated keys
        cfg.Load(ConfigPath);
        cfg.SetValue(ConfigSection, nameof(vol), vol);
        cfg.SetValue(ConfigSection, nameof(gfx), gfx ?? "medium");
        cfg.SetValue(ConfigSection, nameof(lang), lang ?? "en");
        var err = cfg.Save(ConfigPath);
        if (err != Error.Ok)
        {
            GD.PushWarning($"SettingsPanel: failed to save ConfigFile: {err}");
        }
    }

    private bool TryLoadFromConfig(out float vol, out string gfx, out string lang)
    {
        vol = 0.5f; gfx = "medium"; lang = "en";
        var cfg = new ConfigFile();
        var err = cfg.Load(ConfigPath);
        if (err != Error.Ok)
        {
            return false;
        }
        try
        {
            Variant v = cfg.GetValue(ConfigSection, nameof(vol), 0.5f);
            Variant g = cfg.GetValue(ConfigSection, nameof(gfx), "medium");
            Variant l = cfg.GetValue(ConfigSection, nameof(lang), "en");
            vol = v.VariantType == Variant.Type.Nil ? 0.5f : (float)v.AsDouble();
            gfx = g.VariantType == Variant.Type.Nil ? "medium" : g.AsString();
            lang = l.VariantType == Variant.Type.Nil ? "en" : l.AsString();
            return true;
        }
        catch
        {
            return false;
        }
    }

    private void MigrateFromDbIfConfigMissing()
    {
        // If config already exists, do nothing
        var cfgProbe = new ConfigFile();
        if (cfgProbe.Load(ConfigPath) == Error.Ok)
            return;

        // Attempt read from DB once and save to config
        var db = Db();
        if (db == null)
            return;
        var rows = db.Query("SELECT audio_volume, graphics_quality, language FROM settings WHERE user_id=@0;", UserId);
        if (rows.Count == 0) return;
        var r = rows[0];
        float vol = 0.5f; string gfx = "medium"; string lang = "en";
        if (r.TryGetValue("audio_volume", out var v) && v != null)
            vol = Convert.ToSingle(v);
        if (r.TryGetValue("graphics_quality", out var g) && g != null)
            gfx = g.ToString() ?? "medium";
        if (r.TryGetValue("language", out var l) && l != null)
            lang = l.ToString() ?? "en";
        SaveToConfig(vol, gfx, lang);
    }

    private void OnSave()
    {
        var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        var vol = Mathf.Clamp((float)_volume.Value, 0, 1);
        var gfx = _graphics.GetItemText(_graphics.Selected);
        var lang = _language.GetItemText(_language.Selected);
        // SSoT to ConfigFile
        SaveToConfig(vol, gfx, lang);

        // Apply immediately
        ApplyVolume(vol);
        ApplyLanguage(lang);
    }

    private void OnLoad()
    {
        // Prefer ConfigFile; migrate once from DB if missing
        float vol; string gfx; string lang;
        if (!TryLoadFromConfig(out vol, out gfx, out lang))
        {
            MigrateFromDbIfConfigMissing();
            if (!TryLoadFromConfig(out vol, out gfx, out lang))
                return;
        }
        _volume.Value = vol;
        ApplyVolume(vol);
        // graphics selection
        if (!string.IsNullOrEmpty(gfx))
        {
            for (int i = 0; i < _graphics.ItemCount; i++)
            {
                if (_graphics.GetItemText(i).Equals(gfx, StringComparison.OrdinalIgnoreCase))
                { _graphics.Selected = i; break; }
            }
        }
        // language
        if (!string.IsNullOrEmpty(lang))
        {
            for (int i = 0; i < _language.ItemCount; i++)
            {
                if (_language.GetItemText(i).Equals(lang, StringComparison.OrdinalIgnoreCase))
                { _language.Selected = i; break; }
            }
            ApplyLanguage(_language.GetItemText(_language.Selected));
        }
    }

    public void ShowPanel() => Visible = true;

    private void OnVolumeChanged(double value)
    {
        ApplyVolume((float)value);
    }

    private void OnGraphicsChanged(long index)
    {
        var gfx = _graphics.GetItemText((int)index);
        ApplyGraphicsQuality(gfx);
    }

    private void OnLanguageChanged(long index)
    {
        var lang = _language.GetItemText((int)index);
        ApplyLanguage(lang);
    }

    private void ApplyVolume(float vol)
    {
        int bus = AudioServer.GetBusIndex("Master");
        if (bus >= 0)
        {
            AudioServer.SetBusVolumeDb(bus, Mathf.LinearToDb(Mathf.Clamp(vol, 0, 1)));
        }
    }

    private void ApplyLanguage(string lang)
    {
        if (!string.IsNullOrEmpty(lang))
            TranslationServer.SetLocale(lang);
    }

    private void ApplyGraphicsQuality(string quality)
    {
        // Map: low -> no vsync, no MSAA; medium -> vsync on, 2x; high -> vsync on, 4x/8x
        var q = (quality ?? "medium").ToLowerInvariant();
        try
        {
            if (q == "low")
                DisplayServer.WindowSetVsyncMode(DisplayServer.VSyncMode.Disabled);
            else
                DisplayServer.WindowSetVsyncMode(DisplayServer.VSyncMode.Enabled);
        }
        catch { /* not critical */ }

        var vp = GetViewport();
        if (vp != null)
        {
            int msaa = 0; // disabled
            if (q == "medium") msaa = 1; // 2x
            else if (q == "high") msaa = 2; // 4x (use 8x if needed: 3)
            // Set via dynamic property names to avoid API differences
            try { vp.Set("msaa_2d", msaa); } catch { }
            try { vp.Set("msaa_3d", msaa); } catch { }
        }
    }
}
