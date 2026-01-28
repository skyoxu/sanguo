using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Xunit;

namespace Game.Core.Tests.Contracts;

public sealed class SanguoEconomyMoneyDeltaAppliedMultipliersContractsTests
{
    // White list: economy events with money deltas must carry AppliedMultipliers snapshots.
    // Non-economy money changes (combat/loot/random events) are intentionally excluded.
    // If a new economy money event is added, append its EventType here and explain the rationale in code review.
    private static readonly string[] EconomyMoneyDeltaEventTypes =
    {
        SanguoCityBought.EventType,
        SanguoCityTollPaid.EventType,
        SanguoCityTollSynergyPaid.EventType, // Uses Breakdown items to carry AppliedMultipliers snapshots.
        SanguoMonthSettled.EventType,
        SanguoSeasonEventApplied.EventType,
        SanguoYearPriceAdjusted.EventType,
    };

    [Fact]
    public void EconomyMoneyDeltaEvents_MustExposeAppliedMultipliersSnapshots()
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
            if (field is null || !field.IsLiteral || field.FieldType != typeof(string))
                continue;

            var eventType = (string)field.GetRawConstantValue()!;
            eventTypeToDtoType.TryAdd(eventType, t).Should().BeTrue($"EventType must be unique (duplicate: {eventType})");
        }

        foreach (var eventType in EconomyMoneyDeltaEventTypes)
        {
            eventTypeToDtoType.TryGetValue(eventType, out var dtoType).Should().BeTrue(
                $"EventType list must match contracts; missing contract for {eventType}");

            var appliedProp = dtoType!.GetProperty("AppliedMultipliers", BindingFlags.Public | BindingFlags.Instance);
            if (appliedProp is not null)
            {
                appliedProp.PropertyType.Should().Be(
                    typeof(AppliedMultipliers),
                    $"{dtoType.Name}.AppliedMultipliers must be a pure contract type");

                dtoType
                    .GetConstructors()
                    .SelectMany(c => c.GetParameters())
                    .Any(p => string.Equals(p.Name, "AppliedMultipliers", StringComparison.Ordinal)
                              || string.Equals(p.Name, "appliedMultipliers", StringComparison.Ordinal))
                    .Should()
                    .BeTrue($"{dtoType.Name} must include appliedMultipliers in its public constructor parameters");
                continue;
            }

            var breakdownProp = dtoType.GetProperty("Breakdown", BindingFlags.Public | BindingFlags.Instance);
            breakdownProp.Should().NotBeNull(
                $"{dtoType.Name} must expose AppliedMultipliers or Breakdown items with AppliedMultipliers for UI snapshots");

            var breakdownItemType = breakdownProp!.PropertyType.GenericTypeArguments.FirstOrDefault();
            breakdownItemType.Should().NotBeNull($"{dtoType.Name}.Breakdown must be a generic list of contract items");

            var itemAppliedProp = breakdownItemType!.GetProperty("AppliedMultipliers", BindingFlags.Public | BindingFlags.Instance);
            itemAppliedProp.Should().NotBeNull(
                $"{dtoType.Name}.Breakdown items must expose AppliedMultipliers for UI snapshots");

            dtoType
                .GetConstructors()
                .SelectMany(c => c.GetParameters())
                .Any(p => string.Equals(p.Name, "Breakdown", StringComparison.Ordinal)
                          || string.Equals(p.Name, "breakdown", StringComparison.Ordinal))
                .Should()
                .BeTrue($"{dtoType.Name} must include breakdown in its public constructor parameters");
        }
    }
}
