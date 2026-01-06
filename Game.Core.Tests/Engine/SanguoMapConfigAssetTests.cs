using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using Xunit;

namespace Game.Core.Tests.Engine;

public sealed class SanguoMapConfigAssetTests
{
    [Fact]
    public void ShouldLoadAndValidate_DefaultMapJson_AsUtf8()
    {
        var repoRoot = FindRepoRoot();

        var runtimePath = Path.Combine(repoRoot, "Game.Godot", "Assets", "Config", "Sanguo", "map-default.json");
        var testProjectPath = Path.Combine(repoRoot, "Tests.Godot", "Game.Godot", "Assets", "Config", "Sanguo", "map-default.json");

        ValidateMapJson(runtimePath);
        ValidateMapJson(testProjectPath);
    }

    private static void ValidateMapJson(string fullPath)
    {
        File.Exists(fullPath).Should().BeTrue($"map json must exist: {fullPath}");

        var utf8Strict = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true);
        var bytes = File.ReadAllBytes(fullPath);
        var json = utf8Strict.GetString(bytes);

        var options = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            ReadCommentHandling = JsonCommentHandling.Skip,
            AllowTrailingCommas = true,
            MaxDepth = 64,
        };

        var map = JsonSerializer.Deserialize<SanguoMapDefinition>(json, options);
        SanguoMapDefinitionValidator.TryValidate(map, out var errors).Should().BeTrue(string.Join(" | ", errors));
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var tm = Path.Combine(dir.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(tm))
                return dir.FullName;
            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks.json).");
    }
}

