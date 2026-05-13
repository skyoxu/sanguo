using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task177AcceptanceTests
{
    private const int TaskId = 177;
    private const string Task177Ref = "Game.Core.Tests/Tasks/Task177AcceptanceTests.cs";
    private const string Task177RuntimeUiRef = "Tests.Godot/tests/UI/test_task177_runtime_hud_outcome_surfaces.gd";
    private const string Task78DraftRef = "Game.Core.Tests/Tasks/Task78RewardDraftEngineTests.cs";
    private const string Task78SplitRef = "Game.Core.Tests/Tasks/Task78SplitIntegrationTests.cs";
    private const string Task104SplitRef = "Game.Core.Tests/Tasks/Task104SplitIntegrationTests.cs";
    private const string Task106SplitRef = "Game.Core.Tests/Tasks/Task106SplitIntegrationTests.cs";
    private const string Task137SplitRef = "Game.Core.Tests/Tasks/Task137SplitTests.cs";
    private const string Task141SplitRef = "Game.Core.Tests/Tasks/Task141ObjectiveRewardSourceTests.cs";
    private const string Task142SplitRef = "Game.Core.Tests/Tasks/Task142ObjectiveRewardDraftDeterminismTests.cs";
    private const string CandidatePath = "docs/gdd/ui-gdd-flow.candidates.json";
    private const string CandidateScreenGroup = "Runtime HUD And Outcome Surfaces";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    // ACC:T177.1
    [Fact]
    [Trait("acceptance", "ACC:T177.1")]
    public void ShouldRouteTask177ToChapter7RuntimeHudCandidate_WhenReadingTaskViews()
    {
        var repoRoot = FindRepoRoot();
        using var candidateDoc = LoadJson(repoRoot, CandidatePath);
        var candidate = FindCandidateByScreenGroup(candidateDoc.RootElement, CandidateScreenGroup);

        candidate.Should().NotBeNull();
        candidate.Value.GetProperty("ui_entry").GetString().Should().Be("HUD / Prompt / Outcome Surfaces");
        var suggestedSurfaces = ReadStringArray(candidate.Value, "suggested_standalone_surfaces");
        suggestedSurfaces.Should().Contain(new[] { "RuntimeHud", "OutcomePanel", "RuntimePromptPanel" });

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var overlayRefs = ReadStringArray(task, "overlay_refs");
            var acceptance = ReadStringArray(task, "acceptance");

            overlayRefs.Should().Contain("docs/architecture/overlays/PRD-SANGUO-V4/08/_index.md");
            acceptance.Should().HaveCount(8);
            acceptance[0].Should().Contain("Runtime HUD And Outcome Surfaces");
            acceptance[0].Should().Contain("HUD / Prompt / Outcome Surfaces");
        }
    }

    // ACC:T177.2
    [Fact]
    [Trait("acceptance", "ACC:T177.2")]
    public void ShouldRequireRuntimeHudOutcomeAndPromptSurfaces_WhenReadingCandidateSlice()
    {
        var repoRoot = FindRepoRoot();
        using var candidateDoc = LoadJson(repoRoot, CandidatePath);
        var candidate = FindCandidateByScreenGroup(candidateDoc.RootElement, CandidateScreenGroup);

        candidate.Should().NotBeNull();
        var surfaces = ReadStringArray(candidate.Value, "suggested_standalone_surfaces");
        surfaces.Should().ContainInOrder("RuntimeHud", "OutcomePanel", "RuntimePromptPanel");

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            ReadStringArray(task, "acceptance")[1]
                .Should().Contain("RuntimeHud")
                .And.Contain("OutcomePanel")
                .And.Contain("RuntimePromptPanel");
        }
    }

    // ACC:T177.3
    [Fact]
    [Trait("acceptance", "ACC:T177.3")]
    public void ShouldMapRuntimeHudFieldsUsingProductionMapper_WhenRuntimePayloadIsProvided()
    {
        var vm = CampaignHudParameterViewModelMapper.Map(
            commanderId: "liu_bei",
            activeStrategemId: "strat_supply",
            passiveStrategemId: "strat_defense",
            difficultyCode: "normal",
            turnNumber: 8,
            bossId: "dong_zhuo",
            bossRoundNumber: 8,
            nextRoundPressureForecast: 3,
            releaseMode: false,
            resolveCommanderLabel: token => token == "liu_bei" ? "Liu Bei" : token,
            resolveStrategemLabel: token => token switch
            {
                "strat_supply" => "Supply Boost",
                "strat_defense" => "Shield Wall",
                _ => token,
            },
            resolveDifficultyLabel: token => token == "normal" ? "Normal" : token,
            resolveBossLabel: token => token == "dong_zhuo" ? "Dong Zhuo" : token);

        vm.Commander.Should().Be("Liu Bei");
        vm.Strategems.Should().Be("Supply Boost / Shield Wall");
        vm.Difficulty.Should().Be("Normal");
        vm.RoundMarker.Should().Be("R8");
        vm.BossPressureContext.Should().Be("Dong Zhuo | R8 | +3");
    }

    // ACC:T177.4
    [Fact]
    [Trait("acceptance", "ACC:T177.4")]
    public void ShouldKeepRewardDraftDeterministicWithObjectiveEvidence_WhenInputsRepeat()
    {
        var first = RewardDraftCandidateDeterminismEngine.GenerateDraftCandidates(
            seed: 119120,
            source: "objective_reward",
            choiceCount: 3,
            actionCardsCatalog: null,
            relicsCatalog: null);
        var second = RewardDraftCandidateDeterminismEngine.GenerateDraftCandidates(
            seed: 119120,
            source: "objective_reward",
            choiceCount: 3,
            actionCardsCatalog: null,
            relicsCatalog: null);

        first.Should().HaveCount(3);
        second.Should().Equal(first);

        var emissions = new[]
        {
            new ObjectiveRewardSourceEmission("event", "reward_evt_1", 10),
            new ObjectiveRewardSourceEmission("elite", "reward_elite_1", 20),
            new ObjectiveRewardSourceEmission("boss", "reward_boss_1", 30),
        };
        var evidence = ObjectiveRewardSourceIntegration.BuildDeterministicEvidence(emissions);
        evidence.EvidenceSignature.Should().Be("R8:event|elite|boss");
    }

    // ACC:T177.5
    [Fact]
    [Trait("acceptance", "ACC:T177.5")]
    public void ShouldAllowSkipOnlyAsRuleBlockedFallback_WhenEvaluatingEventTileFlow()
    {
        var module = new EventTileAutoTriggerEnforcementModule();

        module.OnPlayerLanded(EventTileType.Event);
        var duringEvent = module.EvaluateSkip();
        duringEvent.IsAllowed.Should().BeFalse();
        duringEvent.BlockedReason.Should().Be(EventTileAutoTriggerEnforcementModule.SkipBlockedReasonMandatoryEventResolutionActive);

        module.OnPlayerLanded(EventTileType.Normal);
        module.SetSkipEligibility(isEligible: false, blockedReason: "boss-action-pending");
        var ruleBlocked = module.EvaluateSkip();
        ruleBlocked.IsAllowed.Should().BeFalse();
        ruleBlocked.BlockedReason.Should().Be("boss-action-pending");

        module.SetSkipEligibility(isEligible: true);
        var allowed = module.EvaluateSkip();
        allowed.IsAllowed.Should().BeTrue();
        allowed.BlockedReason.Should().BeNull();
    }

    // ACC:T177.6
    [Fact]
    [Trait("acceptance", "ACC:T177.6")]
    public void ShouldFailClosure_WhenDeterminismIsMissingOrScopeLeaks()
    {
        // Use production split-evidence closure pack as real gate behavior.
        var closureWithoutDeterminism = CampLifecycleEngineIntegrationPack.EvaluateSplitEvidence(
            hasTask87Evidence: true,
            hasTask88Evidence: false,
            CampLifecycleEngineIntegrationPack.SplitScopeT87);
        var closureWithoutDeterminismOutcome = ToTask177ClosureOutcome(closureWithoutDeterminism);
        closureWithoutDeterminismOutcome.IsClosed.Should().BeFalse();
        closureWithoutDeterminismOutcome.FailureCode.Should().Be("MISSING_DETERMINISTIC_DRAFT_EVIDENCE");

        // Missing required scope token should fail closure even when split evidence flags are true.
        var closureWithScopeLeak = CampLifecycleEngineIntegrationPack.EvaluateSplitEvidence(
            hasTask87Evidence: true,
            hasTask88Evidence: true,
            CampLifecycleEngineIntegrationPack.SplitScopeT87);
        var closureWithScopeLeakOutcome = ToTask177ClosureOutcome(closureWithScopeLeak);
        closureWithScopeLeakOutcome.IsClosed.Should().BeFalse();
        closureWithScopeLeakOutcome.FailureCode.Should().Be("UNRELATED_GAMEPLAY_CHANGE_DETECTED");

        var closurePass = CampLifecycleEngineIntegrationPack.EvaluateSplitEvidence(
            hasTask87Evidence: true,
            hasTask88Evidence: true,
            CampLifecycleEngineIntegrationPack.SplitScopeT87,
            CampLifecycleEngineIntegrationPack.SplitScopeT88);
        var closurePassOutcome = ToTask177ClosureOutcome(closurePass);
        closurePassOutcome.IsClosed.Should().BeTrue();
        closurePassOutcome.FailureCode.Should().BeNull();
    }

    // ACC:T177.7
    [Fact]
    [Trait("acceptance", "ACC:T177.7")]
    public void ShouldMapAcceptanceRefsToAllRequiredScopeTasks_WhenReadingTaskViews()
    {
        var repoRoot = FindRepoRoot();
        var requiredEvidenceRefs = new[]
        {
            Task78DraftRef,
            Task78SplitRef,
            Task104SplitRef,
            Task106SplitRef,
            Task137SplitRef,
            Task141SplitRef,
            Task142SplitRef,
        };
        var requiredScopeIds = new[] { "T78", "T104", "T106", "T119", "T120", "T137", "T141", "T142" };

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");
            var testStrategy = ReadStringArray(task, "test_strategy");
            var scopeRefs = ReadStringArray(task, "acceptanceRefs");
            var mergedAcceptance = string.Join("\n", acceptance);
            var mergedStrategy = string.Join("\n", testStrategy);

            testRefs.Should().Contain(Task177Ref);
            testRefs.Should().Contain(Task177RuntimeUiRef);

            foreach (var requiredRef in requiredEvidenceRefs)
            {
                mergedStrategy.Should().Contain(requiredRef);
            }

            foreach (var scopeId in requiredScopeIds)
            {
                scopeRefs.Should().Contain(scopeId);
                mergedAcceptance.Should().Contain(scopeId);
            }
        }
    }

    // ACC:T177.8
    [Fact]
    [Trait("acceptance", "ACC:T177.8")]
    public void ShouldKeepAuditableEvidenceAcrossFrameworks_WhenValidatingChapter7Artifacts()
    {
        var repoRoot = FindRepoRoot();
        var task177Path = Path.Combine(repoRoot, Task177Ref.Replace('/', Path.DirectorySeparatorChar));
        var task177UiPath = Path.Combine(repoRoot, Task177RuntimeUiRef.Replace('/', Path.DirectorySeparatorChar));
        File.Exists(task177Path).Should().BeTrue();
        File.Exists(task177UiPath).Should().BeTrue();
        ContainsTokenInFile(task177Path, "ACC:T177.8").Should().BeTrue();
        ContainsTokenInFile(task177UiPath, "ACC:T177.1").Should().BeTrue();
        ContainsTokenInFile(task177UiPath, "ACC:T177.3").Should().BeTrue();

        var chapter7Summary = FindLatestArtifact(repoRoot, "chapter7-ui-wiring", "summary.json");
        var chapter7Manifest = FindLatestArtifact(repoRoot, "chapter7-ui-wiring", "artifact-manifest.json");
        var chapter7GateSummary = FindLatestArtifact(repoRoot, "chapter7-ui-wiring-gate", "summary.json");

        chapter7Summary.Should().NotBeNull();
        chapter7Manifest.Should().NotBeNull();
        chapter7GateSummary.Should().NotBeNull();

        using var chapter7SummaryDoc = JsonDocument.Parse(File.ReadAllText(chapter7Summary!, System.Text.Encoding.UTF8));
        using var chapter7ManifestDoc = JsonDocument.Parse(File.ReadAllText(chapter7Manifest!, System.Text.Encoding.UTF8));
        using var chapter7GateDoc = JsonDocument.Parse(File.ReadAllText(chapter7GateSummary!, System.Text.Encoding.UTF8));

        chapter7SummaryDoc.RootElement.GetProperty("status").GetString().Should().Be("ok");
        chapter7GateDoc.RootElement.GetProperty("status").GetString().Should().Be("ok");
        chapter7ManifestDoc.RootElement.GetProperty("status").GetString().Should().Be("ok");

        var artifactTypes = chapter7ManifestDoc.RootElement
            .GetProperty("artifacts")
            .EnumerateArray()
            .Select(static item => item.GetProperty("artifact_type").GetString() ?? string.Empty)
            .ToArray();
        artifactTypes.Should().Contain("input-snapshot");
        artifactTypes.Should().Contain("candidate-sidecar");
        artifactTypes.Should().Contain("summary");

        var splitEvidenceRefs = new[] { Task78DraftRef, Task104SplitRef, Task106SplitRef, Task141SplitRef, Task142SplitRef };
        foreach (var splitRef in splitEvidenceRefs)
        {
            var abs = Path.Combine(repoRoot, splitRef.Replace('/', Path.DirectorySeparatorChar));
            File.Exists(abs).Should().BeTrue($"required evidence file must exist: {splitRef}");
        }
    }

    private static string FindRepoRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            var marker = Path.Combine(current.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(marker))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks.json).");
    }

    private static JsonDocument LoadJson(string repoRoot, params string[] parts)
    {
        var path = Path.Combine(new[] { repoRoot }.Concat(parts).ToArray());
        using var stream = File.OpenRead(path);
        return JsonDocument.Parse(stream);
    }

    private static JsonElement GetTaskByTaskmasterId(string repoRoot, string fileName, int taskmasterId)
    {
        using var doc = LoadJson(repoRoot, ".taskmaster", "tasks", fileName);
        foreach (var task in doc.RootElement.EnumerateArray())
        {
            if (task.TryGetProperty("taskmaster_id", out var idProperty) &&
                idProperty.ValueKind == JsonValueKind.Number &&
                idProperty.TryGetInt32(out var idValue) &&
                idValue == taskmasterId)
            {
                return task.Clone();
            }
        }

        throw new InvalidOperationException($"Task {taskmasterId} not found in {fileName}.");
    }

    private static JsonElement? FindCandidateByScreenGroup(JsonElement root, string screenGroup)
    {
        if (!root.TryGetProperty("candidates", out var candidates) || candidates.ValueKind != JsonValueKind.Array)
        {
            return null;
        }

        foreach (var candidate in candidates.EnumerateArray())
        {
            if (!candidate.TryGetProperty("screen_group", out var value) || value.ValueKind != JsonValueKind.String)
            {
                continue;
            }

            if (string.Equals(value.GetString(), screenGroup, StringComparison.Ordinal))
            {
                return candidate.Clone();
            }
        }

        return null;
    }

    private static string[] ReadStringArray(JsonElement element, string propertyName)
    {
        element.TryGetProperty(propertyName, out var value).Should().BeTrue();
        value.ValueKind.Should().Be(JsonValueKind.Array);
        return value.EnumerateArray().Select(static item => item.GetString() ?? string.Empty).ToArray();
    }

    private static bool ContainsTokenInFile(string path, string token)
    {
        foreach (var line in File.ReadLines(path))
        {
            if (line.Contains(token, StringComparison.Ordinal))
            {
                return true;
            }
        }

        return false;
    }

    private static string? FindLatestArtifact(string repoRoot, string artifactDirectoryName, string fileName)
    {
        var logsCiRoot = Path.Combine(repoRoot, "logs", "ci");
        if (!Directory.Exists(logsCiRoot))
        {
            return null;
        }

        var marker = "/" + artifactDirectoryName.Trim().Replace('\\', '/').Trim('/') + "/";
        return Directory.GetFiles(logsCiRoot, fileName, SearchOption.AllDirectories)
            .Where(path => path.Replace('\\', '/').Contains(marker, StringComparison.OrdinalIgnoreCase))
            .OrderByDescending(File.GetLastWriteTimeUtc)
            .FirstOrDefault();
    }

    private static ClosureOutcome ToTask177ClosureOutcome(CampLifecycleEngineIntegrationEvidence evidence)
    {
        if (!evidence.IsClosureComplete)
        {
            if (!evidence.Task88Delivered)
            {
                return new ClosureOutcome(false, "MISSING_DETERMINISTIC_DRAFT_EVIDENCE");
            }

            return new ClosureOutcome(false, "UNRELATED_GAMEPLAY_CHANGE_DETECTED");
        }

        return new ClosureOutcome(true, null);
    }

    private readonly record struct ClosureOutcome(bool IsClosed, string? FailureCode);
}
