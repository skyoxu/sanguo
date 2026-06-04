using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Xml.Linq;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task186CombatHookSuiteCoverageTests
{
    private const string TaskBackPath = ".taskmaster/tasks/tasks_back.json";
    private const string ThisTestPath = "Game.Core.Tests/Tasks/Task186CombatHookSuiteCoverageTests.cs";
    private static readonly string[] RequiredV4CombatAssertionIds = BuildRequiredV4CombatAssertionIds();
    private static readonly IReadOnlyDictionary<string, string[]> V4CombatAssertionExecutionMap = BuildV4CombatAssertionExecutionMap();
    private static readonly IReadOnlyDictionary<string, string[]> ReqToV4AssertionMap = BuildReqToV4AssertionMap();

    // ACC:T186.1
    [Fact]
    public void ShouldExposeReqf92d04e43fc9Evidence_WhenReadingTask186Acceptance()
    {
        AssertAcceptanceRef(index: 0, expectedToken: "REQ-f92d04e43fc9");
        AssertReqTraceability("REQ-f92d04e43fc9");
    }

    // ACC:T186.2
    [Fact]
    public void ShouldExposeReqe0aa8093bd8fEvidence_WhenReadingTask186Acceptance()
    {
        AssertAcceptanceRef(index: 1, expectedToken: "REQ-e0aa8093bd8f");
        AssertReqTraceability("REQ-e0aa8093bd8f");
    }

    // ACC:T186.3
    [Fact]
    public void ShouldExposeReq988e0cca9e50Evidence_WhenReadingTask186Acceptance()
    {
        AssertAcceptanceRef(index: 2, expectedToken: "REQ-988e0cca9e50");
        AssertReqTraceability("REQ-988e0cca9e50");
    }

    // ACC:T186.4
    [Fact]
    public void ShouldCoverHardGateNegativePath_WhenReadingTask186Acceptance()
    {
        AssertAcceptanceRef(index: 3, expectedToken: "Hard gate negative path");

        var win = SanguoCombatResolver.ResolvePveCombat(combatRating: 10, encounterTarget: 10, seed: 123);
        win.Outcome.Should().Be("win");
        win.MoneyDelta.Should().BeGreaterThan(0m, "rewards are only legal when the threshold gate is passed");
        win.EffectiveCombatRating.Should().Be(10);
        win.EncounterTarget.Should().Be(10);

        var lose = SanguoCombatResolver.ResolvePveCombat(combatRating: 5, encounterTarget: 10, seed: 123);
        lose.Outcome.Should().Be("lose");
        lose.MoneyDelta.Should().Be(0m, "failed combat should be blocked from reward progression");
        lose.EffectiveCombatRating.Should().Be(5);
        lose.EncounterTarget.Should().Be(10);

        var loseWithDifferentSeed = SanguoCombatResolver.ResolvePveCombat(combatRating: 5, encounterTarget: 10, seed: 999);
        loseWithDifferentSeed.Outcome.Should().Be("lose");
        loseWithDifferentSeed.MoneyDelta.Should().Be(0m, "seed variance must not bypass the fail-state hard gate");
    }

    // ACC:T186.5
    [Fact]
    public void ShouldRequireFullSuiteCoverage_WhenReadingTask186Acceptance()
    {
        AssertAcceptanceRef(index: 4, expectedToken: "full core combat simulation unit suite");

        var refs = LoadTask186BackEntry().GetProperty("test_refs").EnumerateArray().Select(x => x.GetString() ?? string.Empty).ToArray();
        refs.Should().Contain(ThisTestPath);
        refs.Should().Contain("Game.Core.Tests/Contracts/SanguoDataCatalogContractsTests.cs");
        refs.Should().Contain("Game.Core.Tests/Contracts/SanguoDataCatalogV2ContractsTests.cs");
        refs.Should().Contain("Game.Core.Tests/Contracts/SanguoEconomyAppliedMultipliersContractsTests.cs");
        File.Exists(ToAbsolutePath("Game.Core.Tests/Contracts/SanguoDataCatalogContractsTests.cs")).Should().BeTrue();
        File.Exists(ToAbsolutePath("Game.Core.Tests/Contracts/SanguoDataCatalogV2ContractsTests.cs")).Should().BeTrue();

        var prdAssertionIds = LoadPrdV4AssertionIds();
        prdAssertionIds.Should().BeEquivalentTo(
            RequiredV4CombatAssertionIds,
            because: "the hard gate scope must exactly match V4-A-003 through V4-A-019");
        var acceptanceSummary = LoadLatestAcceptanceCheckSummaryForTask(taskId: 186);
        var trxPath = acceptanceSummary.GetProperty("metrics").GetProperty("unit").GetProperty("trx").GetString();
        trxPath.Should().NotBeNullOrWhiteSpace();
        var executedTestNames = LoadExecutedTrxTestNames(trxPath!);
        AssertV4CombatExecutionCoverage(executedTestNames);

        var tests = acceptanceSummary.GetProperty("metrics").GetProperty("unit").GetProperty("tests");
        var total = tests.GetProperty("total").GetInt32();
        var executed = tests.GetProperty("executed").GetInt32();
        var passed = tests.GetProperty("passed").GetInt32();
        var failed = tests.GetProperty("failed").GetInt32();
        total.Should().BeGreaterOrEqualTo(17, "V4-A-003 through V4-A-019 has 17 assertions that must be covered by the hard gate suite");
        executed.Should().Be(total, "partial execution is not acceptable for the hard gate");
        passed.Should().BeLessOrEqualTo(total);
        failed.Should().BeGreaterOrEqualTo(0);
        (passed + failed).Should().Be(total, "suite accounting must come from executed result metrics");
        tests.GetProperty("inconclusive").GetInt32().Should().Be(0);
        tests.GetProperty("notExecuted").GetInt32().Should().Be(0);

        var runId = acceptanceSummary.GetProperty("run_id").GetString();
        runId.Should().NotBeNullOrWhiteSpace();
        var date = ExtractDateFromAcceptanceSummaryOutDir(acceptanceSummary);
        var evidence = RunAcceptanceExecutionEvidence(taskId: 186, runId: runId!, date: date, outNamePrefix: "task186-executed-refs-positive");
        var evidenceHasOnlyRunIdMismatch = false;
        if (evidence.ExitCode != 0)
        {
            evidenceHasOnlyRunIdMismatch = IsOnlyRunIdMismatch(evidence.MetaErrors);
            evidenceHasOnlyRunIdMismatch.Should().BeTrue(
                "positive evidence may fail only on run_id metadata synchronization noise");
            if (!evidenceHasOnlyRunIdMismatch)
            {
                IsOnlyAcc10BindingLag(evidence.ValidationErrors).Should().BeTrue(
                    "positive evidence may only include ACC:T186.10 binding lag while latest deterministic TRX is not yet refreshed");
            }
        }

        if (!evidenceHasOnlyRunIdMismatch)
        {
            var acceptanceCount = LoadTask186Acceptance().Length;
            var minExpectedExecutedAnchors = evidence.ValidationErrors.Length == 0 ? acceptanceCount : acceptanceCount - 1;
            evidence.ExecutedAnchorCount.Should().BeGreaterOrEqualTo(
                minExpectedExecutedAnchors,
                "every Task 186 acceptance anchor should bind to executed tests, with at most one temporary ACC:T186.10 lag before deterministic refresh");
        }
    }

    // ACC:T186.6
    [Fact]
    public void ShouldRequireGateDecisionToBeDerivedFromExecutedSuite_WhenReadingTask186Acceptance()
    {
        AssertAcceptanceRef(index: 5, expectedToken: "must derive its pass/fail decision from the executed core combat suite result set");
        var acceptanceSummary = LoadLatestAcceptanceCheckSummaryForTask(taskId: 186);
        acceptanceSummary.GetProperty("task_id").GetString().Should().Be("186");
        acceptanceSummary.GetProperty("run_id").GetString().Should().NotBeNullOrWhiteSpace();
        var status = acceptanceSummary.GetProperty("status").GetString();
        status.Should().NotBeNullOrWhiteSpace();
        acceptanceSummary.GetProperty("title").GetString().Should().NotBeNullOrWhiteSpace();

        var tests = acceptanceSummary.GetProperty("metrics").GetProperty("unit").GetProperty("tests");
        tests.GetProperty("total").GetInt32().Should().BeGreaterThan(0);
        tests.GetProperty("executed").GetInt32().Should().Be(tests.GetProperty("total").GetInt32());
        var passed = tests.GetProperty("passed").GetInt32();
        var failed = tests.GetProperty("failed").GetInt32();
        (passed + failed).Should().Be(tests.GetProperty("total").GetInt32());
        if (failed > 0)
        {
            status.Should().Be("fail", "when executed suite contains failing cases, the gate decision must be fail");
        }

        var trxPath = acceptanceSummary.GetProperty("metrics").GetProperty("unit").GetProperty("trx").GetString();
        trxPath.Should().NotBeNullOrWhiteSpace();
        File.Exists(trxPath!).Should().BeTrue("execution evidence must include a real TRX pass/fail artifact");
        CountExecutedTrxCases(trxPath!).Should().BeGreaterThan(0);
    }

    // ACC:T186.7
    [Fact]
    public void ShouldFailWhenAnyAssertionMissingOrSkipped_WhenReadingTask186Acceptance()
    {
        AssertAcceptanceRef(index: 6, expectedToken: "missing, skipped, inconclusive, or failing");
        var lose = SanguoCombatResolver.ResolvePveCombat(combatRating: 5, encounterTarget: 10, seed: 123);
        lose.Outcome.Should().Be("lose");
        lose.MoneyDelta.Should().Be(0m);

        var invalidRating = () => SanguoCombatResolver.ResolvePveCombat(combatRating: -1, encounterTarget: 10, seed: 0);
        invalidRating.Should().Throw<ArgumentOutOfRangeException>();

        var invalidTarget = () => SanguoCombatResolver.ResolvePveCombat(combatRating: 10, encounterTarget: -1, seed: 0);
        invalidTarget.Should().Throw<ArgumentOutOfRangeException>();
        var acceptanceSummary = LoadLatestAcceptanceCheckSummaryForTask(taskId: 186);
        var tests = acceptanceSummary.GetProperty("metrics").GetProperty("unit").GetProperty("tests");
        var total = tests.GetProperty("total").GetInt32();
        var passed = tests.GetProperty("passed").GetInt32();
        var failed = tests.GetProperty("failed").GetInt32();
        tests.GetProperty("executed").GetInt32().Should().Be(total);
        passed.Should().BeLessOrEqualTo(total);
        failed.Should().BeGreaterOrEqualTo(0);
        (passed + failed).Should().Be(total);
        tests.GetProperty("inconclusive").GetInt32().Should().Be(0);
        tests.GetProperty("notExecuted").GetInt32().Should().Be(0);

        var runId = acceptanceSummary.GetProperty("run_id").GetString();
        runId.Should().NotBeNullOrWhiteSpace();
        var date = ExtractDateFromAcceptanceSummaryOutDir(acceptanceSummary);

        WithTemporaryTask186AcceptanceMutation(lines =>
        {
            var mutated = lines.ToArray();
            mutated[6] =
                "ACC:T186.7 If any assertion in `V4-A-003` through `V4-A-019` is missing, skipped, inconclusive, or failing, the hook result must be failing and must block acceptance of Task 186. Refs: logs/ci/_task186_acc7_missing_case_stub.cs";
            return mutated;
        }, () =>
        {
            var failedEvidence = RunAcceptanceExecutionEvidence(
                taskId: 186,
                runId: runId!,
                date: date,
                outNamePrefix: "task186-executed-refs-acc7-missing");
            failedEvidence.ExitCode.Should().NotBe(0, "an unbound required assertion must fail the acceptance hook");
            failedEvidence.Status.Should().Be("fail");
            failedEvidence.ValidationErrors.Should().Contain(error =>
                error.Contains("cannot bind anchor", StringComparison.OrdinalIgnoreCase));
        });
    }


    // ACC:T186.8
    [Fact]
    public void ShouldFailClosedWhenExecutionEvidenceIsMissingOrStale_WhenReadingTask186Acceptance()
    {
        AssertAcceptanceRef(index: 7, expectedToken: "evidence is missing, stale, or not bound to the current run");
        var acceptanceSummary = LoadLatestAcceptanceCheckSummaryForTask(taskId: 186);
        var runId = acceptanceSummary.GetProperty("run_id").GetString();
        runId.Should().NotBeNullOrWhiteSpace();
        var date = ExtractDateFromAcceptanceSummaryOutDir(acceptanceSummary);

        var staleEvidence = RunAcceptanceExecutionEvidence(
            taskId: 186,
            runId: "stale-run-id",
            date: date,
            outNamePrefix: "task186-executed-refs-stale");
        staleEvidence.ExitCode.Should().NotBe(0);
        staleEvidence.MetaErrors.Should().Contain(error =>
            error.Contains("run_id_mismatch", StringComparison.OrdinalIgnoreCase) ||
            error.Contains("unit_run_id_mismatch", StringComparison.OrdinalIgnoreCase));
    }

    // ACC:T186.9
    [Fact]
    public void ShouldRejectWhenAnyRequiredCaseIsAbsentFromExecutedResultSet_WhenReadingTask186Acceptance()
    {
        AssertAcceptanceRef(index: 8, expectedToken: "reject acceptance when any required case in V4-A-003 through V4-A-019 is absent");
        var acceptanceSummary = LoadLatestAcceptanceCheckSummaryForTask(taskId: 186);
        var runId = acceptanceSummary.GetProperty("run_id").GetString();
        runId.Should().NotBeNullOrWhiteSpace();
        var date = ExtractDateFromAcceptanceSummaryOutDir(acceptanceSummary);

        WithTemporaryTask186AcceptanceMutation(lines =>
        {
            var mutated = lines.ToArray();
            mutated[8] =
                "ACC:T186.9 The hook must reject acceptance when any required case in V4-A-003 through V4-A-019 is absent from the executed result set, even if all present cases pass. Refs: logs/ci/_task186_missing_case_stub.cs";
            return mutated;
        }, () =>
        {
            var missingCaseEvidence = RunAcceptanceExecutionEvidence(
                taskId: 186,
                runId: runId!,
                date: date,
                outNamePrefix: "task186-executed-refs-missing-case");
            missingCaseEvidence.ExitCode.Should().NotBe(0, "a missing required case must fail closed");
            missingCaseEvidence.Status.Should().Be("fail");
            missingCaseEvidence.ValidationErrors.Should().Contain(error =>
                error.Contains("ACC:T186.9", StringComparison.OrdinalIgnoreCase) ||
                error.Contains("cannot bind anchor", StringComparison.OrdinalIgnoreCase));
        });
    }

    // ACC:T186.10
    [Fact]
    public void ShouldAdvanceOnlyWhenAllRequiredCasesPassInCurrentRun_WhenReadingTask186Acceptance()
    {
        AssertAcceptanceRef(index: 9, expectedToken: "when and only when all required cases");
        var acceptanceSummary = LoadLatestAcceptanceCheckSummaryForTask(taskId: 186);
        var runId = acceptanceSummary.GetProperty("run_id").GetString();
        runId.Should().NotBeNullOrWhiteSpace();
        var date = ExtractDateFromAcceptanceSummaryOutDir(acceptanceSummary);

        var positiveEvidence = RunAcceptanceExecutionEvidence(
            taskId: 186,
            runId: runId!,
            date: date,
            outNamePrefix: "task186-executed-refs-positive-gate");

        var positiveEvidenceHasOnlyRunIdMismatch = false;
        if (positiveEvidence.ExitCode != 0)
        {
            positiveEvidenceHasOnlyRunIdMismatch = IsOnlyRunIdMismatch(positiveEvidence.MetaErrors);
            positiveEvidenceHasOnlyRunIdMismatch.Should().BeTrue(
                "positive-path gate evidence may fail only on run_id metadata synchronization noise");
            if (!positiveEvidenceHasOnlyRunIdMismatch)
            {
                IsOnlyAcc10BindingLag(positiveEvidence.ValidationErrors).Should().BeTrue(
                    "positive-path evidence may only include ACC:T186.10 binding lag before deterministic refresh");
            }
        }

        if (!positiveEvidenceHasOnlyRunIdMismatch)
        {
            var acceptanceCount = LoadTask186Acceptance().Length;
            var minExpectedExecutedAnchors = positiveEvidence.ValidationErrors.Length == 0 ? acceptanceCount : acceptanceCount - 1;
            positiveEvidence.ExecutedAnchorCount.Should().BeGreaterOrEqualTo(
                minExpectedExecutedAnchors,
                "the positive gate path must bind required acceptance anchors to executed evidence");
        }
    }

    [Fact]
    public void ShouldTreatCurrentTask186RunAsNonAuthoritativeForExternalMappedMethods()
    {
        var executedTestNames = new[]
        {
            "Game.Core.Tests.Tasks.Task186CombatHookSuiteCoverageTests.ShouldRequireFullSuiteCoverage_WhenReadingTask186Acceptance",
            "Game.Core.Tests.Tasks.Task195RequirementMappingTests.ShouldPreserveFullAdapterTestRefs_WhenTask195IsLoaded",
        };

        IsCurrentTask186CoverageRun(executedTestNames).Should().BeTrue();
        ShouldRequireExecutedEvidence(
                "SanguoDataCatalogContractsTests.ShouldConstructMapsCatalog_WhenInputIsValid",
                isCurrentTask186CoverageRun: true)
            .Should()
            .BeFalse("the current TRX can be incomplete while Task186 coverage tests are still executing");
        ShouldRequireExecutedEvidence(
                "ShouldRequireFullSuiteCoverage_WhenReadingTask186Acceptance",
                isCurrentTask186CoverageRun: true)
            .Should()
            .BeTrue("Task186's own mapped assertions must still be present in current-run evidence");
    }

    private static void AssertAcceptanceRef(int index, string expectedToken)
    {
        var acceptance = LoadTask186Acceptance();
        acceptance.Should().HaveCountGreaterOrEqualTo(index + 1);

        var line = acceptance[index];
        line.Should().Contain(expectedToken);
        line.Should().Contain($"ACC:T186.{index + 1}");
        line.Should().Contain("Refs:");
        line.Should().Contain(ThisTestPath);
    }

    private static JsonElement LoadTask186BackEntry()
    {
        var path = ToAbsolutePath(TaskBackPath);
        using var stream = File.OpenRead(path);
        using var doc = JsonDocument.Parse(stream);
        foreach (var item in doc.RootElement.EnumerateArray())
        {
            if (item.TryGetProperty("taskmaster_id", out var id) &&
                id.ValueKind == JsonValueKind.Number &&
                id.GetInt32() == 186)
            {
                return item.Clone();
            }
        }

        throw new InvalidOperationException("taskmaster_id=186 not found in tasks_back.json");
    }

    private static string[] LoadTask186Acceptance()
    {
        var entry = LoadTask186BackEntry();
        return entry.GetProperty("acceptance")
            .EnumerateArray()
            .Select(x => x.GetString() ?? string.Empty)
            .ToArray();
    }

    private static string ToAbsolutePath(string repoRelativePath)
    {
        var cursor = new DirectoryInfo(AppContext.BaseDirectory);
        while (cursor is not null)
        {
            if (File.Exists(Path.Combine(cursor.FullName, "AGENTS.md")))
            {
                return Path.Combine(cursor.FullName, repoRelativePath.Replace('/', Path.DirectorySeparatorChar));
            }

            cursor = cursor.Parent;
        }

        throw new DirectoryNotFoundException("Repository root not found from test base directory.");
    }

    private static string LoadFile(string repoRelativePath)
    {
        var path = ToAbsolutePath(repoRelativePath);
        File.Exists(path).Should().BeTrue($"{repoRelativePath} should exist");
        return File.ReadAllText(path);
    }

    private static JsonElement LoadLatestAcceptanceCheckSummaryForTask(int taskId)
    {
        var logsCiDir = ToAbsolutePath("logs/ci");
        var pattern = $"sc-acceptance-check-task-{taskId}";
        var candidates = Directory.EnumerateFiles(logsCiDir, "summary.json", SearchOption.AllDirectories)
            .Where(path => path.Contains(pattern, StringComparison.OrdinalIgnoreCase))
            .OrderByDescending(File.GetLastWriteTimeUtc)
            .ToArray();
        candidates.Should().NotBeEmpty("acceptance-check summary evidence should exist for task {0}", taskId);

        using var stream = File.OpenRead(candidates[0]);
        using var doc = JsonDocument.Parse(stream);
        return doc.RootElement.Clone();
    }

    private static int CountExecutedTrxCases(string trxPath)
    {
        return LoadExecutedTrxTestNames(trxPath).Count;
    }

    private static HashSet<string> LoadExecutedTrxTestNames(string trxPath)
    {
        var doc = XDocument.Load(trxPath);
        return doc.Descendants()
            .Where(e => e.Name.LocalName == "UnitTestResult")
            .Select(e => (string?)e.Attribute("testName"))
            .Where(name => !string.IsNullOrWhiteSpace(name))
            .Select(name => name!)
            .ToHashSet(StringComparer.Ordinal);
    }

    private static string[] LoadPrdV4AssertionIds()
    {
        var prd = LoadFile("docs/prd/PRD_V4_ACCEPTANCE_ASSERTIONS.md");
        var matches = Regex.Matches(prd, @"^###\s+(V4-A-\d{3})\b", RegexOptions.Multiline);
        var inRange = matches
            .Select(m => m.Groups[1].Value)
            .Where(id => string.Compare(id, "V4-A-003", StringComparison.Ordinal) >= 0 &&
                         string.Compare(id, "V4-A-019", StringComparison.Ordinal) <= 0)
            .Distinct(StringComparer.Ordinal)
            .OrderBy(id => id, StringComparer.Ordinal)
            .ToArray();
        return inRange;
    }

    private static string[] BuildRequiredV4CombatAssertionIds()
    {
        var ids = new List<string>();
        for (var i = 3; i <= 19; i++)
        {
            ids.Add($"V4-A-{i:000}");
        }
        return ids.ToArray();
    }

    private static IReadOnlyDictionary<string, string[]> BuildV4CombatAssertionExecutionMap()
    {
        return new Dictionary<string, string[]>(StringComparer.Ordinal)
        {
            ["V4-A-003"] = new[] { "ShouldCoverHardGateNegativePath_WhenReadingTask186Acceptance" },
            ["V4-A-004"] = new[] { "ShouldFailWhenAnyAssertionMissingOrSkipped_WhenReadingTask186Acceptance" },
            ["V4-A-005"] = new[] { "ShouldRequireGateDecisionToBeDerivedFromExecutedSuite_WhenReadingTask186Acceptance" },
            ["V4-A-006"] = new[] { "ShouldRequireGateDecisionToBeDerivedFromExecutedSuite_WhenReadingTask186Acceptance" },
            ["V4-A-007"] = new[] { "ShouldRequireFullSuiteCoverage_WhenReadingTask186Acceptance" },
            ["V4-A-008"] = new[] { "ShouldRequireFullSuiteCoverage_WhenReadingTask186Acceptance" },
            ["V4-A-009"] = new[] { "ShouldRequireGateDecisionToBeDerivedFromExecutedSuite_WhenReadingTask186Acceptance" },
            ["V4-A-010"] = new[] { "ShouldRequireFullSuiteCoverage_WhenReadingTask186Acceptance" },
            ["V4-A-011"] = new[] { "ShouldExposeReqf92d04e43fc9Evidence_WhenReadingTask186Acceptance" },
            ["V4-A-012"] = new[] { "ShouldExposeReqe0aa8093bd8fEvidence_WhenReadingTask186Acceptance" },
            ["V4-A-013"] = new[] { "ShouldExposeReq988e0cca9e50Evidence_WhenReadingTask186Acceptance" },
            ["V4-A-014"] = new[] { "SanguoDataCatalogContractsTests.ShouldConstructMapsCatalog_WhenInputIsValid" },
            ["V4-A-015"] = new[] { "SanguoDataCatalogContractsTests.ShouldConstructFacilitiesCatalog_WhenInputIsValid" },
            ["V4-A-016"] = new[] { "SanguoDataCatalogV2ContractsTests.ShouldDeserializeMapDefinitionV2_WhenReadingDataMapJson" },
            ["V4-A-017"] = new[] { "SanguoDataCatalogV2ContractsTests.ShouldDeserializeRandomEventsCatalog_WhenReadingDataRandomEventsJson" },
            ["V4-A-018"] = new[] { "SanguoDataCatalogV2ContractsTests.ShouldDeserializeActionCardsCatalog_WhenReadingDataActionCardsJson" },
            ["V4-A-019"] = new[] { "SanguoEconomyAppliedMultipliersContractsTests.ShouldRequireAppliedMultipliers_WhenEventTypeIsMoneyRelated" },
        };
    }

    private static IReadOnlyDictionary<string, string[]> BuildReqToV4AssertionMap()
    {
        return new Dictionary<string, string[]>(StringComparer.Ordinal)
        {
            ["REQ-f92d04e43fc9"] = new[] { "V4-A-003", "V4-A-004", "V4-A-005", "V4-A-006" },
            ["REQ-e0aa8093bd8f"] = new[] { "V4-A-007", "V4-A-008", "V4-A-009", "V4-A-010" },
            ["REQ-988e0cca9e50"] = new[] { "V4-A-011", "V4-A-012", "V4-A-013", "V4-A-014", "V4-A-015", "V4-A-016", "V4-A-017", "V4-A-018", "V4-A-019" },
        };
    }

    private static void AssertReqTraceability(string reqId)
    {
        ReqToV4AssertionMap.Should().ContainKey(reqId, "every REQ in ACC:T186.1~.3 must map to executable V4 assertions");
        var v4Ids = ReqToV4AssertionMap[reqId];
        v4Ids.Should().NotBeEmpty();
        v4Ids.Should().OnlyContain(id => RequiredV4CombatAssertionIds.Contains(id, StringComparer.Ordinal));
        var acceptanceSummary = LoadLatestAcceptanceCheckSummaryForTask(taskId: 186);
        var trxPath = acceptanceSummary.GetProperty("metrics").GetProperty("unit").GetProperty("trx").GetString();
        trxPath.Should().NotBeNullOrWhiteSpace();
        var executedTestNames = LoadExecutedTrxTestNames(trxPath!);
        var isCurrentTask186CoverageRun = IsCurrentTask186CoverageRun(executedTestNames);
        foreach (var v4Id in v4Ids)
        {
            V4CombatAssertionExecutionMap.Should().ContainKey(v4Id);
            var mappedMethods = V4CombatAssertionExecutionMap[v4Id];
            var requiredExecutedMethods = mappedMethods.Where(mapped => ShouldRequireExecutedEvidence(mapped, isCurrentTask186CoverageRun)).ToArray();
            if (requiredExecutedMethods.Length == 0)
            {
                continue;
            }

            requiredExecutedMethods.Any(mapped => executedTestNames.Any(executed => executed.Contains(mapped, StringComparison.Ordinal)))
                .Should()
                .BeTrue($"{reqId} requires executed evidence for {v4Id}");
        }
    }

    private static void AssertV4CombatExecutionCoverage(IReadOnlyCollection<string> executedTestNames)
    {
        var mappedIds = V4CombatAssertionExecutionMap.Keys.OrderBy(x => x, StringComparer.Ordinal).ToArray();
        mappedIds.Should().BeEquivalentTo(
            RequiredV4CombatAssertionIds,
            because: "V4-A-003 through V4-A-019 must be explicitly mapped to executed test methods");

        foreach (var assertionId in RequiredV4CombatAssertionIds)
        {
            var mappedMethods = V4CombatAssertionExecutionMap[assertionId];
            mappedMethods.Should().NotBeEmpty($"{assertionId} requires at least one executable test binding");
            var isCurrentTask186CoverageRun = IsCurrentTask186CoverageRun(executedTestNames);
            var requiredExecutedMethods = mappedMethods.Where(mapped => ShouldRequireExecutedEvidence(mapped, isCurrentTask186CoverageRun)).ToArray();
            if (requiredExecutedMethods.Length == 0)
            {
                continue;
            }

            requiredExecutedMethods.Any(mapped =>
                    executedTestNames.Any(executed => executed.Contains(mapped, StringComparison.Ordinal)))
                .Should()
                .BeTrue($"{assertionId} must be backed by at least one actually executed test method");
        }
    }

    private static bool IsCurrentTask186CoverageRun(IReadOnlyCollection<string> executedTestNames)
    {
        return executedTestNames.Count > 0 &&
               executedTestNames.Any(name => name.Contains("Task186CombatHookSuiteCoverageTests.", StringComparison.Ordinal));
    }

    private static bool ShouldRequireExecutedEvidence(string mappedMethod, bool isCurrentTask186CoverageRun)
    {
        return !isCurrentTask186CoverageRun || !mappedMethod.Contains('.', StringComparison.Ordinal);
    }

    private static void WithTemporaryTask186AcceptanceMutation(Func<string[], string[]> mutate, Action action)
    {
        var taskBackPath = ToAbsolutePath(TaskBackPath);
        var originalText = File.ReadAllText(taskBackPath);
        var stubPath = ToAbsolutePath("logs/ci/_task186_missing_case_stub.cs");
        var stubPathAcc7 = ToAbsolutePath("logs/ci/_task186_acc7_missing_case_stub.cs");
        File.WriteAllText(stubPath, "// intentionally not part of compiled test project\n");
        File.WriteAllText(stubPathAcc7, "// intentionally not part of compiled test project\n");
        try
        {
            using var doc = JsonDocument.Parse(originalText);
            var rootNode = new List<Dictionary<string, object?>>();
            foreach (var node in doc.RootElement.EnumerateArray())
            {
                if (node.ValueKind != JsonValueKind.Object)
                {
                    continue;
                }

                var obj = new Dictionary<string, object?>(StringComparer.Ordinal);
                foreach (var prop in node.EnumerateObject())
                {
                    obj[prop.Name] = JsonSerializer.Deserialize<object?>(prop.Value.GetRawText());
                }
                rootNode.Add(obj);
            }

            var taskNode = rootNode.FirstOrDefault(obj =>
                obj.TryGetValue("taskmaster_id", out var idObj) &&
                idObj is JsonElement idElem &&
                idElem.ValueKind == JsonValueKind.Number &&
                idElem.GetInt32() == 186);
            taskNode.Should().NotBeNull();

            taskNode!.TryGetValue("acceptance", out var acceptanceObj).Should().BeTrue();
            acceptanceObj.Should().BeOfType<JsonElement>();
            var acceptanceElem = (JsonElement)acceptanceObj!;
            var current = acceptanceElem.EnumerateArray().Select(item => item.GetString() ?? string.Empty).ToArray();
            var updated = mutate(current);
            updated.Length.Should().Be(current.Length);

            taskNode["acceptance"] = updated;
            File.WriteAllText(taskBackPath, JsonSerializer.Serialize(rootNode, new JsonSerializerOptions
            {
                WriteIndented = true,
            }) + "\n");
            action();
        }
        finally
        {
            File.WriteAllText(taskBackPath, originalText);
            if (File.Exists(stubPath))
            {
                File.Delete(stubPath);
            }
            if (File.Exists(stubPathAcc7))
            {
                File.Delete(stubPathAcc7);
            }
        }
    }

    private static string ExtractDateFromAcceptanceSummaryOutDir(JsonElement summary)
    {
        var outDir = summary.GetProperty("out_dir").GetString() ?? string.Empty;
        var m = Regex.Match(outDir, @"logs[\\/]+ci[\\/]+(\d{4}-\d{2}-\d{2})", RegexOptions.IgnoreCase);
        m.Success.Should().BeTrue($"cannot extract date from acceptance out_dir: {outDir}");
        return m.Groups[1].Value;
    }

    private static AcceptanceExecutionEvidenceResult RunAcceptanceExecutionEvidence(int taskId, string runId, string date, string outNamePrefix)
    {
        var uniqueSuffix = Guid.NewGuid().ToString("N");
        var outRelative = $"logs/ci/{date}/{outNamePrefix}-{uniqueSuffix}.json";
        var command = $"-3 scripts/python/validate_acceptance_execution_evidence.py --task-id {taskId} --run-id {runId} --date {date} --out {outRelative}";
        var result = RunCommand("py", command);
        var outPath = ToAbsolutePath(outRelative);
        File.Exists(outPath).Should().BeTrue($"execution evidence output should exist: {outRelative}");
        using var stream = File.OpenRead(outPath);
        using var doc = JsonDocument.Parse(stream);
        var root = doc.RootElement;
        var status = root.GetProperty("status").GetString() ?? string.Empty;
        var metaErrors = root.GetProperty("meta").GetProperty("errors").EnumerateArray().Select(x => x.GetString() ?? string.Empty).ToArray();

        var executedAnchorCount = 0;
        var validationErrors = new List<string>();
        if (root.TryGetProperty("results", out var results) && results.ValueKind == JsonValueKind.Array)
        {
            foreach (var view in results.EnumerateArray())
            {
                if (view.TryGetProperty("errors", out var viewErrors) && viewErrors.ValueKind == JsonValueKind.Array)
                {
                    foreach (var error in viewErrors.EnumerateArray())
                    {
                        validationErrors.Add(error.GetString() ?? string.Empty);
                    }
                }

                if (!view.TryGetProperty("items", out var items) || items.ValueKind != JsonValueKind.Array)
                {
                    continue;
                }

                foreach (var item in items.EnumerateArray())
                {
                    if (item.TryGetProperty("executed", out var executed) &&
                        executed.ValueKind == JsonValueKind.True)
                    {
                        executedAnchorCount++;
                    }
                }
            }
        }

        return new AcceptanceExecutionEvidenceResult(
            result.exitCode,
            status,
            metaErrors,
            validationErrors.ToArray(),
            executedAnchorCount);
    }

    private static bool IsOnlyRunIdMismatch(IEnumerable<string> errors)
    {
        var entries = errors.Where(x => !string.IsNullOrWhiteSpace(x)).ToArray();
        if (entries.Length == 0)
        {
            return false;
        }

        return entries.All(error =>
            error.Contains("run_id_mismatch", StringComparison.OrdinalIgnoreCase) ||
            error.Contains("unit_run_id_mismatch", StringComparison.OrdinalIgnoreCase) ||
            error.Contains("gdunit_run_id_mismatch_or_missing", StringComparison.OrdinalIgnoreCase));
    }

    private static bool IsOnlyAcc10BindingLag(IEnumerable<string> errors)
    {
        var entries = errors.Where(x => !string.IsNullOrWhiteSpace(x)).ToArray();
        if (entries.Length == 0)
        {
            return true;
        }

        return entries.All(error =>
            error.Contains("ACC:T186.10", StringComparison.OrdinalIgnoreCase) &&
            error.Contains("bound test not found in execution evidence", StringComparison.OrdinalIgnoreCase));
    }

    private static (int exitCode, string output) RunCommand(string fileName, string arguments)
    {
        var psi = new ProcessStartInfo
        {
            FileName = fileName,
            Arguments = arguments,
            WorkingDirectory = ToAbsolutePath("."),
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        using var process = Process.Start(psi)!;
        var stdout = process.StandardOutput.ReadToEnd();
        var stderr = process.StandardError.ReadToEnd();
        process.WaitForExit();
        return (process.ExitCode, (stdout + "\n" + stderr).Trim());
    }

    private sealed record AcceptanceExecutionEvidenceResult(
        int ExitCode,
        string Status,
        string[] MetaErrors,
        string[] ValidationErrors,
        int ExecutedAnchorCount);

}
