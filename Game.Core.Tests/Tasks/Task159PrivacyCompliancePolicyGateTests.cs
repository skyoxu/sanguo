using System;
using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task159PrivacyCompliancePolicyGateTests
{
    private static readonly string[] RequiredClauses = { "PRIV-001", "PRIV-002", "PRIV-003" };

    private static readonly Dictionary<string, string> ClauseArtifactLinks = new(StringComparer.Ordinal)
    {
        ["PRIV-001"] = "logs/ci/freeze/T159/assertion.json",
        ["PRIV-002"] = "logs/ci/freeze/T159/policy.json",
        ["PRIV-003"] = "logs/ci/freeze/T159/retention.json",
    };

    // ACC:T159.3
    [Fact]
    [Trait("acceptance", "ACC:T159.3")]
    public void ShouldRejectPolicy_WhenRequiredClauseIsMissingAndFreezeArtifactLinkIsRequired()
    {
        var gate = new PrivacyCompliancePolicyGate();
        var policyContent = string.Join(Environment.NewLine, new[]
        {
            "# Privacy Policy",
            "## Clause:PRIV-001",
            "Data minimization is mandatory.",
            "## Clause:PRIV-003",
            "Assertion artifacts must be retained."
        });

        var result = gate.Evaluate(policyContent, RequiredClauses, ClauseArtifactLinks);

        result.IsCompliant.Should().BeFalse();
        result.MissingClauses.Should().Contain("PRIV-002");
        result.ViolatedClause.Should().Be("PRIV-002");
        result.OffendingArtifactPath.Should().Be("logs/ci/freeze/T159/policy.json");
    }

    // ACC:T159.4
    [Fact]
    [Trait("acceptance", "ACC:T159.4")]
    public void ShouldFail_WhenImplementationAndCiConsumeDifferentPolicyClauseSets()
    {
        var gate = new PrivacyCompliancePolicyGate();
        var implementationClauses = new[] { "PRIV-001", "PRIV-002", "PRIV-003" };
        var ciClauses = new[] { "PRIV-001", "PRIV-003" };

        var result = gate.EvaluateClauseSetParity(implementationClauses, ciClauses);

        result.IsAligned.Should().BeFalse();
        result.MissingInCi.Should().Contain("PRIV-002");
    }

    // ACC:T159.5
    [Fact]
    [Trait("acceptance", "ACC:T159.5")]
    public void ShouldSurfaceViolatedClauseAndOffendingArtifact_WhenBuildingCiSummary()
    {
        var gate = new PrivacyCompliancePolicyGate();
        var summary = gate.BuildSummary(new PrivacyPolicyGateEvaluation(
            IsCompliant: false,
            ViolatedClause: "PRIV-004",
            OffendingArtifactPath: "logs/ci/2026-04-30/privacy/T159/freeze-proof.json",
            MissingClauses: new[] { "PRIV-004" }));

        summary.Status.Should().Be("fail");
        summary.ViolatedClause.Should().Be("PRIV-004");
        summary.OffendingArtifact.Should().Be("logs/ci/2026-04-30/privacy/T159/freeze-proof.json");
    }
}
