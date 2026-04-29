using System.Collections.Generic;
using System.Linq;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public class Task148CampaignContentQualityGatesTests
{
    // ACC:T148.1
    [Fact]
    public void ShouldEmitPinpointedEvidenceForAllMandatoryGates_WhenFixtureViolatesCrossRefVersionAndI18n()
    {
        var fixture = CampaignFixture.InvalidWithMissingCrossRefAndI18n(
            datasetType: "campaign.chapter",
            filePath: "fixtures/campaign/chapter_001.json",
            previousVersion: 3,
            currentVersion: 3);

        var validator = new CampaignContentQualityGateValidator();

        var issues = validator.Validate(fixture);

        issues.Should().Contain(i =>
            i.GateName == "mandatory-cross-ref" &&
            i.FilePath == "fixtures/campaign/chapter_001.json" &&
            i.Field == "chapter.heroId");

        issues.Should().Contain(i =>
            i.GateName == "version-bump" &&
            i.FilePath == "fixtures/campaign/chapter_001.json" &&
            i.Field == "meta.version");

        issues.Should().Contain(i =>
            i.GateName == "i18n-coverage" &&
            i.FilePath == "fixtures/campaign/chapter_001.json" &&
            i.Field == "title.zh-CN");
    }

    // ACC:T148.2
    [Theory]
    [InlineData("mandatory-cross-ref", "chapter.heroId")]
    [InlineData("version-bump", "meta.version")]
    [InlineData("i18n-coverage", "title.zh-CN")]
    public void ShouldRejectMinimalFailingFixture_WhenRuleIsViolated(string gateName, string expectedField)
    {
        var fixture = CampaignFixture.MinimalFailingFor(gateName, "fixtures/campaign/minimal_failure.json");
        var validator = new CampaignContentQualityGateValidator();

        var issues = validator.Validate(fixture);

        issues.Should().ContainSingle(i => i.GateName == gateName && i.Field == expectedField);
    }

    // ACC:T148.4
    [Fact]
    public void ShouldCoverEachDatasetCategoryDeterministically_WhenRunningRegressionFixtureSuite()
    {
        var fixtures = new[]
        {
            CampaignFixture.Valid("chapter", "fixtures/regression/chapter_valid.json"),
            CampaignFixture.Valid("battle", "fixtures/regression/battle_valid.json"),
            CampaignFixture.Valid("event", "fixtures/regression/event_valid.json")
        };

        var validator = new CampaignContentQualityGateValidator();

        var resultsByCategory = fixtures.ToDictionary(
            fixture => fixture.DatasetType,
            fixture => validator.Validate(fixture));

        resultsByCategory.Keys.Should().BeEquivalentTo(new[] { "chapter", "battle", "event" });
        resultsByCategory.Values.SelectMany(issues => issues).Should().BeEmpty();
    }

    [Fact]
    public void ShouldKeepFixtureAccepted_WhenMandatoryRulesRemainSatisfied()
    {
        var fixture = CampaignFixture.Valid("chapter", "fixtures/campaign/chapter_valid.json");
        var validator = new CampaignContentQualityGateValidator();

        var issues = validator.Validate(fixture);

        issues.Should().BeEmpty();
    }

    private sealed class CampaignContentQualityGateValidator
    {
        private static readonly string[] RequiredLocales = { "en-US", "zh-CN" };

        public IReadOnlyList<QualityIssue> Validate(CampaignFixture fixture)
        {
            var issues = new List<QualityIssue>();

            if (!fixture.ExistingHeroIds.Contains(fixture.ReferencedHeroId))
            {
                issues.Add(new QualityIssue(
                    "mandatory-cross-ref",
                    fixture.FilePath,
                    "chapter.heroId",
                    "Referenced hero id does not exist in the target dataset."));
            }

            if (fixture.CurrentVersion <= fixture.PreviousVersion)
            {
                issues.Add(new QualityIssue(
                    "version-bump",
                    fixture.FilePath,
                    "meta.version",
                    "Version must increase for modified content."));
            }

            var missingLocale = RequiredLocales.FirstOrDefault(locale => !fixture.LocalizedTitle.ContainsKey(locale));
            if (missingLocale is not null)
            {
                issues.Add(new QualityIssue(
                    "i18n-coverage",
                    fixture.FilePath,
                    $"title.{missingLocale}",
                    "Localized title is missing for a required locale."));
            }

            return issues;
        }
    }

    private sealed class CampaignFixture
    {
        public CampaignFixture(
            string datasetType,
            string filePath,
            int previousVersion,
            int currentVersion,
            IReadOnlyCollection<string> existingHeroIds,
            string referencedHeroId,
            IReadOnlyDictionary<string, string> localizedTitle)
        {
            DatasetType = datasetType;
            FilePath = filePath;
            PreviousVersion = previousVersion;
            CurrentVersion = currentVersion;
            ExistingHeroIds = existingHeroIds;
            ReferencedHeroId = referencedHeroId;
            LocalizedTitle = localizedTitle;
        }

        public string DatasetType { get; }

        public string FilePath { get; }

        public int PreviousVersion { get; }

        public int CurrentVersion { get; }

        public IReadOnlyCollection<string> ExistingHeroIds { get; }

        public string ReferencedHeroId { get; }

        public IReadOnlyDictionary<string, string> LocalizedTitle { get; }

        public static CampaignFixture InvalidWithMissingCrossRefAndI18n(
            string datasetType,
            string filePath,
            int previousVersion,
            int currentVersion)
        {
            return new CampaignFixture(
                datasetType,
                filePath,
                previousVersion,
                currentVersion,
                new[] { "hero_001" },
                "hero_404",
                new Dictionary<string, string>
                {
                    ["en-US"] = "Campaign Intro"
                });
        }

        public static CampaignFixture MinimalFailingFor(string gateName, string filePath)
        {
            return gateName switch
            {
                "mandatory-cross-ref" => new CampaignFixture(
                    "campaign.chapter",
                    filePath,
                    1,
                    2,
                    new[] { "hero_001" },
                    "hero_404",
                    new Dictionary<string, string>
                    {
                        ["en-US"] = "Campaign Intro",
                        ["zh-CN"] = "Campaign Intro"
                    }),
                "version-bump" => new CampaignFixture(
                    "campaign.chapter",
                    filePath,
                    2,
                    2,
                    new[] { "hero_001" },
                    "hero_001",
                    new Dictionary<string, string>
                    {
                        ["en-US"] = "Campaign Intro",
                        ["zh-CN"] = "Campaign Intro"
                    }),
                "i18n-coverage" => new CampaignFixture(
                    "campaign.chapter",
                    filePath,
                    1,
                    2,
                    new[] { "hero_001" },
                    "hero_001",
                    new Dictionary<string, string>
                    {
                        ["en-US"] = "Campaign Intro"
                    }),
                _ => Valid("campaign.chapter", filePath)
            };
        }

        public static CampaignFixture Valid(string datasetType, string filePath)
        {
            return new CampaignFixture(
                datasetType,
                filePath,
                1,
                2,
                new[] { "hero_001" },
                "hero_001",
                new Dictionary<string, string>
                {
                    ["en-US"] = "Campaign Intro",
                    ["zh-CN"] = "Campaign Intro"
                });
        }
    }

    private sealed record QualityIssue(string GateName, string FilePath, string Field, string Message);
}
