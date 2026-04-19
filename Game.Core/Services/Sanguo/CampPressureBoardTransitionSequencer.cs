using System;
using System.Collections.Generic;

using Game.Core.Contracts.Sanguo;

namespace Game.Core.Services.Sanguo;

/// <summary>
/// Deterministic replay helper for the camp -> pressure -> board transition path.
/// </summary>
public static class CampPressureBoardTransitionSequencer
{
    private const string SequencerPathId = "camp_pressure_board_sequencer";
    private const string StandardBoardEntryBranch = "standard_board_entry";
    private const string BossPreemptedBoardEntryBranch = "boss_preempted_board_entry";

    public static CampPressureBoardTransitionReplayResult ReplayEventTypes(IEnumerable<string> eventTypes)
    {
        ArgumentNullException.ThrowIfNull(eventTypes);

        var pathIds = new List<string>();
        var checkpoints = new List<string>();
        var reasonCodes = new List<string>();
        var frozenPhaseOrder = new[] { "camp", "pressure", "board" };

        var campEntered = false;
        var pressureEntered = false;
        var bossPreempted = false;

        foreach (var eventType in eventTypes)
        {
            if (string.Equals(eventType, SanguoGameTurnAdvanced.EventType, StringComparison.Ordinal))
            {
                if (!campEntered)
                {
                    campEntered = true;
                    AddCheckpoint(pathIds, checkpoints, reasonCodes, "camp_entered", "nominal");
                }

                continue;
            }

            if (string.Equals(eventType, SanguoBossChallengePrompted.EventType, StringComparison.Ordinal))
            {
                if (!pressureEntered)
                {
                    pressureEntered = true;
                    AddCheckpoint(pathIds, checkpoints, reasonCodes, "pressure_entered", "nominal");
                }

                bossPreempted = true;
                AddCheckpoint(pathIds, checkpoints, reasonCodes, "pressure_preempted_by_boss", "boss_preempted");
                continue;
            }

            if (string.Equals(eventType, SanguoTokenMoved.EventType, StringComparison.Ordinal))
            {
                if (!pressureEntered)
                {
                    pressureEntered = true;
                    AddCheckpoint(pathIds, checkpoints, reasonCodes, "pressure_entered", "nominal");
                }

                AddCheckpoint(
                    pathIds,
                    checkpoints,
                    reasonCodes,
                    "board_entered",
                    bossPreempted ? "boss_preempted" : "nominal");
                continue;
            }

            if (string.Equals(eventType, SanguoCombatStarted.EventType, StringComparison.Ordinal) ||
                string.Equals(eventType, SanguoCombatEnded.EventType, StringComparison.Ordinal))
            {
                pathIds.Add(SequencerPathId);
            }
        }

        if (pathIds.Count == 0)
        {
            pathIds.Add(SequencerPathId);
        }

        return new CampPressureBoardTransitionReplayResult(
            SequencerPathIds: pathIds,
            Checkpoints: checkpoints,
            CheckpointReasonCodes: reasonCodes,
            FrozenPhaseOrder: frozenPhaseOrder,
            BoardEntryBranch: bossPreempted ? BossPreemptedBoardEntryBranch : StandardBoardEntryBranch);
    }

    private static void AddCheckpoint(
        List<string> pathIds,
        List<string> checkpoints,
        List<string> reasonCodes,
        string checkpoint,
        string reasonCode)
    {
        pathIds.Add(SequencerPathId);
        checkpoints.Add(checkpoint);
        reasonCodes.Add(reasonCode);
    }
}

public sealed record CampPressureBoardTransitionReplayResult(
    IReadOnlyList<string> SequencerPathIds,
    IReadOnlyList<string> Checkpoints,
    IReadOnlyList<string> CheckpointReasonCodes,
    IReadOnlyList<string> FrozenPhaseOrder,
    string BoardEntryBranch);
