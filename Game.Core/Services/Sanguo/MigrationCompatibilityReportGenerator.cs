using System;
using System.Collections.Generic;

namespace Game.Core.Services.Sanguo;

public sealed class MigrationCompatibilityReportGenerator
{
    public MigrationCompatibilityReport Generate(
        IReadOnlyCollection<string> assertions,
        IReadOnlyCollection<string> gates,
        IReadOnlyCollection<string> scenarioEvidence,
        IReadOnlyCollection<string> deterministicTestEvidence)
    {
        ArgumentNullException.ThrowIfNull(assertions);
        ArgumentNullException.ThrowIfNull(gates);
        ArgumentNullException.ThrowIfNull(scenarioEvidence);
        ArgumentNullException.ThrowIfNull(deterministicTestEvidence);

        if (deterministicTestEvidence.Count == 0)
        {
            throw new InvalidOperationException("Migration compatibility report requires deterministic test evidence.");
        }

        var sections = new List<string>();

        if (assertions.Count > 0)
        {
            sections.Add("Assertions");
        }

        if (gates.Count > 0)
        {
            sections.Add("Gates");
        }

        if (scenarioEvidence.Count > 0)
        {
            sections.Add("ScenarioEvidence");
        }

        sections.Add("DeterministicTests");
        return new MigrationCompatibilityReport(sections);
    }
}

public sealed record MigrationCompatibilityReport(IReadOnlyList<string> Sections);
