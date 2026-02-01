using Godot;
using System;
using Game.Godot.Adapters;

namespace Game.Godot.Scripts.UI;

public partial class SettingsPanel : Control
{
    [Signal]
    public delegate void ResolutionAppliedEventHandler(Vector2I effective);

    [Signal]
    public delegate void WindowModeAppliedEventHandler(int mode);

    private HSlider _volume = default!;
    private OptionButton _graphics = default!;
    private OptionButton _language = default!;
    private OptionButton _resolution = default!;
    private OptionButton _windowMode = default!;
    private Button _save = default!;
    private Button _close = default!;

    private const string UserId = "default";
    private const string ConfigPath = "user://settings.cfg";
    private const string ConfigSection = "settings";
    private const string KeyVolume = "vol";
    private const string KeyGraphics = "gfx";
    private const string KeyLanguage = "lang";
    private const string KeyResolution = "resolution";
    private const string KeyWindowMode = "window_mode";
    private const string GraphicsLowKey = "ui.settings.graphics.low";
    private const string GraphicsMediumKey = "ui.settings.graphics.medium";
    private const string GraphicsHighKey = "ui.settings.graphics.high";
    private const string LanguageEnKey = "ui.settings.language.en";
    private const string LanguageZhKey = "ui.settings.language.zh";
    private const string LanguageJaKey = "ui.settings.language.ja";
    private const string WindowModeWindowedKey = "ui.settings.window_mode.windowed";
    private const string WindowModeFullscreenKey = "ui.settings.window_mode.fullscreen";
    private const string WindowModeExclusiveKey = "ui.settings.window_mode.exclusive_fullscreen";

    private Vector2I _lastValidResolution;
    private DisplayServer.WindowMode _lastValidWindowMode;

    public override void _Ready()
    {
        ProcessMode = Node.ProcessModeEnum.Always;
        _volume = GetNode<HSlider>("Center/VBox/VolRow/VolSlider");
        _graphics = GetNode<OptionButton>("Center/VBox/GraphicsRow/GraphicsOpt");
        _language = GetNode<OptionButton>("Center/VBox/LangRow/LangOpt");
        _resolution = GetNode<OptionButton>("Center/VBox/ResolutionRow/ResolutionOpt");
        _windowMode = GetNode<OptionButton>("Center/VBox/WindowModeRow/WindowModeOpt");
        _save = GetNode<Button>("Center/VBox/Buttons/SaveBtn");
        _close = GetNode<Button>("Center/VBox/Buttons/CloseBtn");

        _save.Pressed += OnSave;
        _close.Pressed += () => Visible = false;

        SetupGraphicsOptions();
        SetupLanguageOptions();

        // Realtime apply handlers
        _volume.ValueChanged += OnVolumeChanged;
        _graphics.ItemSelected += OnGraphicsChanged;
        _language.ItemSelected += OnLanguageChanged;
        _resolution.ItemSelected += OnResolutionChanged;
        _windowMode.ItemSelected += OnWindowModeChanged;

        SetupResolutionOptions();
        SetupWindowModeOptions();

        ApplyLocalizedTexts();
        Visible = false;
    }

    private SqliteDataStore? Db() => GetNodeOrNull<SqliteDataStore>("/root/SqlDb");

    private void SaveToConfig(float vol, string gfx, string lang, string resolution, string windowMode)
    {
        var cfg = new ConfigFile();
        // Load existing to preserve unrelated keys
        cfg.Load(ConfigPath);
        cfg.SetValue(ConfigSection, KeyVolume, vol);
        cfg.SetValue(ConfigSection, KeyGraphics, gfx ?? "medium");
        cfg.SetValue(ConfigSection, KeyLanguage, lang ?? "en");
        cfg.SetValue(ConfigSection, KeyResolution, resolution ?? string.Empty);
        cfg.SetValue(ConfigSection, KeyWindowMode, windowMode ?? string.Empty);
        var err = cfg.Save(ConfigPath);
        if (err != Error.Ok)
        {
            GD.PushWarning($"SettingsPanel: failed to save ConfigFile: {err}");
        }
    }

