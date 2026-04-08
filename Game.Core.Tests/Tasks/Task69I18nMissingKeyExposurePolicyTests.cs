using FluentAssertions;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task69I18nMissingKeyExposurePolicyTests
{
    private const string MissingKey = "ui.task69.explanation.missing";
    private const string FriendlyFallback = "Explanation is temporarily unavailable.";

    // ACC:T69.1
    [Fact]
    [Trait("acceptance", "ACC:T69.1")]
    public void ShouldReturnFriendlyFallback_WhenBuildModeIsReleaseAndKeyMissing()
    {
        var rendered = I18nMissingKeyExposurePolicy.ResolveForBuildMode("release", MissingKey, FriendlyFallback);
        rendered.Should().Be(FriendlyFallback);
    }

    // ACC:T69.2
    [Fact]
    [Trait("acceptance", "ACC:T69.2")]
    public void ShouldProvideObservableDiagnosticsPath_WhenDevModeAllowsRawKeyExposure()
    {
        var diagnosticsAllowed = I18nMissingKeyExposurePolicy.AllowsDiagnosticRawKeyExposure("dev");
        var devRendered = I18nMissingKeyExposurePolicy.ResolveForBuildMode("dev", MissingKey, FriendlyFallback);
        diagnosticsAllowed.Should().BeTrue();
        devRendered.Should().Be(MissingKey);
    }

    // ACC:T69.4
    [Fact]
    [Trait("acceptance", "ACC:T69.4")]
    public void ShouldTreatDebugAndEditorAsDiagnosticsModes_WhenEvaluatingExposurePolicy()
    {
        I18nMissingKeyExposurePolicy.AllowsDiagnosticRawKeyExposure("debug").Should().BeTrue();
        I18nMissingKeyExposurePolicy.AllowsDiagnosticRawKeyExposure("editor").Should().BeTrue();
        I18nMissingKeyExposurePolicy.AllowsDiagnosticRawKeyExposure("release").Should().BeFalse();
    }

    // ACC:T69.6
    [Fact]
    [Trait("acceptance", "ACC:T69.6")]
    public void ShouldUseDefaultFriendlyFallback_WhenExplicitFallbackIsBlank()
    {
        var rendered = I18nMissingKeyExposurePolicy.ResolveForBuildMode("release", MissingKey, string.Empty);
        rendered.Should().Be(I18nMissingKeyExposurePolicy.DefaultFriendlyFallback);
    }

    // ACC:T69.6
    [Fact]
    [Trait("acceptance", "ACC:T69.6")]
    public void ShouldUseDefaultFriendlyFallback_WhenExplicitFallbackIsWhitespace()
    {
        var rendered = I18nMissingKeyExposurePolicy.ResolveForBuildMode("release", MissingKey, "   ");
        rendered.Should().Be(I18nMissingKeyExposurePolicy.DefaultFriendlyFallback);
        rendered.Should().NotBe(MissingKey);
    }

    // ACC:T69.3
    [Fact]
    [Trait("acceptance", "ACC:T69.3")]
    public void ShouldEnforceCiGuardRule_WhenReleaseAndDevEvaluateSameMissingKeyInput()
    {
        var releaseRendered = I18nMissingKeyExposurePolicy.ResolveForBuildMode("release", MissingKey, FriendlyFallback);
        var devRendered = I18nMissingKeyExposurePolicy.ResolveForBuildMode("dev", MissingKey, FriendlyFallback);

        releaseRendered.Should().NotBe(MissingKey);
        releaseRendered.Should().Be(FriendlyFallback);
        devRendered.Should().Be(MissingKey);
    }

    [Fact]
    public void ShouldClassifyModeNamesCaseInsensitively_WhenEvaluatingDiagnosticsExposure()
    {
        I18nMissingKeyExposurePolicy.AllowsDiagnosticRawKeyExposure("DEV").Should().BeTrue();
        I18nMissingKeyExposurePolicy.AllowsDiagnosticRawKeyExposure("Editor").Should().BeTrue();
        I18nMissingKeyExposurePolicy.AllowsDiagnosticRawKeyExposure("ReLeAsE").Should().BeFalse();
    }

    // ACC:T69.7
    [Fact]
    [Trait("acceptance", "ACC:T69.7")]
    public void ShouldApplyPolicyAgnosticallyAcrossScopedMissingKeys_WhenComparingReleaseAndDevPaths()
    {
        var scopedMissingKeys = new[]
        {
            "ui.task69.explanation.missing",
            "ui.task69.explanation.alt_missing",
        };

        foreach (var missingKey in scopedMissingKeys)
        {
            var releaseRendered = I18nMissingKeyExposurePolicy.ResolveForBuildMode("release", missingKey, FriendlyFallback);
            var devRendered = I18nMissingKeyExposurePolicy.ResolveForBuildMode("dev", missingKey, FriendlyFallback);

            releaseRendered.Should().NotBe(missingKey);
            releaseRendered.Should().Be(FriendlyFallback);
            devRendered.Should().Be(missingKey);
        }
    }

    // ACC:T69.8
    [Fact]
    [Trait("acceptance", "ACC:T69.8")]
    public void ShouldReturnDefaultFriendlyFallback_WhenFallbackIsNullOrOmittedInReleaseMode()
    {
        var withNullFallback = I18nMissingKeyExposurePolicy.ResolveForBuildMode("release", MissingKey, null!);
        var withOmittedFallback = I18nMissingKeyExposurePolicy.ResolveForBuildMode("release", MissingKey);

        withNullFallback.Should().Be(I18nMissingKeyExposurePolicy.DefaultFriendlyFallback);
        withOmittedFallback.Should().Be(I18nMissingKeyExposurePolicy.DefaultFriendlyFallback);
        withNullFallback.Should().NotBe(MissingKey);
        withOmittedFallback.Should().NotBe(MissingKey);
    }
}
