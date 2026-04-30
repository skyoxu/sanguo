using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task159PrivacyComplianceCiSummaryTests
{
    // ACC:T159.5
    [Fact]
    public void ShouldIncludeViolatedClauseAndOffendingArtifact_WhenPolicyGateFails()
    {
        var sut = new PrivacyCompliancePolicyGate();
        var result = new PrivacyPolicyGateEvaluation(
            IsCompliant: false,
            ViolatedClause: "PRIV-7.2",
            OffendingArtifactPath: "build/output/player_profile_dump.json",
            MissingClauses: new[] { "PRIV-7.2" });

        var summary = sut.BuildSummary(result);

        summary.Status.Should().Be("fail");
        summary.ViolatedClause.Should().Be("PRIV-7.2");
        summary.OffendingArtifact.Should().Be("build/output/player_profile_dump.json");
    }
}
