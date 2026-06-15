using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts;
using Xunit;

namespace Game.Core.Tests.Contracts;

public sealed class JsonEventDataContractsTests
{
    private const int TaskId178 = 178;
    private const int TaskId219 = 219;
    private const string CandidatePath = "docs/gdd/ui-gdd-flow.candidates.json";
    private const string CandidateScreenGroup = "Combat Pressure And Interaction Surfaces";

    [Fact]
    public void ShouldCarryJsonString_WhenUsingRawJsonEventData()
    {
        var payload = new RawJsonEventData("{\"a\":1}");
        payload.Json.Should().Be("{\"a\":1}");
        payload.Should().BeAssignableTo<IEventData>();
    }

    [Fact]
    public void ShouldProduceJsonElement_WhenJsonElementEventDataIsCreatedFromObject()
    {
        var payload = JsonElementEventData.FromObject(new { a = 1 });
        payload.Should().BeAssignableTo<IEventData>();

        payload.Value.ValueKind.Should().Be(JsonValueKind.Object);
        payload.Value.GetProperty("a").GetInt32().Should().Be(1);
    }

    // ACC:T178.1
    [Trait("acceptance", "ACC:T178.1")]
    [Fact]
    public void ShouldKeepTask178BoundToCombatPressureInteractionSlice_WhenReadingTaskViews()
    {
        var back = LoadTaskFromView("tasks_back.json", TaskId178);
        var gameplay = LoadTaskFromView("tasks_gameplay.json", TaskId178);

        AcceptanceLine(back, 0).Should().Contain("Combat Pressure And Interaction Surfaces");
        AcceptanceLine(back, 0).Should().Contain("Combat HUD / Pressure / Camera Feedback");
        AcceptanceLine(gameplay, 0).Should().Contain("Combat Pressure And Interaction Surfaces");
        AcceptanceLine(gameplay, 0).Should().Contain("Combat HUD / Pressure / Camera Feedback");
    }

    // ACC:T178.2
    [Trait("acceptance", "ACC:T178.2")]
    [Fact]
    public void ShouldRequireCombatHudPressureAndCameraSurfaces_WhenReadingCandidateAndAcceptance()
    {
        using var candidate = LoadJsonDocument(CandidatePath);
        var slice = FindCandidateByScreenGroup(candidate.RootElement, CandidateScreenGroup);
        slice.Should().NotBeNull();
        var surfaces = ReadStringArray(slice.Value, "suggested_standalone_surfaces");

        surfaces.Should().Contain("CombatHud");
        surfaces.Should().Contain("PressurePanel");
        surfaces.Should().Contain("CameraControlOverlay");

        var back = LoadTaskFromView("tasks_back.json", TaskId178);
        AcceptanceLine(back, 1).Should().Contain("CombatHud");
        AcceptanceLine(back, 1).Should().Contain("PressurePanel");
        AcceptanceLine(back, 1).Should().Contain("CameraControlOverlay");
    }

    // ACC:T178.3
    [Trait("acceptance", "ACC:T178.3")]
    [Fact]
    public void ShouldRequireRuntimeCombatVisibilityWithoutHiddenState_WhenReadingAcceptance()
    {
        var gameplay = LoadTaskFromView("tasks_gameplay.json", TaskId178);
        var line = AcceptanceLine(gameplay, 2);

        line.Should().Contain("enemy pressure");
        line.Should().Contain("targeting");
        line.Should().Contain("combat outcomes");
        line.Should().Contain("camera interaction");
        line.Should().Contain("trigger-to-response mappings");
        line.Should().Contain("target changes");
        line.Should().Contain("pathing previews");
        line.Should().Contain("combat resolution");
        line.Should().Contain("visible contract data");
        line.Should().MatchRegex("(?i)(must not depend on hidden combat state|without hidden combat state)");
    }

    // ACC:T178.4
    [Trait("acceptance", "ACC:T178.4")]
    [Fact]
    public void ShouldRequireExplicitEmptyStateBeforeCombatDataIsAvailable_WhenReadingAcceptance()
    {
        var back = LoadTaskFromView("tasks_back.json", TaskId178);
        var line = AcceptanceLine(back, 3);

        line.Should().Contain("combat data is not yet available");
        line.Should().Contain("defined empty state");
        line.Should().Contain("no active pressure or combat indicators");
        line.Should().Contain("must not present stale or implied active combat state");
    }

