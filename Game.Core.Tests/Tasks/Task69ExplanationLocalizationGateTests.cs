using FluentAssertions;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task69ExplanationLocalizationGateTests
{
    private const string Task69MissingKey = "ui.task69.explanation.missing";
    private const string NonTask69MissingKey = "ui.menu.title.missing";
    private const string FriendlyFallback = "Explanation is temporarily unavailable.";

    // ACC:T69.5
    // ACC:T205.4
    [Fact]
    [Trait("acceptance", "ACC:T69.5")]
    public void ShouldApplyBuildModePolicyForTask69KeyAndKeepNonTask69KeyOnFallbackPath_WhenTranslationIsMissing()
    {
        var releaseTask69 = Task69ExplanationLocalizationGate.ResolveMissingTranslation("release", Task69MissingKey, FriendlyFallback);
        var devTask69 = Task69ExplanationLocalizationGate.ResolveMissingTranslation("dev", Task69MissingKey, FriendlyFallback);
        var releaseNonTask69 = Task69ExplanationLocalizationGate.ResolveMissingTranslation("release", NonTask69MissingKey, FriendlyFallback);
        var devNonTask69 = Task69ExplanationLocalizationGate.ResolveMissingTranslation("dev", NonTask69MissingKey, FriendlyFallback);

        releaseTask69.Should().Be(FriendlyFallback);
        devTask69.Should().Be(Task69MissingKey);
        releaseNonTask69.Should().Be(FriendlyFallback, "non-task69 keys must stay on the fallback path in release mode");
        devNonTask69.Should().Be(FriendlyFallback, "non-task69 keys must not enter the raw-key exposure branch");
    }
}
