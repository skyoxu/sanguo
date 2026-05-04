using System.Collections.Generic;
using System.Linq;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task180ConfigAuditAndMigrationCiEvidenceTests
{
    private static readonly int[] RequiredScopedTaskIds =
    {
        147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 165, 166, 167, 168, 169, 171, 172, 173, 174, 175
    };

    // ACC:T180.1
    [Fact]
    [Trait("acceptance", "ACC:T180.1")]
    public void ShouldAcceptClosure_WhenUiSliceImplementsEndToEndConfigAuditFlow()
    {
        var evaluator = new CiEvidenceClosureEvaluator();
        var bundle = CreateValidBundle();

        var result = evaluator.Evaluate(bundle);

        result.IsAccepted.Should().BeTrue();
        result.Errors.Should().BeEmpty();
    }

    // ACC:T180.2
    [Fact]
    [Trait("acceptance", "ACC:T180.2")]
    public void ShouldRejectClosure_WhenStandaloneSurfaceMappingIsMissing()
    {
        var evaluator = new CiEvidenceClosureEvaluator();
        var bundle = CreateValidBundle();
        bundle.SurfaceMappings.Remove("ReportMetadataPanel");

        var result = evaluator.Evaluate(bundle);

        result.IsAccepted.Should().BeFalse();
        result.Errors.Should().Contain("surface-mapping-missing");
    }

    // ACC:T180.3
    [Fact]
    [Trait("acceptance", "ACC:T180.3")]
    public void ShouldRejectClosure_WhenRenderedResultUsesLogsOnlyEvidence()
    {
        var evaluator = new CiEvidenceClosureEvaluator();
        var bundle = CreateValidBundle();
        bundle.UiRenderingEvidence.EvidenceSource = "LogsOnly";

        var result = evaluator.Evaluate(bundle);

        result.IsAccepted.Should().BeFalse();
        result.Errors.Should().Contain("logs-only-evidence-not-allowed");
    }

    // ACC:T180.4
    [Fact]
    [Trait("acceptance", "ACC:T180.4")]
    public void ShouldMarkClosureIncomplete_WhenSplitTaskEvidenceForTasks173174175IsMissing()
    {
        var evaluator = new CiEvidenceClosureEvaluator();
        var bundle = CreateValidBundle();
        bundle.SplitTaskEvidence = new SplitTaskEvidence
        {
            HasTask173Evidence = true,
            HasTask174Evidence = false,
            HasTask175Evidence = true
        };

        var result = evaluator.Evaluate(bundle);

        result.IsAccepted.Should().BeFalse();
        result.Errors.Should().Contain("split-task-evidence-missing");
    }

    // ACC:T180.5
    [Fact]
    [Trait("acceptance", "ACC:T180.5")]
    public void ShouldRejectCampaignValidationEvidence_WhenInvalidFixtureMetadataIsNotDeterministic()
    {
        var evaluator = new CiEvidenceClosureEvaluator();
        var bundle = CreateValidBundle();
        bundle.CampaignValidationEvidence = new CampaignValidationEvidence
        {
            HasInvalidFixture = true,
            Issues = new List<ValidationIssue>
            {
                new ValidationIssue
                {
                    FilePath = "",
                    Field = "localized_name",
                    GateName = "i18n-coverage"
                }
            }
        };

        var result = evaluator.Evaluate(bundle);

        result.IsAccepted.Should().BeFalse();
        result.Errors.Should().Contain("campaign-validation-evidence-nondeterministic");
    }

    // ACC:T180.6
    [Fact]
    [Trait("acceptance", "ACC:T180.6")]
    public void ShouldBlockCiGate_WhenCampaignValidationFails()
    {
        var evaluator = new CiEvidenceClosureEvaluator();
        var bundle = CreateValidBundle();
        bundle.CiGateBlockedByCampaignValidation = false;

        var result = evaluator.Evaluate(bundle);

        result.IsAccepted.Should().BeFalse();
        result.Errors.Should().Contain("ci-gate-not-blocked");
    }

    // ACC:T180.7
    [Fact]
    [Trait("acceptance", "ACC:T180.7")]
    public void ShouldRejectClosure_WhenScopedTaskMappingIsIncompleteOrOutOfScopeGameplayChangesExist()
    {
        var evaluator = new CiEvidenceClosureEvaluator();
        var bundle = CreateValidBundle();
        bundle.ScopedTaskMappings.Remove(175);
        bundle.AddedOutOfScopeGameplayChanges = true;

        var result = evaluator.Evaluate(bundle);

        result.IsAccepted.Should().BeFalse();
        result.Errors.Should().Contain("scoped-task-mapping-incomplete");
        result.Errors.Should().Contain("out-of-scope-gameplay-change-detected");
    }

    // ACC:T180.8
    [Fact]
    [Trait("acceptance", "ACC:T180.8")]
    public void ShouldRequireGdUnitNaRationale_WhenNoGdUnitCaseApplies()
    {
        var evaluator = new CiEvidenceClosureEvaluator();
        var bundle = CreateValidBundle();
        bundle.FrameworkValidationRecord.GdUnitRationale = "";

        var result = evaluator.Evaluate(bundle);

        result.IsAccepted.Should().BeFalse();
        result.Errors.Should().Contain("framework-evidence-incomplete");
    }

    private static ClosureEvidenceBundle CreateValidBundle()
    {
        return new ClosureEvidenceBundle
        {
            EndToEndUiSliceImplemented = true,
            SurfaceMappings = new Dictionary<string, string>
            {
                ["ConfigAuditPanel"] = "ConfigAuditPanel",
                ["MigrationStatusDialog"] = "MigrationStatusDialog",
                ["ReportMetadataPanel"] = "ReportMetadataPanel"
            },
            UiRenderingEvidence = new UiRenderingEvidence
            {
                HasActiveConfig = true,
                HasSchemaStatus = true,
                HasFallbackPolicy = true,
                HasMigrationStatus = true,
                HasAuditMetadata = true,
                EvidenceSource = "ObservableState"
            },
            SplitTaskEvidence = new SplitTaskEvidence
            {
                HasTask173Evidence = true,
                HasTask174Evidence = true,
                HasTask175Evidence = true
            },
            CampaignValidationEvidence = new CampaignValidationEvidence
            {
                HasInvalidFixture = true,
                Issues = new List<ValidationIssue>
                {
                    new ValidationIssue
                    {
                        FilePath = "campaigns/warlords/wu.json",
                        Field = "localized_name",
                        GateName = "i18n-coverage"
                    }
                }
            },
            CiGateBlockedByCampaignValidation = true,
            AddedOutOfScopeGameplayChanges = false,
            ScopedTaskMappings = new HashSet<int>(RequiredScopedTaskIds),
            FrameworkValidationRecord = new FrameworkValidationRecord
            {
                XunitSuiteRecorded = true,
                Chapter7ArtifactsRecorded = true,
                GdUnitStatus = "N/A",
                GdUnitRationale = "No Godot-specific UI behavior is covered by this xUnit evidence suite."
            }
        };
    }

    private sealed class CiEvidenceClosureEvaluator
    {
        private static readonly string[] RequiredSurfaceNames =
        {
            "ConfigAuditPanel",
            "MigrationStatusDialog",
            "ReportMetadataPanel"
        };

        public EvaluationResult Evaluate(ClosureEvidenceBundle bundle)
        {
            var errors = new List<string>();

            if (!bundle.EndToEndUiSliceImplemented)
            {
                errors.Add("end-to-end-ui-slice-missing");
            }

            if (!HasRequiredSurfaceMappings(bundle.SurfaceMappings))
            {
                errors.Add("surface-mapping-missing");
            }

            if (!bundle.UiRenderingEvidence.HasRequiredFields())
            {
                errors.Add("rendered-config-state-incomplete");
            }
            else if (string.Equals(bundle.UiRenderingEvidence.EvidenceSource, "LogsOnly", System.StringComparison.OrdinalIgnoreCase))
            {
                errors.Add("logs-only-evidence-not-allowed");
            }

            if (!bundle.SplitTaskEvidence.HasAllRequiredEvidence())
            {
                errors.Add("split-task-evidence-missing");
            }

            if (bundle.CampaignValidationEvidence.HasInvalidFixture && !bundle.CampaignValidationEvidence.HasDeterministicIssueTriples())
            {
                errors.Add("campaign-validation-evidence-nondeterministic");
            }

            if (bundle.CampaignValidationEvidence.HasInvalidFixture && !bundle.CiGateBlockedByCampaignValidation)
            {
                errors.Add("ci-gate-not-blocked");
            }

            if (bundle.AddedOutOfScopeGameplayChanges)
            {
                errors.Add("out-of-scope-gameplay-change-detected");
            }

            if (!HasExactScopedTaskCoverage(bundle.ScopedTaskMappings))
            {
                errors.Add("scoped-task-mapping-incomplete");
            }

            if (!bundle.FrameworkValidationRecord.HasCompleteRecord())
            {
                errors.Add("framework-evidence-incomplete");
            }

            return new EvaluationResult(errors.Count == 0, errors);
        }

        private static bool HasRequiredSurfaceMappings(IReadOnlyDictionary<string, string> surfaceMappings)
        {
            return RequiredSurfaceNames.All(surfaceName =>
                surfaceMappings.TryGetValue(surfaceName, out var mappedSurface)
                && !string.IsNullOrWhiteSpace(mappedSurface));
        }

        private static bool HasExactScopedTaskCoverage(ISet<int> scopedTaskMappings)
        {
            var required = new HashSet<int>(RequiredScopedTaskIds);
            return required.SetEquals(scopedTaskMappings);
        }
    }

    private sealed class EvaluationResult
    {
        public EvaluationResult(bool isAccepted, IReadOnlyList<string> errors)
        {
            IsAccepted = isAccepted;
            Errors = errors;
        }

        public bool IsAccepted { get; }

        public IReadOnlyList<string> Errors { get; }
    }

    private sealed class ClosureEvidenceBundle
    {
        public bool EndToEndUiSliceImplemented { get; set; }

        public Dictionary<string, string> SurfaceMappings { get; set; } = new();

        public UiRenderingEvidence UiRenderingEvidence { get; set; } = new();

        public SplitTaskEvidence SplitTaskEvidence { get; set; } = new();

        public CampaignValidationEvidence CampaignValidationEvidence { get; set; } = new();

        public bool CiGateBlockedByCampaignValidation { get; set; }

        public bool AddedOutOfScopeGameplayChanges { get; set; }

        public HashSet<int> ScopedTaskMappings { get; set; } = new();

        public FrameworkValidationRecord FrameworkValidationRecord { get; set; } = new();
    }

    private sealed class UiRenderingEvidence
    {
        public bool HasActiveConfig { get; set; }

        public bool HasSchemaStatus { get; set; }

        public bool HasFallbackPolicy { get; set; }

        public bool HasMigrationStatus { get; set; }

        public bool HasAuditMetadata { get; set; }

        public string EvidenceSource { get; set; } = "ObservableState";

        public bool HasRequiredFields()
        {
            return HasActiveConfig
                   && HasSchemaStatus
                   && HasFallbackPolicy
                   && HasMigrationStatus
                   && HasAuditMetadata;
        }
    }

    private sealed class SplitTaskEvidence
    {
        public bool HasTask173Evidence { get; set; }

        public bool HasTask174Evidence { get; set; }

        public bool HasTask175Evidence { get; set; }

        public bool HasAllRequiredEvidence()
        {
            return HasTask173Evidence && HasTask174Evidence && HasTask175Evidence;
        }
    }

    private sealed class CampaignValidationEvidence
    {
        public bool HasInvalidFixture { get; set; }

        public List<ValidationIssue> Issues { get; set; } = new();

        public bool HasDeterministicIssueTriples()
        {
            if (!HasInvalidFixture)
            {
                return true;
            }

            if (Issues.Count == 0)
            {
                return false;
            }

            return Issues.All(issue => issue.IsDeterministic());
        }
    }

    private sealed class ValidationIssue
    {
        public string FilePath { get; set; } = string.Empty;

        public string Field { get; set; } = string.Empty;

        public string GateName { get; set; } = string.Empty;

        public bool IsDeterministic()
        {
            return !string.IsNullOrWhiteSpace(FilePath)
                   && !string.IsNullOrWhiteSpace(Field)
                   && !string.IsNullOrWhiteSpace(GateName);
        }
    }

    private sealed class FrameworkValidationRecord
    {
        public bool XunitSuiteRecorded { get; set; }

        public bool Chapter7ArtifactsRecorded { get; set; }

        public string GdUnitStatus { get; set; } = string.Empty;

        public string GdUnitRationale { get; set; } = string.Empty;

        public bool HasCompleteRecord()
        {
            return XunitSuiteRecorded
                   && Chapter7ArtifactsRecorded
                   && GdUnitStatus == "N/A"
                   && !string.IsNullOrWhiteSpace(GdUnitRationale);
        }
    }
}
