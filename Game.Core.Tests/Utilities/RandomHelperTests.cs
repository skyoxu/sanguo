using FluentAssertions;
using Game.Core.Utilities;
using Xunit;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace Game.Core.Tests.Utilities;

public class RandomHelperTests
{
    [Fact]
    public void NextIntShouldReturnValueWithinRange()
    {
        // Arrange & Act
        var results = Enumerable.Range(0, 100)
            .Select(_ => RandomHelper.NextInt(0, 10))
            .ToList();

        // Assert
        results.Should().AllSatisfy(r =>
        {
            r.Should().BeGreaterOrEqualTo(0);
            r.Should().BeLessThan(10);
        });
    }

    [Fact]
    public void NextIntShouldProduceVariedResults()
    {
        // Arrange & Act
        var results = Enumerable.Range(0, 100)
            .Select(_ => RandomHelper.NextInt(0, 100))
            .Distinct()
            .ToList();

        // Assert - Should have at least some variation
        results.Should().HaveCountGreaterThan(10);
    }

    [Fact]
    public void NextDoubleShouldReturnValueBetweenZeroAndOne()
    {
        // Arrange & Act
        var results = Enumerable.Range(0, 100)
            .Select(_ => RandomHelper.NextDouble())
            .ToList();

        // Assert
        results.Should().AllSatisfy(r =>
        {
            r.Should().BeGreaterOrEqualTo(0.0);
            r.Should().BeLessThan(1.0);
        });
    }

    [Fact]
    public void NextDoubleShouldProduceVariedResults()
    {
        // Arrange & Act
        var results = Enumerable.Range(0, 100)
            .Select(_ => RandomHelper.NextDouble())
            .Distinct()
            .ToList();

        // Assert - Should have high variation
        results.Should().HaveCountGreaterThan(90);
    }

    [Fact]
    public async Task RandomHelperShouldBeThreadSafe()
    {
        // Arrange
        var tasks = Enumerable.Range(0, 10)
            .Select(_ => Task.Run(() =>
            {
                var results = new List<int>();
                for (int i = 0; i < 100; i++)
                {
                    results.Add(RandomHelper.NextInt(0, 100));
                }
                return results;
            }))
            .ToArray();

        // Act
        var results = await Task.WhenAll(tasks);

        // Assert - Should not throw and produce valid results
        results.Should().AllSatisfy(list =>
        {
            list.Should().HaveCount(100);
            list.Should().AllSatisfy(r => r.Should().BeInRange(0, 99));
        });
    }
}
