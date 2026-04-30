using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Docs;

public class PrivacyComplianceDocumentationTests
{
    private static readonly string BaselineDocumentPath = Path.Combine(
        AppContext.BaseDirectory,
        "..",
        "..",
        "..",
        "..",
        "docs",
        "privacy",
        "campaign-telemetry-privacy-compliance.md");

    // ACC:T159.1
    [Fact]
    public void ShouldContainRequiredPrivacySections_WhenValidatingBaselineDocument()
    {
        File.Exists(BaselineDocumentPath).Should().BeTrue("privacy baseline document must be authored at the expected path");

        var content = File.ReadAllText(BaselineDocumentPath);
        var result = ValidateDocument(content);

        result.IsValid.Should().BeTrue("baseline document must be machine-checkable and complete");
        result.MissingSections.Should().BeEmpty();
    }

    // ACC:T159.2
    [Fact]
    public void ShouldRejectDocument_WhenRequiredPrivacySectionsAreMissing()
    {
        var content = "# Privacy Compliance\n\n## Data Minimization\nRules are listed here.";

        var result = ValidateDocument(content);

        result.IsValid.Should().BeFalse();
        result.MissingSections.Should().Contain("Retention Bounds");
        result.MissingSections.Should().Contain("Non-Crash Feedback Suppression Linkage");
    }

    [Fact]
    public void ShouldRejectDocument_WhenSuppressionLinkageAllowsUnsuppressedFeedback()
    {
        var content = string.Join(Environment.NewLine, new[]
        {
            "# Privacy Compliance",
            "## Data Minimization",
            "Only aggregate counters are allowed.",
            "## Retention Bounds",
            "Retention is capped to 30 days.",
            "## Non-Crash Feedback Suppression Linkage",
            "Feedback may be sent even when suppression is enabled."
        });

        var result = ValidateDocument(content);

        result.IsValid.Should().BeFalse();
        result.Errors.Should().Contain(error => error.Contains("must not allow unsuppressed feedback", StringComparison.OrdinalIgnoreCase));
    }

    private static ValidationResult ValidateDocument(string content)
    {
        var missingSections = new List<string>();
        var errors = new List<string>();

        if (!ContainsHeading(content, "Data Minimization"))
        {
            missingSections.Add("Data Minimization");
        }

        if (!ContainsHeading(content, "Retention Bounds"))
        {
            missingSections.Add("Retention Bounds");
        }

        if (!ContainsHeading(content, "Non-Crash Feedback Suppression Linkage"))
        {
            missingSections.Add("Non-Crash Feedback Suppression Linkage");
        }

        if (ContainsHeading(content, "Non-Crash Feedback Suppression Linkage") &&
            content.Contains("may be sent even when suppression is enabled", StringComparison.OrdinalIgnoreCase))
        {
            errors.Add("Suppression linkage must not allow unsuppressed feedback.");
        }

        return new ValidationResult(missingSections.Count == 0 && errors.Count == 0, missingSections, errors);
    }

    private static bool ContainsHeading(string content, string heading)
    {
        var lines = content
            .Split(new[] { "\r\n", "\n" }, StringSplitOptions.None)
            .Select(line => line.Trim());

        return lines.Any(line => line.Equals($"## {heading}", StringComparison.OrdinalIgnoreCase));
    }

    private sealed record ValidationResult(bool IsValid, IReadOnlyList<string> MissingSections, IReadOnlyList<string> Errors);
}
