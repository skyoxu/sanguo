using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services.Sanguo;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task212CombatPressureTargetingCameraInteractTests
{
    // ACC:T212.2
    [Fact]
    public void ShouldExposePathingFallbackState_WhenTargetPathMissing()
    {
        var state = CombatPressureTargetingState.CreateDefault();
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        var feedback = surface.PreviewPath(state, "target-1", pathAvailable: false);

        feedback.PathAvailable.Should().BeFalse();
        feedback.TargetId.Should().Be("target-1");
        feedback.FeedbackState.Should().Be("missing-path");
        feedback.State.Should().Be(state);
    }

    // ACC:T212.2
    [Fact]
    public void ShouldExposeInvalidTargetPathingFeedback_WhenTargetUnknown()
    {
        var state = CombatPressureTargetingState.CreateDefault();
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        var feedback = surface.PreviewPath(state, "missing-target", pathAvailable: true);

        feedback.PathAvailable.Should().BeFalse();
        feedback.TargetId.Should().Be("missing-target");
        feedback.FeedbackState.Should().Be("invalid-target");
        feedback.State.Should().Be(state);
    }

    // ACC:T212.3
    [Fact]
    public void ShouldExposeNoActiveCombatState_WhenCombatDataNotReady()
    {
        var state = CombatPressureTargetingState.CreateDefault();
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        var readiness = surface.GetReadiness(state, hasCombatData: false, hasCameraOwnership: true);

        readiness.Ready.Should().BeFalse();
        readiness.Reason.Should().Be("no-active-combat");
        readiness.State.Should().Be(state);
    }

    // ACC:T212.3
    [Fact]
    public void ShouldExposeCameraOwnershipNotReadyState_WhenCameraOwnershipMissing()
    {
        var state = CombatPressureTargetingState.CreateDefault();
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        var readiness = surface.GetReadiness(state, hasCombatData: true, hasCameraOwnership: false);

        readiness.Ready.Should().BeFalse();
        readiness.Reason.Should().Be("camera-ownership-not-ready");
        readiness.State.Should().Be(state);
    }

    // ACC:T212.5
    [Fact]
    public void ShouldRefuseInvalidTargetWithoutChangingCombatState_WhenSelectingTargetThroughGovernedSurface()
    {
        var state = CombatPressureTargetingState.CreateDefault();
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        var result = surface.SelectTarget(state, "missing-target");

        result.Accepted.Should().BeFalse();
        result.State.Should().Be(state);
        result.DecisionSource.Should().Be("Game.Core");
        result.RequiresGodotNode.Should().BeFalse();
    }

    // ACC:T212.6
    [Fact]
    public void ShouldExposeOnlyGovernedInteractionSurface_WhenCombatPressureTargetingIsAvailable()
    {
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        surface.CanInspectTarget.Should().BeTrue();
        surface.CanConfirmTarget.Should().BeTrue();
        surface.CanMutateCombatStateDirectly.Should().BeFalse();
    }

    // ACC:T212.8
    [Fact]
    public void ShouldPresentHoveredTargetStateWithoutMutatingCombatState_WhenCameraHoverChanges()
    {
        var state = CombatPressureTargetingState.CreateDefault();
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        var hover = surface.HoverTarget(state, "target-1");

        hover.Found.Should().BeTrue();
        hover.TargetId.Should().Be("target-1");
        hover.State.Should().Be(state);
    }

    // ACC:T212.2
    [Fact]
    public void ShouldExposePathReadyState_WhenTargetPathExists()
    {
        var state = CombatPressureTargetingState.CreateDefault();
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        var feedback = surface.PreviewPath(state, "target-1", pathAvailable: true);

        feedback.PathAvailable.Should().BeTrue();
        feedback.TargetId.Should().Be("target-1");
        feedback.FeedbackState.Should().Be("path-ready");
        feedback.State.Should().Be(state);
    }

    // ACC:T212.2
    [Fact]
    public void ShouldClearSelectedTargetFeedbackWithoutMutatingOtherSystems_WhenCameraResetOccurs()
    {
        var state = CombatPressureTargetingState.CreateDefault() with
        {
            SelectedTargetId = "target-1",
            CombatVersion = 9,
        };
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        var result = surface.ClearTargetingFeedback(state);

        result.Accepted.Should().BeTrue();
        result.State.SelectedTargetId.Should().BeNull();
        result.State.CombatVersion.Should().Be(state.CombatVersion);
        result.State.EconomyVersion.Should().Be(state.EconomyVersion);
        result.State.ProgressionVersion.Should().Be(state.ProgressionVersion);
        result.State.MetaVersion.Should().Be(state.MetaVersion);
    }

    // ACC:T212.10
    [Fact]
    public void ShouldRouteCombatPressureConfirmationThroughCoreDecision_WhenTargetIsValid()
    {
        var state = CombatPressureTargetingState.CreateDefault();
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        var result = surface.ConfirmTarget(state, "target-1");

        result.Accepted.Should().BeTrue();
        result.State.SelectedTargetId.Should().Be("target-1");
        result.State.CombatVersion.Should().Be(state.CombatVersion + 1);
        result.State.EconomyVersion.Should().Be(state.EconomyVersion);
        result.State.ProgressionVersion.Should().Be(state.ProgressionVersion);
        result.State.MetaVersion.Should().Be(state.MetaVersion);
    }

    // ACC:T212.11
    [Fact]
    public void ShouldLeaveEconomyProgressionAndMetaStateUnchanged_WhenTargetSelectionIsInvalid()
    {
        var state = CombatPressureTargetingState.CreateDefault();
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        var result = surface.ConfirmTarget(state, "missing-target");

        result.Accepted.Should().BeFalse();
        result.State.Should().Be(state);
    }

    // ACC:T212.7
    [Fact]
    public void ShouldApplyEconomyMultiplierThroughGovernedSurface_WhenCombatInteractionIsValid()
    {
        var state = CombatPressureTargetingState.CreateDefault();
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        var result = surface.ApplyInteractionEffect(state, "target-1", CombatPressureInteractionEffect.Building);

        result.Accepted.Should().BeTrue();
        result.DecisionSource.Should().Be("Game.Core");
        result.RequiresGodotNode.Should().BeFalse();
        result.EventType.Should().Be("combat_pressure.building.applied");
        result.AppliedMultipliers.Should().NotBeNull();
        result.AppliedMultipliers!.Sources.Should().Be(AppliedMultiplierSources.Building);
        result.AppliedMultipliers.BuildingStepDelta.Should().Be(1);
        result.AppliedMultipliers.EffectiveMultiplier.Should().Be(1.5m);
        result.State.BuildingVersion.Should().Be(state.BuildingVersion + 1);
        result.State.EconomyVersion.Should().Be(state.EconomyVersion);
        result.State.ProgressionVersion.Should().Be(state.ProgressionVersion);
        result.State.MetaVersion.Should().Be(state.MetaVersion);
    }

    // ACC:T212.12
    [Fact]
    public void ShouldReportInspectableTargetState_WhenCameraSelectsKnownCombatTarget()
    {
        var state = CombatPressureTargetingState.CreateDefault();
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        var inspection = surface.InspectTarget(state, "target-1");

        inspection.Found.Should().BeTrue();
        inspection.TargetId.Should().Be("target-1");
        inspection.State.Should().Be(state);
    }

    // ACC:T212.13
    [Fact]
    public void ShouldRefuseInspectionWithoutStateMutation_WhenCameraSelectsUnknownCombatTarget()
    {
        var state = CombatPressureTargetingState.CreateDefault();
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        var inspection = surface.InspectTarget(state, "missing-target");

        inspection.Found.Should().BeFalse();
        inspection.TargetId.Should().Be("missing-target");
        inspection.State.Should().Be(state);
    }

    // ACC:T212.9
    [Fact]
    public void ShouldSerializeTargetingContractOutputWithoutGodotTypes_WhenCrossSystemEffectsAreObserved()
    {
        var state = CombatPressureTargetingState.CreateDefault();
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        var result = surface.ApplyInteractionEffect(state, "target-1", CombatPressureInteractionEffect.Building);
        var json = JsonSerializer.Serialize(result);
        var publicTypes = typeof(CombatPressureTargetingSurface).Assembly.GetTypes()
            .Where(type => type.Namespace == "Game.Core.Services.Sanguo" && type.Name.Contains("CombatPressureTarget"))
            .ToArray();

        json.Should().Contain("combat_pressure.building.applied");
        json.Should().Contain(nameof(CombatPressureTargetingResult.AppliedMultipliers));
        publicTypes.SelectMany(type => type.GetProperties())
            .Select(property => property.PropertyType.FullName ?? property.PropertyType.Name)
            .Should()
            .NotContain(typeName => typeName.StartsWith("Godot.", StringComparison.Ordinal));
    }

    // ACC:T212.14
    [Fact]
    public void ShouldNotApplyCardBuildingEventOrGameEndEffects_WhenInteractionInvalid()
    {
        var state = CombatPressureTargetingState.CreateDefault();
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        foreach (var effect in Enum.GetValues<CombatPressureInteractionEffect>())
        {
            var result = surface.ApplyInteractionEffect(state, "missing-target", effect);

            result.Accepted.Should().BeFalse();
            result.State.Should().Be(state);
            result.AppliedMultipliers.Should().BeNull();
            result.EventType.Should().BeNull();
        }
    }

    // ACC:T212.14
    [Fact]
    public void ShouldRouteCardBuildingEventProgressionAndGameEndEffectsThroughGovernedContracts_WhenInteractionValid()
    {
        var state = CombatPressureTargetingState.CreateDefault();
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        foreach (var effect in Enum.GetValues<CombatPressureInteractionEffect>())
        {
            var result = surface.ApplyInteractionEffect(state, "target-1", effect);

            result.Accepted.Should().BeTrue();
            result.DecisionSource.Should().Be("Game.Core");
            result.RequiresGodotNode.Should().BeFalse();
            result.EventType.Should().Be(ExpectedEventType(effect));
            result.State.EconomyVersion.Should().Be(state.EconomyVersion);

            switch (effect)
            {
                case CombatPressureInteractionEffect.Card:
                    result.State.ProgressionVersion.Should().Be(state.ProgressionVersion);
                    result.State.CardVersion.Should().Be(state.CardVersion + 1);
                    result.State.BuildingVersion.Should().Be(state.BuildingVersion);
                    result.State.EventVersion.Should().Be(state.EventVersion);
                    result.State.GameEndVersion.Should().Be(state.GameEndVersion);
                    result.State.MetaVersion.Should().Be(state.MetaVersion);
                    result.AppliedMultipliers.Should().NotBeNull();
                    result.AppliedMultipliers!.Sources.Should().Be(AppliedMultiplierSources.ActionCard);
                    result.AppliedMultipliers.ActionCardStepDelta.Should().Be(1);
                    break;
                case CombatPressureInteractionEffect.Building:
                    result.State.ProgressionVersion.Should().Be(state.ProgressionVersion);
                    result.State.CardVersion.Should().Be(state.CardVersion);
                    result.State.BuildingVersion.Should().Be(state.BuildingVersion + 1);
                    result.State.EventVersion.Should().Be(state.EventVersion);
                    result.State.GameEndVersion.Should().Be(state.GameEndVersion);
                    result.State.MetaVersion.Should().Be(state.MetaVersion);
                    result.AppliedMultipliers.Should().NotBeNull();
                    result.AppliedMultipliers!.Sources.Should().Be(AppliedMultiplierSources.Building);
                    result.AppliedMultipliers.BuildingStepDelta.Should().Be(1);
                    break;
                case CombatPressureInteractionEffect.Event:
                    result.State.ProgressionVersion.Should().Be(state.ProgressionVersion);
                    result.State.CardVersion.Should().Be(state.CardVersion);
                    result.State.BuildingVersion.Should().Be(state.BuildingVersion);
                    result.State.EventVersion.Should().Be(state.EventVersion + 1);
                    result.State.GameEndVersion.Should().Be(state.GameEndVersion);
                    result.State.MetaVersion.Should().Be(state.MetaVersion);
                    result.AppliedMultipliers.Should().NotBeNull();
                    result.AppliedMultipliers!.Sources.Should().Be(AppliedMultiplierSources.Event);
                    result.AppliedMultipliers.EventStepDelta.Should().Be(1);
                    break;
                case CombatPressureInteractionEffect.Progression:
                    result.State.ProgressionVersion.Should().Be(state.ProgressionVersion + 1);
                    result.State.CardVersion.Should().Be(state.CardVersion);
                    result.State.BuildingVersion.Should().Be(state.BuildingVersion);
                    result.State.EventVersion.Should().Be(state.EventVersion);
                    result.State.GameEndVersion.Should().Be(state.GameEndVersion);
                    result.State.MetaVersion.Should().Be(state.MetaVersion);
                    result.AppliedMultipliers.Should().BeNull();
                    break;
                case CombatPressureInteractionEffect.GameEnd:
                    result.State.ProgressionVersion.Should().Be(state.ProgressionVersion);
                    result.State.CardVersion.Should().Be(state.CardVersion);
                    result.State.BuildingVersion.Should().Be(state.BuildingVersion);
                    result.State.EventVersion.Should().Be(state.EventVersion);
                    result.State.GameEndVersion.Should().Be(state.GameEndVersion + 1);
                    result.State.MetaVersion.Should().Be(state.MetaVersion + 1);
                    result.AppliedMultipliers.Should().BeNull();
                    break;
                default:
                    throw new InvalidOperationException($"Unhandled effect: {effect}");
            }
        }
    }

    // ACC:T212.15
    [Fact]
    public void ShouldKeepRuleDecisionInPureCoreLogic_WhenCameraAdapterRequestsTargetingDecision()
    {
        var state = CombatPressureTargetingState.CreateDefault();
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        var result = surface.SelectTarget(state, "target-1");

        result.DecisionSource.Should().Be("Game.Core");
        result.RequiresGodotNode.Should().BeFalse();
    }

    // ACC:T212.3
    [Fact]
    public void ShouldPreserveSelectedPlayersAndCharacterAssignments_WhenTargetingBeginsFromNewGameSetup()
    {
        var state = CombatPressureTargetingState.CreateDefault();
        var setup = new CombatPressureNewGameSetup(
            ["player-1", "player-2", "player-3"],
            new Dictionary<string, string>
            {
                ["player-1"] = "liu-bei",
                ["player-2"] = "cao-cao",
                ["player-3"] = "sun-quan",
            },
            RandomSeed: 42,
            StartingMoneyPreset: 20000);
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        var session = surface.BeginTargetingFromSetup(state, setup);
        var result = surface.ConfirmTarget(session.State, "target-1");

        session.SelectedPlayers.Should().Equal("player-1", "player-2", "player-3");
        session.CharacterAssignments.Should().ContainKey("player-1").WhoseValue.Should().Be("liu-bei");
        session.CharacterAssignments.Should().ContainKey("player-2").WhoseValue.Should().Be("cao-cao");
        session.CharacterAssignments.Should().ContainKey("player-3").WhoseValue.Should().Be("sun-quan");
        session.RandomSeed.Should().Be(42);
        session.StartingMoneyPreset.Should().Be(20000);
        result.Accepted.Should().BeTrue();
        result.State.SelectedTargetId.Should().Be("target-1");
    }

    // ACC:T212.16
    [Fact]
    public void ShouldPreservePreviouslyPassingDeterministicStateAssertions_WhenCoverageAuditRunsAfterRefactor()
    {
        var state = CombatPressureTargetingState.CreateDefault();
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        var result = surface.HoverTarget(state, "target-1");

        result.State.CombatVersion.Should().Be(state.CombatVersion);
        result.State.SelectedTargetId.Should().BeNull();
    }

    // ACC:T212.17
    [Fact]
    public void ShouldExposeExecutableTaskEvidenceThroughDeterministicCoreAssertions_WhenTripletBaselineValidatorsRunAfterTaskViewUpdate()
    {
        var state = CombatPressureTargetingState.CreateDefault();
        var surface = CombatPressureTargetingSurface.Create(["target-1"]);

        var result = surface.ApplyInteractionEffect(state, "target-1", CombatPressureInteractionEffect.Progression);

        result.Accepted.Should().BeTrue();
        result.EventType.Should().Be("combat_pressure.progression.applied");
        result.State.ProgressionVersion.Should().Be(state.ProgressionVersion + 1);
        result.State.EconomyVersion.Should().Be(state.EconomyVersion);
        result.State.MetaVersion.Should().Be(state.MetaVersion);
    }

    private static string ExpectedEventType(CombatPressureInteractionEffect effect)
    {
        return effect switch
        {
            CombatPressureInteractionEffect.Card => "combat_pressure.card.applied",
            CombatPressureInteractionEffect.Building => "combat_pressure.building.applied",
            CombatPressureInteractionEffect.Event => "combat_pressure.event.applied",
            CombatPressureInteractionEffect.Progression => "combat_pressure.progression.applied",
            CombatPressureInteractionEffect.GameEnd => "combat_pressure.game_end.applied",
            _ => throw new InvalidOperationException($"Unhandled effect: {effect}"),
        };
    }
}
