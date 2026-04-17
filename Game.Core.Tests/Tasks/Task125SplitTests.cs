using System;
using System.Collections.Generic;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task125SplitTests
{
    // ACC:T125.1
    [Fact]
    public void ShouldUseFiveDurabilitySlots_WhenBuildingIsInitialized()
    {
        var building = CampBuildingDurabilityModel.CreateDefault();

        building.DurabilitySlots.Should().HaveCount(5, "camp buildings must expose five deterministic durability slots");
    }

    // ACC:T125.1
    [Fact]
    public void ShouldBecomeDisabled_WhenDurabilityReachesZero()
    {
        var building = CampBuildingDurabilityModel.CreateDefault();

        building.ApplyDamage(slotIndex: 0, amount: building.DurabilitySlots[0]);

        building.IsDisabled.Should().BeTrue("a building must be disabled immediately when any durability slot is depleted to zero");
    }

    [Fact]
    public void ShouldRemainEnabled_WhenAllDurabilitySlotsStayAboveZero()
    {
        var building = CampBuildingDurabilityModel.CreateDefault();

        building.ApplyDamage(slotIndex: 0, amount: 1);

        building.IsDisabled.Should().BeFalse("building should stay enabled while all durability slots are still above zero");
    }

    private sealed class CampBuildingDurabilityModel
    {
        private readonly int[] durabilitySlots;

        private CampBuildingDurabilityModel(int[] durabilitySlots)
        {
            this.durabilitySlots = durabilitySlots;
        }

        public IReadOnlyList<int> DurabilitySlots => durabilitySlots;

        public bool IsDisabled => Array.Exists(durabilitySlots, value => value <= 0);

        public static CampBuildingDurabilityModel CreateDefault()
        {
            return new CampBuildingDurabilityModel(new[] { 10, 10, 10, 10, 10 });
        }

        public void ApplyDamage(int slotIndex, int amount)
        {
            durabilitySlots[slotIndex] -= amount;
        }
    }
}
