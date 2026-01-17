using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task55CharacterConfigParsingTests
{
    // ACC:T55.1
    [Fact]
    public void CharacterDefinition_ShouldBeConstructible()
    {
        var c = new SanguoCharacterDefinition(
            "c_liu_bei",
            "character.c_liu_bei.name",
            "character.c_liu_bei.desc",
            10,
            "res://Assets/Textures/portraits/liu_bei.png",
            StartingMoneyStepDelta: 0,
            new SanguoEconomyStepDeltas(
                BuyPrice: 0,
                Toll: 0,
                IncomeSettlement: 0,
                BuildCost: 0,
                UpgradeCost: 0));

        c.CharacterId.Should().Be("c_liu_bei");
        c.CombatRating.Should().Be(10);
        c.EconomyStepDeltas.BuyPrice.Should().Be(0);
    }
}
