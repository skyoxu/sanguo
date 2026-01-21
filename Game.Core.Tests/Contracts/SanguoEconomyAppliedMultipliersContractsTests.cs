using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Xunit;

namespace Game.Core.Tests.Contracts;

public sealed class SanguoEconomyAppliedMultipliersContractsTests
{
    private static readonly HashSet<string> AdditionalMoneyRelatedEventTypes = new(StringComparer.Ordinal)
    {
        "core.sanguo.city.bought",
        "core.sanguo.city.toll.paid",
    };

    private static bool RequiresAppliedMultipliers(string eventType)
        => eventType.StartsWith("core.sanguo.economy.", StringComparison.Ordinal)
           || AdditionalMoneyRelatedEventTypes.Contains(eventType);

    [Fact]
    public void ShouldRequireAppliedMultipliers_WhenEventTypeIsMoneyRelated()
    {
        var assembly = typeof(SanguoCityBought).Assembly;
        var contractTypes = assembly
            .GetTypes()
            .Where(t => t is { IsPublic: true, IsAbstract: false } && t.Namespace == typeof(SanguoCityBought).Namespace)
            .ToArray();

        var eventTypeToDtoType = new Dictionary<string, Type>(StringComparer.Ordinal);
        foreach (var t in contractTypes)
        {
            var field = t.GetField("EventType", BindingFlags.Public | BindingFlags.Static);
            if (field is null)
                continue;

            if (!field.IsLiteral || field.FieldType != typeof(string))
                continue;

            var eventType = (string)field.GetRawConstantValue()!;
            eventTypeToDtoType.TryAdd(eventType, t).Should().BeTrue($"EventType must be unique (duplicate: {eventType})");
        }

        var moneyRelated = eventTypeToDtoType
            .Where(kvp => RequiresAppliedMultipliers(kvp.Key))
            .Select(kvp => kvp.Value)
            .OrderBy(t => t.Name, StringComparer.Ordinal)
            .ToArray();

        moneyRelated.Should().NotBeEmpty("at least one money-related event contract is expected");

        foreach (var dtoType in moneyRelated)
        {
            var appliedProp = dtoType.GetProperty("AppliedMultipliers", BindingFlags.Public | BindingFlags.Instance);
            appliedProp.Should().NotBeNull($"{dtoType.Name} must expose AppliedMultipliers for replayable UI snapshots");
            appliedProp!.PropertyType.Should().Be(typeof(AppliedMultipliers), $"{dtoType.Name}.AppliedMultipliers must be a pure contract type");

            dtoType
                .GetConstructors()
                .SelectMany(c => c.GetParameters())
                .Any(p => string.Equals(p.Name, "AppliedMultipliers", StringComparison.Ordinal)
                          || string.Equals(p.Name, "appliedMultipliers", StringComparison.Ordinal))
                .Should()
                .BeTrue($"{dtoType.Name} must include appliedMultipliers in its public constructor parameters");
        }
    }
}
