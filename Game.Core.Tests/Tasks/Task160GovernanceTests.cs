using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task160GovernanceTests
{
    // ACC:T160.1
    [Fact]
    [Trait("acceptance", "ACC:T160.1")]
    public void ShouldRequireStructuredLoggingRedactionAndTraceabilityFields_WhenValidatingLoggingGuidelinesBaseline()
    {
        var documentation = LoadLoggingGuidelinesBaseline();
        var configuration = BuildConfigurationJson(includeTraceabilityFields: false);

        var report = LoggingGuidelinesGate.Validate(documentation, configuration);

        report.IsSuccess.Should().BeFalse();
        report.MissingRequirements.Should().Contain("config:traceability-fields");
    }

    // ACC:T160.2
    [Fact]
    [Trait("acceptance", "ACC:T160.2")]
    public void ShouldExposeDocumentationAndConfigurationChecks_WhenBuildingObservabilityValidationReport()
    {
        var documentation = LoadLoggingGuidelinesBaseline();
        var configuration = BuildConfigurationJson();

        var report = LoggingGuidelinesGate.Validate(documentation, configuration);

        report.IsSuccess.Should().BeTrue();
        report.Checks.Should().ContainSingle(check => check.Kind == "documentation" && check.Code == "structured-logging");
        report.Checks.Should().ContainSingle(check => check.Kind == "documentation" && check.Code == "redaction-rules");
        report.Checks.Should().ContainSingle(check => check.Kind == "documentation" && check.Code == "traceability-fields");
        report.Checks.Should().ContainSingle(check => check.Kind == "configuration" && check.Code == "baseline-path");
        report.Checks.Should().ContainSingle(check => check.Kind == "configuration" && check.Code == "redaction-rules");
        report.Checks.Should().ContainSingle(check => check.Kind == "configuration" && check.Code == "traceability-fields");
    }

    // ACC:T160.3
    [Theory]
    [Trait("acceptance", "ACC:T160.3")]
    [InlineData("loggingGuidelinesBaseline", "config:baseline-path")]
    [InlineData("redactionRules", "config:redaction-rules")]
    [InlineData("traceabilityFields", "config:traceability-fields")]
    public void ShouldFailLintCheck_WhenMandatoryConfigurationInputIsMissing(string missingKey, string expectedRequirement)
    {
        var documentation = LoadLoggingGuidelinesBaseline();
        var configuration = BuildConfigurationJsonWithMissingKey(missingKey);

        var report = LoggingGuidelinesGate.Validate(documentation, configuration);

        report.IsSuccess.Should().BeFalse();
        report.MissingRequirements.Should().Contain(expectedRequirement);
    }

    // ACC:T160.3
    [Fact]
    [Trait("acceptance", "ACC:T160.3")]
    public void ShouldFailLintCheck_WhenBaselinePathDoesNotMatchDocumentationContract()
    {
        var documentation = LoadLoggingGuidelinesBaseline();
        var configuration = BuildConfigurationJsonWithOverrideBaselinePath("docs/observability/other-guidelines.md");

        var report = LoggingGuidelinesGate.Validate(documentation, configuration);

        report.IsSuccess.Should().BeFalse();
        report.MissingRequirements.Should().Contain("config:baseline-path");
    }

    // ACC:T160.3
    [Theory]
    [Trait("acceptance", "ACC:T160.3")]
    [InlineData("structured", "doc:structured-logging")]
    [InlineData("redaction", "doc:redaction-rules")]
    [InlineData("traceability", "doc:traceability-fields")]
    public void ShouldFailLintCheck_WhenMandatoryDocumentationSectionIsMissing(string mode, string expectedRequirement)
    {
        var documentation = mode switch
        {
            "structured" => "# Logging Guidelines\n\n## Redaction Rules\nSensitive fields include email and token.\n\n## Traceability Fields\ntraceId spanId taskId",
            "redaction" => "# Logging Guidelines\n\n## Structured Logging\nUse structured logging for production events.\n\n## Traceability Fields\ntraceId spanId taskId",
            "traceability" => "# Logging Guidelines\n\n## Structured Logging\nUse structured logging for production events.\n\n## Redaction Rules\nSensitive fields include email and token.",
            _ => throw new ArgumentOutOfRangeException(nameof(mode), mode, "Unsupported documentation mode."),
        };
        var configuration = BuildConfigurationJson();

        var report = LoggingGuidelinesGate.Validate(documentation, configuration);

        report.IsSuccess.Should().BeFalse();
        report.MissingRequirements.Should().Contain(expectedRequirement);
    }

    private static string LoadLoggingGuidelinesBaseline()
    {
        var repoRoot = FindRepoRoot();
        var baselinePath = Path.Combine(repoRoot, "docs", "observability", "logging-guidelines.md");
        File.Exists(baselinePath).Should().BeTrue("Task 160 baseline documentation must exist.");
        return File.ReadAllText(baselinePath);
    }

    private static string FindRepoRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            var markerPath = Path.Combine(directory.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(markerPath))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks.json).");
    }

    private static string BuildConfigurationJson(
        bool includeBaselinePath = true,
        bool includeRedactionRules = true,
        bool includeTraceabilityFields = true)
    {
        var payload = new Dictionary<string, object?>();
        if (includeBaselinePath)
        {
            payload["loggingGuidelinesBaseline"] = "docs/observability/logging-guidelines.md";
        }

        if (includeRedactionRules)
        {
            payload["redactionRules"] = new[] { "email", "token" };
        }

        if (includeTraceabilityFields)
        {
            payload["traceabilityFields"] = new[] { "traceId", "spanId", "taskId" };
        }

        return JsonSerializer.Serialize(payload);
    }

    private static string BuildConfigurationJsonWithMissingKey(string missingKey)
    {
        return missingKey switch
        {
            "loggingGuidelinesBaseline" => BuildConfigurationJson(includeBaselinePath: false),
            "redactionRules" => BuildConfigurationJson(includeRedactionRules: false),
            "traceabilityFields" => BuildConfigurationJson(includeTraceabilityFields: false),
            _ => throw new ArgumentOutOfRangeException(nameof(missingKey), missingKey, "Unsupported configuration key."),
        };
    }

    private static string BuildConfigurationJsonWithOverrideBaselinePath(string baselinePath)
    {
        var payload = new Dictionary<string, object?>
        {
            ["loggingGuidelinesBaseline"] = baselinePath,
            ["redactionRules"] = new[] { "email", "token" },
            ["traceabilityFields"] = new[] { "traceId", "spanId", "taskId" },
        };
        return JsonSerializer.Serialize(payload);
    }
}
