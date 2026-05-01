using System;
using System.Collections.Generic;
using System.Linq;
using FluentAssertions;
using Game.Core.Modifiers;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task112SplitIntegrationTests
{
    [Fact]
    public void ReplayLogPayload_ContainsTop3BreakdownAndDiscardedCount_WhenCardsExceedCap()
    {
        ModifierCard.Factory factory = id => new ModifierCard(
            id,
            $"Card-{id}",
            ModifierRarity.Epic,
            ModifierType.Offense,
            1,
            Array.Empty<ModifierEffect>());

        List<ModifierCard> cards = new();
        for (int i = 0; i < 10; i++)
        {
            cards.Add(factory($"C{i:00}"));
        }

        MonopolySplitResult result = MonopolyRewardSplitter.Split(cards, 7);
        Dictionary<string, object?> payload = ReplayTracePayloadBuilder.FromSplitResult(result);

        payload.Should().ContainKey("splitType").WhoseValue.Should().Be("3+3+1");
        payload.Should().ContainKey("discardedCount").WhoseValue.Should().Be(3);

        payload.Should().ContainKey("bucketSizes");
        ((IReadOnlyList<int>)payload["bucketSizes"]!).Should().Equal(3, 3, 1);

        payload.Should().ContainKey("top3ByRarityThenPower");
        IReadOnlyList<Dictionary<string, object?>> top3 = (IReadOnlyList<Dictionary<string, object?>>)payload["top3ByRarityThenPower"]!;
        top3.Should().HaveCount(3);
        top3.Select(x => x["cardId"]).Should().Equal("C00", "C01", "C02");
    }
}
