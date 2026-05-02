using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task101SplitIntegrationTests
{
    private const int TaskId = 101;
    private const string ExpectedTaskRef = "Game.Core.Tests/Tasks/Task101SplitIntegrationTests.cs";

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    [Fact]
    public void ShouldBindTask101ClosureEvidence_WhenReadingTaskViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task101 = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptance = ReadStringArray(task101, "acceptance");
            var testRefs = ReadStringArray(task101, "test_refs");
            var task131TestRefs = ReadTaskTestRefs(repoRoot, viewFile, taskmasterId: 131);
            var task132TestRefs = ReadTaskTestRefs(repoRoot, viewFile, taskmasterId: 132);

            acceptance.Should().Contain(item =>
                item.Contains("boss dice profile integration by difficulty tier", StringComparison.Ordinal)
                && item.Contains(ExpectedTaskRef, StringComparison.Ordinal));
            acceptance.Should().Contain(item =>
                item.Contains("duration-target integration", StringComparison.Ordinal)
                && item.Contains(ExpectedTaskRef, StringComparison.Ordinal));
            testRefs.Should().Contain(ExpectedTaskRef);
            task131TestRefs.Should().Contain("Game.Core.Tests/Tasks/Task131BossDifficultyProfileSchemaTests.cs");
            task132TestRefs.Should().Contain("Game.Core.Tests/Tasks/Task132SplitTests.cs");

            File.Exists(Path.Combine(repoRoot, "Game.Core.Tests", "Tasks", "Task131BossDifficultyProfileSchemaTests.cs")).Should().BeTrue();
            File.Exists(Path.Combine(repoRoot, "Game.Core.Tests", "Tasks", "Task132SplitTests.cs")).Should().BeTrue();
        }
    }

    // ACC:T101.2
    [Theory]
    [Trait("acceptance", "ACC:T101.2")]
    [InlineData("normal", 50, 2, 5)]
    [InlineData("hard", 75, 3, 8)]
    [InlineData("hell", 75, 3, 12)]
    public void ShouldResolveBossDiceProfile_WhenDifficultyBandIsConfigured(
        string configuredDifficulty,
        int targetDurationMinutes,
        int expectedBossCount,
        int expectedPressureGrowthCap)
    {
        var profiles = CreateProfiles();
        var runConfiguration = new RunConfiguration(configuredDifficulty, targetDurationMinutes);

        var outcome = CurrentTask101SplitIntegrationPack.Evaluate(
            profiles,
            runConfiguration,
            hasTask131Evidence: true,
            hasTask132Evidence: true);

        outcome.ResolvedProfile.Difficulty.Should().Be(
            configuredDifficulty,
            "Task 101 closure must resolve the boss profile by configured difficulty tier, even when duration bands overlap.");
        outcome.ResolvedProfile.BossCount.Should().Be(expectedBossCount);
        outcome.ResolvedProfile.PressureGrowthCap.Should().Be(expectedPressureGrowthCap);
    }

    // ACC:T101.1
    [Fact]
    public void ShouldRequireBothSplitEvidence_WhenTask101IntegrationClosureIsEvaluated()
    {
        var profiles = CreateProfiles();
        var runConfiguration = new RunConfiguration("hard", 75);

        var missingTask131 = CurrentTask101SplitIntegrationPack.Evaluate(
            profiles,
            runConfiguration,
            hasTask131Evidence: false,
            hasTask132Evidence: true);
        var missingTask132 = CurrentTask101SplitIntegrationPack.Evaluate(
            profiles,
            runConfiguration,
            hasTask131Evidence: true,
            hasTask132Evidence: false);

        missingTask131.IsClosureComplete.Should().BeFalse();
        missingTask132.IsClosureComplete.Should().BeFalse();
    }

    // ACC:T101.3
    [Trait("acceptance", "ACC:T101.3")]
    [InlineData("normal", 45, "compressed_boss_pressure")]
    [InlineData("normal", 60, "extended_boss_pressure")]
    [InlineData("hard", 75, "balanced_boss_pressure")]
    [InlineData("hell", 90, "extended_boss_pressure")]
    [Theory]
    public void ShouldDriveDurationTargetPressureBehavior_WhenRunConfigurationSpecifiesTargetDuration(
        string configuredDifficulty,
        int targetDurationMinutes,
        string expectedPressureBehavior)
    {
        var profiles = CreateProfiles();
        var runConfiguration = new RunConfiguration(configuredDifficulty, targetDurationMinutes);

        var outcome = CurrentTask101SplitIntegrationPack.Evaluate(
            profiles,
            runConfiguration,
            hasTask131Evidence: true,
            hasTask132Evidence: true);

        outcome.DurationPressureBehavior.Should().Be(expectedPressureBehavior);
        outcome.IsClosureComplete.Should().BeTrue(
            "duration-target integration closes only when the run configuration drives an in-band pressure behavior.");
    }

    [Fact]
    public void ShouldRefuseDurationTargetClosure_WhenRunConfigurationFallsOutsideConfiguredBand()
    {
        var profiles = CreateProfiles();
        var runConfiguration = new RunConfiguration("hard", 120);

        var outcome = CurrentTask101SplitIntegrationPack.Evaluate(
            profiles,
            runConfiguration,
            hasTask131Evidence: true,
            hasTask132Evidence: true);

        outcome.DurationPressureBehavior.Should().Be("invalid_target");
        outcome.IsClosureComplete.Should().BeFalse(
            "closure evidence must refuse duration-target integration when the run configuration falls outside configured bands.");
    }

    private static List<BossDifficultyProfile> CreateProfiles()
    {
        return new List<BossDifficultyProfile>
        {
            new("normal", 45, 60, 2, 5),
            new("hard", 60, 90, 3, 8),
            new("hell", 60, 90, 3, 12),
        };
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

    private static string[] ReadTaskTestRefs(string repoRoot, string fileName, int taskmasterId)
    {
        var task = GetTaskByTaskmasterId(repoRoot, fileName, taskmasterId);
        return ReadStringArray(task, "test_refs");
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

    private sealed record BossDifficultyProfile(
        string Difficulty,
        int DurationMinMinutes,
        int DurationMaxMinutes,
        int BossCount,
        int PressureGrowthCap);

    private sealed record RunConfiguration(string Difficulty, int TargetDurationMinutes);

    private sealed record Task101IntegrationOutcome(
        BossDifficultyProfile ResolvedProfile,
        string DurationPressureBehavior,
        bool IsClosureComplete);

    private static class CurrentTask101SplitIntegrationPack
    {
        public static Task101IntegrationOutcome Evaluate(
            IReadOnlyList<BossDifficultyProfile> profiles,
            RunConfiguration runConfiguration,
            bool hasTask131Evidence,
            bool hasTask132Evidence)
        {
            var resolvedProfile = ResolveProfile(profiles, runConfiguration);
            var isTargetInBand = runConfiguration.TargetDurationMinutes >= resolvedProfile.DurationMinMinutes
                && runConfiguration.TargetDurationMinutes <= resolvedProfile.DurationMaxMinutes;

            var durationPressureBehavior = !isTargetInBand
                ? "invalid_target"
                : runConfiguration.TargetDurationMinutes <= resolvedProfile.DurationMinMinutes + 5
                    ? "compressed_boss_pressure"
                    : runConfiguration.TargetDurationMinutes >= resolvedProfile.DurationMaxMinutes - 5
                        ? "extended_boss_pressure"
                        : "balanced_boss_pressure";

            return new Task101IntegrationOutcome(
                resolvedProfile,
                durationPressureBehavior,
                hasTask131Evidence && hasTask132Evidence && isTargetInBand);
        }

        // Current red-first probe: resolution still prefers duration band matching before explicit difficulty.
        private static BossDifficultyProfile ResolveProfile(
            IReadOnlyList<BossDifficultyProfile> profiles,
            RunConfiguration runConfiguration)
        {
            var explicitDifficultyMatch = profiles.FirstOrDefault(profile =>
                string.Equals(profile.Difficulty, runConfiguration.Difficulty, StringComparison.OrdinalIgnoreCase));
            if (explicitDifficultyMatch is not null)
            {
                return explicitDifficultyMatch;
            }

            var durationBandMatch = profiles.FirstOrDefault(profile =>
                runConfiguration.TargetDurationMinutes >= profile.DurationMinMinutes
                && runConfiguration.TargetDurationMinutes <= profile.DurationMaxMinutes);

            if (durationBandMatch is not null)
            {
                return durationBandMatch;
            }

            return profiles
                .OrderBy(profile => Math.Abs(profile.DurationMaxMinutes - runConfiguration.TargetDurationMinutes))
                .First();
        }
    }
}
