using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task119RewardDraftCandidateDeterminismTests
{
    // ACC:T119.1
    [Fact]
    public async Task ShouldReturnExactlyThreeStableCandidates_WhenGeneratingDraftFromSameInputs()
    {
        var first = await TryGenerateRewardDraftCandidatesAsync();
        var second = await TryGenerateRewardDraftCandidatesAsync();

        first.Failure.Should().BeNullOrWhiteSpace($"reward draft probe failed: {first.Failure}");
        second.Failure.Should().BeNullOrWhiteSpace($"reward draft probe failed: {second.Failure}");

        first.CandidateIds.Should().HaveCount(3, "reward draft must expose exactly three candidate choices");
        second.CandidateIds.Should().HaveCount(3, "reward draft must expose exactly three candidate choices");
        first.CandidateIds.Should().OnlyHaveUniqueItems("each draft choice should map to a distinct candidate");
        second.CandidateIds.Should().OnlyHaveUniqueItems("each draft choice should map to a distinct candidate");
        second.CandidateIds.Should().Equal(first.CandidateIds, "the same reward draft inputs must produce a stable deterministic candidate order");
    }

    private static async Task<RewardDraftProbeResult> TryGenerateRewardDraftCandidatesAsync()
    {
        try
        {
            var assembly = typeof(EventTypes).Assembly;
            var rewardDraftType = assembly.GetTypes()
                .Where(type => type.Name.Contains("RewardDraft", StringComparison.OrdinalIgnoreCase))
                .OrderBy(type => type.FullName, StringComparer.Ordinal)
                .FirstOrDefault();

            if (rewardDraftType is null)
            {
                return RewardDraftProbeResult.Fail("No RewardDraft implementation type was found in Game.Core.");
            }

            var method = FindCandidateGenerationMethod(rewardDraftType);
            if (method is null)
            {
                return RewardDraftProbeResult.Fail($"Type '{rewardDraftType.FullName}' does not expose a supported candidate generation method.");
            }

            object? target = null;
            if (!method.IsStatic && !TryCreateValue(rewardDraftType, rewardDraftType.Name, out target))
            {
                return RewardDraftProbeResult.Fail($"Type '{rewardDraftType.FullName}' could not be instantiated for the deterministic candidate probe.");
            }

            var args = BuildArguments(method.GetParameters());
            if (args is null)
            {
                return RewardDraftProbeResult.Fail($"Method '{rewardDraftType.FullName}.{method.Name}' has unsupported parameters for the deterministic candidate probe.");
            }

            var rawResult = method.Invoke(target, args);
            var candidateIds = await ExtractCandidateIdsAsync(rawResult).ConfigureAwait(false);

            return candidateIds.Count == 0
                ? RewardDraftProbeResult.Fail($"Method '{rewardDraftType.FullName}.{method.Name}' did not yield any candidate ids.")
                : RewardDraftProbeResult.Success(candidateIds);
        }
        catch (ReflectionTypeLoadException ex)
        {
            var message = ex.LoaderExceptions.FirstOrDefault(loaderException => loaderException is not null)?.Message ?? ex.Message;
            return RewardDraftProbeResult.Fail(message);
        }
        catch (TargetInvocationException ex)
        {
            return RewardDraftProbeResult.Fail(ex.InnerException?.Message ?? ex.Message);
        }
        catch (Exception ex)
        {
            return RewardDraftProbeResult.Fail(ex.Message);
        }
    }

    private static MethodInfo? FindCandidateGenerationMethod(Type rewardDraftType)
    {
        return rewardDraftType
            .GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static)
            .Where(method =>
                method.Name.Equals("GenerateCandidates", StringComparison.OrdinalIgnoreCase) ||
                method.Name.Equals("GenerateDraftCandidates", StringComparison.OrdinalIgnoreCase) ||
                method.Name.Equals("CreateCandidates", StringComparison.OrdinalIgnoreCase) ||
                method.Name.Equals("CreateDraftCandidates", StringComparison.OrdinalIgnoreCase) ||
                method.Name.Equals("BuildCandidates", StringComparison.OrdinalIgnoreCase) ||
                method.Name.Equals("BuildRewardOffer", StringComparison.OrdinalIgnoreCase) ||
                method.Name.Equals("PresentRewardOffer", StringComparison.OrdinalIgnoreCase) ||
                (method.Name.Contains("Generate", StringComparison.OrdinalIgnoreCase) && method.Name.Contains("Candidate", StringComparison.OrdinalIgnoreCase)) ||
                (method.Name.Contains("Reward", StringComparison.OrdinalIgnoreCase) && method.Name.Contains("Offer", StringComparison.OrdinalIgnoreCase)))
            .OrderBy(method => method.GetParameters().Length)
            .ThenBy(method => method.Name, StringComparer.Ordinal)
            .FirstOrDefault();
    }

    private static object[]? BuildArguments(ParameterInfo[] parameters)
    {
        var args = new object?[parameters.Length];
        for (var index = 0; index < parameters.Length; index++)
        {
            var parameter = parameters[index];
            if (parameter.HasDefaultValue)
            {
                var defaultValue = parameter.DefaultValue;
                args[index] = defaultValue is DBNull or null ? GetDefaultValue(parameter.ParameterType) : defaultValue;
                continue;
            }

            if (!TryCreateValue(parameter.ParameterType, parameter.Name ?? string.Empty, out var value))
            {
                return null;
            }

            args[index] = value;
        }

        return args!;
    }

    private static bool TryCreateValue(Type type, string name, out object? value, int depth = 0)
    {
        value = null;
        if (depth > 4)
        {
            return false;
        }

        var underlyingType = Nullable.GetUnderlyingType(type);
        if (underlyingType is not null)
        {
            return TryCreateValue(underlyingType, name, out value, depth + 1);
        }

        if (type == typeof(string))
        {
            value = BuildStringValue(name);
            return true;
        }

        if (type == typeof(int))
        {
            value = name.Contains("count", StringComparison.OrdinalIgnoreCase) || name.Contains("choice", StringComparison.OrdinalIgnoreCase)
                ? 3
                : 119;
            return true;
        }

        if (type == typeof(long))
        {
            value = name.Contains("count", StringComparison.OrdinalIgnoreCase) || name.Contains("choice", StringComparison.OrdinalIgnoreCase)
                ? 3L
                : 119L;
            return true;
        }

        if (type == typeof(bool))
        {
            value = false;
            return true;
        }

        if (type == typeof(double))
        {
            value = 119d;
            return true;
        }

        if (type == typeof(float))
        {
            value = 119f;
            return true;
        }

        if (type == typeof(decimal))
        {
            value = 119m;
            return true;
        }

        if (type == typeof(Guid))
        {
            value = Guid.Parse("00000000-0000-0000-0000-000000000119");
            return true;
        }

        if (type == typeof(DateTime))
        {
            value = new DateTime(2026, 4, 25, 0, 0, 0, DateTimeKind.Utc);
            return true;
        }

        if (type == typeof(CancellationToken))
        {
            value = CancellationToken.None;
            return true;
        }

        if (type == typeof(Random))
        {
            value = new Random(119);
            return true;
        }

        if (type == typeof(SanguoActionCardsCatalog))
        {
            value = BuildActionCardsCatalog();
            return true;
        }

        if (type == typeof(SanguoRelicsCatalog))
        {
            value = BuildRelicsCatalog();
            return true;
        }

        if (type.IsEnum)
        {
            value = Enum.GetValues(type).GetValue(0);
            return true;
        }

        if (TryCreateCollection(type, out value))
        {
            return true;
        }

        if (TryCreateCustomObject(type, out value, depth + 1))
        {
            return true;
        }

        return false;
    }

    private static bool TryCreateCollection(Type type, out object? value)
    {
        value = null;

        if (type.IsArray)
        {
            var elementType = type.GetElementType();
            if (elementType is null || !TryCreateSequence(elementType, out var arrayItems))
            {
                return false;
            }

            var array = Array.CreateInstance(elementType, arrayItems.Count);
            for (var index = 0; index < arrayItems.Count; index++)
            {
                array.SetValue(arrayItems[index], index);
            }

            value = array;
            return true;
        }

        if (!type.IsGenericType)
        {
            return false;
        }

        var elementTypeArgument = type.GetGenericArguments().SingleOrDefault();
        if (elementTypeArgument is null || !TryCreateSequence(elementTypeArgument, out var listItems))
        {
            return false;
        }

        var listType = typeof(List<>).MakeGenericType(elementTypeArgument);
        var list = (IList)Activator.CreateInstance(listType)!;
        foreach (var item in listItems)
        {
            list.Add(item);
        }

        value = list;
        return true;
    }

    private static bool TryCreateSequence(Type elementType, out List<object?> items)
    {
        items = new List<object?>();

        if (elementType == typeof(SanguoActionCardCatalogEntry))
        {
            items.AddRange(BuildActionCardsCatalog().Cards.Cast<object?>());
            return true;
        }

        if (elementType == typeof(SanguoRelicDefinition))
        {
            items.AddRange(BuildRelicsCatalog().Relics.Cast<object?>());
            return true;
        }

        if (elementType == typeof(string))
        {
            items.Add("reward.alpha");
            items.Add("reward.beta");
            items.Add("reward.gamma");
            items.Add("reward.delta");
            return true;
        }

        return false;
    }

    private static bool TryCreateCustomObject(Type type, out object? value, int depth)
    {
        value = null;
        if (type.IsAbstract || type.IsInterface || type.Assembly != typeof(EventTypes).Assembly)
        {
            return false;
        }

        var constructors = type
            .GetConstructors(BindingFlags.Public | BindingFlags.Instance)
            .OrderBy(constructor => constructor.GetParameters().Length)
            .ToArray();

        foreach (var constructor in constructors)
        {
            var parameters = constructor.GetParameters();
            var args = new object?[parameters.Length];
            var supported = true;

            for (var index = 0; index < parameters.Length; index++)
            {
                var parameter = parameters[index];
                if (!TryCreateValue(parameter.ParameterType, parameter.Name ?? string.Empty, out var argument, depth + 1))
                {
                    supported = false;
                    break;
                }

                args[index] = argument;
            }

            if (supported)
            {
                value = constructor.Invoke(args);
                return true;
            }
        }

        var parameterlessConstructor = type.GetConstructor(Type.EmptyTypes);
        if (parameterlessConstructor is null)
        {
            return false;
        }

        var instance = parameterlessConstructor.Invoke(Array.Empty<object>());
        foreach (var property in type.GetProperties(BindingFlags.Public | BindingFlags.Instance).Where(property => property.CanWrite))
        {
            if (TryCreateValue(property.PropertyType, property.Name, out var propertyValue, depth + 1))
            {
                property.SetValue(instance, propertyValue);
            }
        }

        value = instance;
        return true;
    }

    private static async Task<IReadOnlyList<string>> ExtractCandidateIdsAsync(object? rawResult)
    {
        var result = await UnwrapAsync(rawResult).ConfigureAwait(false);
        return ExtractCandidateIds(result);
    }

    private static async Task<object?> UnwrapAsync(object? value)
    {
        if (value is null)
        {
            return null;
        }

        if (value is Task task)
        {
            await task.ConfigureAwait(false);
            return task.GetType().IsGenericType
                ? task.GetType().GetProperty("Result", BindingFlags.Public | BindingFlags.Instance)?.GetValue(task)
                : null;
        }

        var valueType = value.GetType();
        if (valueType.FullName is not null && valueType.FullName.StartsWith("System.Threading.Tasks.ValueTask", StringComparison.Ordinal))
        {
            var asTaskMethod = valueType.GetMethod("AsTask", BindingFlags.Public | BindingFlags.Instance, binder: null, Type.EmptyTypes, modifiers: null);
            if (asTaskMethod is not null)
            {
                var taskValue = asTaskMethod.Invoke(value, Array.Empty<object>());
                return await UnwrapAsync(taskValue).ConfigureAwait(false);
            }
        }

        return value;
    }

    private static IReadOnlyList<string> ExtractCandidateIds(object? result)
    {
        if (result is null)
        {
            return Array.Empty<string>();
        }

        if (TryGetNamedValue(result, out var nestedCollection, "CandidateIds", "Candidates", "Choices", "Rewards", "Options", "Entries", "Items"))
        {
            var nestedIds = ExtractCandidateIds(nestedCollection);
            if (nestedIds.Count > 0)
            {
                return nestedIds;
            }
        }

        if (result is IEnumerable enumerable and not string)
        {
            var ids = new List<string>();
            foreach (var item in enumerable)
            {
                var candidateId = ExtractCandidateId(item);
                if (!string.IsNullOrWhiteSpace(candidateId))
                {
                    ids.Add(candidateId!);
                }
            }

            return ids;
        }

        var singleId = ExtractCandidateId(result);
        return string.IsNullOrWhiteSpace(singleId)
            ? Array.Empty<string>()
            : new[] { singleId! };
    }

    private static string? ExtractCandidateId(object? candidate)
    {
        if (candidate is null)
        {
            return null;
        }

        if (candidate is string text)
        {
            return text;
        }

        if (TryGetNamedValue(candidate, out var directId, "CandidateId", "RewardId", "Id", "CardId", "RelicId", "ItemId", "NameKey"))
        {
            return Convert.ToString(directId);
        }

        if (TryGetNamedValue(candidate, out var nestedValue, "Reward", "Candidate", "Choice", "Option"))
        {
            return ExtractCandidateId(nestedValue);
        }

        return null;
    }

    private static bool TryGetNamedValue(object source, out object? value, params string[] candidateNames)
    {
        var sourceType = source.GetType();
        foreach (var candidateName in candidateNames)
        {
            var property = sourceType.GetProperty(candidateName, BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
            if (property is not null)
            {
                value = property.GetValue(source);
                return true;
            }

            var field = sourceType.GetField(candidateName, BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
            if (field is not null)
            {
                value = field.GetValue(source);
                return true;
            }
        }

        value = null;
        return false;
    }

    private static object? GetDefaultValue(Type type)
    {
        return type.IsValueType ? Activator.CreateInstance(type) : null;
    }

    private static string BuildStringValue(string name)
    {
        if (name.Contains("source", StringComparison.OrdinalIgnoreCase))
        {
            return "objective_reward";
        }

        if (name.Contains("fingerprint", StringComparison.OrdinalIgnoreCase))
        {
            return "fp-task-119";
        }

        if (name.Contains("pack", StringComparison.OrdinalIgnoreCase))
        {
            return "pack.core";
        }

        if (name.Contains("player", StringComparison.OrdinalIgnoreCase))
        {
            return "p1";
        }

        if (name.Contains("run", StringComparison.OrdinalIgnoreCase))
        {
            return "run-119";
        }

        if (name.Contains("correlation", StringComparison.OrdinalIgnoreCase))
        {
            return "corr-task-119";
        }

        if (name.Contains("causation", StringComparison.OrdinalIgnoreCase))
        {
            return "ut.task119";
        }

        if (name.Contains("content", StringComparison.OrdinalIgnoreCase))
        {
            return "content-task-119";
        }

        return string.IsNullOrWhiteSpace(name) ? "task119" : $"{name}_task119";
    }

    private static SanguoActionCardsCatalog BuildActionCardsCatalog()
    {
        return new SanguoActionCardsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Cards: Array.AsReadOnly(new[]
            {
                new SanguoActionCardCatalogEntry(
                    CardId: "ac_alpha",
                    NameKey: "card.ac_alpha.name",
                    DescriptionKey: "card.ac_alpha.desc",
                    EffectKind: "economyStepDelta",
                    StepDelta: -1,
                    DurationRounds: 3),
                new SanguoActionCardCatalogEntry(
                    CardId: "ac_beta",
                    NameKey: "card.ac_beta.name",
                    DescriptionKey: "card.ac_beta.desc",
                    EffectKind: "economyStepDelta",
                    StepDelta: 1,
                    DurationRounds: 3),
                new SanguoActionCardCatalogEntry(
                    CardId: "ac_gamma",
                    NameKey: "card.ac_gamma.name",
                    DescriptionKey: "card.ac_gamma.desc",
                    EffectKind: "economyStepDelta",
                    StepDelta: 2,
                    DurationRounds: 3),
                new SanguoActionCardCatalogEntry(
                    CardId: "ac_delta",
                    NameKey: "card.ac_delta.name",
                    DescriptionKey: "card.ac_delta.desc",
                    EffectKind: "economyStepDelta",
                    StepDelta: -2,
                    DurationRounds: 3),
            }));
    }

    private static SanguoRelicsCatalog BuildRelicsCatalog()
    {
        return new SanguoRelicsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Relics: Array.AsReadOnly(new[]
            {
                new SanguoRelicDefinition(
                    RelicId: "relic_alpha",
                    NameKey: "relic.alpha.name",
                    DescriptionKey: "relic.alpha.desc",
                    EffectKind: "economyStepDelta",
                    MoneyDelta: null,
                    EconomyStepDelta: 1),
                new SanguoRelicDefinition(
                    RelicId: "relic_beta",
                    NameKey: "relic.beta.name",
                    DescriptionKey: "relic.beta.desc",
                    EffectKind: "moneyDelta",
                    MoneyDelta: 100,
                    EconomyStepDelta: null),
                new SanguoRelicDefinition(
                    RelicId: "relic_gamma",
                    NameKey: "relic.gamma.name",
                    DescriptionKey: "relic.gamma.desc",
                    EffectKind: "economyStepDelta",
                    MoneyDelta: null,
                    EconomyStepDelta: 2),
                new SanguoRelicDefinition(
                    RelicId: "relic_delta",
                    NameKey: "relic.delta.name",
                    DescriptionKey: "relic.delta.desc",
                    EffectKind: "moneyDelta",
                    MoneyDelta: 200,
                    EconomyStepDelta: null),
            }));
    }

    private sealed record RewardDraftProbeResult(IReadOnlyList<string> CandidateIds, string? Failure)
    {
        public static RewardDraftProbeResult Success(IReadOnlyList<string> candidateIds) => new(candidateIds, null);

        public static RewardDraftProbeResult Fail(string failure) => new(Array.Empty<string>(), failure);
    }
}
