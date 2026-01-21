using System;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task55CharacterEventSnapshotTests
{
    // ACC:T55.7
    [Fact]
    public void ShouldBeStableAndReproducible_WhenBuildingTollPaidEventSnapshot()
    {
        var first = BuildTollPaidSnapshot();
        var second = BuildTollPaidSnapshot();

        first.Should().Be(second);

        first.Amount.Should().Be(100m);
        first.AppliedMultipliers.Sources.Should().Be(AppliedMultiplierSources.Character);
        first.AppliedMultipliers.EffectiveMultiplier.Should().Be(first.AppliedMultipliers.EffectiveSteps * AppliedMultipliers.Step);
        SanguoCityTollPaid.EventType.Should().Be("core.sanguo.city.toll.paid");
    }

    [Fact]
    public void ShouldExposeCloudEventTypes_WhenReferencingContracts()
    {
        SanguoGameStarted.EventType.Should().Be("core.sanguo.game.started");
        SanguoCityTollPaid.EventType.Should().Be("core.sanguo.city.toll.paid");
    }

    [Theory]
    [InlineData(0, AppliedMultipliers.MinSteps)]
    [InlineData(999, AppliedMultipliers.MaxSteps)]
    public void ShouldClampToBounds_WhenClampStepsOutOfRange(int value, int expected)
    {
        AppliedMultipliers.ClampSteps(value).Should().Be(expected);
    }

    [Fact]
    public void ShouldIdentifyHalfStepValues_WhenValidatingMultiplierFormat()
    {
        AppliedMultipliers.IsHalfStepMultiplier(1.5m).Should().BeTrue();
        AppliedMultipliers.IsHalfStepMultiplier(1.25m).Should().BeFalse();
    }

    private static SanguoCityTollPaid BuildTollPaidSnapshot()
    {
        var multipliers = new AppliedMultipliers(
            BaseSteps: AppliedMultipliers.BaseDefaultSteps,
            CharacterStepDelta: 1,
            BuildingStepDelta: 0,
            EventStepDelta: 0,
            ActionCardStepDelta: 0,
            RelicStepDelta: 0,
            RegionStepDelta: 0,
            EffectiveSteps: 3,
            Sources: AppliedMultiplierSources.Character);

        return new SanguoCityTollPaid(
            GameId: "game-001",
            TurnNumber: 1,
            PayerId: "p1",
            OwnerId: "p2",
            CityId: "city-001",
            Amount: 100m,
            OwnerAmount: 80m,
            TreasuryOverflow: 20m,
            OccurredAt: new DateTimeOffset(2026, 1, 1, 0, 0, 0, TimeSpan.Zero),
            CorrelationId: "corr-001",
            CausationId: "cause-001",
            AppliedMultipliers: multipliers);
    }
}
