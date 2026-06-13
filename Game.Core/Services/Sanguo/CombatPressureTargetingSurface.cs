using System;
using System.Collections.Generic;
using Game.Core.Contracts.Sanguo;

namespace Game.Core.Services.Sanguo;

public sealed class CombatPressureTargetingSurface
{
    private readonly HashSet<string> validTargetIds;

    private CombatPressureTargetingSurface(IEnumerable<string> validTargetIds)
    {
        this.validTargetIds = new HashSet<string>(validTargetIds ?? throw new ArgumentNullException(nameof(validTargetIds)), StringComparer.Ordinal);
    }

    public bool CanInspectTarget => true;

    public bool CanConfirmTarget => true;

    public bool CanMutateCombatStateDirectly => false;

    public static CombatPressureTargetingSurface Create(IEnumerable<string> validTargetIds)
    {
        return new CombatPressureTargetingSurface(validTargetIds);
    }

    public CombatPressureTargetingResult SelectTarget(CombatPressureTargetingState state, string targetId)
    {
        if (!IsKnownTarget(targetId))
        {
            return CombatPressureTargetingResult.Refused(state);
        }

        return CombatPressureTargetingResult.Confirmed(state with
        {
            SelectedTargetId = targetId,
            CombatVersion = state.CombatVersion + 1,
        });
    }

    public CombatPressureTargetingResult ConfirmTarget(CombatPressureTargetingState state, string targetId)
    {
        return SelectTarget(state, targetId);
    }

    public CombatPressureTargetingResult ClearTargetingFeedback(CombatPressureTargetingState state)
    {
        return CombatPressureTargetingResult.Confirmed(state with { SelectedTargetId = null });
    }

    public CombatPressureTargetingSession BeginTargetingFromSetup(
        CombatPressureTargetingState state,
        CombatPressureNewGameSetup setup)
    {
        return new CombatPressureTargetingSession(
            state,
            setup.SelectedPlayers,
            setup.CharacterAssignments,
            setup.RandomSeed,
            setup.StartingMoneyPreset);
    }

    public CombatPressureTargetInspection HoverTarget(CombatPressureTargetingState state, string targetId)
    {
        return new CombatPressureTargetInspection(IsKnownTarget(targetId), targetId, state);
    }

    public CombatPressureTargetInspection InspectTarget(CombatPressureTargetingState state, string targetId)
    {
        return new CombatPressureTargetInspection(IsKnownTarget(targetId), targetId, state);
    }

    public CombatPressureTargetingReadiness GetReadiness(CombatPressureTargetingState state, bool hasCombatData, bool hasCameraOwnership)
    {
        if (!hasCombatData)
        {
            return new CombatPressureTargetingReadiness(false, "no-active-combat", state);
        }

        if (!hasCameraOwnership)
        {
            return new CombatPressureTargetingReadiness(false, "camera-ownership-not-ready", state);
        }

        return new CombatPressureTargetingReadiness(true, "ready", state);
    }

    public CombatPressurePathingFeedback PreviewPath(CombatPressureTargetingState state, string targetId, bool pathAvailable)
    {
        if (!IsKnownTarget(targetId))
        {
            return new CombatPressurePathingFeedback(false, targetId, "invalid-target", state);
        }

        if (!pathAvailable)
        {
            return new CombatPressurePathingFeedback(false, targetId, "missing-path", state);
        }

        return new CombatPressurePathingFeedback(true, targetId, "path-ready", state);
    }

