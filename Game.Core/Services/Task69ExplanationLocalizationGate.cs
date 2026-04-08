using System;

namespace Game.Core.Services;

/// <summary>
/// Prefix-scoped localization gate for Task69 explanation keys.
/// Only task69 explanation keys are allowed to enter build-mode raw-key exposure policy.
/// Non-task69 keys always return the provided fallback on missing translations.
/// </summary>
public static class Task69ExplanationLocalizationGate
{
    public const string Task69ExplanationKeyPrefix = "ui.task69.explanation.";

    public static bool IsTask69ExplanationKey(string key)
    {
        return !string.IsNullOrWhiteSpace(key)
               && key.StartsWith(Task69ExplanationKeyPrefix, StringComparison.Ordinal);
    }

    public static string ResolveMissingTranslation(string buildMode, string key, string fallback)
    {
        if (!IsTask69ExplanationKey(key))
        {
            return fallback;
        }

        return I18nMissingKeyExposurePolicy.ResolveForBuildMode(buildMode, key, fallback);
    }
}
