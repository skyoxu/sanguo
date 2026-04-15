using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Security;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// Task 91 split runner for A-013~A-020 core assertions.
/// Exposes stable gate units and machine-readable summary records.
/// </summary>
public static class CoreAssertionGateRunner
{
    public const string StatePass = "pass";
    public const string StateFail = "fail";
    public const string StateSkipped = "skipped";

    private static readonly CoreAssertionGateUnit[] RequiredGateUnits =
    {
        new("A-013", "A-013.ReplayTrustHash", "ReplayTrustHashPersistence", true),
        new("A-014", "A-014.SaveUntrusted", "ReplayTrustHashPersistence", true),
        new("A-015", "A-015.MismatchMode", "ReplayMismatchModePolicy", true),
        new("A-016", "A-016.PayloadDesensitization", "DiagnosticPayloadProtection", true),
        new("A-017", "A-017.RetentionWindow", "DiagnosticPayloadProtection", true),
        new("A-018", "A-018.AuditFallback", "AuditFallbackAndRotation", true),
        new("A-019", "A-019.AuditRotationCap", "AuditFallbackAndRotation", true),
        new("A-020", "A-020.ContractCompatibility", "ContractCompatibilityPolicy", true),
    };

    public static IReadOnlyList<CoreAssertionGateUnit> GetRequiredGateUnits()
    {
        return RequiredGateUnits;
    }

    public static CoreAssertionGateRunResult Run(CoreAssertionGateExecutionInputs? inputs = null)
    {
        var effectiveInputs = inputs ?? CoreAssertionGateExecutionInputs.AllPassing;
        var forcedFailures = new HashSet<string>(
            effectiveInputs.ForcedFailAccIds ?? Array.Empty<string>(),
            StringComparer.Ordinal);

        var replayEvidence = ReplayIntegrityIntegrationPack.EvaluateSplitEvidence(
            hasTask83Evidence: effectiveInputs.HasReplayTrustHashEvidence && effectiveInputs.HasSaveUntrustedEvidence,
            hasTask84Evidence: effectiveInputs.HasMismatchModeEvidence,
            ReplayIntegrityIntegrationPack.SplitScopeT83,
            ReplayIntegrityIntegrationPack.SplitScopeT84);

        var records = new List<CoreAssertionGateRecord>(RequiredGateUnits.Length);
        foreach (var unit in RequiredGateUnits)
        {
            if (ShouldSkipUnit(unit.AccId, effectiveInputs))
            {
                records.Add(new CoreAssertionGateRecord(
                    unit.AccId,
                    unit.StableId,
                    unit.CheckName,
                    StateSkipped,
                    $"Required assertion {unit.AccId} is skipped because its evidence source is not enabled in this run.",
                    unit.IsMandatory));
                continue;
            }

            var evaluation = EvaluateUnit(unit, replayEvidence, effectiveInputs);
            var forcedFail = forcedFailures.Contains(unit.AccId);
            var state = forcedFail || !evaluation.Passed ? StateFail : StatePass;
            var message = forcedFail
                ? $"Forced failure for required assertion {unit.AccId}."
                : evaluation.Message;

            records.Add(new CoreAssertionGateRecord(
                unit.AccId,
                unit.StableId,
                unit.CheckName,
                state,
                message,
                unit.IsMandatory));
        }

        var hasMandatoryFailure = records.Any(record =>
            record.IsMandatory &&
            string.Equals(record.State, StateFail, StringComparison.OrdinalIgnoreCase));
        var status = hasMandatoryFailure ? "fail" : "ok";
        var exitCode = hasMandatoryFailure ? 1 : 0;
        var summaryJson = SerializeSummary(status, exitCode, records);

        return new CoreAssertionGateRunResult(
            ExitCode: exitCode,
            Status: status,
            Records: records,
            MachineReadableSummaryJson: summaryJson);
    }

    public static CoreAssertionGateRunResult RunWithForcedFailures(IEnumerable<string> failingAccIds)
    {
        ArgumentNullException.ThrowIfNull(failingAccIds);

        return Run(CoreAssertionGateExecutionInputs.AllPassing with
        {
            ForcedFailAccIds = failingAccIds
                .Where(static id => !string.IsNullOrWhiteSpace(id))
                .Select(static id => id.Trim())
                .Distinct(StringComparer.Ordinal)
                .ToArray(),
        });
    }

