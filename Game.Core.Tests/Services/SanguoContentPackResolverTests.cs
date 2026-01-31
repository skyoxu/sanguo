using FluentAssertions;
using Game.Core.Ports;
using Game.Core.Services.Sanguo;
using System;
using System.Collections.Generic;
using Xunit;

namespace Game.Core.Tests.Services;

public sealed class SanguoContentPackResolverTests
{
    private const string PackPath = "res://Data/packs/core_a/pack.json";

    [Fact]
    public void TryResolveDefaultPack_ShouldFail_WhenIndexMissing()
    {
        var loader = new FakeResourceLoader(new Dictionary<string, string?>());

        var ok = SanguoContentPackResolver.TryResolveDefaultPack(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("content_pack_index_missing");
    }

    [Fact]
    public void TryResolveDefaultPack_ShouldFail_WhenIndexJsonInvalid()
    {
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [SanguoContentPackResolver.PacksIndexResPath] = "{bad-json",
        });

        var ok = SanguoContentPackResolver.TryResolveDefaultPack(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().StartWith("content_pack_index_json_invalid:");
    }

    [Fact]
    public void TryResolveDefaultPack_ShouldFail_WhenNoEnabledPack()
    {
        var indexJson = "{\"schemaVersion\":1,\"version\":1,\"packs\":[{\"packId\":\"core_a\",\"nameKey\":\"pack.core_a.name\",\"descriptionKey\":\"pack.core_a.desc\",\"path\":\"res://Data/packs/core_a/pack.json\",\"order\":1,\"enabled\":false}]}";
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [SanguoContentPackResolver.PacksIndexResPath] = indexJson,
        });

        var ok = SanguoContentPackResolver.TryResolveDefaultPack(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("content_pack_index_no_enabled");
    }

    [Fact]
    public void TryResolveDefaultPack_ShouldFail_WhenIndexRootInvalid()
    {
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [SanguoContentPackResolver.PacksIndexResPath] = "[]",
        });

        var ok = SanguoContentPackResolver.TryResolveDefaultPack(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("content_pack_index_root_not_object");
    }

    [Fact]
    public void TryResolveDefaultPack_ShouldFail_WhenPacksMissing()
    {
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [SanguoContentPackResolver.PacksIndexResPath] = "{\"schemaVersion\":1,\"version\":1}",
        });

        var ok = SanguoContentPackResolver.TryResolveDefaultPack(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("content_pack_index_missing_packs");
    }

    [Fact]
    public void TryResolveDefaultPack_ShouldFail_WhenPackEntryInvalid()
    {
        var indexJson = "{\"schemaVersion\":1,\"version\":1,\"packs\":[{\"packId\":\"core_a\",\"path\":1,\"enabled\":true,\"order\":1}]}";
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [SanguoContentPackResolver.PacksIndexResPath] = indexJson,
        });

        var ok = SanguoContentPackResolver.TryResolveDefaultPack(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("content_pack_index_entry_invalid");
    }

    [Fact]
    public void TryResolveDefaultPack_ShouldFail_WhenPackEntryNotObject()
    {
        var indexJson = "{\"schemaVersion\":1,\"version\":1,\"packs\":[1]}";
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [SanguoContentPackResolver.PacksIndexResPath] = indexJson,
        });

        var ok = SanguoContentPackResolver.TryResolveDefaultPack(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("content_pack_index_entry_not_object");
    }

    [Fact]
    public void TryResolveDefaultPack_ShouldFail_WhenPackMissing()
    {
        var indexJson = "{\"schemaVersion\":1,\"version\":1,\"packs\":[{\"packId\":\"core_a\",\"nameKey\":\"pack.core_a.name\",\"descriptionKey\":\"pack.core_a.desc\",\"path\":\"res://Data/packs/core_a/pack.json\",\"order\":1,\"enabled\":true}]}";
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [SanguoContentPackResolver.PacksIndexResPath] = indexJson,
        });

        var ok = SanguoContentPackResolver.TryResolveDefaultPack(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("content_pack_missing");
    }

    [Fact]
    public void TryResolveDefaultPack_ShouldFail_WhenPackJsonInvalid()
    {
        var indexJson = "{\"schemaVersion\":1,\"version\":1,\"packs\":[{\"packId\":\"core_a\",\"nameKey\":\"pack.core_a.name\",\"descriptionKey\":\"pack.core_a.desc\",\"path\":\"res://Data/packs/core_a/pack.json\",\"order\":1,\"enabled\":true}]}";
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [SanguoContentPackResolver.PacksIndexResPath] = indexJson,
            [PackPath] = "{bad-json",
        });

        var ok = SanguoContentPackResolver.TryResolveDefaultPack(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().StartWith("content_pack_json_invalid:");
    }

    [Fact]
    public void TryResolveDefaultPack_ShouldFail_WhenPackIdMismatch()
    {
        var indexJson = "{\"schemaVersion\":1,\"version\":1,\"packs\":[{\"packId\":\"core_a\",\"nameKey\":\"pack.core_a.name\",\"descriptionKey\":\"pack.core_a.desc\",\"path\":\"res://Data/packs/core_a/pack.json\",\"order\":1,\"enabled\":true}]}";
        var packJson = BuildPackJson(packId: "core_b");
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [SanguoContentPackResolver.PacksIndexResPath] = indexJson,
            [PackPath] = packJson,
        });

        var ok = SanguoContentPackResolver.TryResolveDefaultPack(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("content_pack_id_mismatch");
    }

    [Fact]
    public void TryResolveDefaultPack_ShouldFail_WhenPackSchemaInvalid()
    {
        var indexJson = "{\"schemaVersion\":1,\"version\":1,\"packs\":[{\"packId\":\"core_a\",\"nameKey\":\"pack.core_a.name\",\"descriptionKey\":\"pack.core_a.desc\",\"path\":\"res://Data/packs/core_a/pack.json\",\"order\":1,\"enabled\":true}]}";
        var packJson = BuildPackJson(schemaVersion: 0);
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [SanguoContentPackResolver.PacksIndexResPath] = indexJson,
            [PackPath] = packJson,
        });

        var ok = SanguoContentPackResolver.TryResolveDefaultPack(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("content_pack_bad_schema");
    }

    [Fact]
    public void TryResolveDefaultPack_ShouldFail_WhenPackVersionInvalid()
    {
        var indexJson = "{\"schemaVersion\":1,\"version\":1,\"packs\":[{\"packId\":\"core_a\",\"nameKey\":\"pack.core_a.name\",\"descriptionKey\":\"pack.core_a.desc\",\"path\":\"res://Data/packs/core_a/pack.json\",\"order\":1,\"enabled\":true}]}";
        var packJson = BuildPackJson(version: 0);
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [SanguoContentPackResolver.PacksIndexResPath] = indexJson,
            [PackPath] = packJson,
        });

        var ok = SanguoContentPackResolver.TryResolveDefaultPack(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("content_pack_bad_version");
    }

    [Fact]
    public void TryResolveDefaultPack_ShouldFail_WhenContentMissing()
    {
        var indexJson = "{\"schemaVersion\":1,\"version\":1,\"packs\":[{\"packId\":\"core_a\",\"nameKey\":\"pack.core_a.name\",\"descriptionKey\":\"pack.core_a.desc\",\"path\":\"res://Data/packs/core_a/pack.json\",\"order\":1,\"enabled\":true}]}";
        var packJson = "{\"schemaVersion\":1,\"version\":1,\"packId\":\"core_a\",\"nameKey\":\"pack.core_a.name\",\"descriptionKey\":\"pack.core_a.desc\",\"enabledByDefault\":true,\"compatibility\":{\"minGameVersion\":\"0.2.0\",\"maxGameVersion\":null},\"dependencies\":[],\"tags\":[\"core\"]}";
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [SanguoContentPackResolver.PacksIndexResPath] = indexJson,
            [PackPath] = packJson,
        });

        var ok = SanguoContentPackResolver.TryResolveDefaultPack(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("content_pack_missing_content");
    }

    [Fact]
    public void TryResolveDefaultPack_ShouldFail_WhenContentPathsMissing()
    {
        var indexJson = "{\"schemaVersion\":1,\"version\":1,\"packs\":[{\"packId\":\"core_a\",\"nameKey\":\"pack.core_a.name\",\"descriptionKey\":\"pack.core_a.desc\",\"path\":\"res://Data/packs/core_a/pack.json\",\"order\":1,\"enabled\":true}]}";
        var packJson = "{\"schemaVersion\":1,\"version\":1,\"packId\":\"core_a\",\"nameKey\":\"pack.core_a.name\",\"descriptionKey\":\"pack.core_a.desc\",\"enabledByDefault\":true,\"compatibility\":{\"minGameVersion\":\"0.2.0\",\"maxGameVersion\":null},\"dependencies\":[],\"tags\":[\"core\"],\"content\":{\"maps\":[],\"characters\":[],\"events\":[],\"cards\":[],\"buildings\":[],\"relics\":[],\"regions\":[],\"facilities\":[],\"i18n\":{}}}";
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [SanguoContentPackResolver.PacksIndexResPath] = indexJson,
            [PackPath] = packJson,
        });

        var ok = SanguoContentPackResolver.TryResolveDefaultPack(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("content_pack_missing_content_paths");
    }

    [Fact]
    public void TryResolveDefaultPack_ShouldFail_WhenI18nMissing()
    {
        var indexJson = "{\"schemaVersion\":1,\"version\":1,\"packs\":[{\"packId\":\"core_a\",\"nameKey\":\"pack.core_a.name\",\"descriptionKey\":\"pack.core_a.desc\",\"path\":\"res://Data/packs/core_a/pack.json\",\"order\":1,\"enabled\":true}]}";
        var packJson = "{\"schemaVersion\":1,\"version\":1,\"packId\":\"core_a\",\"nameKey\":\"pack.core_a.name\",\"descriptionKey\":\"pack.core_a.desc\",\"enabledByDefault\":true,\"compatibility\":{\"minGameVersion\":\"0.2.0\",\"maxGameVersion\":null},\"dependencies\":[],\"tags\":[\"core\"],\"content\":{\"maps\":[\"res://Data/packs/core_a/maps/_index.json\"],\"characters\":[\"res://Data/packs/core_a/characters.json\"],\"events\":[\"res://Data/packs/core_a/random_events.json\"],\"cards\":[\"res://Data/packs/core_a/action_cards.json\"],\"buildings\":[\"res://Data/packs/core_a/buildings.json\"],\"relics\":[\"res://Data/packs/core_a/relics.json\"],\"regions\":[\"res://Data/packs/core_a/regions.json\"],\"facilities\":[\"res://Data/packs/core_a/facilities.json\"]}}";
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [SanguoContentPackResolver.PacksIndexResPath] = indexJson,
            [PackPath] = packJson,
        });

        var ok = SanguoContentPackResolver.TryResolveDefaultPack(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("content_pack_missing_i18n");
    }

    [Fact]
    public void TryResolveDefaultPack_ShouldFail_WhenI18nPathsMissing()
    {
        var indexJson = "{\"schemaVersion\":1,\"version\":1,\"packs\":[{\"packId\":\"core_a\",\"nameKey\":\"pack.core_a.name\",\"descriptionKey\":\"pack.core_a.desc\",\"path\":\"res://Data/packs/core_a/pack.json\",\"order\":1,\"enabled\":true}]}";
        var packJson = "{\"schemaVersion\":1,\"version\":1,\"packId\":\"core_a\",\"nameKey\":\"pack.core_a.name\",\"descriptionKey\":\"pack.core_a.desc\",\"enabledByDefault\":true,\"compatibility\":{\"minGameVersion\":\"0.2.0\",\"maxGameVersion\":null},\"dependencies\":[],\"tags\":[\"core\"],\"content\":{\"maps\":[\"res://Data/packs/core_a/maps/_index.json\"],\"characters\":[\"res://Data/packs/core_a/characters.json\"],\"events\":[\"res://Data/packs/core_a/random_events.json\"],\"cards\":[\"res://Data/packs/core_a/action_cards.json\"],\"buildings\":[\"res://Data/packs/core_a/buildings.json\"],\"relics\":[\"res://Data/packs/core_a/relics.json\"],\"regions\":[\"res://Data/packs/core_a/regions.json\"],\"facilities\":[\"res://Data/packs/core_a/facilities.json\"],\"i18n\":{}}}";
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [SanguoContentPackResolver.PacksIndexResPath] = indexJson,
            [PackPath] = packJson,
        });

        var ok = SanguoContentPackResolver.TryResolveDefaultPack(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("content_pack_missing_i18n_paths");
    }

    [Fact]
    public void TryResolveDefaultPack_ShouldSelectEnabledPack()
    {
        var indexJson = "{\"schemaVersion\":1,\"version\":1,\"packs\":[{\"packId\":\"core_b\",\"nameKey\":\"pack.core_b.name\",\"descriptionKey\":\"pack.core_b.desc\",\"path\":\"res://Data/packs/core_b/pack.json\",\"order\":2,\"enabled\":true},{\"packId\":\"core_a\",\"nameKey\":\"pack.core_a.name\",\"descriptionKey\":\"pack.core_a.desc\",\"path\":\"res://Data/packs/core_a/pack.json\",\"order\":1,\"enabled\":true}]}";
        var packJson = BuildPackJson();
        var loader = new FakeResourceLoader(new Dictionary<string, string?>
        {
            [SanguoContentPackResolver.PacksIndexResPath] = indexJson,
            [PackPath] = packJson,
        });

        var ok = SanguoContentPackResolver.TryResolveDefaultPack(loader, out var pack, out var error);

        ok.Should().BeTrue();
        error.Should().BeEmpty();
        pack.PackId.Should().Be("core_a");
        pack.PackVersion.Should().Be(1);
        pack.MapsIndexPath.Should().Be("res://Data/packs/core_a/maps/_index.json");
        pack.I18nZhPath.Should().Be("res://Data/packs/core_a/i18n/zh_cn.json");
        pack.I18nEnPath.Should().Be("res://Data/packs/core_a/i18n/en_us.json");
    }

    private static string BuildPackJson(string packId = "core_a", int schemaVersion = 1, int version = 1)
    {
        return $"{{\"schemaVersion\":{schemaVersion},\"version\":{version},\"packId\":\"{packId}\",\"nameKey\":\"pack.{packId}.name\",\"descriptionKey\":\"pack.{packId}.desc\",\"enabledByDefault\":true,\"compatibility\":{{\"minGameVersion\":\"0.2.0\",\"maxGameVersion\":null}},\"dependencies\":[],\"tags\":[\"core\"],\"content\":{{\"maps\":[\"res://Data/packs/{packId}/maps/_index.json\"],\"characters\":[\"res://Data/packs/{packId}/characters.json\"],\"events\":[\"res://Data/packs/{packId}/random_events.json\"],\"cards\":[\"res://Data/packs/{packId}/action_cards.json\"],\"buildings\":[\"res://Data/packs/{packId}/buildings.json\"],\"relics\":[\"res://Data/packs/{packId}/relics.json\"],\"regions\":[\"res://Data/packs/{packId}/regions.json\"],\"facilities\":[\"res://Data/packs/{packId}/facilities.json\"],\"i18n\":{{\"zh-CN\":\"res://Data/packs/{packId}/i18n/zh_cn.json\",\"en-US\":\"res://Data/packs/{packId}/i18n/en_us.json\"}}}}}}";
    }

    private sealed class FakeResourceLoader : IResourceLoader
    {
        private readonly Dictionary<string, string?> _files;

        public FakeResourceLoader(Dictionary<string, string?> files)
        {
            _files = files;
        }

        public string? LoadText(string path) => _files.TryGetValue(path, out var content) ? content : null;

        public byte[]? LoadBytes(string path) => null;
    }
}
