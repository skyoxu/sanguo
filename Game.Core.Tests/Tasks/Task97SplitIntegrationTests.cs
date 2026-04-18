using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public class Task97SplitIntegrationTests
{
    // ACC:T97.1
    [Fact]
    public void ShouldCloseIntegration_WhenSplit125And126ProvideDirectCoverageWithoutGaps()
    {
        var split125Evidence = IntegrationEvidence.ForTask(
            taskId: 125,
            coversCampBuildingSlotIntegration: true,
            coversDurabilityModelIntegration: false,
            isDirectEvidence: true,
            hasUnresolvedLinkageGap: false);

        var split126Evidence = IntegrationEvidence.ForTask(
            taskId: 126,
            coversCampBuildingSlotIntegration: false,
            coversDurabilityModelIntegration: true,
            isDirectEvidence: true,
            hasUnresolvedLinkageGap: false);

        var outcome = CurrentTask97ClosureEvaluator.Evaluate(split125Evidence, split126Evidence);

        outcome.IsClosed.Should().BeTrue();
        outcome.Reason.Should().Be("All required integration evidence is direct and gap-free.");
    }

    // ACC:T97.2
    [Theory]
    [InlineData(false, true)]
    [InlineData(true, false)]
    [InlineData(false, false)]
    public void ShouldFailAcceptance_WhenEitherCampSlotOrDurabilityCoverageIsMissing(
        bool hasCampSlotCoverage,
        bool hasDurabilityCoverage)
    {
        var split125Evidence = IntegrationEvidence.ForTask(
            taskId: 125,
            coversCampBuildingSlotIntegration: hasCampSlotCoverage,
            coversDurabilityModelIntegration: false,
            isDirectEvidence: true,
            hasUnresolvedLinkageGap: false);

        var split126Evidence = IntegrationEvidence.ForTask(
            taskId: 126,
            coversCampBuildingSlotIntegration: false,
            coversDurabilityModelIntegration: hasDurabilityCoverage,
            isDirectEvidence: true,
            hasUnresolvedLinkageGap: false);

        var outcome = CurrentTask97ClosureEvaluator.Evaluate(split125Evidence, split126Evidence);

        outcome.IsClosed.Should().BeFalse("acceptance requires explicit coverage for both integration concerns.");
    }

    [Fact]
    public void ShouldFailAcceptance_WhenDurabilityEvidenceIsOnlyIndirectlyInferred()
    {
        var split125Evidence = IntegrationEvidence.ForTask(
            taskId: 125,
            coversCampBuildingSlotIntegration: true,
            coversDurabilityModelIntegration: false,
            isDirectEvidence: true,
            hasUnresolvedLinkageGap: false);

        var split126Evidence = IntegrationEvidence.ForTask(
            taskId: 126,
            coversCampBuildingSlotIntegration: false,
            coversDurabilityModelIntegration: true,
            isDirectEvidence: false,
            hasUnresolvedLinkageGap: false);

        var outcome = CurrentTask97ClosureEvaluator.Evaluate(split125Evidence, split126Evidence);

        outcome.IsClosed.Should().BeFalse("indirect evidence must not close task acceptance.");
    }

    [Fact]
    public void ShouldFailAcceptance_WhenUnresolvedInterfaceOrModelLinkageGapExists()
    {
        var split125Evidence = IntegrationEvidence.ForTask(
            taskId: 125,
            coversCampBuildingSlotIntegration: true,
            coversDurabilityModelIntegration: false,
            isDirectEvidence: true,
            hasUnresolvedLinkageGap: false);

        var split126Evidence = IntegrationEvidence.ForTask(
            taskId: 126,
            coversCampBuildingSlotIntegration: false,
            coversDurabilityModelIntegration: true,
            isDirectEvidence: true,
            hasUnresolvedLinkageGap: true);

        var outcome = CurrentTask97ClosureEvaluator.Evaluate(split125Evidence, split126Evidence);

        outcome.IsClosed.Should().BeFalse();
        outcome.Reason.Should().Be("Unresolved interface/model linkage gap exists.");
    }

    private sealed record IntegrationEvidence(
        int TaskId,
        bool CoversCampBuildingSlotIntegration,
        bool CoversDurabilityModelIntegration,
        bool IsDirectEvidence,
        bool HasUnresolvedLinkageGap)
    {
        public static IntegrationEvidence ForTask(
            int taskId,
            bool coversCampBuildingSlotIntegration,
            bool coversDurabilityModelIntegration,
            bool isDirectEvidence,
            bool hasUnresolvedLinkageGap)
        {
            return new IntegrationEvidence(
                TaskId: taskId,
                CoversCampBuildingSlotIntegration: coversCampBuildingSlotIntegration,
                CoversDurabilityModelIntegration: coversDurabilityModelIntegration,
                IsDirectEvidence: isDirectEvidence,
                HasUnresolvedLinkageGap: hasUnresolvedLinkageGap);
        }
    }

    private sealed record ClosureOutcome(bool IsClosed, string Reason);

    private static class CurrentTask97ClosureEvaluator
    {
        public static ClosureOutcome Evaluate(IntegrationEvidence split125Evidence, IntegrationEvidence split126Evidence)
        {
            if (split125Evidence is null || split126Evidence is null)
            {
                return new ClosureOutcome(false, "Missing split-task evidence.");
            }

            if (split125Evidence.TaskId != 125 || split126Evidence.TaskId != 126)
            {
                return new ClosureOutcome(false, "Unexpected split-task evidence source.");
            }

            if (split125Evidence.HasUnresolvedLinkageGap || split126Evidence.HasUnresolvedLinkageGap)
            {
                return new ClosureOutcome(false, "Unresolved interface/model linkage gap exists.");
            }

            var hasCampSlotCoverage =
                split125Evidence.CoversCampBuildingSlotIntegration ||
                split126Evidence.CoversCampBuildingSlotIntegration;
            var hasDurabilityCoverage =
                split125Evidence.CoversDurabilityModelIntegration ||
                split126Evidence.CoversDurabilityModelIntegration;

            if (!hasCampSlotCoverage || !hasDurabilityCoverage)
            {
                return new ClosureOutcome(false, "Missing explicit camp-slot or durability coverage.");
            }

            if (!split125Evidence.IsDirectEvidence || !split126Evidence.IsDirectEvidence)
            {
                return new ClosureOutcome(false, "Indirect evidence is not eligible for integration closure.");
            }

            return new ClosureOutcome(true, "All required integration evidence is direct and gap-free.");
        }
    }
}
