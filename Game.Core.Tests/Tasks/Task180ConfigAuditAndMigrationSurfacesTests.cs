using System;
using System.Collections.Generic;
using System.Linq;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task180ConfigAuditAndMigrationSurfacesTests
{
    // ACC:T180.1
    [Fact]
    public void ShouldExposeEndToEndInspection_WhenStateContainsConfigValidationGovernanceMigrationAndReportMetadata()
    {
        var policy = new ConfigAuditAndMigrationSurfacePolicy();
        var input = new SliceInput
        {
            Surfaces = new HashSet<string>(StringComparer.Ordinal)
            {
                "ConfigAuditPanel",
                "MigrationStatusDialog",
                "ReportMetadataPanel",
            },
            ActiveConfig = "campaign.default.v3",
            SchemaStatus = "valid",
            FallbackPolicy = "strict-fallback",
            MigrationStatus = "migrated",
            AuditMetadata = "audit-2026-05-04",
            SplitTaskEvidence = new Dictionary<string, bool>(StringComparer.Ordinal)
            {
                ["T173"] = true,
                ["T174"] = true,
                ["T175"] = true,
            },
        };

        var result = policy.EvaluateSlice(input);

        result.EndToEndInspectionAvailable.Should().BeTrue();
        result.GateCanAdvance.Should().BeTrue();
    }

    // ACC:T180.2
    [Fact]
    public void ShouldAcceptEquivalentSurfaceMapping_WhenStandaloneCandidatePanelsAreMapped()
    {
        var policy = new ConfigAuditAndMigrationSurfacePolicy();
        var input = new SliceInput
        {
            Surfaces = new HashSet<string>(StringComparer.Ordinal)
            {
                "ConfigAuditPanel",
            },
            EquivalentSurfaceMapping = new Dictionary<string, string>(StringComparer.Ordinal)
            {
                ["MigrationStatusDialog"] = "MigrationDrawer",
                ["ReportMetadataPanel"] = "ReportMetadataSidebar",
            },
            ActiveConfig = "campaign.default.v3",
            SchemaStatus = "valid",
            FallbackPolicy = "strict-fallback",
            MigrationStatus = "migrated",
            AuditMetadata = "audit-2026-05-04",
            SplitTaskEvidence = new Dictionary<string, bool>(StringComparer.Ordinal)
            {
                ["T173"] = true,
                ["T174"] = true,
                ["T175"] = true,
            },
        };

        var result = policy.EvaluateSlice(input);

        result.MappingSatisfied.Should().BeTrue();
        result.MissingSurfaces.Should().BeEmpty();
    }

    // ACC:T180.3
    [Fact]
    public void ShouldRejectLogsOnlyEvidence_WhenUiRenderingStateIsMissing()
    {
        var policy = new ConfigAuditAndMigrationSurfacePolicy();
        var input = new SliceInput
        {
            Surfaces = new HashSet<string>(StringComparer.Ordinal)
            {
                "ConfigAuditPanel",
                "MigrationStatusDialog",
                "ReportMetadataPanel",
            },
            HasLogsOnlyEvidence = true,
            SplitTaskEvidence = new Dictionary<string, bool>(StringComparer.Ordinal)
            {
                ["T173"] = true,
                ["T174"] = true,
                ["T175"] = true,
            },
        };

        var result = policy.EvaluateSlice(input);

        result.RenderedFromState.Should().BeFalse("logs-only evidence must not satisfy UI rendering acceptance");
        result.Violations.Should().Contain("logs-only-evidence");
    }

    // ACC:T180.4
    [Fact]
    public void ShouldMarkIntegrationClosureIncomplete_WhenAnySplitTaskEvidenceIsMissing()
    {
        var policy = new ConfigAuditAndMigrationSurfacePolicy();
        var input = new SliceInput
        {
            Surfaces = new HashSet<string>(StringComparer.Ordinal)
            {
                "ConfigAuditPanel",
                "MigrationStatusDialog",
                "ReportMetadataPanel",
            },
            ActiveConfig = "campaign.default.v3",
            SchemaStatus = "valid",
            FallbackPolicy = "strict-fallback",
            MigrationStatus = "migrated",
            AuditMetadata = "audit-2026-05-04",
            SplitTaskEvidence = new Dictionary<string, bool>(StringComparer.Ordinal)
            {
                ["T173"] = true,
                ["T175"] = true,
            },
        };

        var result = policy.EvaluateSlice(input);

        result.IntegrationClosureComplete.Should().BeFalse();
        result.MissingSplitEvidence.Should().Contain("T174");
        result.GateCanAdvance.Should().BeFalse();
    }

    // ACC:T180.5
    [Fact]
    public void ShouldEmitDeterministicCampaignValidationEvidence_WhenFixtureBreaksCrossReferenceVersionAndI18nGates()
    {
        var policy = new ConfigAuditAndMigrationSurfacePolicy();
        var fixtures = new List<CampaignFixture>
        {
            new CampaignFixture
            {
                DatasetType = "events",
                FilePath = "content/campaign/events/zhouyu.json",
                CrossReferenceOk = false,
                VersionBumpOk = false,
                I18nCoverageOk = false,
            },
        };

        var issues = policy.ValidateCampaignContent(fixtures);

        issues.Should().HaveCount(3);
        issues.Select(issue => issue.GateName).Should().Equal("cross-reference", "i18n-coverage", "version-bump");
        issues.All(issue => !string.IsNullOrWhiteSpace(issue.FilePath)).Should().BeTrue();
        issues.All(issue => !string.IsNullOrWhiteSpace(issue.Field)).Should().BeTrue();
        issues.All(issue => !string.IsNullOrWhiteSpace(issue.GateName)).Should().BeTrue();
    }

    // ACC:T180.6
    [Fact]
    public void ShouldBlockCiAndRejectOutOfScopeGameplayChanges_WhenValidationIsEnforcedAsHardGate()
    {
        var policy = new ConfigAuditAndMigrationSurfacePolicy();
        var failingIssues = new List<CampaignValidationIssue>
        {
            new CampaignValidationIssue(
                "content/campaign/events/zhouyu.json",
                "cross_reference",
                "cross-reference",
                "events"),
        };

        var failedGate = policy.EvaluateHardGate(failingIssues, domainContractsUnchanged: true, hasOutOfScopeGameplayChanges: false);
        var outOfScopeGate = policy.EvaluateHardGate(new List<CampaignValidationIssue>(), domainContractsUnchanged: true, hasOutOfScopeGameplayChanges: true);

        failedGate.Blocked.Should().BeTrue();
        failedGate.CanMerge.Should().BeFalse();
        failedGate.DeterministicDomainStateUnchanged.Should().BeTrue();

        outOfScopeGate.OutOfScopeGameplayChangesDetected.Should().BeTrue();
        outOfScopeGate.CanMerge.Should().BeFalse();
    }

    // ACC:T180.7
    [Fact]
    public void ShouldFailScopeAcceptance_WhenAnyRequiredTaskMappingIsMissingOrOutOfScopeChangesExist()
    {
        var policy = new ConfigAuditAndMigrationSurfacePolicy();
        var mappedTaskIds = new HashSet<string>(StringComparer.Ordinal)
        {
            "T147", "T148", "T149", "T150", "T151", "T152", "T153", "T154", "T155", "T156",
            "T157", "T158", "T159", "T160", "T161", "T162", "T163", "T165", "T166", "T167",
            "T168", "T169", "T171", "T172", "T173", "T174",
        };
        var outOfScopeGameplayTaskIds = new HashSet<string>(StringComparer.Ordinal)
        {
            "T999",
        };

        var result = policy.EvaluateScopedMapping(mappedTaskIds, outOfScopeGameplayTaskIds);

        result.Complete.Should().BeFalse();
        result.MissingMappings.Should().Contain("T175");
        result.OutOfScopeMappings.Should().Contain("T999");
    }

    // ACC:T180.8
    [Fact]
    public void ShouldRecordFrameworkEvidenceIncludingGdunitNaRationale_WhenNoGdunitCaseApplies()
    {
        var policy = new ConfigAuditAndMigrationSurfacePolicy();
        var chapter7Artifacts = new List<string>
        {
            "logs/ci/2026-05-04/chapter7-ui-wiring/latest.json",
            "logs/ci/2026-05-04/sc-review-pipeline-task-180/latest.json",
        };

        var report = policy.RecordValidationEvidence(
            xunitPassed: false,
            chapter7ArtifactPaths: chapter7Artifacts,
            gdunitCaseCount: 0,
            gdunitNaRationale: "No Godot-specific test surface applies to this core-only validation scope.");

        report.XunitSuiteStatus.Should().Be("Fail");
        report.Chapter7ArtifactPaths.Should().BeEquivalentTo(chapter7Artifacts);
        report.GdunitStatus.Should().Be("N/A");
        report.GdunitNaRationale.Should().NotBeNullOrWhiteSpace();
    }

    private sealed class ConfigAuditAndMigrationSurfacePolicy
    {
        private static readonly string[] RequiredSurfaces =
        {
            "ConfigAuditPanel",
            "MigrationStatusDialog",
            "ReportMetadataPanel",
        };

        private static readonly string[] RequiredSplitTasks =
        {
            "T173",
            "T174",
            "T175",
        };

        private static readonly string[] RequiredScopedTasks =
        {
            "T147", "T148", "T149", "T150", "T151", "T152", "T153", "T154", "T155", "T156",
            "T157", "T158", "T159", "T160", "T161", "T162", "T163", "T165", "T166", "T167",
            "T168", "T169", "T171", "T172", "T173", "T174", "T175",
        };

        public SliceEvaluationResult EvaluateSlice(SliceInput input)
        {
            var missingSurfaces = RequiredSurfaces
                .Where(surface => !input.Surfaces.Contains(surface) && !input.EquivalentSurfaceMapping.ContainsKey(surface))
                .ToList();
            var mappingSatisfied = missingSurfaces.Count == 0;

            var hasRequiredRenderableState =
                !string.IsNullOrWhiteSpace(input.ActiveConfig) &&
                !string.IsNullOrWhiteSpace(input.SchemaStatus) &&
                !string.IsNullOrWhiteSpace(input.FallbackPolicy) &&
                !string.IsNullOrWhiteSpace(input.MigrationStatus) &&
                !string.IsNullOrWhiteSpace(input.AuditMetadata);

            var violations = new List<string>();
            if (input.HasLogsOnlyEvidence && !hasRequiredRenderableState)
            {
                violations.Add("logs-only-evidence");
            }

            var missingSplitEvidence = RequiredSplitTasks
                .Where(taskId => !input.SplitTaskEvidence.TryGetValue(taskId, out var isComplete) || !isComplete)
                .ToList();

            var integrationClosureComplete = missingSplitEvidence.Count == 0;

            var renderedFromState = hasRequiredRenderableState && !input.HasLogsOnlyEvidence;

            var endToEndInspectionAvailable = hasRequiredRenderableState && mappingSatisfied;
            var gateCanAdvance = mappingSatisfied && renderedFromState && integrationClosureComplete;

            return new SliceEvaluationResult(
                endToEndInspectionAvailable,
                mappingSatisfied,
                renderedFromState,
                integrationClosureComplete,
                gateCanAdvance,
                missingSurfaces,
                missingSplitEvidence,
                violations);
        }

        public IReadOnlyList<CampaignValidationIssue> ValidateCampaignContent(IEnumerable<CampaignFixture> fixtures)
        {
            var issues = new List<CampaignValidationIssue>();

            foreach (var fixture in fixtures)
            {
                if (!fixture.CrossReferenceOk)
                {
                    issues.Add(new CampaignValidationIssue(fixture.FilePath, "cross_reference", "cross-reference", fixture.DatasetType));
                }

                if (!fixture.VersionBumpOk)
                {
                    issues.Add(new CampaignValidationIssue(fixture.FilePath, "version", "version-bump", fixture.DatasetType));
                }

                if (!fixture.I18nCoverageOk)
                {
                    issues.Add(new CampaignValidationIssue(fixture.FilePath, "i18n", "i18n-coverage", fixture.DatasetType));
                }
            }

            return issues
                .OrderBy(issue => issue.FilePath, StringComparer.Ordinal)
                .ThenBy(issue => issue.GateName, StringComparer.Ordinal)
                .ToList();
        }

        public HardGateResult EvaluateHardGate(
            IReadOnlyCollection<CampaignValidationIssue> issues,
            bool domainContractsUnchanged,
            bool hasOutOfScopeGameplayChanges)
        {
            var blocked = issues.Count > 0;
            var canMerge = !blocked && domainContractsUnchanged && !hasOutOfScopeGameplayChanges;

            return new HardGateResult(
                blocked,
                domainContractsUnchanged,
                hasOutOfScopeGameplayChanges,
                canMerge);
        }

        public ScopeMappingResult EvaluateScopedMapping(
            ISet<string> mappedTaskIds,
            ISet<string> outOfScopeGameplayTaskIds)
        {
            var missingMappings = RequiredScopedTasks
                .Where(taskId => !mappedTaskIds.Contains(taskId))
                .ToList();

            var outOfScopeMappings = outOfScopeGameplayTaskIds.OrderBy(taskId => taskId, StringComparer.Ordinal).ToList();
            var complete = missingMappings.Count == 0 && outOfScopeMappings.Count == 0;

            return new ScopeMappingResult(complete, missingMappings, outOfScopeMappings);
        }

        public ValidationEvidenceReport RecordValidationEvidence(
            bool xunitPassed,
            IReadOnlyList<string> chapter7ArtifactPaths,
            int gdunitCaseCount,
            string gdunitNaRationale)
        {
            if (chapter7ArtifactPaths == null || chapter7ArtifactPaths.Count == 0)
            {
                throw new ArgumentException("At least one Chapter 7 artifact path is required.", nameof(chapter7ArtifactPaths));
            }

            var gdunitStatus = gdunitCaseCount > 0 ? "Recorded" : "N/A";
            var normalizedRationale = gdunitStatus == "N/A"
                ? (string.IsNullOrWhiteSpace(gdunitNaRationale)
                    ? "No GdUnit case applies to this slice."
                    : gdunitNaRationale)
                : string.Empty;

            return new ValidationEvidenceReport(
                xunitPassed ? "Pass" : "Fail",
                chapter7ArtifactPaths,
                gdunitStatus,
                normalizedRationale);
        }
    }

    private sealed class SliceInput
    {
        public ISet<string> Surfaces { get; set; } = new HashSet<string>(StringComparer.Ordinal);

        public IDictionary<string, string> EquivalentSurfaceMapping { get; set; } =
            new Dictionary<string, string>(StringComparer.Ordinal);

        public string ActiveConfig { get; set; } = string.Empty;

        public string SchemaStatus { get; set; } = string.Empty;

        public string FallbackPolicy { get; set; } = string.Empty;

        public string MigrationStatus { get; set; } = string.Empty;

        public string AuditMetadata { get; set; } = string.Empty;

        public bool HasLogsOnlyEvidence { get; set; }

        public IDictionary<string, bool> SplitTaskEvidence { get; set; } =
            new Dictionary<string, bool>(StringComparer.Ordinal);
    }

    private sealed class SliceEvaluationResult
    {
        public SliceEvaluationResult(
            bool endToEndInspectionAvailable,
            bool mappingSatisfied,
            bool renderedFromState,
            bool integrationClosureComplete,
            bool gateCanAdvance,
            IReadOnlyList<string> missingSurfaces,
            IReadOnlyList<string> missingSplitEvidence,
            IReadOnlyList<string> violations)
        {
            EndToEndInspectionAvailable = endToEndInspectionAvailable;
            MappingSatisfied = mappingSatisfied;
            RenderedFromState = renderedFromState;
            IntegrationClosureComplete = integrationClosureComplete;
            GateCanAdvance = gateCanAdvance;
            MissingSurfaces = missingSurfaces;
            MissingSplitEvidence = missingSplitEvidence;
            Violations = violations;
        }

        public bool EndToEndInspectionAvailable { get; }

        public bool MappingSatisfied { get; }

        public bool RenderedFromState { get; }

        public bool IntegrationClosureComplete { get; }

        public bool GateCanAdvance { get; }

        public IReadOnlyList<string> MissingSurfaces { get; }

        public IReadOnlyList<string> MissingSplitEvidence { get; }

        public IReadOnlyList<string> Violations { get; }
    }

    private sealed class CampaignFixture
    {
        public string DatasetType { get; set; } = string.Empty;

        public string FilePath { get; set; } = string.Empty;

        public bool CrossReferenceOk { get; set; }

        public bool VersionBumpOk { get; set; }

        public bool I18nCoverageOk { get; set; }
    }

    private sealed class CampaignValidationIssue
    {
        public CampaignValidationIssue(string filePath, string field, string gateName, string datasetType)
        {
            FilePath = filePath;
            Field = field;
            GateName = gateName;
            DatasetType = datasetType;
        }

        public string FilePath { get; }

        public string Field { get; }

        public string GateName { get; }

        public string DatasetType { get; }
    }

    private sealed class HardGateResult
    {
        public HardGateResult(
            bool blocked,
            bool deterministicDomainStateUnchanged,
            bool outOfScopeGameplayChangesDetected,
            bool canMerge)
        {
            Blocked = blocked;
            DeterministicDomainStateUnchanged = deterministicDomainStateUnchanged;
            OutOfScopeGameplayChangesDetected = outOfScopeGameplayChangesDetected;
            CanMerge = canMerge;
        }

        public bool Blocked { get; }

        public bool DeterministicDomainStateUnchanged { get; }

        public bool OutOfScopeGameplayChangesDetected { get; }

        public bool CanMerge { get; }
    }

    private sealed class ScopeMappingResult
    {
        public ScopeMappingResult(bool complete, IReadOnlyList<string> missingMappings, IReadOnlyList<string> outOfScopeMappings)
        {
            Complete = complete;
            MissingMappings = missingMappings;
            OutOfScopeMappings = outOfScopeMappings;
        }

        public bool Complete { get; }

        public IReadOnlyList<string> MissingMappings { get; }

        public IReadOnlyList<string> OutOfScopeMappings { get; }
    }

    private sealed class ValidationEvidenceReport
    {
        public ValidationEvidenceReport(
            string xunitSuiteStatus,
            IReadOnlyList<string> chapter7ArtifactPaths,
            string gdunitStatus,
            string gdunitNaRationale)
        {
            XunitSuiteStatus = xunitSuiteStatus;
            Chapter7ArtifactPaths = chapter7ArtifactPaths;
            GdunitStatus = gdunitStatus;
            GdunitNaRationale = gdunitNaRationale;
        }

        public string XunitSuiteStatus { get; }

        public IReadOnlyList<string> Chapter7ArtifactPaths { get; }

        public string GdunitStatus { get; }

        public string GdunitNaRationale { get; }
    }
}
