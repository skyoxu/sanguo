using System;
using System.Globalization;

namespace Game.Core.Services.Sanguo;

public sealed record Part2CompletionResultResourceReadInput(
    string PlayerId,
    string ResourceId,
    int ResourceDelta,
    string ProgressionId,
    int ProgressionDelta,
    int CompletionSequence);

public sealed record Part2CompletionResultResourceReadState(
    string CompletionResultKey,
    string ResourceOutcome,
    string ProgressionOutcome,
    string PlayerReadableSummary);

public sealed record Part2CompletionResultResourceReadResult(
    bool Accepted,
    string ReasonCode,
    string CompletionResultKey,
    string ResourceOutcome,
    string ProgressionOutcome,
    string PlayerReadableSummary,
    string EvidenceRefs,
    Part2CompletionResultResourceReadState State);

public static class Part2CompletionResultResourceReader
{
    public const string InvalidInputReason = "invalid_deterministic_resource_input";

    public static readonly Part2CompletionResultResourceReadState EmptyState = new(
        CompletionResultKey: string.Empty,
        ResourceOutcome: string.Empty,
        ProgressionOutcome: string.Empty,
        PlayerReadableSummary: string.Empty);

    public static Part2CompletionResultResourceReadResult ReadDeterministicResource(
        Part2CompletionResultResourceReadInput input)
    {
        return ReadDeterministicResource(input, EmptyState);
    }

    public static Part2CompletionResultResourceReadResult ReadDeterministicResource(
        Part2CompletionResultResourceReadInput input,
        Part2CompletionResultResourceReadState currentState)
    {
        ArgumentNullException.ThrowIfNull(input);
        ArgumentNullException.ThrowIfNull(currentState);

        if (!IsValid(input))
        {
            return new Part2CompletionResultResourceReadResult(
                Accepted: false,
                ReasonCode: InvalidInputReason,
                CompletionResultKey: currentState.CompletionResultKey,
                ResourceOutcome: string.Empty,
                ProgressionOutcome: string.Empty,
                PlayerReadableSummary: currentState.PlayerReadableSummary,
                EvidenceRefs: "ACC:T214",
                State: currentState);
        }

        var resourceOutcome = "resource:"
            + input.ResourceId.Trim()
            + ":"
            + FormatSigned(input.ResourceDelta);
        var progressionOutcome = "progression:"
            + input.ProgressionId.Trim()
            + ":"
            + FormatSigned(input.ProgressionDelta);
        var key = string.Join(
            "|",
            input.PlayerId.Trim(),
            input.ResourceId.Trim(),
            input.ResourceDelta.ToString(CultureInfo.InvariantCulture),
            input.ProgressionId.Trim(),
            input.ProgressionDelta.ToString(CultureInfo.InvariantCulture),
            input.CompletionSequence.ToString(CultureInfo.InvariantCulture));
        var summary = resourceOutcome
            + ";"
            + progressionOutcome
            + ";sequence:"
            + input.CompletionSequence.ToString(CultureInfo.InvariantCulture);
        var state = new Part2CompletionResultResourceReadState(
            CompletionResultKey: key,
            ResourceOutcome: resourceOutcome,
            ProgressionOutcome: progressionOutcome,
            PlayerReadableSummary: summary);

        return new Part2CompletionResultResourceReadResult(
            Accepted: true,
            ReasonCode: string.Empty,
            CompletionResultKey: key,
            ResourceOutcome: resourceOutcome,
            ProgressionOutcome: progressionOutcome,
            PlayerReadableSummary: summary,
            EvidenceRefs: "ACC:T214",
            State: state);
    }

    private static bool IsValid(Part2CompletionResultResourceReadInput input)
    {
        return !string.IsNullOrWhiteSpace(input.PlayerId)
            && !string.IsNullOrWhiteSpace(input.ResourceId)
            && !string.IsNullOrWhiteSpace(input.ProgressionId)
            && input.CompletionSequence > 0;
    }

    private static string FormatSigned(int value)
    {
        return value >= 0
            ? "+" + value.ToString(CultureInfo.InvariantCulture)
            : value.ToString(CultureInfo.InvariantCulture);
    }
}