    private static CoreAssertionGateEvaluation EvaluateUnit(
        CoreAssertionGateUnit unit,
        ReplayIntegrityIntegrationEvidence replayEvidence,
        CoreAssertionGateExecutionInputs inputs)
    {
        return unit.AccId switch
        {
            "A-013" => EvaluateReplayTrustHash(replayEvidence, inputs),
            "A-014" => EvaluateSaveUntrusted(replayEvidence, inputs),
            "A-015" => EvaluateMismatchMode(replayEvidence, inputs),
            "A-016" => EvaluatePayloadDesensitization(inputs),
            "A-017" => EvaluateRetentionWindow(inputs),
            "A-018" => EvaluateAuditFallback(inputs),
            "A-019" => EvaluateAuditRotationCap(inputs),
            "A-020" => EvaluateContractCompatibility(inputs),
            _ => new CoreAssertionGateEvaluation(false, $"Unsupported assertion id: {unit.AccId}."),
        };
    }

    private static bool ShouldSkipUnit(string accId, CoreAssertionGateExecutionInputs inputs)
    {
        return accId switch
        {
            "A-013" => !inputs.EnableReplayTrustHashEvidence,
            "A-014" => !inputs.EnableSaveUntrustedEvidence,
            "A-015" => !inputs.EnableMismatchModeEvidence,
            "A-016" => !inputs.EnablePayloadDesensitizationEvidence,
            "A-017" => !inputs.EnableRetentionWindowEvidence,
            "A-018" => !inputs.EnableAuditFallbackEvidence,
            "A-019" => !inputs.EnableAuditRotationCapEvidence,
            "A-020" => !inputs.EnableContractCompatibilityEvidence,
            _ => false,
        };
    }

    private static CoreAssertionGateEvaluation EvaluateReplayTrustHash(
        ReplayIntegrityIntegrationEvidence replayEvidence,
        CoreAssertionGateExecutionInputs inputs)
    {
        var passed = inputs.HasReplayTrustHashEvidence && replayEvidence.Task83Delivered;
        return passed
            ? new CoreAssertionGateEvaluation(true, "Replay trust-hash persistence evidence is available.")
            : new CoreAssertionGateEvaluation(false, "Replay trust-hash persistence evidence is missing.");
    }

    private static CoreAssertionGateEvaluation EvaluateSaveUntrusted(
        ReplayIntegrityIntegrationEvidence replayEvidence,
        CoreAssertionGateExecutionInputs inputs)
    {
        var passed = inputs.HasSaveUntrustedEvidence && replayEvidence.Task83Delivered;
        return passed
            ? new CoreAssertionGateEvaluation(true, "Save-untrusted derivation evidence is available.")
            : new CoreAssertionGateEvaluation(false, "Save-untrusted derivation evidence is missing.");
    }

    private static CoreAssertionGateEvaluation EvaluateMismatchMode(
        ReplayIntegrityIntegrationEvidence replayEvidence,
        CoreAssertionGateExecutionInputs inputs)
    {
        var passed = inputs.HasMismatchModeEvidence && replayEvidence.Task84Delivered;
        return passed
            ? new CoreAssertionGateEvaluation(true, "Mismatch-mode transition evidence is available.")
            : new CoreAssertionGateEvaluation(false, "Mismatch-mode transition evidence is missing.");
    }

    private static CoreAssertionGateEvaluation EvaluatePayloadDesensitization(CoreAssertionGateExecutionInputs inputs)
    {
        if (!inputs.HasPayloadDesensitizationEvidence)
        {
            return new CoreAssertionGateEvaluation(false, "Payload desensitization evidence is disabled by inputs.");
        }

        var payload = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["authToken"] = "token-abc-123",
            ["eventType"] = EventTypes.TraceabilityChecked,
        };
        var sanitized = DiagnosticPayloadDesensitizationPolicy.Apply("release", payload);
        var ok = sanitized.TryGetValue("authToken", out var tokenValue) &&
                 tokenValue.StartsWith("[masked:", StringComparison.Ordinal) &&
                 string.Equals(sanitized["eventType"], EventTypes.TraceabilityChecked, StringComparison.Ordinal);

