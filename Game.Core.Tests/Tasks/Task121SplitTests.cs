using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task121SplitTests
{
    private const int TaskId = 121;
    private const string ExpectedCoreRef = "Game.Core.Tests/Tasks/Task121SplitTests.cs";
    private const string ExpectedUiRef1 = "Tests.Godot/tests/UI/test_task121_new_game_setup_constraints_and_start.gd";
    private const string ExpectedUiRef2 = "Tests.Godot/tests/UI/test_task121_new_game_setup_starts_game_with_selected_players_and_money.gd";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    private static readonly string[] CommanderPool =
    {
        "c_liu_bei",
        "c_guan_yu",
        "c_zhang_fei",
        "c_cao_cao",
        "c_sun_quan",
        "c_zhuge_liang",
        "c_lu_bu",
        "c_sima_yi",
    };

    // ACC:T121.1
    [Fact]
    [Trait("acceptance", "ACC:T121.1")]
    public void ShouldKeepTaskSpecificRefs_WhenReadingTask121FromBothViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");
            var chapterRefs = ReadStringArray(task, "chapter_refs");
            var adrRefs = ReadStringArray(task, "adr_refs");

            acceptance.Should().ContainSingle();
            acceptance[0].Should().Contain("commander roster lock/open/default availability model");
            acceptance[0].Should().Contain(ExpectedUiRef1);
            acceptance[0].Should().Contain(ExpectedUiRef2);

            testRefs.Should().Contain(ExpectedCoreRef);
            testRefs.Should().Contain(ExpectedUiRef1);
            testRefs.Should().Contain(ExpectedUiRef2);

            chapterRefs.Should().Contain(new[] { "CH04", "CH05", "CH06", "CH10" });
            adrRefs.Should().Contain(new[] { "ADR-0004", "ADR-0010", "ADR-0020" });
        }
    }

    [Fact]
    public void ShouldResolveTask121UiEvidenceFiles_WhenRepoRootIsLocated()
    {
        var repoRoot = FindRepoRoot();
        var path1 = Path.Combine(repoRoot, "Tests.Godot", "tests", "UI", "test_task121_new_game_setup_constraints_and_start.gd");
        var path2 = Path.Combine(repoRoot, "Tests.Godot", "tests", "UI", "test_task121_new_game_setup_starts_game_with_selected_players_and_money.gd");

        File.Exists(path1).Should().BeTrue();
        File.Exists(path2).Should().BeTrue();
    }

    [Fact]
    [Trait("acceptance", "ACC:T121.1")]
    public void ShouldKeepCommanderSelectableByDefault_WhenNoRosterOverrideIsApplied()
    {
        var ok = SanguoCharacterAssignmentsGenerator.TryBuildAssignments(
            availableCharacterIds: CommanderPool,
            playersCount: 4,
            playerCharacterId: "c_liu_bei",
            seed: 121,
            assignments: out var assignments,
            error: out var error);

        ok.Should().BeTrue(error);
        assignments.Should().ContainKey("p1");
        assignments["p1"].Should().Be("c_liu_bei");
        assignments.Should().HaveCount(4);
        assignments.Values.Should().OnlyHaveUniqueItems();
    }

    [Fact]
    [Trait("acceptance", "ACC:T121.1")]
    public void ShouldRejectCommanderSelection_WhenCommanderIsLockedOutOfAvailableRoster()
    {
        var lockedRoster = CommanderPool.Where(id => !string.Equals(id, "c_liu_bei", StringComparison.Ordinal)).ToArray();

        var ok = SanguoCharacterAssignmentsGenerator.TryBuildAssignments(
            availableCharacterIds: lockedRoster,
            playersCount: 4,
            playerCharacterId: "c_liu_bei",
            seed: 121,
            assignments: out var assignments,
            error: out var error);

        ok.Should().BeFalse();
        error.Should().Be("player_character_not_found");
        assignments.Should().BeEmpty();
    }

    [Fact]
    [Trait("acceptance", "ACC:T121.1")]
    public void ShouldAllowCommanderSelectionAgain_WhenCommanderIsOpenedBackIntoRoster()
    {
        var lockedRoster = CommanderPool.Where(id => !string.Equals(id, "c_liu_bei", StringComparison.Ordinal)).ToArray();
        var openRoster = lockedRoster.Concat(new[] { "c_liu_bei" }).ToArray();

        var lockedOk = SanguoCharacterAssignmentsGenerator.TryBuildAssignments(
            availableCharacterIds: lockedRoster,
            playersCount: 4,
            playerCharacterId: "c_liu_bei",
            seed: 121,
            assignments: out _,
            error: out var lockedError);
        lockedOk.Should().BeFalse();
        lockedError.Should().Be("player_character_not_found");

        var openOk = SanguoCharacterAssignmentsGenerator.TryBuildAssignments(
            availableCharacterIds: openRoster,
            playersCount: 4,
            playerCharacterId: "c_liu_bei",
            seed: 121,
            assignments: out var openedAssignments,
            error: out var openError);

        openOk.Should().BeTrue(openError);
        openedAssignments.Should().ContainKey("p1");
        openedAssignments["p1"].Should().Be("c_liu_bei");
        openedAssignments.Values.Should().OnlyHaveUniqueItems();
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var marker = Path.Combine(dir.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(marker))
            {
                return dir.FullName;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks.json).");
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

    private static string[] ReadStringArray(JsonElement task, string propertyName)
    {
        task.TryGetProperty(propertyName, out var property)
            .Should().BeTrue($"Task {TaskId} must contain '{propertyName}'.");

        property.ValueKind.Should().Be(JsonValueKind.Array);

        return property
            .EnumerateArray()
            .Select(static item => item.GetString() ?? string.Empty)
            .ToArray();
    }

    private static JsonDocument LoadJson(string repoRoot, params string[] relativeParts)
    {
        var path = Path.Combine(new[] { repoRoot }.Concat(relativeParts).ToArray());
        var text = File.ReadAllText(path);
        return JsonDocument.Parse(text);
    }
}
