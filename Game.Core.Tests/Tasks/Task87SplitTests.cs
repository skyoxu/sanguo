using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task87SplitTests
{
    private const int TaskId = 87;

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    private static readonly string[] ExpectedTaskRefs =
    {
        "Game.Core.Tests/Tasks/Task87SplitTests.cs",
        "Game.Core.Tests/Domain/SanguoCampaignContractsTests.cs",
        "Game.Core.Tests/Services/SanguoTurnActionFlowTests.cs",
    };

    // ACC:T87.1
    [Fact]
    [Trait("acceptance", "ACC:T87.1")]
    public void ShouldKeepIndependentR2R5SplitNarrative_WhenReadingTask87AcceptanceFromBothViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptanceRefs = ReadStringArray(task, "acceptanceRefs");
            var acceptance = ReadStringArray(task, "acceptance");

            acceptanceRefs.Should().Equal("R2/R5");
            acceptance.Should().HaveCount(1);
            acceptance[0].Should().Contain("R2 camp transition obligation");
            acceptance[0].Should().Contain("R5 one-action-rule obligation");
            acceptance[0].Should().Contain("Game.Core.Tests/Tasks/Task87SplitTests.cs");
            acceptance[0].Should().Contain("Game.Core.Tests/Domain/SanguoCampaignContractsTests.cs");
            acceptance[0].Should().Contain("Game.Core.Tests/Services/SanguoTurnActionFlowTests.cs");
        }
    }

    [Fact]
    public void ShouldRefuseEvidenceScopeExpansion_WhenReadingTask87TestRefsFromBothViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var testRefs = ReadStringArray(task, "test_refs");

            testRefs.Should().HaveCount(3, "Task 87 is split scope and should keep a minimal, deterministic evidence set.");
            testRefs.Should().Equal(ExpectedTaskRefs);
            testRefs.Should().OnlyContain(testRef => ExpectedTaskRefs.Contains(testRef, StringComparer.Ordinal));
        }
    }

    // ACC:T87.1
    [Fact]
    [Trait("acceptance", "ACC:T87.1")]
    public void ShouldExposeCampTransitionCompatibilityMarkers_WhenCheckingR2Boundary()
    {
        SanguoGameTurnAdvanced.EventType.Should().Be("core.sanguo.game.turn.advanced");
        SanguoBossChallengePrompted.FailConsequenceReturnToCampAndEndRound.Should().Be("return_to_camp_end_round");
    }

    // ACC:T87.1
    [Fact]
    [Trait("acceptance", "ACC:T87.1")]
    public async Task ShouldEnforceOneActionRuleDeterministically_WhenEvaluatingR5Boundary()
    {
        var first = await ExecuteSingleTurnTwoActionAttemptsAsync();
        var second = await ExecuteSingleTurnTwoActionAttemptsAsync();

        second.Should().BeEquivalentTo(first);
        first.FirstPlayAccepted.Should().BeTrue();
        first.SecondPlayAccepted.Should().BeFalse();
        first.SecondRejectReason.Should().Be(SanguoActionCardPlayRejected.ReasonAlreadyPlayedThisTurn);
        first.PlayedCount.Should().Be(1);
        first.RejectedCount.Should().Be(1);
    }

    private static async Task<OneActionRuleOutcome> ExecuteSingleTurnTwoActionAttemptsAsync()
    {
        var bus = new CapturingEventBus();
        var economy = new SanguoEconomyManager(bus);
        var manager = new SanguoTurnManager(
            bus: bus,
            economy: economy,
            boardState: new SanguoBoardState(
                players: new[]
                {
                    new SanguoPlayer(playerId: "p1", money: 200m, positionIndex: 0, economyRules: SanguoEconomyRules.Default),
                },
                citiesById: new Dictionary<string, City>(StringComparer.Ordinal)),
            treasury: new SanguoTreasury(),
            totalPositionsHint: 10,
            actionCardsCatalog: BuildActionCardsCatalog());

        await manager.StartNewGameAsync(
            gameId: "g-t87-r5",
            playerOrder: new[] { "p1" },
            year: 1,
            month: 1,
            day: 1,
            correlationId: "corr-start",
            causationId: null);
        bus.Published.Clear();

        var first = await manager.TryPlayHumanActionCardAsync(
            cardId: "ac_step_down",
            correlationId: "corr-first",
            causationId: "ut.action.1");
        var second = await manager.TryPlayHumanActionCardAsync(
            cardId: "ac_step_up",
            correlationId: "corr-second",
            causationId: "ut.action.2");

        var rejected = bus.Published.Single(e => e.Type == SanguoActionCardPlayRejected.EventType);
        var rejectedPayload = JsonSerializer.Deserialize<SanguoActionCardPlayRejected>(
            ((JsonElementEventData)rejected.Data!).Value.GetRawText());

        return new OneActionRuleOutcome(
            FirstPlayAccepted: first,
            SecondPlayAccepted: second,
            SecondRejectReason: rejectedPayload?.ReasonCode,
            PlayedCount: bus.Published.Count(e => e.Type == SanguoActionCardPlayed.EventType),
            RejectedCount: bus.Published.Count(e => e.Type == SanguoActionCardPlayRejected.EventType));
    }

    private static SanguoActionCardsCatalog BuildActionCardsCatalog()
    {
        return new SanguoActionCardsCatalog(
            SchemaVersion: 1,
            Version: 1,
            Cards: Array.AsReadOnly(new[]
            {
                new SanguoActionCardCatalogEntry(
                    CardId: "ac_step_down",
                    NameKey: "card.ac_step_down.name",
                    DescriptionKey: "card.ac_step_down.desc",
                    EffectKind: "economyStepDelta",
                    StepDelta: -1,
                    DurationRounds: 3),
                new SanguoActionCardCatalogEntry(
                    CardId: "ac_step_up",
                    NameKey: "card.ac_step_up.name",
                    DescriptionKey: "card.ac_step_up.desc",
                    EffectKind: "economyStepDelta",
                    StepDelta: 2,
                    DurationRounds: 3),
            }));
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

    private sealed record OneActionRuleOutcome(
        bool FirstPlayAccepted,
        bool SecondPlayAccepted,
        string? SecondRejectReason,
        int PlayedCount,
        int RejectedCount);

    private sealed class CapturingEventBus : IEventBus
    {
        public List<DomainEvent> Published { get; } = new();

        public Task PublishAsync(DomainEvent evt)
        {
            Published.Add(evt);
            return Task.CompletedTask;
        }

        public IDisposable Subscribe(Func<DomainEvent, Task> handler) => throw new NotSupportedException();
    }
}
