using FluentAssertions;
using Game.Core.Ports;
using Game.Core.Services.Sanguo;
using System;
using Xunit;

namespace Game.Core.Tests.Services;

public sealed class SanguoMapsCatalogLoaderTests
{
    [Fact]
    public void TryLoadMapsCatalog_ShouldFail_WhenMissing()
    {
        var loader = new FakeResourceLoader(SanguoMapsCatalogLoader.MapsIndexResPath, null);

        var ok = SanguoMapsCatalogLoader.TryLoadMapsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("maps_index_missing");
    }

    [Fact]
    public void TryLoadMapsCatalog_ShouldFail_WhenJsonInvalid()
    {
        var loader = new FakeResourceLoader(SanguoMapsCatalogLoader.MapsIndexResPath, "{not json");

        var ok = SanguoMapsCatalogLoader.TryLoadMapsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().StartWith("json_parse_failed:");
    }

    [Fact]
    public void TryLoadMapsCatalog_ShouldFail_WhenBadVersions()
    {
        var loader = new FakeResourceLoader(SanguoMapsCatalogLoader.MapsIndexResPath, "{\"schemaVersion\":0,\"version\":0,\"maps\":[]}");

        var ok = SanguoMapsCatalogLoader.TryLoadMapsCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_maps_index:bad_versions");
    }

    [Fact]
    public void TryLoadMapsCatalog_ShouldLoad_WhenValid()
    {
        var loader = new FakeResourceLoader(SanguoMapsCatalogLoader.MapsIndexResPath, "{\"schemaVersion\":1,\"version\":1,\"maps\":[{\"mapId\":\"map001\",\"nameKey\":\"map.name\",\"path\":\"res://Data/maps/map001.json\",\"recommendedPlayersMin\":4,\"recommendedPlayersMax\":8,\"version\":1,\"descriptionKey\":\"map.desc\",\"previewImageResPath\":\"res://Assets/preview.png\"}]}");

        var ok = SanguoMapsCatalogLoader.TryLoadMapsCatalog(loader, out var catalog, out var error);

        ok.Should().BeTrue();
        error.Should().BeEmpty();
        catalog.SchemaVersion.Should().Be(1);
        catalog.Version.Should().Be(1);
        catalog.Maps.Should().HaveCount(1);
        catalog.Maps[0].MapId.Should().Be("map001");
    }

    private sealed class FakeResourceLoader : IResourceLoader
    {
        private readonly string _path;
        private readonly string? _content;

        public FakeResourceLoader(string path, string? content)
        {
            _path = path;
            _content = content;
        }

        public string? LoadText(string path) => string.Equals(path, _path, StringComparison.Ordinal) ? _content : null;

        public byte[]? LoadBytes(string path) => null;
    }
}
