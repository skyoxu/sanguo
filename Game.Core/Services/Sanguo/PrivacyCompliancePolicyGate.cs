using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace Game.Core.Services.Sanguo;

public sealed class PrivacyCompliancePolicyGate
{
    public PrivacyPolicyGateEvaluation Evaluate(
        string policyContent,
        IReadOnlyCollection<string> requiredClauses,
        IReadOnlyDictionary<string, string> clauseArtifactLinks)
    {
        ArgumentNullException.ThrowIfNull(policyContent);
        ArgumentNullException.ThrowIfNull(requiredClauses);
        ArgumentNullException.ThrowIfNull(clauseArtifactLinks);

        var missingClauses = requiredClauses
            .Where(clause => !string.IsNullOrWhiteSpace(clause))
            .Select(clause => clause.Trim())
            .Where(clause => !policyContent.Contains($"## Clause:{clause}", StringComparison.Ordinal))
            .Distinct(StringComparer.Ordinal)
            .ToArray();

        if (missingClauses.Length == 0)
        {
            return new PrivacyPolicyGateEvaluation(
                IsCompliant: true,
                ViolatedClause: string.Empty,
                OffendingArtifactPath: string.Empty,
                MissingClauses: Array.Empty<string>());
        }

        var violatedClause = missingClauses[0];
        clauseArtifactLinks.TryGetValue(violatedClause, out var offendingArtifactPath);

        return new PrivacyPolicyGateEvaluation(
            IsCompliant: false,
            ViolatedClause: violatedClause,
            OffendingArtifactPath: offendingArtifactPath ?? string.Empty,
            MissingClauses: missingClauses);
    }

    public ClauseSetParityEvaluation EvaluateClauseSetParity(
        IReadOnlyCollection<string> implementationClauses,
        IReadOnlyCollection<string> ciClauses)
    {
        ArgumentNullException.ThrowIfNull(implementationClauses);
        ArgumentNullException.ThrowIfNull(ciClauses);

        var implementation = new HashSet<string>(
            implementationClauses.Where(static item => !string.IsNullOrWhiteSpace(item)).Select(static item => item.Trim()),
            StringComparer.Ordinal);
        var ci = new HashSet<string>(
            ciClauses.Where(static item => !string.IsNullOrWhiteSpace(item)).Select(static item => item.Trim()),
            StringComparer.Ordinal);

        var missingInCi = implementation.Where(clause => !ci.Contains(clause)).OrderBy(static clause => clause, StringComparer.Ordinal).ToArray();
        var unexpectedInCi = ci.Where(clause => !implementation.Contains(clause)).OrderBy(static clause => clause, StringComparer.Ordinal).ToArray();

        return new ClauseSetParityEvaluation(
            IsAligned: missingInCi.Length == 0 && unexpectedInCi.Length == 0,
            MissingInCi: missingInCi,
            UnexpectedInCi: unexpectedInCi);
    }

    public CiPolicyGateSummary BuildSummary(PrivacyPolicyGateEvaluation evaluation)
    {
        ArgumentNullException.ThrowIfNull(evaluation);

        return new CiPolicyGateSummary(
            Status: evaluation.IsCompliant ? "ok" : "fail",
            ViolatedClause: evaluation.ViolatedClause,
            OffendingArtifact: evaluation.OffendingArtifactPath);
    }

    public string BuildSummaryJson(PrivacyPolicyGateEvaluation evaluation)
    {
        var summary = BuildSummary(evaluation);
        return JsonSerializer.Serialize(new
        {
            status = summary.Status,
            violated_clause = summary.ViolatedClause,
            offending_artifact = summary.OffendingArtifact,
        });
    }
}

public sealed record PrivacyPolicyGateEvaluation(
    bool IsCompliant,
    string ViolatedClause,
    string OffendingArtifactPath,
    IReadOnlyList<string> MissingClauses);

public sealed record ClauseSetParityEvaluation(
    bool IsAligned,
    IReadOnlyList<string> MissingInCi,
    IReadOnlyList<string> UnexpectedInCi);

public sealed record CiPolicyGateSummary(
    string Status,
    string ViolatedClause,
    string OffendingArtifact);
