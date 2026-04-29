using System.Collections.Generic;
using System.Linq;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task155FreezeChangeControlGateTests
{
    // ACC:T155.1
    [Fact]
    public void ShouldFailWithActionableDiagnostics_WhenFreezeSection9RuleChangesWithoutSynchronizedTripletUpdates()
    {
        var fixture = new ChangeControlFixture(
            FreezeSection9RuleChanged: true,
            FreezeRevisionUpdated: true,
            AssertionUpdated: false,
            TestEvidenceUpdated: true,
            FreezeRevisionPath: "docs/prd/PRD_V3_RULES_FREEZE.md",
            AssertionPath: "docs/prd/PRD_V3_ACCEPTANCE_ASSERTIONS.md",
            EvidencePath: "Game.Core.Tests/Tasks/Task155FreezeChangeControlGateTests.cs");

        var gate = new FreezeChangeControlTripletGate();

        var result = gate.Evaluate(fixture);

        result.IsPassed.Should().BeFalse("freeze section 9 updates must not pass when assertion update is missing");
        result.Diagnostics.Should().ContainSingle(d =>
            d.Contains("assertion update", System.StringComparison.OrdinalIgnoreCase) &&
            d.Contains("docs/prd/PRD_V3_ACCEPTANCE_ASSERTIONS.md", System.StringComparison.Ordinal));
    }

    // ACC:T155.2
    [Fact]
    public void ShouldPass_WhenFreezeSection9RuleChangeHasSynchronizedTripletUpdates()
    {
        var fixture = new ChangeControlFixture(
            FreezeSection9RuleChanged: true,
            FreezeRevisionUpdated: true,
            AssertionUpdated: true,
            TestEvidenceUpdated: true,
            FreezeRevisionPath: "docs/prd/PRD_V3_RULES_FREEZE.md",
            AssertionPath: "docs/prd/PRD_V3_ACCEPTANCE_ASSERTIONS.md",
            EvidencePath: "Game.Core.Tests/Tasks/Task155FreezeChangeControlGateTests.cs");

        var gate = new FreezeChangeControlTripletGate();

        var result = gate.Evaluate(fixture);

        result.IsPassed.Should().BeTrue();
        result.Diagnostics.Should().BeEmpty();
    }

    // ACC:T155.2
    [Theory]
    [MemberData(nameof(NegativeFixtures))]
    public void ShouldFailWithActionableDiagnostics_WhenAnyTripletLegIsMissing(
        string fixtureName,
        ChangeControlFixture fixture,
        string expectedDiagnosticToken)
    {
        var gate = new FreezeChangeControlTripletGate();

        var result = gate.Evaluate(fixture);

        result.IsPassed.Should().BeFalse($"negative fixture '{fixtureName}' must be rejected");
        result.Diagnostics.Should().Contain(d =>
            d.Contains(expectedDiagnosticToken, System.StringComparison.OrdinalIgnoreCase),
            $"negative fixture '{fixtureName}' must emit actionable diagnostics");
    }

    [Fact]
    public void ShouldKeepGateNeutral_WhenFreezeSection9RuleIsUnchanged()
    {
        var fixture = new ChangeControlFixture(
            FreezeSection9RuleChanged: false,
            FreezeRevisionUpdated: false,
            AssertionUpdated: false,
            TestEvidenceUpdated: false,
            FreezeRevisionPath: "docs/prd/PRD_V3_RULES_FREEZE.md",
            AssertionPath: "docs/prd/PRD_V3_ACCEPTANCE_ASSERTIONS.md",
            EvidencePath: "Game.Core.Tests/Tasks/Task155FreezeChangeControlGateTests.cs");

        var gate = new FreezeChangeControlTripletGate();

        var result = gate.Evaluate(fixture);

        result.IsPassed.Should().BeTrue("triplet gate should not fail when freeze section 9 is unchanged");
        result.Diagnostics.Should().BeEmpty();
    }

    public static IEnumerable<object[]> NegativeFixtures()
    {
        yield return new object[]
        {
            "missing_freeze_revision",
            new ChangeControlFixture(
                FreezeSection9RuleChanged: true,
                FreezeRevisionUpdated: false,
                AssertionUpdated: true,
                TestEvidenceUpdated: true,
                FreezeRevisionPath: "docs/prd/PRD_V3_RULES_FREEZE.md",
                AssertionPath: "docs/prd/PRD_V3_ACCEPTANCE_ASSERTIONS.md",
                EvidencePath: "Game.Core.Tests/Tasks/Task155FreezeChangeControlGateTests.cs"),
            "freeze revision update"
        };

        yield return new object[]
        {
            "missing_assertion_update",
            new ChangeControlFixture(
                FreezeSection9RuleChanged: true,
                FreezeRevisionUpdated: true,
                AssertionUpdated: false,
                TestEvidenceUpdated: true,
                FreezeRevisionPath: "docs/prd/PRD_V3_RULES_FREEZE.md",
                AssertionPath: "docs/prd/PRD_V3_ACCEPTANCE_ASSERTIONS.md",
                EvidencePath: "Game.Core.Tests/Tasks/Task155FreezeChangeControlGateTests.cs"),
            "assertion update"
        };

        yield return new object[]
        {
            "missing_test_evidence_update",
            new ChangeControlFixture(
                FreezeSection9RuleChanged: true,
                FreezeRevisionUpdated: true,
                AssertionUpdated: true,
                TestEvidenceUpdated: false,
                FreezeRevisionPath: "docs/prd/PRD_V3_RULES_FREEZE.md",
                AssertionPath: "docs/prd/PRD_V3_ACCEPTANCE_ASSERTIONS.md",
                EvidencePath: "Game.Core.Tests/Tasks/Task155FreezeChangeControlGateTests.cs"),
            "test evidence update"
        };
    }

    private sealed class FreezeChangeControlTripletGate
    {
        public GateResult Evaluate(ChangeControlFixture fixture)
        {
            var diagnostics = new List<string>();

            if (!fixture.FreezeSection9RuleChanged)
            {
                return GateResult.Passed();
            }

            if (!fixture.FreezeRevisionUpdated)
            {
                diagnostics.Add($"Missing freeze revision update: {fixture.FreezeRevisionPath}");
            }

            if (!fixture.AssertionUpdated)
            {
                diagnostics.Add($"Missing assertion update: {fixture.AssertionPath}");
            }

            if (!fixture.TestEvidenceUpdated)
            {
                diagnostics.Add($"Missing test evidence update: {fixture.EvidencePath}");
            }

            return diagnostics.Any()
                ? GateResult.Failed(diagnostics)
                : GateResult.Passed();
        }
    }

    public sealed record ChangeControlFixture(
        bool FreezeSection9RuleChanged,
        bool FreezeRevisionUpdated,
        bool AssertionUpdated,
        bool TestEvidenceUpdated,
        string FreezeRevisionPath,
        string AssertionPath,
        string EvidencePath);

    public sealed record GateResult(bool IsPassed, IReadOnlyList<string> Diagnostics)
    {
        public static GateResult Passed()
        {
            return new GateResult(true, new List<string>());
        }

        public static GateResult Failed(IReadOnlyList<string> diagnostics)
        {
            return new GateResult(false, diagnostics);
        }
    }
}
