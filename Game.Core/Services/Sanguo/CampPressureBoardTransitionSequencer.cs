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
        => ReplayEventTypes(eventTypes, hardCapReachedAtLeaveCampEdge: false);

    public static CampPressureBoardTransitionReplayResult ReplayEventTypes(
        IEnumerable<string> eventTypes,
        bool hardCapReachedAtLeaveCampEdge)
    {
        ArgumentNullException.ThrowIfNull(eventTypes);

        var pathIds = new List<string>();
        var checkpoints = new List<string>();
        var reasonCodes = new List<string>();
        var frozenPhaseOrder = new[] { "camp", "pressure", "board" };

        var campEntered = false;
        var pressureEntered = false;
        var bossChallengePrompted = false;
        var bossPreempted = false;
        var bossBranchCompleted = false;
        var objectivePublished = false;
        var gameEnded = false;

        foreach (var eventType in eventTypes)
        {
            if (string.Equals(eventType, SanguoGameTurnAdvanced.EventType, StringComparison.Ordinal))
            {
                if (!campEntered)
                {
                    campEntered = true;
                    AddCheckpoint(pathIds, checkpoints, reasonCodes, "camp_entered", "nominal");
                    AddCheckpoint(pathIds, checkpoints, reasonCodes, "objective_settled", "nominal");
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

                bossChallengePrompted = true;
                if (hardCapReachedAtLeaveCampEdge)
                {
                    bossPreempted = true;
                    AddCheckpoint(pathIds, checkpoints, reasonCodes, "pressure_preempted_by_boss", "boss_preempted");
                }
                continue;
            }

            if (string.Equals(eventType, SanguoTokenMoved.EventType, StringComparison.Ordinal))
            {
                if (!pressureEntered)
                {
                    pressureEntered = true;
                    AddCheckpoint(pathIds, checkpoints, reasonCodes, "pressure_entered", "nominal");
                }

                if (bossChallengePrompted && bossBranchCompleted && !objectivePublished && !gameEnded)
                {
                    AddCheckpoint(
                        pathIds,
                        checkpoints,
                        reasonCodes,
                        "objective_published",
                        bossPreempted ? "boss_preempted" : "nominal");
                    objectivePublished = true;
                }

                AddCheckpoint(
                    pathIds,
                    checkpoints,
                    reasonCodes,
                    "board_entered",
                    bossPreempted ? "boss_preempted" : "nominal");
                continue;
            }

            if (string.Equals(eventType, SanguoGameEnded.EventType, StringComparison.Ordinal))
            {
                gameEnded = true;
                pathIds.Add(SequencerPathId);
                continue;
            }

            if (string.Equals(eventType, SanguoGameTurnEnded.EventType, StringComparison.Ordinal))
            {
                // Task 136 hard-cap preemption closes the leave-camp boundary at turn end.
                // If board traversal was marked earlier in the same preempted sequence,
                // remove that checkpoint so normal board entry does not continue.
                if (hardCapReachedAtLeaveCampEdge && bossPreempted)
                {
                    RemoveLastCheckpoint(checkpoints, reasonCodes, pathIds, "board_entered", "boss_preempted");
                }

                continue;
            }

            if (string.Equals(eventType, SanguoCombatStarted.EventType, StringComparison.Ordinal) ||
                string.Equals(eventType, SanguoCombatEnded.EventType, StringComparison.Ordinal))
            {
                if (string.Equals(eventType, SanguoCombatEnded.EventType, StringComparison.Ordinal) &&
                    bossChallengePrompted)
                {
                    bossBranchCompleted = true;
                }

                if (string.Equals(eventType, SanguoCombatStarted.EventType, StringComparison.Ordinal) &&
                    bossChallengePrompted &&
                    !bossPreempted)
                {
                    bossPreempted = true;
                    AddCheckpoint(pathIds, checkpoints, reasonCodes, "pressure_preempted_by_boss", "boss_preempted");
                }

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

    private static void RemoveLastCheckpoint(
        List<string> checkpoints,
        List<string> reasonCodes,
        List<string> pathIds,
        string checkpoint,
        string reasonCode)
    {
        for (var index = checkpoints.Count - 1; index >= 0; index--)
        {
            if (!string.Equals(checkpoints[index], checkpoint, StringComparison.Ordinal))
            {
                continue;
            }

            if (index >= reasonCodes.Count || !string.Equals(reasonCodes[index], reasonCode, StringComparison.Ordinal))
            {
                continue;
            }

            checkpoints.RemoveAt(index);
            reasonCodes.RemoveAt(index);
            if (index < pathIds.Count)
            {
                pathIds.RemoveAt(index);
            }

            return;
        }
    }
}

public sealed record CampPressureBoardTransitionReplayResult(
    IReadOnlyList<string> SequencerPathIds,
    IReadOnlyList<string> Checkpoints,
    IReadOnlyList<string> CheckpointReasonCodes,
    IReadOnlyList<string> FrozenPhaseOrder,
    string BoardEntryBranch);
