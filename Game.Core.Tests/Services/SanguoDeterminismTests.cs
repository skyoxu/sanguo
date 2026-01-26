using FluentAssertions;
using Game.Core.Services;
using System;
using Xunit;

namespace Game.Core.Tests.Services;

public class SanguoDeterminismTests
{
    [Fact]
    public void ComputeCandidatesSortedIdsHash_ShouldThrow_WhenCandidatesNull()
    {
        Action act = () => SanguoDeterminism.ComputeCandidatesSortedIdsHash((string[])null!);
        act.Should().Throw<ArgumentNullException>();
    }

    [Fact]
    public void ComputeCandidatesSortedIdsHash_ShouldFilterWhitespaceAndSort()
    {
        var unsorted = new[] { "b", " ", "a", "", "c" };
        var expected = SanguoDeterminism.ComputeCandidatesSortedIdsHash(new[] { "a", "b", "c" });

        var hash = SanguoDeterminism.ComputeCandidatesSortedIdsHash(unsorted);
        hash.Should().Be(expected);
    }

    [Fact]
    public void ShouldMatch_WhenUsingOverloads()
    {
        var ids = new[] { "b", "a" };
        var hash1 = SanguoDeterminism.ComputeCandidatesSortedIdsHash(ids);
        var hash2 = SanguoDeterminism.ComputeCandidatesSortedIdsHash((System.Collections.Generic.IReadOnlyList<string>)ids);
        var hash3 = SanguoDeterminism.ComputeCandidatesSortedIdsHash((System.Collections.Generic.IEnumerable<string>)ids);

        hash1.Should().Be(hash2);
        hash2.Should().Be(hash3);
    }
}
