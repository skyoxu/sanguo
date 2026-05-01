using System;
using System.Collections.Generic;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// Task 153 explicit integration gate for campaign explainability, localized HUD summaries,
/// and deterministic replay digest locking under fixed seed.
/// </summary>
public sealed class Task153R4IntegrationGate
{
    public Task153R4CiGateResult Evaluate(Task153R4ScenarioEvidence evidence)
    {
        ArgumentNullException.ThrowIfNull(evidence);

        if (!string.Equals(evidence.ScenarioKind, "campaign", StringComparison.Ordinal))
        {
            return new Task153R4CiGateResult(
                IsLocked: false,
                LockedScenario: evidence.ScenarioKind,
                FailureCode: "NON_CAMPAIGN_SCENARIO",
                LockedEvidenceKeys: Array.Empty<string>(),
                MissingRequirements: Array.Empty<string>());
        }

        var replayDigestMatches =
            evidence.BaselineReplay.FixedSeed == evidence.FixedSeed &&
            evidence.RerunReplay.FixedSeed == evidence.FixedSeed &&
            evidence.BaselineReplay.FixedSeed == evidence.RerunReplay.FixedSeed &&
            string.Equals(evidence.BaselineReplay.OutputDigest, evidence.RerunReplay.OutputDigest, StringComparison.Ordinal);
        if (!replayDigestMatches)
        {
            return new Task153R4CiGateResult(
                IsLocked: false,
                LockedScenario: evidence.ScenarioKind,
                FailureCode: "REPLAY_DIGEST_MISMATCH",
                LockedEvidenceKeys: Array.Empty<string>(),
                MissingRequirements: new[] { "replay_digest" });
        }

        var missingRequirements = new List<string>();
        if (evidence.ExplainabilityEntries.Count == 0)
        {
            missingRequirements.Add("explainability");
        }

        if (evidence.LocalizedHudSummaries.Count == 0)
        {
            missingRequirements.Add("hud_summary");
        }

        if (missingRequirements.Count > 0)
        {
            return new Task153R4CiGateResult(
                IsLocked: false,
                LockedScenario: evidence.ScenarioKind,
                FailureCode: "MISSING_EVIDENCE_LOCK",
                LockedEvidenceKeys: new[] { "replay_digest" },
                MissingRequirements: missingRequirements.ToArray());
        }

        return new Task153R4CiGateResult(
            IsLocked: true,
            LockedScenario: evidence.ScenarioKind,
            FailureCode: null,
            LockedEvidenceKeys: new[] { "explainability", "hud_summary", "replay_digest" },
            MissingRequirements: Array.Empty<string>());
    }
}

public sealed record Task153R4ScenarioEvidence(
    string ScenarioKind,
    int FixedSeed,
    IReadOnlyList<Task153ExplainabilityEntry> ExplainabilityEntries,
    IReadOnlyList<string> LocalizedHudSummaries,
    Task153ReplaySnapshot BaselineReplay,
    Task153ReplaySnapshot RerunReplay);

public sealed record Task153ExplainabilityEntry(
    string TriggerSource,
    string TimingMarker,
    string ImpactSummary);

public sealed record Task153ReplaySnapshot(
    int FixedSeed,
    string OutputDigest);

public sealed record Task153R4CiGateResult(
    bool IsLocked,
    string LockedScenario,
    string? FailureCode,
    IReadOnlyList<string> LockedEvidenceKeys,
    IReadOnlyList<string> MissingRequirements);

