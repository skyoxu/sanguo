using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task170SplitTests
{
    private static readonly string[] CanonicalFieldOrder =
    {
        "GameId",
        "CorrelationId",
        "CausationId",
        "OccurredAt",
        "TurnNumber",
        "RoundNumber",
        "ActivePlayerId",
    };

    // ACC:T170.1
    [Fact]
    [Trait("acceptance", "ACC:T170.1")]
    public void ShouldHarmonizeSharedRuntimeFields_WhenProducingDeterministicCampaignEvidence()
    {
        var occurredAt = DateTimeOffset.Parse("2026-01-02T03:04:05+00:00", CultureInfo.InvariantCulture);
        var gameStarted = new SanguoGameStarted(
            GameId: "game-170",
            MapId: "map-main",
            PlayersCount: 2,
            StartingMoneyPreset: 10000,
            GlobalEventIntervalTurns: 3,
            RandomSeed: 170,
            RunMode: "campaign",
            CommanderId: "commander-1",
            Difficulty: "normal",
            PlayerOrder: new[] { "p1", "p2" },
            CharacterAssignments: new Dictionary<string, string>(StringComparer.Ordinal)
            {
                ["p1"] = "char-a",
                ["p2"] = "char-b",
            },
            ActiveStrategemId: "strat-a",
            PassiveStrategemId: "strat-b",
            OccurredAt: occurredAt,
            CorrelationId: "corr-170",
            CausationId: null);

        var turnStarted = new SanguoGameTurnStarted(
            GameId: "game-170",
            TurnNumber: 1,
            ActivePlayerId: "p1",
            Year: 208,
            Month: 1,
            Day: 1,
            OccurredAt: occurredAt.AddMinutes(1),
            CorrelationId: "corr-170",
            CausationId: SanguoGameStarted.EventType);

        var objectiveSkipped = new SanguoObjectiveSkipped(
            GameId: "game-170",
            ObjectiveId: "obj-1",
            RoundNumber: 1,
            Reason: SanguoObjectiveSkipped.ReasonRunEndedInBoss,
            BossId: "boss-1",
            OccurredAt: occurredAt.AddMinutes(2),
            CorrelationId: "corr-170",
            CausationId: SanguoGameTurnStarted.EventType);

        var runtimeContracts = new object[]
        {
            gameStarted,
            turnStarted,
            objectiveSkipped,
        };

        Action act = () => BuildDeterministicRuntimeEvidence(runtimeContracts);

        act.Should().NotThrow(
            "runtime start, round, and objective contracts should expose one harmonized canonical field set for deterministic R9/A-020 evidence.");
    }

    [Fact]
    public void ShouldRefuseMergedRuntimeEnvelope_WhenCanonicalScopeValuesDiverge()
    {
        var occurredAt = DateTimeOffset.Parse("2026-01-02T03:04:05+00:00", CultureInfo.InvariantCulture);
        var canonicalEnvelopes = new[]
        {
            new Dictionary<string, object?>(StringComparer.Ordinal)
            {
                ["GameId"] = "game-170",
                ["CorrelationId"] = "corr-170-a",
                ["CausationId"] = null,
                ["OccurredAt"] = occurredAt,
                ["TurnNumber"] = 1,
                ["RoundNumber"] = 1,
                ["ActivePlayerId"] = "p1",
            },
            new Dictionary<string, object?>(StringComparer.Ordinal)
            {
                ["GameId"] = "game-170",
                ["CorrelationId"] = "corr-170-b",
                ["CausationId"] = SanguoGameTurnStarted.EventType,
                ["OccurredAt"] = occurredAt.AddSeconds(30),
                ["TurnNumber"] = 1,
                ["RoundNumber"] = 1,
                ["ActivePlayerId"] = "p1",
            },
        };

        Action act = () => EnsureScopeValuesAreStable(canonicalEnvelopes, "GameId", "CorrelationId");

        act.Should().Throw<InvalidOperationException>()
            .WithMessage("*CorrelationId*");
    }

    private static string BuildDeterministicRuntimeEvidence(IEnumerable<object> runtimeContracts)
    {
        var canonicalEnvelopes = runtimeContracts
            .Select(ProjectCanonicalEnvelope)
            .ToArray();

        EnsureScopeValuesAreStable(canonicalEnvelopes, "GameId", "CorrelationId");

        var rows = canonicalEnvelopes
            .Select((envelope, index) =>
                $"{index:D2}|{string.Join("|", CanonicalFieldOrder.Select(field => $"{field}={FormatEnvelopeValue(envelope[field])}"))}")
            .ToArray();

        return string.Join("||", rows);
    }

    private static IReadOnlyDictionary<string, object?> ProjectCanonicalEnvelope(object runtimeContract)
    {
        var contractType = runtimeContract.GetType();
        var canonicalEnvelope = new Dictionary<string, object?>(StringComparer.Ordinal);

        foreach (var canonicalField in CanonicalFieldOrder)
        {
            var property = contractType.GetProperty(canonicalField);
            if (property is null)
            {
                throw new InvalidOperationException(
                    $"Contract '{contractType.Name}' is missing canonical runtime field '{canonicalField}'.");
            }

            canonicalEnvelope[canonicalField] = property.GetValue(runtimeContract);
        }

        return canonicalEnvelope;
    }

    private static void EnsureScopeValuesAreStable(
        IEnumerable<IReadOnlyDictionary<string, object?>> canonicalEnvelopes,
        params string[] scopeFields)
    {
        var envelopeArray = canonicalEnvelopes.ToArray();

        foreach (var scopeField in scopeFields)
        {
            var distinctValues = envelopeArray
                .Select(envelope => FormatEnvelopeValue(envelope[scopeField]))
                .Distinct(StringComparer.Ordinal)
                .ToArray();

            if (distinctValues.Length > 1)
            {
                throw new InvalidOperationException(
                    $"Canonical scope value '{scopeField}' diverged across runtime flow payloads.");
            }
        }
    }

    private static string FormatEnvelopeValue(object? value)
    {
        return value switch
        {
            null => "<null>",
            DateTimeOffset dateTimeOffset => dateTimeOffset.ToString("O", CultureInfo.InvariantCulture),
            _ => Convert.ToString(value, CultureInfo.InvariantCulture) ?? string.Empty,
        };
    }
}
