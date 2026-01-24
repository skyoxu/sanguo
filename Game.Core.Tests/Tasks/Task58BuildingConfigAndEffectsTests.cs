using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task58BuildingConfigAndEffectsTests
{
    // ACC:T58.1
    // ACC:T58.2
    // ACC:T58.4
    [Fact]
    public void ShouldExposeEconomyStepDeltas_WhenCreatingBuildingDefinition()
    {
        var b = new SanguoBuildingDefinition(
            BuildingId: "building_house",
            NameKey: "building.building_house.name",
            DescriptionKey: "building.building_house.desc",
            MaxLevel: 3,
            BuildCostBase: 300,
            UpgradeCostBase: 200,
            SettlementIncomeBase: 50,
            EconomyStepDeltas: new SanguoEconomyStepDeltas(
                BuyPrice: 0,
                Toll: 1,
                IncomeSettlement: 1,
                BuildCost: 0,
                UpgradeCost: 0));

        b.BuildingId.Should().Be("building_house");
        b.MaxLevel.Should().Be(3);
        b.EconomyStepDeltas.Toll.Should().Be(1);
    }
}
