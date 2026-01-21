using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Ports;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task55CharacterConfigParsingTests
{
    // ACC:T55.1
    [Fact]
    public void ShouldLoadCharactersCatalog_WhenCharactersJsonIsValid()
    {
        var loader = new RepoResourceLoader();

        var ok = SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, out var catalog, out var error);

        ok.Should().BeTrue(error);
        catalog.SchemaVersion.Should().BeGreaterThan(0);
        catalog.Version.Should().BeGreaterThan(0);
        catalog.Characters.Should().NotBeNull();
        catalog.Characters.Count.Should().BeGreaterThanOrEqualTo(8);
        catalog.Characters.Select(c => c.CharacterId).Should().OnlyHaveUniqueItems();

        foreach (var c in catalog.Characters)
        {
            c.CharacterId.Should().NotBeNullOrWhiteSpace();
            c.NameKey.Should().NotBeNullOrWhiteSpace();
            c.DescriptionKey.Should().NotBeNullOrWhiteSpace();
            c.CombatRating.Should().BeInRange(0, 100);

            c.PortraitPath.Should().StartWith("res://Assets/", "portrait paths must be res://Assets/*");
            Path.GetExtension(c.PortraitPath).Should().MatchRegex("^\\.(png|webp|svg)$");

            c.EconomyStepDeltas.Should().NotBeNull();
        }
    }

    // ACC:T55.4
    [Fact]
    public void ShouldRejectCharactersCatalog_WhenPortraitPathIsNotUnderResAssets()
    {
        var json = BuildCharactersCatalogJson(portraitPath: "res://Data/not_allowed.png");
        var loader = new TestResourceLoader(json, bytes: new byte[1]);

        var ok = SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_characters_catalog:portrait_path_not_allowed");
    }

    // ACC:T55.4
    [Fact]
    public void ShouldRejectCharactersCatalog_WhenPortraitPathContainsTraversalSegments()
    {
        var json = BuildCharactersCatalogJson(portraitPath: "res://Assets/../Data/not_allowed.png");
        var loader = new TestResourceLoader(json, bytes: new byte[1]);

        var ok = SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_characters_catalog:portrait_path_not_allowed");
    }

    // ACC:T55.4
    [Fact]
    public void ShouldRejectCharactersCatalog_WhenPortraitPathIsAnAbsoluteOsPath()
    {
        var json = BuildCharactersCatalogJson(portraitPath: @"C:\Windows\win.ini");
        var loader = new TestResourceLoader(json, bytes: new byte[1]);

        var ok = SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_characters_catalog:portrait_path_not_allowed");
    }

    // ACC:T55.4
    [Fact]
    public void ShouldRejectCharactersCatalog_WhenPortraitBytesExceedMaxSize()
    {
        var json = BuildCharactersCatalogJson(portraitPath: "res://Assets/portraits/portrait_placeholder.svg");
        var bytes = new byte[SanguoCharactersCatalogLoader.MaxPortraitBytes + 1];
        var loader = new TestResourceLoader(json, bytes);

        var ok = SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_characters_catalog:portrait_too_large");
    }

    // ACC:T55.5
    [Fact]
    public void ShouldRejectCharactersCatalog_WhenCharacterIdsAreDuplicated()
    {
        var json = BuildCharactersCatalogJson(characterId: "dup", duplicateIds: true);
        var loader = new TestResourceLoader(json, bytes: new byte[1]);

        var ok = SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_characters_catalog:duplicate_character_id");
    }

    // ACC:T55.6
    [Fact]
    public void ShouldReturnReadOnlyCharactersCollection_WhenLoadingCharactersCatalog()
    {
        var loader = new RepoResourceLoader();

        var ok = SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, out var catalog, out var error);

        ok.Should().BeTrue(error);
        catalog.Characters.Should().BeAssignableTo<System.Collections.ObjectModel.ReadOnlyCollection<SanguoCharacterDefinition>>();

        var list = (IList<SanguoCharacterDefinition>)catalog.Characters;
        Action act = () => list.Add(catalog.Characters[0]);
        act.Should().Throw<NotSupportedException>();

        var ok2 = SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, out var again, out var error2);
        ok2.Should().BeTrue(error2);
        again.Characters.Count.Should().Be(catalog.Characters.Count);
        again.Characters[0].CharacterId.Should().Be(catalog.Characters[0].CharacterId);
    }

    [Fact]
    public void ShouldRejectCharactersCatalog_WhenCharactersJsonIsMissing()
    {
        var loader = new TestResourceLoader(charactersJson: null, bytes: null);

        var ok = SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("characters_catalog_missing");
    }

    [Fact]
    public void ShouldRejectCharactersCatalog_WhenCharactersJsonIsNotValidJson()
    {
        var loader = new TestResourceLoader(charactersJson: "{", bytes: null);

        var ok = SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().StartWith("json_parse_failed:");
    }

    [Fact]
    public void ShouldRejectCharactersCatalog_WhenSchemaOrVersionIsInvalid()
    {
        var json = BuildCharactersCatalogJson(schemaVersion: 0, version: 0);
        var loader = new TestResourceLoader(json, bytes: new byte[1]);

        var ok = SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_characters_catalog:bad_versions");
    }

    [Fact]
    public void ShouldRejectCharactersCatalog_WhenCharactersCountIsTooSmall()
    {
        var json = BuildCharactersCatalogJson(count: 7);
        var loader = new TestResourceLoader(json, bytes: new byte[1]);

        var ok = SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_characters_catalog:too_few_characters");
    }

    [Fact]
    public void ShouldRejectCharactersCatalog_WhenPortraitExtensionIsNotAllowed()
    {
        var json = BuildCharactersCatalogJson(portraitPath: "res://Assets/portraits/portrait_placeholder.exe");
        var loader = new TestResourceLoader(json, bytes: new byte[1]);

        var ok = SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_characters_catalog:portrait_extension_not_allowed");
    }

    [Fact]
    public void ShouldRejectCharactersCatalog_WhenPortraitBytesAreMissing()
    {
        var json = BuildCharactersCatalogJson(portraitPath: "res://Assets/portraits/portrait_placeholder.svg");
        var loader = new TestResourceLoader(json, bytes: null);

        var ok = SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_characters_catalog:portrait_missing");
    }

    [Fact]
    public void ShouldRejectCharactersCatalog_WhenCombatRatingIsOutOfRange()
    {
        var json = BuildCharactersCatalogJson(combatRating: 101);
        var loader = new TestResourceLoader(json, bytes: new byte[1]);

        var ok = SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_characters_catalog:combat_rating_out_of_range");
    }

    [Fact]
    public void ShouldRejectCharactersCatalog_WhenI18nKeysAreEmpty()
    {
        var json = BuildCharactersCatalogJson(nameKey: "", descriptionKey: "");
        var loader = new TestResourceLoader(json, bytes: new byte[1]);

        var ok = SanguoCharactersCatalogLoader.TryLoadCharactersCatalog(loader, out _, out var error);

        ok.Should().BeFalse();
        error.Should().Be("invalid_characters_catalog:i18n_keys_empty");
    }

    private static string BuildCharactersCatalogJson(
        int schemaVersion = 1,
        int version = 1,
        int count = 8,
        string characterId = "c0",
        bool duplicateIds = false,
        string nameKey = "character.c0.name",
        string descriptionKey = "character.c0.desc",
        int combatRating = 10,
        string portraitPath = "res://Assets/portraits/portrait_placeholder.svg")
    {
        var characters = new List<Dictionary<string, object?>>(capacity: count);
        for (var i = 0; i < count; i++)
        {
            var id = duplicateIds ? characterId : $"{characterId}_{i}";
            characters.Add(new Dictionary<string, object?>
            {
                ["characterId"] = id,
                ["nameKey"] = nameKey == "character.c0.name" ? $"character.{id}.name" : nameKey,
                ["descriptionKey"] = descriptionKey == "character.c0.desc" ? $"character.{id}.desc" : descriptionKey,
                ["combatRating"] = combatRating,
                ["portraitPath"] = portraitPath,
                ["startingMoneyStepDelta"] = 0,
                ["economyStepDeltas"] = new Dictionary<string, object?>
                {
                    ["buyPrice"] = 0,
                    ["toll"] = 0,
                    ["incomeSettlement"] = 0,
                    ["buildCost"] = 0,
                    ["upgradeCost"] = 0,
                },
            });
        }

        var root = new Dictionary<string, object?>
        {
            ["schemaVersion"] = schemaVersion,
            ["version"] = version,
            ["characters"] = characters,
        };

        return JsonSerializer.Serialize(root);
    }

    private sealed class TestResourceLoader(string? charactersJson, byte[]? bytes) : IResourceLoader
    {
        public string? LoadText(string path) => path == SanguoCharactersCatalogLoader.CharactersResPath ? charactersJson : null;

        public byte[]? LoadBytes(string path) => path.StartsWith("res://Assets/", StringComparison.Ordinal) ? bytes : null;
    }

    private sealed class RepoResourceLoader : IResourceLoader
    {
        public string? LoadText(string path)
        {
            if (path == SanguoCharactersCatalogLoader.CharactersResPath)
            {
                var repoRoot = FindRepoRoot();
                return File.ReadAllText(Path.Combine(repoRoot, "Data", "characters.json"));
            }

            return null;
        }

        public byte[]? LoadBytes(string path)
        {
            if (!path.StartsWith("res://", StringComparison.Ordinal))
                return null;

            if (!path.StartsWith("res://Assets/", StringComparison.Ordinal))
                return null;

            var repoRoot = FindRepoRoot();
            var relative = path.Replace("res://", string.Empty, StringComparison.Ordinal)
                .Replace("/", Path.DirectorySeparatorChar.ToString(), StringComparison.Ordinal);
            var filePath = Path.Combine(repoRoot, relative);
            return File.Exists(filePath) ? File.ReadAllBytes(filePath) : null;
        }

        private static string FindRepoRoot()
        {
            var dir = new DirectoryInfo(AppContext.BaseDirectory);
            while (dir is not null)
            {
                var marker = Path.Combine(dir.FullName, ".taskmaster", "tasks", "tasks.json");
                if (File.Exists(marker))
                    return dir.FullName;
                dir = dir.Parent;
            }

            throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks.json).");
        }
    }
}
