using Godot;
using System;
using System.Collections.Generic;
using Game.Godot.Scripts.Security;

namespace Game.Godot.Autoloads;

public partial class LocalizationBootstrap : Node
{
    private const string HelpTutorialEnPath = "res://Game.Godot/Translations/help_tutorial.en.csv";
    private const string HelpTutorialZhPath = "res://Game.Godot/Translations/help_tutorial.zh.csv";
    private const string UiEventLogEnPath = "res://Game.Godot/Translations/ui_event_log.en.csv";
    private const string UiEventLogZhPath = "res://Game.Godot/Translations/ui_event_log.zh.csv";

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
        }
        catch (Exception ex)
        {
            GD.PushWarning($"LocalizationBootstrap: failed to register translations: {ex.Message}");
        }
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
}
