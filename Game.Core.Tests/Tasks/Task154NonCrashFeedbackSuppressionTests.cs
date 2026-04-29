using Game.Core.Security;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task154NonCrashFeedbackSuppressionTests
{
    // ACC:T154.1
    [Fact]
    public void ShouldSuppressUserFeedback_WhenDiagnosticsAreNonCrashOnly()
    {
        var chokePoint = new FeedbackRoutingChokePoint(new FreezeFeedbackGuard());

        var decision = chokePoint.Evaluate(new[] { DiagnosticCategory.NonCrash, DiagnosticCategory.NonCrash });

        decision.Feedback.Should().BeFalse();
        decision.AuditOnly.Should().BeTrue();
    }

    // ACC:T154.2
    [Theory]
    [InlineData(true, DiagnosticCategory.Crash)]
    [InlineData(false, DiagnosticCategory.NonCrash)]
    [InlineData(true, DiagnosticCategory.Crash, DiagnosticCategory.NonCrash)]
    public void ShouldReturnDeterministicDecision_WhenCategoryCombinationChanges(bool expectedUserFeedback, params DiagnosticCategory[] categories)
    {
        var guard = new FreezeFeedbackGuard();

        var actualUserFeedback = guard.ShouldEmitUserFeedback(categories);

        actualUserFeedback.Should().Be(expectedUserFeedback);
    }

    // ACC:T154.3
    [Fact]
    public void ShouldEnforceSuppressionAtRoutingChokePoint_WhenDifferentCallSitesSubmitNonCrashDiagnostics()
    {
        var chokePoint = new FeedbackRoutingChokePoint(new FreezeFeedbackGuard());

        var fromUi = chokePoint.Evaluate(new[] { DiagnosticCategory.NonCrash });
        var fromBackground = chokePoint.Evaluate(new[] { DiagnosticCategory.NonCrash });

        fromUi.Feedback.Should().BeFalse();
        fromUi.AuditOnly.Should().BeTrue();
        fromBackground.Feedback.Should().BeFalse();
        fromBackground.AuditOnly.Should().BeTrue();
    }
}
