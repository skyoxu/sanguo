using System;
using System.Collections.Generic;
using System.Linq;

namespace Game.Core.Services.Sanguo;

public static class MigrationCompatibilityCompletenessValidator
{
    private static readonly string[] MandatorySections =
    {
        "Assertions",
        "Gates",
        "ScenarioEvidence",
        "DeterministicTests",
    };

    public static MigrationCompatibilityCompletenessValidationResult Validate(
        MigrationCompatibilityReport report,
        IReadOnlyCollection<string> evidenceLinks,
        string taskSpecificEvidenceRef)
    {
        ArgumentNullException.ThrowIfNull(report);
        ArgumentNullException.ThrowIfNull(evidenceLinks);
        ArgumentNullException.ThrowIfNull(taskSpecificEvidenceRef);

        var failureCodes = new List<string>();
        var sections = new HashSet<string>(report.Sections, StringComparer.Ordinal);

        foreach (var section in MandatorySections)
        {
            if (!sections.Contains(section))
            {
                failureCodes.Add($"missing_mandatory_section:{section}");
            }
        }

        if (evidenceLinks.Count == 0)
        {
            failureCodes.Add("missing_evidence_links");
        }

        if (!evidenceLinks.Contains(taskSpecificEvidenceRef, StringComparer.Ordinal))
        {
            failureCodes.Add("missing_task_specific_test_evidence");
        }

        var orderedFailureCodes = failureCodes
            .OrderBy(static code => code, StringComparer.Ordinal)
            .ToArray();
        var isComplete = orderedFailureCodes.Length == 0;
        var failureOutput = isComplete ? "ok" : string.Join("|", orderedFailureCodes);

        return new MigrationCompatibilityCompletenessValidationResult(isComplete, orderedFailureCodes, failureOutput);
    }
}

public sealed record MigrationCompatibilityCompletenessValidationResult(
    bool IsComplete,
    IReadOnlyList<string> FailureCodes,
    string FailureOutput);
