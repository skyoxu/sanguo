using System;
using System.Collections.Generic;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// Task132 split validator: only validates frozen boss count and duration target bands per difficulty.
/// </summary>
public static class BossCountAndDurationTargetValidator
{
    private const string BossCountField = "bossCount";
    private const string DurationMinField = "durationMinMinutes";
    private const string DurationMaxField = "durationMaxMinutes";

    private static readonly IReadOnlyDictionary<string, IReadOnlyDictionary<string, int>> FrozenTargets =
        new Dictionary<string, IReadOnlyDictionary<string, int>>(StringComparer.OrdinalIgnoreCase)
        {
            ["normal"] = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase)
            {
                [BossCountField] = 2,
                [DurationMinField] = 45,
                [DurationMaxField] = 60,
            },
            ["hard"] = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase)
            {
                [BossCountField] = 3,
                [DurationMinField] = 60,
                [DurationMaxField] = 90,
            },
            ["hell"] = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase)
            {
                [BossCountField] = 3,
                [DurationMinField] = 60,
                [DurationMaxField] = 90,
            },
        };

    public static ValidationResult Validate(
        IReadOnlyDictionary<string, IReadOnlyDictionary<string, int>> profiles)
    {
        _ = TryValidate(profiles, out var errors);
        return new ValidationResult(errors.Count == 0, errors);
    }

    public static bool TryValidate(
        IReadOnlyDictionary<string, IReadOnlyDictionary<string, int>> profiles,
        out IReadOnlyList<string> errors)
    {
        var list = new List<string>();

        if (profiles is null)
        {
            list.Add("task132:profiles:null");
            errors = list;
            return false;
        }

        foreach (var (difficulty, expectedProfile) in FrozenTargets)
        {
            if (!profiles.TryGetValue(difficulty, out var actualProfile) || actualProfile is null)
            {
                list.Add($"task132:{difficulty}:missing_profile");
                continue;
            }

            ValidateField(actualProfile, expectedProfile, difficulty, BossCountField, list);
            ValidateField(actualProfile, expectedProfile, difficulty, DurationMinField, list);
            ValidateField(actualProfile, expectedProfile, difficulty, DurationMaxField, list);
        }

        errors = list;
        return list.Count == 0;
    }

    private static void ValidateField(
        IReadOnlyDictionary<string, int> actualProfile,
        IReadOnlyDictionary<string, int> expectedProfile,
        string difficulty,
        string field,
        ICollection<string> errors)
    {
        if (!actualProfile.TryGetValue(field, out var actualValue))
        {
            errors.Add($"task132:{difficulty}:{field}:missing");
            return;
        }

        var expectedValue = expectedProfile[field];
        if (actualValue != expectedValue)
        {
            errors.Add($"task132:{difficulty}:{field}:expected={expectedValue}:actual={actualValue}");
        }
    }

    public sealed record ValidationResult(bool IsValid, IReadOnlyList<string> ErrorCodes);
}
