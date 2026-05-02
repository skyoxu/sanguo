using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task95CampaignHudParameterViewModelMapperTests
{
    private const int TaskId = 95;
    private const string ExpectedCoreRef = "Game.Core.Tests/Tasks/Task95CampaignHudParameterViewModelMapperTests.cs";
    private const string ExpectedUiRef = "Tests.Godot/tests/UI/test_task95_campaign_integration.gd";

    // Refs: Task 95 task-view metadata consistency
    [Fact]
    [Trait("acceptance", "ACC:T95.1")]
    public void ShouldKeepTaskSpecificRefs_WhenReadingTask95FromBothViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in new[] { "tasks_back.json", "tasks_gameplay.json" })
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");

            acceptance.Should().Contain(item => item.Contains("campaign runtime state", StringComparison.OrdinalIgnoreCase));
            testRefs.Should().Contain(ExpectedCoreRef);
            testRefs.Should().Contain(ExpectedUiRef);
        }
    }

    // ACC:T95.1
    // ACC:T95.2
    [Fact]
    [Trait("acceptance", "ACC:T95.1")]
    public void ShouldMapCampaignHudParametersWithLocalizedValues_WhenResolversReturnLabels()
    {
        var vm = CampaignHudParameterViewModelMapper.Map(
            commanderId: "c_liu_bei",
            activeStrategemId: "strat_active_default",
            passiveStrategemId: "strat_passive_default",
            difficultyCode: "normal",
            turnNumber: 7,
            bossId: "boss_yellow_turban",
            bossRoundNumber: 3,
            nextRoundPressureForecast: 2,
            releaseMode: true,
            resolveCommanderLabel: static id => id == "c_liu_bei" ? "Liu Bei" : null,
            resolveStrategemLabel: static id => id switch
            {
                "strat_active_default" => "Aggressive Push",
                "strat_passive_default" => "Defensive Drill",
                _ => null,
            },
            resolveDifficultyLabel: static code => code == "normal" ? "Normal" : null,
            resolveBossLabel: static id => id == "boss_yellow_turban" ? "Yellow Turban Leader" : null);

        vm.Commander.Should().Be("Liu Bei");
        vm.Strategems.Should().Be("Aggressive Push / Defensive Drill");
        vm.Difficulty.Should().Be("Normal");
        vm.RoundMarker.Should().Be("R3");
        vm.BossPressureContext.Should().Be("Yellow Turban Leader | R3 | +2");
    }

    // ACC:T95.3
    [Fact]
    [Trait("acceptance", "ACC:T95.3")]
    public void ShouldHideRawTokensAndLocalizationKeysInReleaseMode_WhenLabelsAreMissing()
    {
        var vm = CampaignHudParameterViewModelMapper.Map(
            commanderId: "c_unknown",
            activeStrategemId: "strat_missing_active",
            passiveStrategemId: "strat_missing_passive",
            difficultyCode: "nightmare",
            turnNumber: 5,
            bossId: "core.sanguo.boss.challenge.prompted",
            bossRoundNumber: 0,
            nextRoundPressureForecast: 0,
            releaseMode: true,
            resolveCommanderLabel: static _ => "character.c_unknown.name",
            resolveStrategemLabel: static _ => "strategem.raw.missing",
            resolveDifficultyLabel: static _ => "ui.menu.difficulty.nightmare",
            resolveBossLabel: static _ => "core.sanguo.boss.challenge.prompted");

        vm.Commander.Should().Be(CampaignHudParameterViewModelMapper.UnknownCommanderFallback);
        vm.Strategems.Should().Be(
            $"{CampaignHudParameterViewModelMapper.UnknownStrategemFallback} / {CampaignHudParameterViewModelMapper.UnknownStrategemFallback}");
        vm.Difficulty.Should().Be(CampaignHudParameterViewModelMapper.UnknownDifficultyFallback);
        vm.RoundMarker.Should().Be("R5");
        vm.BossPressureContext.Should().Be(CampaignHudParameterViewModelMapper.NoBossPressureFallback);
    }

    [Fact]
    [Trait("acceptance", "ACC:T95.3")]
    public void ShouldAllowDiagnosticRawTokensInDevMode_WhenLabelsAreMissing()
    {
        var vm = CampaignHudParameterViewModelMapper.Map(
            commanderId: "c_missing",
            activeStrategemId: "strat_missing_active",
            passiveStrategemId: "strat_missing_passive",
            difficultyCode: "nightmare",
            turnNumber: 2,
            bossId: "boss_unknown",
            bossRoundNumber: 2,
            nextRoundPressureForecast: 1,
            releaseMode: false,
            resolveCommanderLabel: static _ => null,
            resolveStrategemLabel: static _ => null,
            resolveDifficultyLabel: static _ => null,
            resolveBossLabel: static _ => null);

        vm.Commander.Should().Be("c_missing");
        vm.Strategems.Should().Be("strat_missing_active / strat_missing_passive");
        vm.Difficulty.Should().Be("nightmare");
        vm.RoundMarker.Should().Be("R2");
        vm.BossPressureContext.Should().Be("boss_unknown | R2 | +1");
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
        using var stream = File.OpenRead(path);
        return JsonDocument.Parse(stream);
    }
}
