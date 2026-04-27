using System;
using System.Collections.Generic;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Godot.Scripts.UI;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task146SplitTests
{
    private static readonly JsonDocumentOptions JsonOptions = new() { MaxDepth = 32 };

    // ACC:T146.1
    [Fact]
    [Trait("acceptance", "ACC:T146.1")]
    public void ShouldRouteCampaignEventsThroughDtoMapper_WhenPayloadIsValid()
    {
        var handlers = new FakeHudEventHandlers();
        var controller = BuildController(handlers);
        HudEventHandlerRegistry.RegisterAll(controller, handlers);

        controller.HandleDomainEvent(
            SanguoBossChallengePrompted.EventType,
            source: "domain",
            dataJson: "{\"BossId\":\"boss_yellow_turban\",\"RoundNumber\":3,\"NextRoundPressureForecast\":5}",
            id: "evt-1",
            timestampIso: "2026-04-27T00:00:00Z");

        controller.HandleDomainEvent(
            SanguoObjectiveSkipped.EventType,
            source: "domain",
            dataJson: "{\"ObjectiveId\":\"obj-1\",\"Reason\":\"timeout\",\"BossId\":\"boss_yellow_turban\",\"RoundNumber\":4}",
            id: "evt-2",
            timestampIso: "2026-04-27T00:00:01Z");

        handlers.BossPromptedCalls.Should().Be(1);
        handlers.ObjectiveSkippedCalls.Should().Be(1);
        handlers.UiOnlyCalls.Should().Be(0);

        handlers.LastBossPrompted.Should().NotBeNull();
        handlers.LastBossPrompted!.Value.BossId.Should().Be("boss_yellow_turban");
        handlers.LastBossPrompted!.Value.RoundNumber.Should().Be(3);
        handlers.LastBossPrompted!.Value.NextRoundPressureForecast.Should().Be(5);

        handlers.LastObjectiveSkipped.Should().NotBeNull();
        handlers.LastObjectiveSkipped!.Value.ObjectiveId.Should().Be("obj-1");
        handlers.LastObjectiveSkipped!.Value.Reason.Should().Be("timeout");
        handlers.LastObjectiveSkipped!.Value.BossId.Should().Be("boss_yellow_turban");
        handlers.LastObjectiveSkipped!.Value.RoundNumber.Should().Be(4);
    }

    // ACC:T146.1
    [Fact]
    [Trait("acceptance", "ACC:T146.1")]
    public void ShouldFallbackToUiOnly_WhenCampaignPayloadIsInvalid()
    {
        var handlers = new FakeHudEventHandlers();
        var controller = BuildController(handlers);
        HudEventHandlerRegistry.RegisterAll(controller, handlers);

        controller.HandleDomainEvent(
            SanguoBossChallengePrompted.EventType,
            source: "domain",
            dataJson: "{\"RoundNumber\":3,\"NextRoundPressureForecast\":5}",
            id: "evt-3",
            timestampIso: "2026-04-27T00:00:02Z");

        controller.HandleDomainEvent(
            SanguoObjectiveSkipped.EventType,
            source: "domain",
            dataJson: "{\"ObjectiveId\":\"obj-2\",\"BossId\":\"boss_yellow_turban\",\"RoundNumber\":5}",
            id: "evt-4",
            timestampIso: "2026-04-27T00:00:03Z");

        handlers.BossPromptedCalls.Should().Be(0);
        handlers.ObjectiveSkippedCalls.Should().Be(0);
        handlers.UiOnlyCalls.Should().Be(2);
    }

    private static HudEventHandlersController BuildController(FakeHudEventHandlers handlers)
    {
        var records = new List<string>();
        return new HudEventHandlersController(
            recordEvent: (type, source, id, ts, root) =>
            {
                _ = root.ValueKind;
                records.Add($"{type}:{source}:{id}:{ts}");
            },
            warn: _ => { },
            jsonOptions: JsonOptions);
    }

    private sealed class FakeHudEventHandlers : IHudEventHandlers
    {
        public int UiOnlyCalls { get; private set; }
        public int BossPromptedCalls { get; private set; }
        public int ObjectiveSkippedCalls { get; private set; }
        public HudBossChallengePromptedDto? LastBossPrompted { get; private set; }
        public HudObjectiveSkippedDto? LastObjectiveSkipped { get; private set; }

        public void HandleGameStarted(HudGameStartedDto dto) { }
        public void HandleScore(HudScoreDto dto) { }
        public void HandleHealth(HudHealthDto dto) { }
        public void HandleTurn(HudTurnDto dto) { }
        public void HandlePlayerStateChanged(HudPlayerStateDto dto) { }
        public void HandleDiceRolled(HudDiceRolledDto dto) { }
        public void HandleCityTollPaid(HudCityTollPaidDto dto) { }
        public void HandleCityBought(HudCityBoughtDto dto) { }
        public void HandleTokenMoved(HudTokenMovedDto dto) { }
        public void HandleGameEnded() { }

        public void HandleBossChallengePrompted(HudBossChallengePromptedDto dto)
        {
            BossPromptedCalls++;
            LastBossPrompted = dto;
        }

        public void HandleObjectiveSkipped(HudObjectiveSkippedDto dto)
        {
            ObjectiveSkippedCalls++;
            LastObjectiveSkipped = dto;
        }

        public void HandleUiOnly()
        {
            UiOnlyCalls++;
        }
    }
}
