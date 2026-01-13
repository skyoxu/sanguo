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
            "刘备",
            "desc",
            "res://Assets/Textures/portraits/liu_bei.png",
            new SanguoCharacterEconomy(
                1.0m,
                1.0m,
                1.0m));

        c.CharacterId.Should().Be("c_liu_bei");
        c.Economy.BuyPriceMultiplier.Should().Be(1.0m);
    }
}
