using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Domain;

public sealed class SanguoSaveLoadEventsTests
{
    // ACC:T18.5
    [Fact]
    public void ShouldExposeStableEventTypeConstants_WhenSavingAndLoading()
    {
        SanguoGameSaved.EventType.Should().Be("core.sanguo.game.saved");
        SanguoGameLoaded.EventType.Should().Be("core.sanguo.game.loaded");
    }

    // ACC:T18.5
    [Fact]
    public void ShouldHaveNonEmptyDistinctEventTypes_WhenComparingSavedAndLoaded()
    {
        var saved = SanguoGameSaved.EventType;
        var loaded = SanguoGameLoaded.EventType;

        saved.Should().NotBeNullOrWhiteSpace();
        loaded.Should().NotBeNullOrWhiteSpace();
        saved.Should().NotBe(loaded);
        saved.Should().Contain("sanguo");
        loaded.Should().Contain("sanguo");
    }
}