        return ok
            ? new CoreAssertionGateEvaluation(true, "Release-mode payload desensitization is active.")
            : new CoreAssertionGateEvaluation(false, "Release-mode payload desensitization did not mask sensitive keys.");
    }

    private static CoreAssertionGateEvaluation EvaluateRetentionWindow(CoreAssertionGateExecutionInputs inputs)
    {
        if (!inputs.HasRetentionWindowEvidence)
        {
            return new CoreAssertionGateEvaluation(false, "Retention-window evidence is disabled by inputs.");
        }

        var settlementUtc = new DateTime(2026, 1, 10, 12, 0, 0, DateTimeKind.Utc);
        var diagnostics = new[]
        {
            new DomainEvent(
                Type: EventTypes.TraceabilityChecked,
                Source: EventTypes.GateRunnerSource,
                Data: new RunnerEventData("expired"),
                Timestamp: settlementUtc.AddDays(-5),
                Id: "run-expired"),
            new DomainEvent(
                Type: EventTypes.TraceabilityChecked,
                Source: EventTypes.GateRunnerSource,
                Data: new RunnerEventData("in-window"),
                Timestamp: settlementUtc.AddHours(-4),
                Id: "run-in-window"),
        };

        var cleaned = DiagnosticRetentionWindow.Cleanup(
            diagnostics,
            settlementUtc,
            TimeSpan.FromDays(2),
            maxRetainedRuns: 10);
        var ok = cleaned.Count == 1 && string.Equals(cleaned[0].Id, "run-in-window", StringComparison.Ordinal);

        return ok
            ? new CoreAssertionGateEvaluation(true, "Retention-window cleanup keeps only in-window diagnostics.")
            : new CoreAssertionGateEvaluation(false, "Retention-window cleanup did not produce deterministic in-window evidence.");
    }

    private static CoreAssertionGateEvaluation EvaluateAuditFallback(CoreAssertionGateExecutionInputs inputs)
    {
        if (!inputs.HasAuditFallbackEvidence)
        {
            return new CoreAssertionGateEvaluation(false, "Audit-fallback evidence is disabled by inputs.");
        }

        var warnings = new List<string>();
        var ok = SecurityAuditFallbackPolicy.TryWriteWithFallback(
            primarySinkPath: "res://logs/security/security-audit.jsonl",
            fallbackSinkPath: "user://logs/security/security-audit.jsonl",
            tryWrite: path => !string.Equals(path, "res://logs/security/security-audit.jsonl", StringComparison.Ordinal),
            warningSink: warnings.Add);

        var hasFallbackWarning = warnings.Any(message =>
            message.Contains("fallback", StringComparison.OrdinalIgnoreCase));

        return ok && hasFallbackWarning
            ? new CoreAssertionGateEvaluation(true, "Audit fallback path remains available.")
            : new CoreAssertionGateEvaluation(false, "Audit fallback path is not functioning as expected.");
    }

    private static CoreAssertionGateEvaluation EvaluateAuditRotationCap(CoreAssertionGateExecutionInputs inputs)
    {
        if (!inputs.HasAuditRotationCapEvidence)
        {
            return new CoreAssertionGateEvaluation(false, "Audit-rotation evidence is disabled by inputs.");
        }

        var retained = new List<string>();
        for (var seq = 0; seq < 7; seq++)
        {
            retained.Add($"{{\"seq\":{seq}}}");
            SecurityAuditFallbackPolicy.EnforceRotationCapAndBoundedTotalSize(
                retained,
                rotationCapFiles: 3,
                boundedTotalSizeBytes: 4096);
        }

        var parsed = retained.Select(ParseSequence).ToArray();
        var ok = retained.Count <= 3 && parsed.SequenceEqual(new[] { 4, 5, 6 });

        return ok
            ? new CoreAssertionGateEvaluation(true, "Audit fallback rotation cap stays bounded and deterministic.")
            : new CoreAssertionGateEvaluation(false, "Audit fallback rotation cap is not enforced deterministically.");
    }

    private static CoreAssertionGateEvaluation EvaluateContractCompatibility(CoreAssertionGateExecutionInputs inputs)
    {
        if (!inputs.HasContractCompatibilityEvidence)
        {
            return new CoreAssertionGateEvaluation(false, "Contract-compatibility evidence is disabled by inputs.");
        }

        var contractEventTypes = new[]
        {
            SanguoGameStarted.EventType,
            SanguoGameSaved.EventType,
            SanguoGameLoaded.EventType,
            SanguoBossChallengePrompted.EventType,
            SanguoGameEnded.EventType,
        };

        var hasInvalidEventType = contractEventTypes.Any(string.IsNullOrWhiteSpace);
        var hasDuplicates = contractEventTypes.Distinct(StringComparer.Ordinal).Count() != contractEventTypes.Length;
        if (hasInvalidEventType || hasDuplicates)
        {
            return new CoreAssertionGateEvaluation(false, "Core contract event types contain invalid or duplicate values.");
        }

        try
        {
            SanguoEventOrderingRules.Validate(new[]
            {
                SanguoGameTurnStarted.EventType,
                SanguoPlayerStateChanged.EventType,
                SanguoGameTurnEnded.EventType,
            });
        }
        catch (Exception ex)
        {
            return new CoreAssertionGateEvaluation(false, $"Ordering-rule pass-path validation failed: {ex.Message}");
        }

        var rejectsBrokenOrder = false;
        try
        {
            SanguoEventOrderingRules.Validate(new[]
            {
                SanguoPlayerStateChanged.EventType,
                SanguoGameTurnStarted.EventType,
            });
        }
        catch (InvalidOperationException)
        {
            rejectsBrokenOrder = true;
        }

        return rejectsBrokenOrder
            ? new CoreAssertionGateEvaluation(true, "Core contract ordering rules are deterministic for pass/fail paths.")
            : new CoreAssertionGateEvaluation(false, "Ordering rules did not reject a known broken event sequence.");
    }

    private static int ParseSequence(string payload)
    {
        using var doc = JsonDocument.Parse(payload);
        return doc.RootElement.GetProperty("seq").GetInt32();
    }

    private static string SerializeSummary(
        string status,
        int exitCode,
        IReadOnlyList<CoreAssertionGateRecord> records)
    {
        return JsonSerializer.Serialize(new
        {
            status,
            exit_code = exitCode,
            records = records.Select(record => new
            {
                acc_id = record.AccId,
                stable_id = record.StableId,
                check = record.CheckName,
                state = record.State,
                message = record.Message,
                mandatory = record.IsMandatory,
            }),
        });
    }

    private sealed record RunnerEventData(string Value) : IEventData;

    private readonly record struct CoreAssertionGateEvaluation(bool Passed, string Message);
}

