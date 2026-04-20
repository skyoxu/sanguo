using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task132SplitTests
{
    // ACC:T132.1
    [Theory]
    [Trait("acceptance", "ACC:T132.1")]
    [InlineData("normal", 2, 45, 60, "bossCount")]
    [InlineData("hard", 3, 60, 90, "durationMinMinutes")]
    [InlineData("hell", 3, 60, 90, "durationMaxMinutes")]
    public void ShouldRejectDifficultyProfile_WhenBossCountOrDurationBandDriftsFromFrozenR6Targets(
        string difficulty,
        int expectedBossCount,
        int expectedDurationMinMinutes,
        int expectedDurationMaxMinutes,
        string mutatedField)
    {
        var profiles = CreateFrozenDifficultyProfiles();
        var mutatedProfile = new Dictionary<string, int>(profiles[difficulty]);

        mutatedProfile[mutatedField] = mutatedField switch
        {
            "bossCount" => expectedBossCount + 1,
            "durationMinMinutes" => expectedDurationMinMinutes - 1,
            "durationMaxMinutes" => expectedDurationMaxMinutes + 1,
            _ => throw new InvalidOperationException($"Unsupported mutated field '{mutatedField}'."),
        };

        profiles[difficulty] = mutatedProfile;

        var result = InvokeValidator(profiles);

        result.IsValid.Should().BeFalse(
            "T132 requires deterministic rejection when a difficulty drifts from the frozen R6 boss-count or duration-target band.");
        result.ErrorCodes.Should().Contain(
            code => code.Contains(difficulty, StringComparison.OrdinalIgnoreCase)
                && code.Contains(mutatedField, StringComparison.OrdinalIgnoreCase),
            $"the validator should name the drifting difficulty '{difficulty}' and field '{mutatedField}' in diagnostics.");
    }

    // ACC:T132.1
    [Fact]
    [Trait("acceptance", "ACC:T132.1")]
    public void ShouldAcceptFrozenDifficultyProfiles_WhenBossCountsAndDurationBandsMatchR6Targets()
    {
        var profiles = CreateFrozenDifficultyProfiles();

        var result = InvokeValidator(profiles);

        result.IsValid.Should().BeTrue();
        result.ErrorCodes.Should().BeEmpty();
    }

    // ACC:T132.2
    [Fact]
    [Trait("acceptance", "ACC:T132.2")]
    public void ShouldIgnoreUnrelatedFields_WhenValidatingBossCountAndDurationTargetsOnly()
    {
        var profiles = CreateFrozenDifficultyProfiles();
        profiles["normal"] = new Dictionary<string, int>(profiles["normal"])
        {
            ["pressureGrowthCap"] = -99,
        };
        profiles["hard"] = new Dictionary<string, int>(profiles["hard"])
        {
            ["regenPerRoundPercent"] = 999,
        };

        var result = InvokeValidator(profiles);

        result.IsValid.Should().BeTrue(
            "Task 132 is a narrow split from T101 and should not absorb unrelated validation scope.");
        result.ErrorCodes.Should().NotContain(
            code => code.Contains("pressureGrowthCap", StringComparison.OrdinalIgnoreCase)
                || code.Contains("regenPerRoundPercent", StringComparison.OrdinalIgnoreCase));
    }

    private static Dictionary<string, IReadOnlyDictionary<string, int>> CreateFrozenDifficultyProfiles()
    {
        return new Dictionary<string, IReadOnlyDictionary<string, int>>(StringComparer.OrdinalIgnoreCase)
        {
            ["normal"] = new Dictionary<string, int>
            {
                ["durationMinMinutes"] = 45,
                ["durationMaxMinutes"] = 60,
                ["bossCount"] = 2,
                ["pressureGrowthCap"] = 5,
            },
            ["hard"] = new Dictionary<string, int>
            {
                ["durationMinMinutes"] = 60,
                ["durationMaxMinutes"] = 90,
                ["bossCount"] = 3,
                ["pressureGrowthCap"] = 8,
            },
            ["hell"] = new Dictionary<string, int>
            {
                ["durationMinMinutes"] = 60,
                ["durationMaxMinutes"] = 90,
                ["bossCount"] = 3,
                ["pressureGrowthCap"] = 12,
            },
        };
    }

    private static ValidationProbeResult InvokeValidator(Dictionary<string, IReadOnlyDictionary<string, int>> profiles)
    {
        var validatorType = FindValidatorTypeOrNull();
        validatorType.Should().NotBeNull(
            "T132 requires a dedicated validator for boss-count and duration-target difficulty profiles.");

        if (validatorType is null)
        {
            return new ValidationProbeResult(IsValid: false, ErrorCodes: Array.Empty<string>());
        }

        var validateMethod = FindValidateMethod(validatorType, profiles);
        if (validateMethod is not null)
        {
            var rawResult = validateMethod.Invoke(null, new object[] { profiles });
            return ConvertValidationResult(rawResult);
        }

        var tryValidateMethod = FindTryValidateMethod(validatorType, profiles);
        tryValidateMethod.Should().NotBeNull(
            "the split validator should expose Validate(...) or TryValidate(...) for deterministic core tests.");

        if (tryValidateMethod is null)
        {
            return new ValidationProbeResult(IsValid: false, ErrorCodes: Array.Empty<string>());
        }

        var args = new object?[] { profiles, null };
        var rawTryValidateResult = tryValidateMethod.Invoke(null, args);
        rawTryValidateResult.Should().BeOfType<bool>();

        return new ValidationProbeResult(
            IsValid: (bool)rawTryValidateResult!,
            ErrorCodes: ReadErrorCodes(args[1]));
    }

    private static Type? FindValidatorTypeOrNull()
    {
        var candidateNames = new[]
        {
            "Game.Core.Services.Sanguo.BossCountAndDurationTargetValidator",
            "Game.Core.Services.Sanguo.BossCountDurationTargetValidator",
            "Game.Core.Services.Sanguo.BossDifficultyDurationTargetValidator",
        };

        foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
        {
            foreach (var candidateName in candidateNames)
            {
                var candidate = assembly.GetType(candidateName, throwOnError: false, ignoreCase: false);
                if (candidate is not null)
                {
                    return candidate;
                }
            }
        }

        return AppDomain.CurrentDomain
            .GetAssemblies()
            .SelectMany(SafeGetTypes)
            .FirstOrDefault(type =>
                type.Name.Contains("Boss", StringComparison.Ordinal)
                && type.Name.Contains("Validator", StringComparison.Ordinal)
                && (type.Name.Contains("Duration", StringComparison.Ordinal)
                    || type.Name.Contains("Target", StringComparison.Ordinal)));
    }

    private static IEnumerable<Type> SafeGetTypes(Assembly assembly)
    {
        try
        {
            return assembly.GetTypes();
        }
        catch (ReflectionTypeLoadException ex)
        {
            return ex.Types.Where(type => type is not null).Cast<Type>();
        }
    }

    private static MethodInfo? FindValidateMethod(
        Type validatorType,
        Dictionary<string, IReadOnlyDictionary<string, int>> profiles)
    {
        return validatorType
            .GetMethods(BindingFlags.Public | BindingFlags.Static)
            .FirstOrDefault(method =>
            {
                if (!string.Equals(method.Name, "Validate", StringComparison.Ordinal))
                {
                    return false;
                }

                var parameters = method.GetParameters();
                return parameters.Length == 1
                    && parameters[0].ParameterType.IsAssignableFrom(profiles.GetType());
            });
    }

    private static MethodInfo? FindTryValidateMethod(
        Type validatorType,
        Dictionary<string, IReadOnlyDictionary<string, int>> profiles)
    {
        return validatorType
            .GetMethods(BindingFlags.Public | BindingFlags.Static)
            .FirstOrDefault(method =>
            {
                if (!string.Equals(method.Name, "TryValidate", StringComparison.Ordinal))
                {
                    return false;
                }

                var parameters = method.GetParameters();
                return parameters.Length == 2
                    && parameters[0].ParameterType.IsAssignableFrom(profiles.GetType())
                    && parameters[1].ParameterType.IsByRef;
            });
    }

    private static ValidationProbeResult ConvertValidationResult(object? rawResult)
    {
        rawResult.Should().NotBeNull("Validate(...) should return a deterministic validation result.");

        if (rawResult is null)
        {
            return new ValidationProbeResult(IsValid: false, ErrorCodes: Array.Empty<string>());
        }

        if (rawResult is bool rawBool)
        {
            return new ValidationProbeResult(IsValid: rawBool, ErrorCodes: Array.Empty<string>());
        }

        var isValidProperty = rawResult.GetType().GetProperty("IsValid", BindingFlags.Public | BindingFlags.Instance);
        isValidProperty.Should().NotBeNull("validation result must expose public property 'IsValid'.");

        if (isValidProperty is null)
        {
            return new ValidationProbeResult(IsValid: false, ErrorCodes: Array.Empty<string>());
        }

        var rawIsValid = isValidProperty.GetValue(rawResult);
        rawIsValid.Should().BeOfType<bool>();

        var errorCodesProperty = rawResult.GetType().GetProperty("ErrorCodes", BindingFlags.Public | BindingFlags.Instance)
            ?? rawResult.GetType().GetProperty("Errors", BindingFlags.Public | BindingFlags.Instance);

        var rawErrorCodes = errorCodesProperty?.GetValue(rawResult);

        return new ValidationProbeResult(
            IsValid: (bool)rawIsValid!,
            ErrorCodes: ReadErrorCodes(rawErrorCodes));
    }

    private static string[] ReadErrorCodes(object? rawErrorCodes)
    {
        if (rawErrorCodes is null)
        {
            return Array.Empty<string>();
        }

        rawErrorCodes.Should().BeAssignableTo<IEnumerable>();

        return ((IEnumerable)rawErrorCodes)
            .Cast<object?>()
            .Where(item => item is not null)
            .Select(item => item!.ToString() ?? string.Empty)
            .Where(item => !string.IsNullOrWhiteSpace(item))
            .ToArray();
    }

    private sealed record ValidationProbeResult(bool IsValid, string[] ErrorCodes);
}
