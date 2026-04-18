using System;
using System.Linq;

namespace Game.Core.Tests.Tasks;

/// <summary>
/// Task 158 closure helper owned by tests to avoid adding new production implementation.
/// </summary>
internal static class SignalSubscriptionLifecycleIntegrationPack
{
    public const string SplitScopeT164 = "T164-R11-SubscriptionLifecycleGuard";
    public const string SplitScopeT165 = "T165-R11-LeakFixtureGuard";

    public static SignalSubscriptionLifecycleIntegrationEvidence BuildEvidence(
        Task164SignalSubscriptionEvidence task164Evidence,
        Task165SignalLeakFixtureEvidence task165Evidence)
    {
        var task164Delivered = task164Evidence.HasDeterministicEvidence &&
            task164Evidence.CoversSubscribeUnsubscribeLifecycle &&
            task164Evidence.NoActiveRegistrationsAfterNodeExit;

        var task165Delivered = task165Evidence.HasDeterministicEvidence &&
            task165Evidence.DetectsStaleHandlerLeak &&
            task165Evidence.ValidatesCleanFixtureWithoutLeak;

        return EvaluateSplitEvidence(
            hasTask164Evidence: task164Delivered,
            hasTask165Evidence: task165Delivered,
            splitScopes: MergeSplitScopes(task164Evidence.SplitScopes, task165Evidence.SplitScopes));
    }

    public static SignalSubscriptionLifecycleIntegrationEvidence EvaluateSplitEvidence(
        bool hasTask164Evidence,
        bool hasTask165Evidence,
        params string[] splitScopes)
    {
        var normalizedScopes = splitScopes
            .Where(scope => !string.IsNullOrWhiteSpace(scope))
            .Select(scope => scope.Trim())
            .Distinct(StringComparer.Ordinal)
            .OrderBy(scope => scope, StringComparer.Ordinal)
            .ToArray();

        return new SignalSubscriptionLifecycleIntegrationEvidence(
            Task164Delivered: hasTask164Evidence,
            Task165Delivered: hasTask165Evidence,
            SplitScopes: normalizedScopes);
    }

    private static string[] MergeSplitScopes(string[]? task164SplitScopes, string[]? task165SplitScopes)
    {
        return (task164SplitScopes ?? Array.Empty<string>())
            .Concat(task165SplitScopes ?? Array.Empty<string>())
            .ToArray();
    }
}

internal readonly record struct Task164SignalSubscriptionEvidence(
    bool HasDeterministicEvidence,
    bool CoversSubscribeUnsubscribeLifecycle,
    bool NoActiveRegistrationsAfterNodeExit,
    string[] SplitScopes);

internal readonly record struct Task165SignalLeakFixtureEvidence(
    bool HasDeterministicEvidence,
    bool DetectsStaleHandlerLeak,
    bool ValidatesCleanFixtureWithoutLeak,
    string[] SplitScopes);

internal readonly record struct SignalSubscriptionLifecycleIntegrationEvidence(
    bool Task164Delivered,
    bool Task165Delivered,
    string[] SplitScopes)
{
    public bool HasScope(string splitScope) =>
        SplitScopes.Any(scope => string.Equals(scope, splitScope, StringComparison.Ordinal));

    public string CompletionSignature =>
        string.Join(">", SplitScopes);

    public bool IsClosureComplete =>
        Task164Delivered &&
        Task165Delivered &&
        HasScope(SignalSubscriptionLifecycleIntegrationPack.SplitScopeT164) &&
        HasScope(SignalSubscriptionLifecycleIntegrationPack.SplitScopeT165);
}
