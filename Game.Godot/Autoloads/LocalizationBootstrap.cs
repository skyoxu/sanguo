using Godot;
using System;
using System.Collections.Generic;
using System.Text.Json;
using Game.Core.Ports;
using Game.Core.Services.Sanguo;
using Game.Godot.Scripts.Security;

namespace Game.Godot.Autoloads;

public partial class LocalizationBootstrap : Node
{
    private const string HelpTutorialEnPath = "res://Game.Godot/Translations/help_tutorial.en.csv";
    private const string HelpTutorialZhPath = "res://Game.Godot/Translations/help_tutorial.zh.csv";
    private const string UiEventLogEnPath = "res://Game.Godot/Translations/ui_event_log.en.csv";
    private const string UiEventLogZhPath = "res://Game.Godot/Translations/ui_event_log.zh.csv";
    private const string CoreStringsEnPath = "res://Data/i18n/en_us.json";
    private const string CoreStringsZhPath = "res://Data/i18n/zh_cn.json";

    private static bool _initialized;

    public override void _EnterTree()
    {
        if (_initialized)
        {
            return;
        }

        _initialized = true;
        EnsureTranslationsLoadedFromRes();
    }

    private static void EnsureTranslationsLoadedFromRes()
    {
        try
        {
            TryLoadCsvAndRegister(locale: "en", csvPath: HelpTutorialEnPath);
            TryLoadCsvAndRegister(locale: "zh", csvPath: HelpTutorialZhPath);
            TryLoadCsvAndRegister(locale: "en", csvPath: UiEventLogEnPath);
            TryLoadCsvAndRegister(locale: "zh", csvPath: UiEventLogZhPath);
            var (coreEn, coreZh) = ResolveCoreStringsPaths();
            TryLoadJsonAndRegister(locale: "en", jsonPath: coreEn);
            TryLoadJsonAndRegister(locale: "zh", jsonPath: coreZh);
        }
        catch (Exception ex)
        {
            GD.PushWarning($"LocalizationBootstrap: failed to register translations: {ex.Message}");
        }
    }

    private static void TryLoadJsonAndRegister(string locale, string jsonPath)
    {
        if (string.IsNullOrWhiteSpace(locale) || string.IsNullOrWhiteSpace(jsonPath))
        {
            return;
        }

        var pairs = LoadKeyTextPairsFromJson(jsonPath);
        if (pairs.Count == 0)
        {
            GD.PushWarning($"LocalizationBootstrap: no translations loaded from {jsonPath}");
            return;
        }

        var translation = new Translation
        {
            Locale = locale
        };

        foreach (var (key, text) in pairs)
        {
            if (!string.IsNullOrWhiteSpace(key))
            {
                translation.AddMessage(key, text ?? string.Empty);
            }
        }

        TranslationServer.AddTranslation(translation);
    }

    private static void TryLoadCsvAndRegister(string locale, string csvPath)
    {
        if (string.IsNullOrWhiteSpace(locale) || string.IsNullOrWhiteSpace(csvPath))
        {
            return;
        }

        var pairs = LoadKeyTextPairsFromCsv(csvPath);
        if (pairs.Count == 0)
        {
            GD.PushWarning($"LocalizationBootstrap: no translations loaded from {csvPath}");
            return;
        }

        var translation = new Translation
        {
            Locale = locale
        };

        foreach (var (key, text) in pairs)
        {
            if (!string.IsNullOrWhiteSpace(key))
            {
                translation.AddMessage(key, text ?? string.Empty);
            }
        }

        TranslationServer.AddTranslation(translation);
    }

    private static List<(string Key, string Text)> LoadKeyTextPairsFromJson(string resPath)
    {
        var outList = new List<(string Key, string Text)>();

        try
        {
            if (!SecurityFileAdapter.TryReadText(resPath, caller: nameof(LocalizationBootstrap), out var raw, out _))
            {
                return outList;
            }

            if (string.IsNullOrWhiteSpace(raw))
            {
                return outList;
            }

            using var doc = JsonDocument.Parse(raw);
            if (!doc.RootElement.TryGetProperty("strings", out var stringsEl) || stringsEl.ValueKind != JsonValueKind.Object)
            {
                return outList;
            }

            foreach (var prop in stringsEl.EnumerateObject())
            {
                var key = prop.Name ?? string.Empty;
                var text = prop.Value.ValueKind == JsonValueKind.String ? (prop.Value.GetString() ?? string.Empty) : prop.Value.ToString();
                if (!string.IsNullOrWhiteSpace(key))
                {
                    outList.Add((key, text));
                }
            }
        }
        catch (Exception ex)
        {
            GD.PushWarning($"LocalizationBootstrap: failed to load translations from {resPath}: {ex.Message}");
        }

        return outList;
    }

    private static List<(string Key, string Text)> LoadKeyTextPairsFromCsv(string resPath)
    {
        var outList = new List<(string Key, string Text)>();

        try
        {
            if (!SecurityFileAdapter.TryReadText(resPath, caller: nameof(LocalizationBootstrap), out var raw, out _))
            {
                return outList;
            }

            if (string.IsNullOrWhiteSpace(raw))
            {
                return outList;
            }

            var lines = raw.Replace("\r\n", "\n").Replace("\r", "\n").Split('\n', StringSplitOptions.RemoveEmptyEntries);
            foreach (var lineRaw in lines)
            {
                var line = (lineRaw ?? string.Empty).Trim();
                if (line.Length == 0)
                {
                    continue;
                }

                if (line.StartsWith("key,", StringComparison.OrdinalIgnoreCase) || line.StartsWith("key\t", StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                var idx = line.IndexOf(',');
                if (idx <= 0 || idx >= line.Length - 1)
                {
                    continue;
                }

                var key = line.Substring(0, idx).Trim();
                var text = line.Substring(idx + 1).Trim();

                if (text.Length >= 2 && text.StartsWith("\"", StringComparison.Ordinal) && text.EndsWith("\"", StringComparison.Ordinal))
                {
                    text = text.Substring(1, text.Length - 2).Replace("\"\"", "\"");
                }

                if (!string.IsNullOrWhiteSpace(key))
                {
                    outList.Add((key, text));
                }
            }
        }
        catch (Exception ex)
        {
            GD.PushWarning($"LocalizationBootstrap: failed to load translations from {resPath}: {ex.Message}");
        }

        return outList;
    }

    private static (string EnPath, string ZhPath) ResolveCoreStringsPaths()
    {
        var loader = new BootstrapResourceLoader();
        if (SanguoContentPackResolver.TryResolveDefaultPack(loader, out var pack, out _))
        {
            return (pack.I18nEnPath, pack.I18nZhPath);
        }

        return (CoreStringsEnPath, CoreStringsZhPath);
    }

    private sealed class BootstrapResourceLoader : IResourceLoader
    {
        public string? LoadText(string path)
        {
            return SecurityFileAdapter.TryReadText(path, caller: nameof(LocalizationBootstrap), out var text, out _)
                ? text
                : null;
        }

        public byte[]? LoadBytes(string path)
        {
            return SecurityFileAdapter.TryReadBytes(path, caller: nameof(LocalizationBootstrap), out var bytes, out _)
                ? bytes
                : null;
        }
    }
}
