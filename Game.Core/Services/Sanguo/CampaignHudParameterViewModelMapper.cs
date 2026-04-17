using System;

namespace Game.Core.Services.Sanguo;

public sealed record CampaignHudParameterViewModel(
    string Commander,
    string Strategems,
    string Difficulty,
    string RoundMarker,
    string BossPressureContext);

public static class CampaignHudParameterViewModelMapper
{
    public const string UnknownCommanderFallback = "Unknown commander";
    public const string UnknownStrategemFallback = "Unknown strategem";
    public const string UnknownDifficultyFallback = "Unknown difficulty";
    public const string NoBossPressureFallback = "No boss pressure";

    public static CampaignHudParameterViewModel Map(
        string? commanderId,
        string? activeStrategemId,
        string? passiveStrategemId,
        string? difficultyCode,
        int turnNumber,
        string? bossId,
        int bossRoundNumber,
        int nextRoundPressureForecast,
        bool releaseMode,
        Func<string, string?>? resolveCommanderLabel = null,
        Func<string, string?>? resolveStrategemLabel = null,
        Func<string, string?>? resolveDifficultyLabel = null,
        Func<string, string?>? resolveBossLabel = null)
    {
        var commander = ResolveLabel(
            token: commanderId,
            resolver: resolveCommanderLabel,
            releaseMode: releaseMode,
            fallback: UnknownCommanderFallback);

        var activeStrategem = ResolveLabel(
            token: activeStrategemId,
            resolver: resolveStrategemLabel,
            releaseMode: releaseMode,
            fallback: UnknownStrategemFallback);
        var passiveStrategem = ResolveLabel(
            token: passiveStrategemId,
            resolver: resolveStrategemLabel,
            releaseMode: releaseMode,
            fallback: UnknownStrategemFallback);

        var difficulty = ResolveLabel(
            token: difficultyCode,
            resolver: resolveDifficultyLabel,
            releaseMode: releaseMode,
            fallback: UnknownDifficultyFallback);

        var effectiveRound = bossRoundNumber > 0 ? bossRoundNumber : Math.Max(1, turnNumber);
        var roundMarker = $"R{effectiveRound}";

        var hasPressurePayload = !string.IsNullOrWhiteSpace(bossId) && bossRoundNumber > 0;
        var bossPressureContext = BuildBossPressureContext(
            bossId,
            effectiveRound,
            nextRoundPressureForecast,
            hasPressurePayload,
            releaseMode,
            resolveBossLabel);

        return new CampaignHudParameterViewModel(
            Commander: commander,
            Strategems: $"{activeStrategem} / {passiveStrategem}",
            Difficulty: difficulty,
            RoundMarker: roundMarker,
            BossPressureContext: bossPressureContext);
    }

    private static string BuildBossPressureContext(
        string? bossId,
        int roundNumber,
        int nextRoundPressureForecast,
        bool hasPressurePayload,
        bool releaseMode,
        Func<string, string?>? resolveBossLabel)
    {
        if (!hasPressurePayload)
        {
            return NoBossPressureFallback;
        }

        var boss = ResolveLabel(
            token: bossId,
            resolver: resolveBossLabel,
            releaseMode: releaseMode,
            fallback: NoBossPressureFallback);
        if (string.Equals(boss, NoBossPressureFallback, StringComparison.Ordinal))
        {
            return NoBossPressureFallback;
        }

        return $"{boss} | R{Math.Max(1, roundNumber)} | +{Math.Max(0, nextRoundPressureForecast)}";
    }

    private static string ResolveLabel(
        string? token,
        Func<string, string?>? resolver,
        bool releaseMode,
        string fallback)
    {
        var raw = (token ?? string.Empty).Trim();
        if (string.IsNullOrWhiteSpace(raw))
        {
            return fallback;
        }

        var label = (resolver?.Invoke(raw) ?? string.Empty).Trim();
        if (string.IsNullOrWhiteSpace(label))
        {
            return releaseMode ? fallback : raw;
        }

        if (releaseMode && LooksLikeRawOrLocalizationKey(label))
        {
            return fallback;
        }

        return label;
    }

    private static bool LooksLikeRawOrLocalizationKey(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return true;
        }

        if (value.IndexOf('.') >= 0)
        {
            return true;
        }

        return false;
    }
}