    // ACC:T178.5
    [Trait("acceptance", "ACC:T178.5")]
    [Fact]
    public void ShouldRequireUserVisibleFailureFeedbackForInvalidCombatState_WhenReadingAcceptance()
    {
        var gameplay = LoadTaskFromView("tasks_gameplay.json", TaskId178);
        var line = AcceptanceLine(gameplay, 4);

        line.Should().Contain("blocked, invalid, or hidden combat state");
        line.Should().Contain("explicit per-surface failure feedback");
        line.Should().Contain("reason code or message");
        line.Should().Contain("affected surface");
        line.Should().Contain("next actionable step");
        line.Should().Contain("clear or disable conflicting active indicators");
        line.Should().Contain("silent desync");
    }

    // ACC:T178.6
    [Trait("acceptance", "ACC:T178.6")]
    [Fact]
    public void ShouldRequireSplit145And146ClosureForContractBoundary_WhenReadingAcceptance()
    {
        var back = LoadTaskFromView("tasks_back.json", TaskId178);
        var line = AcceptanceLine(back, 5);

        line.Should().Contain("split tasks 145 and 146");
        line.Should().Contain("campaign events remain contract-first");
        line.Should().Contain("consumed through the DTO mapper registry");
        line.Should().Contain("deterministic domain state stays behind existing contracts");
        line.Should().Contain("no unrelated gameplay behavior");
    }

    // ACC:T178.7
    [Trait("acceptance", "ACC:T178.7")]
    [Fact]
    public void ShouldMapAcceptanceEvidenceToScopeItemsT109T126T134T146_WhenReadingTaskViews()
    {
        var back = LoadTaskFromView("tasks_back.json", TaskId178);
        var gameplay = LoadTaskFromView("tasks_gameplay.json", TaskId178);

        var requiredScope = new[] { "T109", "T126", "T134", "T146" };
        var backRefs = ReadStringArray(back, "acceptanceRefs");
        var gameplayRefs = ReadStringArray(gameplay, "acceptanceRefs");

        foreach (var scope in requiredScope)
        {
            backRefs.Should().Contain(scope);
            gameplayRefs.Should().Contain(scope);
            AcceptanceLine(back, 6).Should().Contain(scope);
            AcceptanceLine(gameplay, 6).Should().Contain(scope);
        }
    }

    // ACC:T178.8
    [Trait("acceptance", "ACC:T178.8")]
    [Fact]
    public void ShouldRequireAuditablePerFrameworkResultsAndNACase_WhenReadingAcceptance()
    {
        var back = LoadTaskFromView("tasks_back.json", TaskId178);
        var line = AcceptanceLine(back, 7);

        line.Should().Contain("xUnit/GdUnit test coverage");
        line.Should().Contain("auditable per-framework pass/fail results");
        line.Should().Contain("N/A with rationale");
    }

    // ACC:T178.9
    [Trait("acceptance", "ACC:T178.9")]
    [Fact]
    public void ShouldRequireDeterministicCameraFeedbackReset_WhenReadingAcceptance()
    {
        var back = LoadTaskFromView("tasks_back.json", TaskId178);
        var line = AcceptanceLine(back, 8);

        line.Should().Contain("Camera feedback must reset deterministically");
        line.Should().Contain("combat pressure becomes unavailable");
        line.Should().Contain("targeting is cleared");
        line.Should().Contain("returns to neutral state");
        line.Should().Contain("without stale focus cues");
    }

    // ACC:T219.1
    [Trait("acceptance", "ACC:T219.1")]
    [Fact]
    public void ShouldBindTask219ToReadableLoopSourceRequirements_WhenReadingGameplayAcceptance()
    {
        var gameplay = LoadTaskFromView("tasks_gameplay.json", TaskId219);

        AcceptanceLine(gameplay, 0).Should().Contain("REQ-f3bdfec8e344");
    }

    // ACC:T219.2
    [Trait("acceptance", "ACC:T219.2")]
    [Fact]
    public void ShouldBindTask219ToReadableLoopUiFlowRequirement_WhenReadingGameplayAcceptance()
    {
        var gameplay = LoadTaskFromView("tasks_gameplay.json", TaskId219);

        AcceptanceLine(gameplay, 1).Should().Contain("REQ-40ca2ff8bb7b");
    }

