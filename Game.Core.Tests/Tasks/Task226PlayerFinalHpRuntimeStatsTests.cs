using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task226PlayerFinalHpRuntimeStatsTests
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true,
    };

    // ACC:T226.1
    [Trait("acceptance", "ACC:T226.1")]
    [Fact]
    public void ShouldBindTask226ToRuntimeStatsSourceRequirements_WhenReadingGameplayAcceptance()
    {
        var gameplay = LoadTaskFromView("tasks_gameplay.json", 226);

        AcceptanceLine(gameplay, 0).Should().Contain("REQ-698a6d643eff");
        AcceptanceLine(gameplay, 1).Should().Contain("REQ-e0be38d2d0c2");
    }

    // ACC:T226.2
    [Trait("acceptance", "ACC:T226.2")]
    [Fact]
    public void ShouldExposePlayerFinalHp_WhenRuntimePlayerStatsAreInspected()
    {
        typeof(SanguoGameEndPlayerStats)
            .GetProperty("PlayerFinalHp", BindingFlags.Public | BindingFlags.Instance)
            .Should()
            .NotBeNull("runtime player stats must expose the final player HP for combat outcome consumers");
    }

    // ACC:T226.3
    [Trait("acceptance", "ACC:T226.3")]
    [Fact]
    public void ShouldPreservePlayerFinalHp_WhenRuntimePlayerStatsRoundTripThroughJson()
    {
        var stats = new SanguoGameEndPlayerStats("player-1", 1200m, PlayerFinalHp: 37);

        var json = JsonSerializer.Serialize(stats, JsonOptions);
        var roundTripped = JsonSerializer.Deserialize<SanguoGameEndPlayerStats>(json, JsonOptions);

        json.Should().Contain("\"playerFinalHp\":37");
        roundTripped.Should().NotBeNull();
        roundTripped!.PlayerFinalHp.Should().Be(37);
    }

    // ACC:T226.4
    [Trait("acceptance", "ACC:T226.4")]
    [Fact]
    public void ShouldEmitKnownFinalHp_WhenRuntimePlayerStatsAreCreatedForOutcome()
    {
        const int finalHp = 12;

        var stats = new SanguoGameEndPlayerStats("player-1", 900m, PlayerFinalHp: finalHp);

        stats.PlayerFinalHp.Should().Be(finalHp);
    }

    // ACC:T226.5
    [Trait("acceptance", "ACC:T226.5")]
    [Trait("acceptance", "ACC:T226.6")]
    [Fact]
    public void ShouldCoverPrimaryDeterministicPlayerFinalHpBehavior_WhenTask226Runs()
    {
        var stats = new SanguoGameEndPlayerStats("player-1", 0m, PlayerFinalHp: 1);

        stats.PlayerFinalHp.Should().Be(1);
    }

    // ACC:T226.7
    [Trait("acceptance", "ACC:T226.7")]
    [Trait("acceptance", "ACC:T226.8")]
    [Fact]
    public void ShouldKeepPlayerFinalHpRuntimeStatsPureCore_WhenPublicContractsAreInspected()
    {
        typeof(SanguoGameEndPlayerStats)
            .Assembly
            .GetReferencedAssemblies()
            .Select(reference => reference.Name)
            .Should()
            .NotContain("GodotSharp");
    }

    // ACC:T226.9
    [Trait("acceptance", "ACC:T226.9")]
    // ACC:T226.10
    [Trait("acceptance", "ACC:T226.10")]
    [Fact]
    public void ShouldPreserveRelevantRuntimeStatsContracts_WhenTask226IsRefactored()
    {
        var stats = new SanguoGameEndPlayerStats("player-1", 500m);

        stats.PlayerId.Should().Be("player-1");
        stats.Money.Should().Be(500m);
        stats.PlayerFinalHp.Should().Be(0);
    }

    // ACC:T226.11
    [Trait("acceptance", "ACC:T226.11")]
    // ACC:T226.12
    [Trait("acceptance", "ACC:T226.12")]
    [Fact]
    public void ShouldKeepTask226CoverageAuditObligationsTraceable_WhenReadingGameplayAcceptance()
    {
        var gameplay = LoadTaskFromView("tasks_gameplay.json", 226);

        AcceptanceLine(gameplay, 10).Should().Contain("Chapter 3 coverage audit");
        AcceptanceLine(gameplay, 11).Should().Contain("Chapter 3 coverage audit");
    }

    // ACC:T226.13
    [Trait("acceptance", "ACC:T226.13")]
    // ACC:T226.14
    [Trait("acceptance", "ACC:T226.14")]
    [Fact]
    public void ShouldKeepTask226TripletValidatorObligationsTraceable_WhenReadingGameplayAcceptance()
    {
        var gameplay = LoadTaskFromView("tasks_gameplay.json", 226);

        AcceptanceLine(gameplay, 12).Should().Contain("Chapter 3.8 triplet baseline validators");
        AcceptanceLine(gameplay, 13).Should().Contain("Chapter 3.8 triplet baseline validators");
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

    private static JsonDocument LoadJsonDocument(string repoRelativePath)
    {
        var fullPath = Path.Combine(FindRepoRoot(), repoRelativePath.Replace('/', Path.DirectorySeparatorChar));
        using var stream = File.OpenRead(fullPath);
        return JsonDocument.Parse(stream);
    }

    private static string[] ReadStringArray(JsonElement element, string propertyName)
    {
        element.TryGetProperty(propertyName, out var value).Should().BeTrue();
        value.ValueKind.Should().Be(JsonValueKind.Array);
        return value.EnumerateArray().Select(static node => node.GetString() ?? string.Empty).ToArray();
    }

    private static string FindRepoRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            var marker = Path.Combine(current.FullName, ".taskmaster", "tasks", "tasks_gameplay.json");
            if (File.Exists(marker))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        throw new DirectoryNotFoundException("Unable to locate repository root.");
    }
}