    private bool TryLoadFromConfig(out float vol, out string gfx, out string lang, out string resolution, out string windowMode)
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
            GD.PushWarning($"SettingsPanel: failed to parse ConfigFile: {ex.GetType().Name}: {ex.Message}");
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
        SaveToConfig(vol, gfx, lang, string.Empty, string.Empty);
    }

    private void OnSave()
    {
        var vol = Mathf.Clamp((float)_volume.Value, 0, 1);
        var gfx = GetSelectedOptionValue(_graphics, "medium");
        var lang = GetSelectedOptionValue(_language, "en");
        var res = _resolution.GetItemText(_resolution.Selected);
        var mode = GetSelectedOptionValue(_windowMode, "windowed");
        // SSoT to ConfigFile
        SaveToConfig(vol, gfx, lang, res, mode);

        // Apply immediately
        ApplyVolume(vol);
        ApplyLanguage(lang);
        ApplyGraphicsQuality(gfx);
        ApplyResolution(ParseResolutionOrFallback(res));
        ApplyWindowMode(ParseWindowModeOrFallback(mode));
    }

    private void LoadAndApplySettings()
    {
        // Prefer ConfigFile; migrate once from DB if missing
        float vol; string gfx; string lang; string res; string mode;
        if (!TryLoadFromConfig(out vol, out gfx, out lang, out res, out mode))
        {
            MigrateFromDbIfConfigMissing();
            if (!TryLoadFromConfig(out vol, out gfx, out lang, out res, out mode))
                return;
        }
        _volume.Value = vol;
        ApplyVolume(vol);
        // graphics selection
        if (!string.IsNullOrEmpty(gfx))
        {
            SelectOptionByValue(_graphics, gfx);
        }
        ApplyGraphicsQuality(GetSelectedOptionValue(_graphics, "medium"));
        // language
        if (!string.IsNullOrEmpty(lang))
        {
            SelectOptionByValue(_language, lang);
            ApplyLanguage(GetSelectedOptionValue(_language, "en"));
        }

        ApplyResolution(ParseResolutionOrFallback(res));
        ApplyWindowMode(ParseWindowModeOrFallback(mode));
    }

    public void ShowPanel()
    {
        Visible = true;
        LoadAndApplySettings();
    }

    private void OnVolumeChanged(double value)
    {
        ApplyVolume((float)value);
    }

    private void OnGraphicsChanged(long index)
    {
        var gfx = GetOptionValueAtIndex(_graphics, (int)index, "medium");
        ApplyGraphicsQuality(gfx);
    }

    private void OnLanguageChanged(long index)
    {
        var lang = GetOptionValueAtIndex(_language, (int)index, "en");
        ApplyLanguage(lang);
    }

    private void OnResolutionChanged(long index)
    {
        var res = _resolution.GetItemText((int)index);
        ApplyResolution(ParseResolutionOrFallback(res));
    }

    private void OnWindowModeChanged(long index)
    {
        var mode = GetOptionValueAtIndex(_windowMode, (int)index, "windowed");
        ApplyWindowMode(ParseWindowModeOrFallback(mode));
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
        {
            TranslationServer.SetLocale(lang);
            ApplyLocalizedTexts();
        }
    }

    private void ApplyLocalizedTexts()
    {
        SetLabelText("Center/VBox/VolRow/VolLabel", "ui.settings.volume", "Volume");
        SetLabelText("Center/VBox/GraphicsRow/GraphicsLabel", "ui.settings.graphics", "Graphics");
        SetLabelText("Center/VBox/LangRow/LangLabel", "ui.settings.language", "Language");
        SetLabelText("Center/VBox/ResolutionRow/ResolutionLabel", "ui.settings.resolution", "Resolution");
        SetLabelText("Center/VBox/WindowModeRow/WindowModeLabel", "ui.settings.window_mode", "Window Mode");
        SetButtonText("Center/VBox/Buttons/SaveBtn", "ui.settings.save", "Save");
        SetButtonText("Center/VBox/Buttons/CloseBtn", "ui.settings.close", "Close");
        ApplyLocalizedOptions();
    }

    private void SetLabelText(string path, string key, string fallback)
    {
        var label = GetNodeOrNull<Label>(path);
        if (label == null)
        {
            return;
        }

        label.Text = TranslateOrFallback(key, fallback);
    }

    private void SetButtonText(string path, string key, string fallback)
    {
        var button = GetNodeOrNull<Button>(path);
        if (button == null)
        {
            return;
        }

        button.Text = TranslateOrFallback(key, fallback);
    }

    private static string TranslateOrFallback(string key, string fallback)
    {
        if (string.IsNullOrWhiteSpace(key))
        {
            return fallback;
        }

        var translated = TranslationServer.Translate(key);
        if (string.IsNullOrWhiteSpace(translated) || string.Equals(translated, key, StringComparison.Ordinal))
        {
            return fallback;
        }

        return translated;
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
        catch (Exception ex)
        {
            GD.PushWarning($"SettingsPanel: failed to apply vsync: {ex.GetType().Name}: {ex.Message}");
        }

        var vp = GetViewport();
        if (vp != null)
        {
            int msaa = 0; // disabled
            if (q == "medium") msaa = 1; // 2x
            else if (q == "high") msaa = 2; // 4x (use 8x if needed: 3)
            // Set via dynamic property names to avoid API differences
            try { vp.Set("msaa_2d", msaa); } catch (Exception ex) { GD.PushWarning($"SettingsPanel: failed to apply msaa_2d: {ex.GetType().Name}: {ex.Message}"); }
            try { vp.Set("msaa_3d", msaa); } catch (Exception ex) { GD.PushWarning($"SettingsPanel: failed to apply msaa_3d: {ex.GetType().Name}: {ex.Message}"); }
        }
    }

    private void SetupResolutionOptions()
    {
        if (_resolution.ItemCount == 0)
        {
            _resolution.AddItem("1280x720");
            _resolution.AddItem("1600x900");
            _resolution.AddItem("1920x1080");
        }

        var current = SafeGetWindowSize();
        _lastValidResolution = current;
        EnsureResolutionItemExists(current);
        SelectResolution(current);
    }

    private void SetupWindowModeOptions()
    {
        EnsureOption(_windowMode, "windowed", WindowModeWindowedKey, "windowed");
        EnsureOption(_windowMode, "fullscreen", WindowModeFullscreenKey, "fullscreen");
        EnsureOption(_windowMode, "exclusive_fullscreen", WindowModeExclusiveKey, "exclusive_fullscreen");

        var current = SafeGetWindowMode();
        _lastValidWindowMode = current;
        SelectWindowMode(current);
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

    private Vector2I ParseResolutionOrFallback(string? text)
    {
        if (TryParseResolution(text ?? string.Empty, out var res))
        {
            return res;
        }
        return _lastValidResolution == default ? SafeGetWindowSize() : _lastValidResolution;
    }

    private DisplayServer.WindowMode ParseWindowModeOrFallback(string? text)
    {
        var t = (text ?? string.Empty).Trim().ToLowerInvariant();
        return t switch
        {
            "fullscreen" => DisplayServer.WindowMode.Fullscreen,
            "exclusive_fullscreen" => DisplayServer.WindowMode.ExclusiveFullscreen,
            "exclusivefullscreen" => DisplayServer.WindowMode.ExclusiveFullscreen,
            "windowed" => DisplayServer.WindowMode.Windowed,
            _ => _lastValidWindowMode,
        };
    }

    private void ApplyResolution(Vector2I candidate)
    {
        var target = SanitizeResolution(candidate, _lastValidResolution == default ? SafeGetWindowSize() : _lastValidResolution);
        try
        {
            DisplayServer.WindowSetSize(target);
        }
        catch (Exception ex)
        {
            GD.PushWarning($"SettingsPanel: failed to apply resolution: {ex.GetType().Name}: {ex.Message}");
        }

        var actual = target;
        try
        {
            actual = DisplayServer.WindowGetSize();
        }
        catch
        {
        }
        if (actual.X <= 0 || actual.Y <= 0)
        {
            actual = target;
        }

        _lastValidResolution = actual;
        EnsureResolutionItemExists(actual);
        SelectResolution(actual);
        EmitSignal(SignalName.ResolutionApplied, actual);
    }

    private void ApplyWindowMode(DisplayServer.WindowMode mode)
    {
        var target = mode;
        try
        {
            DisplayServer.WindowSetMode(target);
        }
        catch (Exception ex)
        {
            GD.PushWarning($"SettingsPanel: failed to apply window mode: {ex.GetType().Name}: {ex.Message}");
        }

        var actual = target;
        try
        {
            actual = DisplayServer.WindowGetMode();
        }
        catch
        {
        }

        _lastValidWindowMode = actual;
        SelectWindowMode(actual);
        EmitSignal(SignalName.WindowModeApplied, (int)actual);
    }

    private static Vector2I SanitizeResolution(Vector2I candidate, Vector2I lastValid)
    {
        if (candidate.X <= 0 || candidate.Y <= 0)
        {
            return lastValid;
        }

        try
        {
            var screen = DisplayServer.ScreenGetSize();
            if (screen.X > 0 && screen.Y > 0)
            {
                if (candidate.X > screen.X || candidate.Y > screen.Y)
                {
                    return lastValid;
                }
            }
        }
        catch
        {
            // If ScreenGetSize is unsupported (e.g., headless), fall back to last valid.
        }

        return candidate;
    }

    private static Vector2I SafeGetWindowSize()
    {
        try { return DisplayServer.WindowGetSize(); }
        catch { return new Vector2I(1280, 720); }
    }

    private static DisplayServer.WindowMode SafeGetWindowMode()
    {
        try { return DisplayServer.WindowGetMode(); }
        catch { return DisplayServer.WindowMode.Windowed; }
    }

    private void EnsureResolutionItemExists(Vector2I size)
    {
        var label = $"{size.X}x{size.Y}";
        for (int i = 0; i < _resolution.ItemCount; i++)
        {
            if (string.Equals(_resolution.GetItemText(i), label, StringComparison.OrdinalIgnoreCase))
            {
                return;
            }
        }
        _resolution.AddItem(label);
    }

    private void SelectResolution(Vector2I size)
    {
        var label = $"{size.X}x{size.Y}";
        for (int i = 0; i < _resolution.ItemCount; i++)
        {
            if (string.Equals(_resolution.GetItemText(i), label, StringComparison.OrdinalIgnoreCase))
            {
                _resolution.Selected = i;
                return;
            }
        }
        _resolution.Selected = 0;
    }

    private void SelectWindowMode(DisplayServer.WindowMode mode)
    {
        var value = mode switch
        {
            DisplayServer.WindowMode.Fullscreen => "fullscreen",
            DisplayServer.WindowMode.ExclusiveFullscreen => "exclusive_fullscreen",
            _ => "windowed",
        };
        SelectOptionByValue(_windowMode, value);
    }

    private void SetupGraphicsOptions()
    {
        EnsureOption(_graphics, "low", GraphicsLowKey, "low");
        EnsureOption(_graphics, "medium", GraphicsMediumKey, "medium");
        EnsureOption(_graphics, "high", GraphicsHighKey, "high");
        if (_graphics.Selected < 0)
        {
            _graphics.Selected = 1;
        }
    }

    private void SetupLanguageOptions()
    {
        EnsureOption(_language, "en", LanguageEnKey, "en");
        EnsureOption(_language, "zh", LanguageZhKey, "zh");
        EnsureOption(_language, "ja", LanguageJaKey, "ja");
        if (_language.Selected < 0)
        {
            _language.Selected = 0;
        }
    }

    private void ApplyLocalizedOptions()
    {
        UpdateOptionLabel(_graphics, "low", GraphicsLowKey, "low");
        UpdateOptionLabel(_graphics, "medium", GraphicsMediumKey, "medium");
        UpdateOptionLabel(_graphics, "high", GraphicsHighKey, "high");
        UpdateOptionLabel(_language, "en", LanguageEnKey, "en");
        UpdateOptionLabel(_language, "zh", LanguageZhKey, "zh");
        UpdateOptionLabel(_language, "ja", LanguageJaKey, "ja");
        UpdateOptionLabel(_windowMode, "windowed", WindowModeWindowedKey, "windowed");
        UpdateOptionLabel(_windowMode, "fullscreen", WindowModeFullscreenKey, "fullscreen");
        UpdateOptionLabel(_windowMode, "exclusive_fullscreen", WindowModeExclusiveKey, "exclusive_fullscreen");
    }

    private static void EnsureOption(OptionButton option, string value, string key, string fallback)
    {
        var idx = FindOptionIndexByValue(option, value);
        if (idx < 0)
        {
            option.AddItem(TranslateOrFallback(key, fallback));
            idx = option.ItemCount - 1;
            option.SetItemMetadata(idx, value);
            return;
        }

        option.SetItemText(idx, TranslateOrFallback(key, fallback));
    }

    private static void UpdateOptionLabel(OptionButton option, string value, string key, string fallback)
    {
        var idx = FindOptionIndexByValue(option, value);
        if (idx < 0)
        {
            return;
        }

        option.SetItemText(idx, TranslateOrFallback(key, fallback));
    }

    private static int FindOptionIndexByValue(OptionButton option, string value)
    {
        for (int i = 0; i < option.ItemCount; i++)
        {
            var meta = option.GetItemMetadata(i);
            if (meta.VariantType == Variant.Type.String && string.Equals(meta.AsString(), value, StringComparison.OrdinalIgnoreCase))
            {
                return i;
            }
        }
        return -1;
    }

    private static void SelectOptionByValue(OptionButton option, string value)
    {
        var idx = FindOptionIndexByValue(option, value);
        if (idx >= 0)
        {
            option.Selected = idx;
            return;
        }

        option.Selected = 0;
    }

    private static string GetSelectedOptionValue(OptionButton option, string fallback)
    {
        return GetOptionValueAtIndex(option, option.Selected, fallback);
    }

    private static string GetOptionValueAtIndex(OptionButton option, int index, string fallback)
    {
        if (option.ItemCount == 0 || index < 0 || index >= option.ItemCount)
        {
            return fallback;
        }

        var meta = option.GetItemMetadata(index);
        if (meta.VariantType == Variant.Type.String)
        {
            return meta.AsString();
        }

        var text = option.GetItemText(index);
        return string.IsNullOrWhiteSpace(text) ? fallback : text;
    }
}
