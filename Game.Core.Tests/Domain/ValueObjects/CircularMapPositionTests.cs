using System;
using System.Collections.Generic;
using System.Linq;
using FluentAssertions;
using Game.Core.Domain.ValueObjects;
using Xunit;
namespace Game.Core.Tests.Domain.ValueObjects;
public class CircularMapPositionTests
{
    [Fact]
    public void ShouldReturnCorrectPosition_WhenAdvancingWithinBounds()
    {
        // Arrange
        var position = new CircularMapPosition(5, totalPositions: 15);
        // Act
        var result = position.Advance(3);
        // Assert
        result.Current.Should().Be(8);
    }

    // ACC:T2.1
    [Fact]
    public void ShouldAdvanceWithinBoundsAndNotReferenceCity_WhenUsingCircularMapPosition()
    {
        static bool ContainsType(Type type, Type needle)
        {
            if (type == needle)
                return true;
            if (type.IsArray)
                return ContainsType(type.GetElementType()!, needle);
            if (type.IsGenericType)
            {
                foreach (var a in type.GetGenericArguments())
                {
                    if (ContainsType(a, needle))
                        return true;
                }
            }

            return false;
        }

        var position = new CircularMapPosition(5, totalPositions: 15);
        var result = position.Advance(3);
        result.Current.Should().Be(8);

        var cityType = typeof(Game.Core.Domain.City);
        var inspectedTypes = new List<Type>();
        var flags = System.Reflection.BindingFlags.Instance
            | System.Reflection.BindingFlags.Static
            | System.Reflection.BindingFlags.Public
            | System.Reflection.BindingFlags.NonPublic;
        var t = typeof(CircularMapPosition);

        foreach (var f in t.GetFields(flags))
            inspectedTypes.Add(f.FieldType);
        foreach (var p in t.GetProperties(flags))
            inspectedTypes.Add(p.PropertyType);
        foreach (var c in t.GetConstructors(flags))
            inspectedTypes.AddRange(c.GetParameters().Select(x => x.ParameterType));
        foreach (var m in t.GetMethods(flags))
        {
            inspectedTypes.Add(m.ReturnType);
            inspectedTypes.AddRange(m.GetParameters().Select(x => x.ParameterType));

            var body = m.GetMethodBody();
            if (body is not null)
            {
                foreach (var local in body.LocalVariables)
                    inspectedTypes.Add(local.LocalType);
                foreach (var clause in body.ExceptionHandlingClauses)
                {
                    if (clause.CatchType is not null)
                        inspectedTypes.Add(clause.CatchType);
                }
            }
        }

        var referencesCity = inspectedTypes.Any(x => ContainsType(x, cityType));
        referencesCity.Should().BeFalse("Task 2 must not introduce City dependency; City is introduced in Task 3");
    }
    [Fact]
    public void ShouldWrapAround_WhenAdvancingBeyondBounds()
    {
        // Arrange
        var position = new CircularMapPosition(12, totalPositions: 15);
        // Act
        var result = position.Advance(5);
        // Assert
        result.Current.Should().Be(2);  // (12 + 5) % 15 = 2
    }