public sealed record CoreAssertionGateUnit(
    string AccId,
    string StableId,
    string CheckName,
    bool IsMandatory);

public sealed record CoreAssertionGateRecord(
    string AccId,
    string StableId,
    string CheckName,
    string State,
    string Message,
    bool IsMandatory);

public sealed record CoreAssertionGateRunResult(
    int ExitCode,
    string Status,
    IReadOnlyList<CoreAssertionGateRecord> Records,
    string MachineReadableSummaryJson);

public sealed record CoreAssertionGateExecutionInputs(
    bool EnableReplayTrustHashEvidence,
    bool HasReplayTrustHashEvidence,
    bool EnableSaveUntrustedEvidence,
    bool HasSaveUntrustedEvidence,
    bool EnableMismatchModeEvidence,
    bool HasMismatchModeEvidence,
    bool EnablePayloadDesensitizationEvidence,
    bool HasPayloadDesensitizationEvidence,
    bool EnableRetentionWindowEvidence,
    bool HasRetentionWindowEvidence,
    bool EnableAuditFallbackEvidence,
    bool HasAuditFallbackEvidence,
    bool EnableAuditRotationCapEvidence,
    bool HasAuditRotationCapEvidence,
    bool EnableContractCompatibilityEvidence,
    bool HasContractCompatibilityEvidence,
    IReadOnlyCollection<string>? ForcedFailAccIds = null)
{
    public static CoreAssertionGateExecutionInputs AllPassing { get; } = new(
        EnableReplayTrustHashEvidence: true,
        HasReplayTrustHashEvidence: true,
        EnableSaveUntrustedEvidence: true,
        HasSaveUntrustedEvidence: true,
        EnableMismatchModeEvidence: true,
        HasMismatchModeEvidence: true,
        EnablePayloadDesensitizationEvidence: true,
        HasPayloadDesensitizationEvidence: true,
        EnableRetentionWindowEvidence: true,
        HasRetentionWindowEvidence: true,
        EnableAuditFallbackEvidence: true,
        HasAuditFallbackEvidence: true,
        EnableAuditRotationCapEvidence: true,
        HasAuditRotationCapEvidence: true,
        EnableContractCompatibilityEvidence: true,
        HasContractCompatibilityEvidence: true,
        ForcedFailAccIds: Array.Empty<string>());
}
