using System;
using FluentAssertions;
using Game.Core.Domain.ValueObjects;
using Xunit;

namespace Game.Core.Tests.Domain.ValueObjects;

public class CircularMapPositionTests
{
    [Fact]
    public void Advance_WithinBounds_ReturnsCorrectPosition()
    {
        // Arrange
        var position = new CircularMapPosition(5, totalPositions: 15);

        // Act
        var result = position.Advance(3);

        // Assert
        result.Current.Should().Be(8);
    }

    [Fact]
    public void Advance_BeyondBounds_WrapsAroundCorrectly()
    {
        // Arrange
        var position = new CircularMapPosition(12, totalPositions: 15);

        // Act
        var result = position.Advance(5);

        // Assert
        result.Current.Should().Be(2);  // (12 + 5) % 15 = 2
    }

    [Fact]
    public void Advance_NegativeSteps_WrapsAroundCorrectly()
    {
        // Arrange
        var position = new CircularMapPosition(2, totalPositions: 15);

        // Act
        var result = position.Advance(-5);

        // Assert
        result.Current.Should().Be(12); // 2 - 5 = -3, wraps to 12 on a 15-position map
    }

    [Fact]
    public void Advance_FromZero_ReturnsCorrectPosition()
    {
        // Arrange
        var position = new CircularMapPosition(0, totalPositions: 15);

        // Act
        var result = position.Advance(7);

        // Assert
        result.Current.Should().Be(7);
    }

    [Fact]
    public void Advance_FullCircle_ReturnsStartPosition()
    {
        // Arrange
        var position = new CircularMapPosition(5, totalPositions: 15);

        // Act
        var result = position.Advance(15);

        // Assert
        result.Current.Should().Be(5);  // (5 + 15) % 15 = 5
    }

    [Fact]
    public void Advance_MultipleSteps_CalculatesCorrectPath()
    {
        // Arrange
        var position = new CircularMapPosition(10, totalPositions: 15);

        // Act
        var step1 = position.Advance(3);   // 13
        var step2 = step1.Advance(4);      // 2 (13 + 4 = 17, 17 % 15 = 2)

        // Assert
        step1.Current.Should().Be(13);
        step2.Current.Should().Be(2);
    }

    [Fact]
    public void Constructor_WithValidInputs_CreatesPosition()
    {
        // Arrange & Act
        var position = new CircularMapPosition(8, totalPositions: 15);

        // Assert
        position.Current.Should().Be(8);
        position.TotalPositions.Should().Be(15);
    }

    [Fact]
    public void Constructor_WithNegativePosition_ThrowsArgumentOutOfRangeException()
    {
        // Arrange & Act
        var act = () => new CircularMapPosition(-1, totalPositions: 15);

        // Assert
        act.Should().Throw<ArgumentOutOfRangeException>()
            .WithParameterName("current");
    }

    [Fact]
    public void Constructor_WithPositionEqualToTotal_ThrowsArgumentOutOfRangeException()
    {
        // Arrange & Act
        var act = () => new CircularMapPosition(15, totalPositions: 15);

        // Assert
        act.Should().Throw<ArgumentOutOfRangeException>()
            .WithParameterName("current");
    }

    [Fact]
    public void Constructor_WithInvalidTotalPositions_ThrowsArgumentOutOfRangeException()
    {
        // Arrange & Act
        var act = () => new CircularMapPosition(5, totalPositions: 0);

        // Assert
        act.Should().Throw<ArgumentOutOfRangeException>()
            .WithParameterName("totalPositions");
    }
}