    // ACC:T2.3
    [Fact]
    public void ShouldReturnVisitedIndexPath_WhenGettingPathSequence()
    {
        var position = new CircularMapPosition(5, totalPositions: 15);
        position.GetPath(3).Should().Equal(6, 7, 8);
        position.GetPath(-5).Should().Equal(4, 3, 2, 1, 0);

        var nearEnd = new CircularMapPosition(13, totalPositions: 15);
        nearEnd.GetPath(4).Should().Equal(14, 0, 1, 2);
        nearEnd.GetPath(-4).Should().Equal(12, 11, 10, 9);
    }
    // ACC:T2.2
    [Fact]
    public void ShouldNotReferenceGodotAssemblies_WhenUsingCircularMapPosition()
    {
        var referenced = typeof(CircularMapPosition).Assembly.GetReferencedAssemblies();
        referenced.Should().NotContain(a => a.Name != null && a.Name.StartsWith("Godot", StringComparison.OrdinalIgnoreCase));
    }
    [Fact]
    public void ShouldWrapAround_WhenAdvancingWithNegativeSteps()
    {
        // Arrange
        var position = new CircularMapPosition(2, totalPositions: 15);
        // Act
        var result = position.Advance(-5);
        // Assert
        result.Current.Should().Be(12); // 2 - 5 = -3, wraps to 12 on a 15-position map
    }
    [Fact]
    public void ShouldReturnCorrectPosition_WhenAdvancingFromZero()
    {
        // Arrange
        var position = new CircularMapPosition(0, totalPositions: 15);
        // Act
        var result = position.Advance(7);
        // Assert
        result.Current.Should().Be(7);
    }
    [Fact]
    public void ShouldReturnStartPosition_WhenAdvancingFullCircle()
    {
        // Arrange
        var position = new CircularMapPosition(5, totalPositions: 15);
        // Act
        var result = position.Advance(15);
        // Assert
        result.Current.Should().Be(5);  // (5 + 15) % 15 = 5
    }
    [Fact]
    public void ShouldCalculateCorrectPath_WhenAdvancingMultipleSteps()
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
    public void ShouldReturnSamePosition_WhenStepsIsZero()
    {
        // Arrange
        var position = new CircularMapPosition(5, totalPositions: 15);
        // Act
        var result = position.Advance(0);
        // Assert
        result.Current.Should().Be(5);
    }
    [Fact]
    public void ShouldCreatePosition_WhenInputsAreValid()
    {
        // Arrange & Act
        var position = new CircularMapPosition(8, totalPositions: 15);
        // Assert
        position.Current.Should().Be(8);
        position.TotalPositions.Should().Be(15);
    }
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenPositionIsNegative()
    {
        // Arrange & Act
        var act = () => new CircularMapPosition(-1, totalPositions: 15);
        // Assert
        act.Should().Throw<ArgumentOutOfRangeException>()
            .WithParameterName("current");
    }
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenPositionEqualsTotalPositions()
    {
        // Arrange & Act
        var act = () => new CircularMapPosition(15, totalPositions: 15);
        // Assert
        act.Should().Throw<ArgumentOutOfRangeException>()
            .WithParameterName("current");
    }
    [Fact]
    public void ShouldThrowArgumentOutOfRangeException_WhenTotalPositionsIsInvalid()
    {
        // Arrange & Act
        var act = () => new CircularMapPosition(5, totalPositions: 0);
        // Assert
        act.Should().Throw<ArgumentOutOfRangeException>()
            .WithParameterName("totalPositions");
    }
    [Fact]
    public void ShouldHandleOverflow_WhenStepsNearIntMax()
    {
        // Arrange: Position that when combined with large steps would overflow int
        var position = new CircularMapPosition(10, totalPositions: 15);
        // Act: Steps that would cause overflow in int arithmetic
        // (10 + 2147483642) would overflow int.MaxValue
        var result = position.Advance(int.MaxValue - 5);
        // Assert: Using long arithmetic, ((long)10 + 2147483642) % 15 = 12
        result.Current.Should().Be(12);
    }
    [Fact]
    public void ShouldHandleUnderflow_WhenStepsIsIntMinValue()
    {
        // Arrange
        var position = new CircularMapPosition(5, totalPositions: 15);
        // Act: Large negative steps (int.MinValue = -2147483648)
        var result = position.Advance(int.MinValue);
        // Assert: ((long)5 + (-2147483648)) % 15 should give correct positive result
        // Result should be in valid range [0, 14]
        result.Current.Should().BeInRange(0, 14);
        // Specifically: (5 - 2147483648) % 15 = 12 after proper wrapping
        result.Current.Should().Be(12);
    }
    [Fact]
    public void ShouldWrapMultipleTimes_WhenStepsIsVeryLargePositive()
    {
        // Arrange
        var position = new CircularMapPosition(5, totalPositions: 15);
        // Act: Steps much larger than total positions (many full circles)
        var result = position.Advance(1000000003);
        // Assert: (5 + 1000000003) % 15 = 1000000008 % 15 = 3
        result.Current.Should().Be(3);
    }
    [Fact]
    public void ShouldWrapMultipleTimes_WhenStepsIsVeryLargeNegative()
    {
        // Arrange
        var position = new CircularMapPosition(5, totalPositions: 15);
        // Act: Large negative steps (many full circles backward)
        var result = position.Advance(-1000000007);
        // Assert: (5 - 1000000007) % 15 = -1000000002 % 15 = 3 after wrapping
        result.Current.Should().Be(3);
    }
}
