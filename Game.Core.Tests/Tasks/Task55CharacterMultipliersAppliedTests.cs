using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task55CharacterMultipliersAppliedTests
{
    // ACC:T55.3
    [Fact]
    public void CharacterEconomy_Multipliers_ShouldDefaultToValidRange()
    {
        var econ = new SanguoCharacterEconomy(1.0m, 1.0m, 1.0m);
        econ.BuyPriceMultiplier.Should().Be(1.0m);
        econ.TollMultiplier.Should().Be(1.0m);
        econ.MonthSettlementMultiplier.Should().Be(1.0m);
    }
}