    public CombatPressureTargetingResult ApplyInteractionEffect(
        CombatPressureTargetingState state,
        string targetId,
        CombatPressureInteractionEffect effect)
    {
        if (!IsKnownTarget(targetId))
        {
            return CombatPressureTargetingResult.Refused(state);
        }

        return effect switch
        {
            CombatPressureInteractionEffect.Card => CombatPressureTargetingResult.Confirmed(
                state with { CardVersion = state.CardVersion + 1 },
                CreateAppliedMultipliers(actionCardStepDelta: 1, sources: AppliedMultiplierSources.ActionCard),
                "combat_pressure.card.applied"),
            CombatPressureInteractionEffect.Building => CombatPressureTargetingResult.Confirmed(
                state with { BuildingVersion = state.BuildingVersion + 1 },
                CreateAppliedMultipliers(buildingStepDelta: 1, sources: AppliedMultiplierSources.Building),
                "combat_pressure.building.applied"),
            CombatPressureInteractionEffect.Event => CombatPressureTargetingResult.Confirmed(
                state with { EventVersion = state.EventVersion + 1 },
                CreateAppliedMultipliers(eventStepDelta: 1, sources: AppliedMultiplierSources.Event),
                "combat_pressure.event.applied"),
            CombatPressureInteractionEffect.Progression => CombatPressureTargetingResult.Confirmed(
                state with { ProgressionVersion = state.ProgressionVersion + 1 },
                null,
                "combat_pressure.progression.applied"),
            CombatPressureInteractionEffect.GameEnd => CombatPressureTargetingResult.Confirmed(
                state with { GameEndVersion = state.GameEndVersion + 1, MetaVersion = state.MetaVersion + 1 },
                null,
                "combat_pressure.game_end.applied"),
            _ => CombatPressureTargetingResult.Confirmed(state),
        };
    }

    private bool IsKnownTarget(string targetId)
    {
        return !string.IsNullOrWhiteSpace(targetId) && validTargetIds.Contains(targetId);
    }

    private static AppliedMultipliers CreateAppliedMultipliers(
        int buildingStepDelta = 0,
        int eventStepDelta = 0,
        int actionCardStepDelta = 0,
        AppliedMultiplierSources sources = AppliedMultiplierSources.None)
    {
        var effectiveSteps = AppliedMultipliers.ClampSteps(
            AppliedMultipliers.BaseDefaultSteps + buildingStepDelta + eventStepDelta + actionCardStepDelta);

        return new AppliedMultipliers(
            BaseSteps: AppliedMultipliers.BaseDefaultSteps,
            CharacterStepDelta: 0,
            BuildingStepDelta: buildingStepDelta,
            EventStepDelta: eventStepDelta,
            ActionCardStepDelta: actionCardStepDelta,
            RelicStepDelta: 0,
            RegionStepDelta: 0,
            EffectiveSteps: effectiveSteps,
            Sources: sources);
    }
}

public sealed record CombatPressureTargetingResult(
    bool Accepted,
    CombatPressureTargetingState State,
    string DecisionSource,
    bool RequiresGodotNode,
    AppliedMultipliers? AppliedMultipliers,
    string? EventType)
{
    public static CombatPressureTargetingResult Confirmed(CombatPressureTargetingState state)
    {
        return Confirmed(state, null, null);
    }

    public static CombatPressureTargetingResult Confirmed(
        CombatPressureTargetingState state,
        AppliedMultipliers? appliedMultipliers,
        string? eventType)
    {
        return new CombatPressureTargetingResult(true, state, "Game.Core", false, appliedMultipliers, eventType);
    }

    public static CombatPressureTargetingResult Refused(CombatPressureTargetingState state)
    {
        return new CombatPressureTargetingResult(false, state, "Game.Core", false, null, null);
    }
}

public sealed record CombatPressureTargetInspection(bool Found, string TargetId, CombatPressureTargetingState State);

public sealed record CombatPressureTargetingReadiness(bool Ready, string Reason, CombatPressureTargetingState State);

public sealed record CombatPressurePathingFeedback(bool PathAvailable, string TargetId, string FeedbackState, CombatPressureTargetingState State);

public sealed record CombatPressureTargetingSession(
    CombatPressureTargetingState State,
    IReadOnlyList<string> SelectedPlayers,
    IReadOnlyDictionary<string, string> CharacterAssignments,
    int RandomSeed,
    int StartingMoneyPreset);

public sealed record CombatPressureNewGameSetup(
    IReadOnlyList<string> SelectedPlayers,
    IReadOnlyDictionary<string, string> CharacterAssignments,
    int RandomSeed,
    int StartingMoneyPreset);

public sealed record CombatPressureTargetingState(
    string? SelectedTargetId,
    int CombatVersion,
    int EconomyVersion,
    int ProgressionVersion,
    int MetaVersion,
    int CardVersion,
    int BuildingVersion,
    int EventVersion,
    int GameEndVersion)
{
    public static CombatPressureTargetingState CreateDefault()
    {
        return new CombatPressureTargetingState(null, 1, 2, 3, 4, 5, 6, 7, 8);
    }
}

public enum CombatPressureInteractionEffect
{
    Card,
    Building,
    Event,
    Progression,
    GameEnd,
}
