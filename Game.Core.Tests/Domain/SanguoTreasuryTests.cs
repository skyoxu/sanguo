using System;
using FluentAssertions;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Xunit;

namespace Game.Core.Tests.Domain;

public class SanguoTreasuryTests
{
    [Fact]
    public void Deposit_WhenAmountNonNegative_IncreasesMinorUnits()
    {
        var treasury = new SanguoTreasury();

        treasury.Deposit(Money.FromMajorUnits(10));
        treasury.MinorUnits.Should().Be(10 * Money.MinorUnitsPerUnit);
    }
}
