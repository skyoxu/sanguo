using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task73ContractCompatibilityGateTests
{
    // ACC:T73.1
    [Fact]
    public void ShouldAcceptAdditiveChangesByDefault_WhenStableIdentifierAndExistingFieldsStayTheSame()
    {
        var beforeContracts = new[]
        {
            new ContractSnapshot(
                "A-020.UnitStats",
                "contracts/unit_stats_v1.json",
                new Dictionary<string, string>
                {
                    ["attack"] = "int",
                    ["defense"] = "int"
                })
        };

        var afterContracts = new[]
        {
            new ContractSnapshot(
                "A-020.UnitStats",
                "contracts/unit_stats_v2.json",
                new Dictionary<string, string>
                {
                    ["attack"] = "int",
                    ["defense"] = "int",
                    ["critRate"] = "float"
                })
        };

        var result = EvaluateCompatibility(beforeContracts, afterContracts, MigrationEvidence.None);

        result.IsCompatible.Should().BeTrue();
        result.Violations.Should().BeEmpty();
    }

    // ACC:T73.2
    [Fact]
    public void ShouldKeepCompatibilityOutcomeUnchanged_WhenOnlyFileNameOrPathDrifts()
    {
        var beforeContracts = new[]
        {
            new ContractSnapshot(
                "A-020.CityLedger",
                "contracts/city/ledger_v1.json",
                new Dictionary<string, string>
                {
                    ["cityId"] = "string",
                    ["gold"] = "int"
                })
        };

        var afterContracts = new[]
        {
            new ContractSnapshot(
                "A-020.CityLedger",
                "moved/contracts/economy/city_ledger_renamed.json",
                new Dictionary<string, string>
                {
                    ["cityId"] = "string",
                    ["gold"] = "int"
                })
        };

        var result = EvaluateCompatibility(beforeContracts, afterContracts, MigrationEvidence.None);

        result.IsCompatible.Should().BeTrue();
        result.Summary.ToLowerInvariant().Should().NotContain("path");
        result.Summary.ToLowerInvariant().Should().NotContain("file");
    }

    [Fact]
    public void ShouldFailAcceptanceCoverage_WhenScriptLevelOrXunitWrapperLayerIsMissing()
    {
        var scriptPassOut = CreateTempSummaryPath("acc-t73-3-pass");
        var scriptFailOut = CreateTempSummaryPath("acc-t73-3-fail");
        var scriptPass = RunDomainContractsScript(arguments: $"--out \"{scriptPassOut}\"");
        var scriptFail = RunDomainContractsScript(arguments: $"--domain-prefix mismatch --out \"{scriptFailOut}\"");

        var missingWrapperCoverage = EvaluateCoverageFromScript(scriptPass, hasXunitWrapperCoverage: false);
        var missingScriptCoverage = EvaluateCoverageFromScript(scriptFail, hasXunitWrapperCoverage: true);
        var passSummary = ReadSummaryStatus(scriptPassOut);
        var failSummary = ReadSummaryStatus(scriptFailOut);
        var reportedPassOut = ExtractSummaryOutPath(scriptPass.Stdout);
        var reportedFailOut = ExtractSummaryOutPath(scriptFail.Stdout);

        scriptPass.ExitCode.Should().Be(0);
        scriptFail.ExitCode.Should().NotBe(0);
        passSummary.Should().Be("ok");
        failSummary.Should().Be("fail");
        reportedPassOut.Should().Be(ToPosix(scriptPassOut));
        reportedFailOut.Should().Be(ToPosix(scriptFailOut));
        missingWrapperCoverage.IsSatisfied.Should().BeFalse();
        missingScriptCoverage.IsSatisfied.Should().BeFalse();
        missingWrapperCoverage.Message.Should().Contain("script-level");
        missingWrapperCoverage.Message.Should().Contain("xUnit-wrapper");
        missingScriptCoverage.Message.Should().Contain("script-exit=");
    }

    [Fact]
    public void ShouldClassifyAdditiveAndBreakingSamples_WhenUsingSyntheticBeforeAfterContractSets()
    {
        var additiveBefore = new[]
        {
            new ContractSnapshot(
                "A-020.BattleOutcome",
                "contracts/battle/outcome_v1.json",
                new Dictionary<string, string>
                {
                    ["winner"] = "string"
                })
        };

        var additiveAfter = new[]
        {
            new ContractSnapshot(
                "A-020.BattleOutcome",
                "contracts/battle/outcome_v2.json",
                new Dictionary<string, string>
                {
                    ["winner"] = "string",
                    ["rounds"] = "int"
                })
        };

        var breakingBefore = new[]
        {
            new ContractSnapshot(
                "A-020.UnitStats",
                "contracts/unit_stats_v1.json",
                new Dictionary<string, string>
                {
                    ["attack"] = "int"
                })
        };

        var breakingAfter = new[]
        {
            new ContractSnapshot(
                "A-020.UnitStats",
                "contracts/unit_stats_v2.json",
                new Dictionary<string, string>
                {
                    ["baseAttack"] = "int"
                })
        };

        var additiveResult = EvaluateCompatibility(additiveBefore, additiveAfter, MigrationEvidence.None);
        var breakingResult = EvaluateCompatibility(breakingBefore, breakingAfter, MigrationEvidence.None);

        additiveResult.IsCompatible.Should().BeTrue();
        breakingResult.IsCompatible.Should().BeFalse();
        breakingResult.Violations.Should().ContainSingle(v =>
            v.StableId == "A-020.UnitStats" &&
            v.Reason.Contains("removed or renamed", StringComparison.OrdinalIgnoreCase));
        breakingResult.Summary.Should().Contain("A-020.UnitStats");
        breakingResult.Summary.Should().Contain("missing migration evidence");
    }

    // ACC:T73.4
    [Fact]
    public void ShouldRejectRenameBreakingChange_WhenNoDualMigrationEvidenceExistsForSameStableIdentifier()
    {
        var beforeContracts = new[]
        {
            new ContractSnapshot(
                "A-020.UnitStats",
                "contracts/unit_stats_v1.json",
                new Dictionary<string, string>
                {
                    ["attack"] = "int"
                })
        };

        var afterContracts = new[]
        {
            new ContractSnapshot(
                "A-020.UnitStats",
                "contracts/unit_stats_v2.json",
                new Dictionary<string, string>
                {
                    ["baseAttack"] = "int"
                })
        };

        var compatibilityResult = EvaluateCompatibility(beforeContracts, afterContracts, MigrationEvidence.None);
        var gateRunResult = RunGate(compatibilityResult);

        compatibilityResult.IsCompatible.Should().BeFalse();
        compatibilityResult.Violations.Should().ContainSingle(v =>
            v.StableId == "A-020.UnitStats" &&
            v.Reason.Contains("removed or renamed", StringComparison.OrdinalIgnoreCase) &&
            !v.HasMigrationEvidence);
        compatibilityResult.Summary.Should().Contain("A-020.UnitStats");
        compatibilityResult.Summary.Should().Contain("missing migration evidence");
        gateRunResult.ExitCode.Should().NotBe(0);
        AssertMachineReadableSummaryHasViolation(
            gateRunResult.MachineReadableSummaryJson,
            stableId: "A-020.UnitStats",
            expectedViolationKind: "rename");
    }

    [Fact]
    public void ShouldAllowBreakingChange_WhenMigrationEvidenceExistsForStableIdentifier()
    {
        var beforeContracts = new[]
        {
            new ContractSnapshot(
                "A-020.UnitStats",
                "contracts/unit_stats_v1.json",
                new Dictionary<string, string>
                {
                    ["attack"] = "int"
                })
        };

        var afterContracts = new[]
        {
            new ContractSnapshot(
                "A-020.UnitStats",
                "contracts/unit_stats_v2.json",
                new Dictionary<string, string>
                {
                    ["baseAttack"] = "int"
                })
        };

        var compatibilityResult = EvaluateCompatibility(
            beforeContracts,
            afterContracts,
            MigrationEvidence.BothFor("A-020.UnitStats"));
        var gateRunResult = RunGate(compatibilityResult);

        compatibilityResult.IsCompatible.Should().BeTrue();
        gateRunResult.ExitCode.Should().Be(0);
        gateRunResult.Summary.Should().Be("Compatibility gate passed.");
    }

    [Fact]
    public void ShouldRejectBreakingChange_WhenOnlyDeprecationWindowEvidenceExists()
    {
        var beforeContracts = new[]
        {
            new ContractSnapshot(
                "A-020.UnitStats",
                "contracts/unit_stats_v1.json",
                new Dictionary<string, string>
                {
                    ["attack"] = "int"
                })
        };

        var afterContracts = new[]
        {
            new ContractSnapshot(
                "A-020.UnitStats",
                "contracts/unit_stats_v2.json",
                new Dictionary<string, string>
                {
                    ["baseAttack"] = "int"
                })
        };

        var compatibilityResult = EvaluateCompatibility(
            beforeContracts,
            afterContracts,
            MigrationEvidence.WindowOnlyFor("A-020.UnitStats"));
        var gateRunResult = RunGate(compatibilityResult);

        compatibilityResult.IsCompatible.Should().BeFalse();
        compatibilityResult.Summary.Should().Contain("missing migration evidence");
        gateRunResult.ExitCode.Should().NotBe(0);
    }

    [Fact]
    public void ShouldRejectBreakingChange_WhenOnlyMigrationPlanEvidenceExists()
    {
        var beforeContracts = new[]
        {
            new ContractSnapshot(
                "A-020.UnitStats",
                "contracts/unit_stats_v1.json",
                new Dictionary<string, string>
                {
                    ["attack"] = "int"
                })
        };

        var afterContracts = new[]
        {
            new ContractSnapshot(
                "A-020.UnitStats",
                "contracts/unit_stats_v2.json",
                new Dictionary<string, string>
                {
                    ["baseAttack"] = "int"
                })
        };

        var compatibilityResult = EvaluateCompatibility(
            beforeContracts,
            afterContracts,
            MigrationEvidence.PlanOnlyFor("A-020.UnitStats"));
        var gateRunResult = RunGate(compatibilityResult);

        compatibilityResult.IsCompatible.Should().BeFalse();
        compatibilityResult.Summary.Should().Contain("missing migration evidence");
        gateRunResult.ExitCode.Should().NotBe(0);
    }

    // ACC:T73.5
    [Fact]
    public void ShouldRejectBreakingChange_WhenMigrationEvidenceTargetsDifferentStableIdentifier()
    {
        var beforeContracts = new[]
        {
            new ContractSnapshot(
                "A-020.UnitStats",
                "contracts/unit_stats_v1.json",
                new Dictionary<string, string>
                {
                    ["attack"] = "int"
                })
        };

        var afterContracts = new[]
        {
            new ContractSnapshot(
                "A-020.UnitStats",
                "contracts/unit_stats_v2.json",
                new Dictionary<string, string>
                {
                    ["baseAttack"] = "int"
                })
        };

        var compatibilityResult = EvaluateCompatibility(
            beforeContracts,
            afterContracts,
            MigrationEvidence.BothFor("A-020.OtherContract"));
        var gateRunResult = RunGate(compatibilityResult);

        compatibilityResult.IsCompatible.Should().BeFalse();
        compatibilityResult.Summary.Should().Contain("A-020.UnitStats");
        compatibilityResult.Summary.Should().Contain("missing migration evidence");
        gateRunResult.ExitCode.Should().NotBe(0);
        AssertMachineReadableSummaryHasViolation(
            gateRunResult.MachineReadableSummaryJson,
            stableId: "A-020.UnitStats",
            expectedViolationKind: "rename");
    }

    [Fact]
    public void ShouldReturnNonZeroExitCode_WhenContractIsRemovedWithoutMigrationEvidence()
    {
        var beforeContracts = new[]
        {
            new ContractSnapshot(
                "A-020.UnitStats",
                "contracts/unit_stats_v1.json",
                new Dictionary<string, string>
                {
                    ["attack"] = "int"
                })
        };

        var afterContracts = Array.Empty<ContractSnapshot>();
        var compatibilityResult = EvaluateCompatibility(beforeContracts, afterContracts, MigrationEvidence.None);
        var gateRunResult = RunGate(compatibilityResult);

        compatibilityResult.IsCompatible.Should().BeFalse();
        compatibilityResult.Summary.Should().Contain("A-020.UnitStats");
        compatibilityResult.Summary.Should().Contain("contract removed");
        compatibilityResult.Summary.Should().Contain("missing migration evidence");
        gateRunResult.ExitCode.Should().NotBe(0);
        AssertMachineReadableSummaryHasViolation(
            gateRunResult.MachineReadableSummaryJson,
            stableId: "A-020.UnitStats",
            expectedViolationKind: "remove");
    }

    // ACC:T73.3
    [Fact]
    public void ShouldReturnNonZeroExitCode_WhenBreakingChangeIsRejected()
    {
        var beforeContracts = new[]
        {
            new ContractSnapshot(
                "A-020.ArmyRoster",
                "contracts/army/roster_v1.json",
                new Dictionary<string, string>
                {
                    ["units"] = "string[]"
                })
        };

        var afterContracts = new[]
        {
            new ContractSnapshot(
                "A-020.ArmyRoster",
                "contracts/army/roster_v2.json",
                new Dictionary<string, string>
                {
                    ["unitIds"] = "string[]"
                })
        };

        var compatibilityResult = EvaluateCompatibility(beforeContracts, afterContracts, MigrationEvidence.None);
        var gateRunResult = RunGate(compatibilityResult);
        var scriptFailOut = CreateTempSummaryPath("acc-t73-5-fail");
        var scriptFail = RunDomainContractsScript(arguments: $"--domain-prefix mismatch --out \"{scriptFailOut}\"");
        var failSummary = ReadSummaryStatus(scriptFailOut);
        var reportedFailOut = ExtractSummaryOutPath(scriptFail.Stdout);

        compatibilityResult.IsCompatible.Should().BeFalse();
        gateRunResult.Summary.Should().Contain("A-020.ArmyRoster");
        gateRunResult.Summary.Should().Contain("missing migration evidence");
        gateRunResult.ExitCode.Should().NotBe(0);
        AssertMachineReadableSummaryHasViolation(
            gateRunResult.MachineReadableSummaryJson,
            stableId: "A-020.ArmyRoster",
            expectedViolationKind: "rename");
        scriptFail.ExitCode.Should().NotBe(0);
        failSummary.Should().Be("fail");
        reportedFailOut.Should().Be(ToPosix(scriptFailOut));
    }

    private static CompatibilityGateResult EvaluateCompatibility(
        IEnumerable<ContractSnapshot> beforeContracts,
        IEnumerable<ContractSnapshot> afterContracts,
        MigrationEvidence migrationEvidence)
    {
        var beforeByStableId = beforeContracts.ToDictionary(x => x.StableId, StringComparer.Ordinal);
        var afterByStableId = afterContracts.ToDictionary(x => x.StableId, StringComparer.Ordinal);
        var violations = new List<CompatibilityViolation>();

        foreach (var beforeContract in beforeByStableId.Values)
        {
            if (!afterByStableId.TryGetValue(beforeContract.StableId, out var afterContract))
            {
                violations.Add(CreateBreakingViolation(beforeContract.StableId, "contract removed", migrationEvidence));
                continue;
            }

            foreach (var beforeField in beforeContract.Fields)
            {
                if (!afterContract.Fields.TryGetValue(beforeField.Key, out var afterType))
                {
                    violations.Add(CreateBreakingViolation(
                        beforeContract.StableId,
                        $"field removed or renamed: {beforeField.Key}",
                        migrationEvidence));
                    continue;
                }

                if (!string.Equals(beforeField.Value, afterType, StringComparison.Ordinal))
                {
                    violations.Add(CreateBreakingViolation(
                        beforeContract.StableId,
                        $"field type changed: {beforeField.Key}",
                        migrationEvidence));
                }
            }
        }

        var unresolvedViolations = violations.Where(x => !x.HasMigrationEvidence).ToList();
        var isCompatible = unresolvedViolations.Count == 0;
        var summary = isCompatible
            ? "Compatibility gate passed."
            : BuildFailureSummary(unresolvedViolations);

        return new CompatibilityGateResult(isCompatible, violations, summary);
    }

    private static CompatibilityViolation CreateBreakingViolation(
        string stableId,
        string reason,
        MigrationEvidence migrationEvidence)
    {
        var hasMigrationEvidence = migrationEvidence.HasEvidenceFor(stableId);
        return new CompatibilityViolation(stableId, reason, hasMigrationEvidence);
    }

    private static string BuildFailureSummary(IEnumerable<CompatibilityViolation> violations)
    {
        var parts = violations
            .Select(x => $"{x.StableId}: {x.Reason}; missing migration evidence")
            .Distinct(StringComparer.Ordinal);

        return "Compatibility gate rejected breaking changes. " + string.Join(" | ", parts);
    }

    private static CoverageGateResult EvaluateCoverage(bool hasScriptLevelCoverage, bool hasXunitWrapperCoverage)
    {
        var isSatisfied = hasScriptLevelCoverage && hasXunitWrapperCoverage;
        var message = isSatisfied
            ? "Coverage gate passed."
            : "Coverage gate failed: script-level and xUnit-wrapper coverage are both required.";

        return new CoverageGateResult(isSatisfied, message);
    }

    private static CoverageGateResult EvaluateCoverageFromScript(ScriptRunResult scriptRun, bool hasXunitWrapperCoverage)
    {
        var hasScriptLevelCoverage = scriptRun.ExitCode == 0;
        var baseResult = EvaluateCoverage(hasScriptLevelCoverage, hasXunitWrapperCoverage);
        var message = $"{baseResult.Message} script-exit={scriptRun.ExitCode}";
        return new CoverageGateResult(baseResult.IsSatisfied, message);
    }

    private static string CreateTempSummaryPath(string suffix)
    {
        var path = Path.Combine(Path.GetTempPath(), $"task73-{suffix}-{Guid.NewGuid():N}", "summary.json");
        var directory = Path.GetDirectoryName(path) ?? throw new InvalidOperationException("Invalid summary path.");
        Directory.CreateDirectory(directory);
        return path;
    }

    private static string ReadSummaryStatus(string summaryPath)
    {
        File.Exists(summaryPath).Should().BeTrue($"summary artifact should exist at {summaryPath}");
        using var stream = File.OpenRead(summaryPath);
        using var document = JsonDocument.Parse(stream);
        return document.RootElement.GetProperty("status").GetString() ?? string.Empty;
    }

    private static string ExtractSummaryOutPath(string stdout)
    {
        const string marker = " out=";
        var markerIndex = stdout.LastIndexOf(marker, StringComparison.Ordinal);
        markerIndex.Should().BeGreaterThanOrEqualTo(0, "script stdout should report summary out path");
        var outValue = stdout[(markerIndex + marker.Length)..].Trim();
        outValue.Should().NotBeEmpty("summary out path should not be empty");
        return outValue;
    }

    private static string ToPosix(string path)
    {
        return path.Replace("\\", "/", StringComparison.Ordinal);
    }

    private static GateRunResult RunGate(CompatibilityGateResult compatibilityResult)
    {
        var exitCode = compatibilityResult.IsCompatible ? 0 : 1;
        var machineReadableSummaryJson = BuildMachineReadableSummary(compatibilityResult);
        return new GateRunResult(exitCode, compatibilityResult.Summary, machineReadableSummaryJson);
    }

    private static string BuildMachineReadableSummary(CompatibilityGateResult compatibilityResult)
    {
        var unresolvedViolations = compatibilityResult.Violations
            .Where(v => !v.HasMigrationEvidence)
            .Select(v => new
            {
                stableId = v.StableId,
                reason = v.Reason,
                violationKind = ClassifyViolationKind(v.Reason),
                missingMigrationEvidence = true
            })
            .ToArray();

        var payload = new
        {
            status = compatibilityResult.IsCompatible ? "ok" : "fail",
            violations = unresolvedViolations
        };

        return JsonSerializer.Serialize(payload);
    }

    private static string ClassifyViolationKind(string reason)
    {
        if (reason.Contains("contract removed", StringComparison.OrdinalIgnoreCase))
        {
            return "remove";
        }

        if (reason.Contains("removed or renamed", StringComparison.OrdinalIgnoreCase))
        {
            return "rename";
        }

        if (reason.Contains("type changed", StringComparison.OrdinalIgnoreCase))
        {
            return "field-break";
        }

        return "unknown";
    }

    private static void AssertMachineReadableSummaryHasViolation(
        string machineReadableSummaryJson,
        string stableId,
        string expectedViolationKind)
    {
        using var document = JsonDocument.Parse(machineReadableSummaryJson);
        var root = document.RootElement;
        root.GetProperty("status").GetString().Should().Be("fail");

        var matched = false;
        foreach (var violation in root.GetProperty("violations").EnumerateArray())
        {
            if (!string.Equals(violation.GetProperty("stableId").GetString(), stableId, StringComparison.Ordinal))
            {
                continue;
            }

            matched = true;
            violation.GetProperty("violationKind").GetString().Should().Be(expectedViolationKind);
            violation.GetProperty("missingMigrationEvidence").GetBoolean().Should().BeTrue();
            break;
        }

        matched.Should().BeTrue($"machine-readable summary should include violation for stableId={stableId}");
    }

    private static ScriptRunResult RunDomainContractsScript(string arguments)
    {
        var repoRoot = FindRepoRoot();
        var scriptPath = Path.Combine(repoRoot, "scripts", "python", "check_domain_contracts.py");

        var psi = new ProcessStartInfo
        {
            FileName = "py",
            Arguments = $"-3 \"{scriptPath}\" {arguments}".Trim(),
            WorkingDirectory = repoRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        using var process = Process.Start(psi) ?? throw new InvalidOperationException("Failed to start script process.");
        var stdout = process.StandardOutput.ReadToEnd();
        var stderr = process.StandardError.ReadToEnd();
        if (!process.WaitForExit(120_000))
        {
            try
            {
                process.Kill(entireProcessTree: true);
            }
            catch
            {
            }

            throw new TimeoutException("check_domain_contracts.py timed out.");
        }

        return new ScriptRunResult(process.ExitCode, stdout, stderr);
    }

    private static string FindRepoRoot()
    {
        var cursor = new DirectoryInfo(AppContext.BaseDirectory);
        while (cursor is not null)
        {
            var agentsPath = Path.Combine(cursor.FullName, "AGENTS.md");
            var scriptPath = Path.Combine(cursor.FullName, "scripts", "python", "check_domain_contracts.py");
            if (File.Exists(agentsPath) && File.Exists(scriptPath))
            {
                return cursor.FullName;
            }

            cursor = cursor.Parent;
        }

        throw new DirectoryNotFoundException("Repository root not found from test base directory.");
    }

    private sealed record ContractSnapshot(
        string StableId,
        string SourcePath,
        IReadOnlyDictionary<string, string> Fields);

    private sealed record CompatibilityViolation(
        string StableId,
        string Reason,
        bool HasMigrationEvidence);

    private sealed record CompatibilityGateResult(
        bool IsCompatible,
        IReadOnlyList<CompatibilityViolation> Violations,
        string Summary);

    private sealed record CoverageGateResult(
        bool IsSatisfied,
        string Message);

    private sealed record GateRunResult(
        int ExitCode,
        string Summary,
        string MachineReadableSummaryJson);

    private sealed record ScriptRunResult(
        int ExitCode,
        string Stdout,
        string Stderr);

    private sealed class MigrationEvidence
    {
        private readonly HashSet<string> stableIdsWithDeprecationWindow;
        private readonly HashSet<string> stableIdsWithMigrationPlan;

        private MigrationEvidence(IEnumerable<string> deprecationWindowStableIds, IEnumerable<string> migrationPlanStableIds)
        {
            stableIdsWithDeprecationWindow = new HashSet<string>(deprecationWindowStableIds, StringComparer.Ordinal);
            stableIdsWithMigrationPlan = new HashSet<string>(migrationPlanStableIds, StringComparer.Ordinal);
        }

        public static MigrationEvidence None { get; } = new(Array.Empty<string>(), Array.Empty<string>());

        public static MigrationEvidence BothFor(params string[] stableIds)
        {
            return new MigrationEvidence(stableIds, stableIds);
        }

        public static MigrationEvidence WindowOnlyFor(params string[] stableIds)
        {
            return new MigrationEvidence(stableIds, Array.Empty<string>());
        }

        public static MigrationEvidence PlanOnlyFor(params string[] stableIds)
        {
            return new MigrationEvidence(Array.Empty<string>(), stableIds);
        }

        public static MigrationEvidence For(params string[] stableIds)
        {
            return BothFor(stableIds);
        }

        public bool HasEvidenceFor(string stableId)
        {
            return stableIdsWithDeprecationWindow.Contains(stableId) &&
                   stableIdsWithMigrationPlan.Contains(stableId);
        }
    }
}
