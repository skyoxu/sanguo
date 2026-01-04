using System;
using FluentAssertions;
using Game.Core.Domain.ValueObjects;
using Xunit;

namespace Game.Core.Tests.Domain;

public sealed class SanguoCalendarDateTests
{
    [Fact]
    public void AddDays_ShouldThrowArgumentOutOfRangeException_WhenDaysIsNegative()
    {
        var date = new SanguoCalendarDate(year: 1, month: 1, day: 1);
        Action act = () => _ = date.AddDays(-1);
        act.Should().Throw<ArgumentOutOfRangeException>().WithParameterName("days");
    }

    [Fact]
    public void AddDays_ShouldRollOverMonth_WhenCrossingMonthBoundary()
    {
        var date = new SanguoCalendarDate(year: 1, month: 1, day: 30);
        var next = date.AddDays(1);
        next.Year.Should().Be(1);
        next.Month.Should().Be(2);
        next.Day.Should().Be(1);
    }

    [Fact]
    public void AddDays_ShouldRollOverYear_WhenCrossingYearBoundary()
    {
        var date = new SanguoCalendarDate(year: 1, month: 12, day: 30);
        var next = date.AddDays(1);
        next.Year.Should().Be(2);
        next.Month.Should().Be(1);
        next.Day.Should().Be(1);
    }
}

