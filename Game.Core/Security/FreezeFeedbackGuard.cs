using System;
using System.Collections.Generic;
using System.Linq;

namespace Game.Core.Security;

public enum DiagnosticCategory
{
    Crash,
    NonCrash
}

public sealed class FreezeFeedbackGuard
{
    public bool ShouldEmitUserFeedback(IReadOnlyCollection<DiagnosticCategory> categories)
    {
        if (categories == null)
        {
            throw new ArgumentNullException(nameof(categories));
        }

        return categories.Any(static category => category == DiagnosticCategory.Crash);
    }
}

public sealed class FeedbackRoutingDecision
{
    public FeedbackRoutingDecision(bool feedback, bool auditOnly)
    {
        Feedback = feedback;
        AuditOnly = auditOnly;
    }

    public bool Feedback { get; }

    public bool AuditOnly { get; }
}

public sealed class FeedbackRoutingChokePoint
{
    private readonly FreezeFeedbackGuard _guard;

    public FeedbackRoutingChokePoint(FreezeFeedbackGuard guard)
    {
        _guard = guard ?? throw new ArgumentNullException(nameof(guard));
    }

    public FeedbackRoutingDecision Evaluate(IReadOnlyCollection<DiagnosticCategory> categories)
    {
        var feedback = _guard.ShouldEmitUserFeedback(categories);
        return new FeedbackRoutingDecision(feedback, !feedback);
    }
}