    // ACC:T219.3
    // ACC:T219.4
    // ACC:T219.5
    // ACC:T219.6
    // ACC:T219.7
    [Trait("acceptance", "ACC:T219.3")]
    [Trait("acceptance", "ACC:T219.4")]
    [Trait("acceptance", "ACC:T219.5")]
    [Trait("acceptance", "ACC:T219.6")]
    [Trait("acceptance", "ACC:T219.7")]
    [Fact]
    public void ShouldRequireTask219ReadableLoopUiSurfaces_WhenReadingGameplayAcceptance()
    {
        var gameplay = LoadTaskFromView("tasks_gameplay.json", TaskId219);

        AcceptanceLine(gameplay, 2).Should().ContainAll("phase", "pressure", "resources", "HP", "prompt", "outcome");
        AcceptanceLine(gameplay, 3).Should().Contain("updates");
        AcceptanceLine(gameplay, 4).Should().ContainAll("player action", "visible context", "outcome impact");
        AcceptanceLine(gameplay, 5).Should().ContainAll("refusal reason", "state unchanged", "visible refusal feedback");
        AcceptanceLine(gameplay, 6).Should().ContainAll("loop progression path", "blocked or invalid action path", "observable UI text");
    }

    [Fact]
    public void ShouldRequireTask219PureCoreDeterministicCoverage_WhenReadingGameplayAcceptance()
    {
        var gameplay = LoadTaskFromView("tasks_gameplay.json", TaskId219);

        AcceptanceLine(gameplay, 7).Should().ContainAll("xUnit coverage", "deterministic loop behavior");
        AcceptanceLine(gameplay, 8).Should().ContainAll("xUnit coverage", "primary deterministic behavior");
        AcceptanceLine(gameplay, 9).Should().ContainAll("pure core logic", "Godot UI code limited to presentation");
        AcceptanceLine(gameplay, 10).Should().ContainAll("pure core logic");
    }

    [Fact]
    public void ShouldRequireTask219PostRefactorAuditEvidence_WhenReadingGameplayAcceptance()
    {
        var gameplay = LoadTaskFromView("tasks_gameplay.json", TaskId219);

        AcceptanceLine(gameplay, 11).Should().ContainAll("passing relevant tests", "Chapter 3 coverage audit");
        AcceptanceLine(gameplay, 12).Should().ContainAll("Chapter 3 coverage audit", "preserving passing tests");
        AcceptanceLine(gameplay, 13).Should().ContainAll("Chapter 3.8 triplet baseline validators", "evidence is recorded");
        AcceptanceLine(gameplay, 14).Should().ContainAll("Chapter 3.8 triplet baseline validators", "task view");
    }

    private static JsonDocument LoadJsonDocument(string repoRelativePath)
    {
        var fullPath = Path.Combine(FindRepoRoot(), repoRelativePath.Replace('/', Path.DirectorySeparatorChar));
        using var stream = File.OpenRead(fullPath);
        return JsonDocument.Parse(stream);
    }

    private static JsonElement LoadTaskFromView(string viewFileName, int taskmasterId)
    {
        using var viewDoc = LoadJsonDocument($".taskmaster/tasks/{viewFileName}");
        foreach (var task in viewDoc.RootElement.EnumerateArray())
        {
            if (task.TryGetProperty("taskmaster_id", out var idNode) &&
                idNode.ValueKind == JsonValueKind.Number &&
                idNode.TryGetInt32(out var id) &&
                id == taskmasterId)
            {
                return task.Clone();
            }
        }

        throw new InvalidOperationException($"Task {taskmasterId} not found in {viewFileName}.");
    }

    private static string AcceptanceLine(JsonElement task, int index)
    {
        var acceptance = ReadStringArray(task, "acceptance");
        acceptance.Length.Should().BeGreaterThan(index);
        return acceptance[index];
    }

    private static string[] ReadStringArray(JsonElement element, string propertyName)
    {
        element.TryGetProperty(propertyName, out var value).Should().BeTrue();
        value.ValueKind.Should().Be(JsonValueKind.Array);
        return value.EnumerateArray().Select(static node => node.GetString() ?? string.Empty).ToArray();
    }

    private static JsonElement? FindCandidateByScreenGroup(JsonElement root, string screenGroup)
    {
        if (!root.TryGetProperty("candidates", out var candidates) || candidates.ValueKind != JsonValueKind.Array)
        {
            return null;
        }

        foreach (var candidate in candidates.EnumerateArray())
        {
            if (!candidate.TryGetProperty("screen_group", out var groupNode) || groupNode.ValueKind != JsonValueKind.String)
            {
                continue;
            }

            if (string.Equals(groupNode.GetString(), screenGroup, StringComparison.Ordinal))
            {
                return candidate.Clone();
            }
        }

        return null;
    }

    private static string FindRepoRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            var marker = Path.Combine(current.FullName, ".taskmaster", "tasks", "tasks_back.json");
            if (File.Exists(marker))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        throw new DirectoryNotFoundException("Unable to locate repository root.");
    }
}
