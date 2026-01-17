using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task55CharacterMultipliersAppliedTests
{
    // ACC:T55.3
    [Fact]
    public void CharacterEconomy_StepDeltas_ShouldBeConstructible()
    {
        var deltas = new SanguoEconomyStepDeltas(
            BuyPrice: 0,
            Toll: 0,
            IncomeSettlement: 0,
            BuildCost: 0,
            UpgradeCost: 0);

        deltas.Toll.Should().Be(0);
    }
}
