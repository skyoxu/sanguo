using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task197CoverageAuditTests
{
    private const int TaskId = 197;
    private static readonly string[] ExpectedRequirementIds =
    [
        "REQ-a9f4f7d10132",
        "REQ-558e8baa8185",
        "REQ-cd5f9ab87ab3",
        "REQ-2b5f52cddf88",
    ];

    private static readonly string[] ExpectedSourceRefs =
    [
        "docs/gdd/ui-gdd-flow.cn.md:302",
        "docs/gdd/ui-gdd-flow.cn.md:308",
        "docs/gdd/ui-gdd-flow.cn.md:364",
        "docs/gdd/ui-gdd-flow.cn.md:375",
    ];

    // ACC:T197.1
    // ACC:T197.2
    // ACC:T197.3
    // ACC:T197.4
    [Fact]
    public void ShouldKeepTask197RequirementMappingsTraceable_WhenGameplayTaskIsLoaded()
    {
        var task = LoadGameplayTask();
        var acceptance = GetStringArray(task, "acceptance");
        var sourceRefs = GetStringArray(task, "source_refs");
        var requirementIds = GetStringArray(task, "requirement_ids");

        requirementIds.Should().Contain(ExpectedRequirementIds);
        sourceRefs.Should().Contain(ExpectedSourceRefs);

        foreach (var requirementId in ExpectedRequirementIds)
        {
            acceptance.Should().Contain(item => item.Contains(requirementId, StringComparison.Ordinal)
                && item.Contains("Refs:", StringComparison.Ordinal));
        }
    }

    // ACC:T197.14
    // ACC:T197.15
    [Fact]
    public void ShouldPreserveDeterministicCoreBoundary_WhenTask197IsLoaded()
    {
        var coreAssembly = typeof(Game.Core.Services.SanguoTurnManager).Assembly;
        var references = coreAssembly
            .GetReferencedAssemblies()
            .Select(assembly => assembly.Name ?? string.Empty)
            .ToArray();

        references.Should().NotContain(name => name.StartsWith("Godot", StringComparison.OrdinalIgnoreCase));

        var acceptance = GetStringArray(LoadGameplayTask(), "acceptance");
        acceptance.Should().Contain(item => item.Contains("[OBL:T197.O10]", StringComparison.Ordinal)
            && item.Contains("Refs:", StringComparison.Ordinal));
    }

    // ACC:T197.16
    // ACC:T197.17
    [Fact]
    public void ShouldRecordChapter3CoverageAuditEvidence_WhenTask197IsLoaded()
    {
        var acceptance = GetStringArray(LoadGameplayTask(), "acceptance");

        acceptance.Should().Contain(item => item.Contains("[OBL:T197.O11]", StringComparison.Ordinal)
            && item.Contains("Chapter 3 coverage audit", StringComparison.Ordinal)
            && item.Contains("Refs:", StringComparison.Ordinal));
    }

    // ACC:T197.18
    // ACC:T197.19
    [Fact]
    public void ShouldRecordChapter38TripletValidatorEvidence_WhenTask197IsLoaded()
    {
        var task = LoadGameplayTask();
        var acceptance = GetStringArray(task, "acceptance");
        var overlayRefs = GetStringArray(task, "overlay_refs");

        overlayRefs.Should().Contain("docs/architecture/overlays/PRD-SANGUO-V4/08/_index.md");
        acceptance.Should().Contain(item => item.Contains("[OBL:T197.O12]", StringComparison.Ordinal)
            && item.Contains("Chapter 3.8 triplet baseline validators", StringComparison.Ordinal)
            && item.Contains("Refs:", StringComparison.Ordinal));
    }

    private static JsonElement LoadGameplayTask()
    {
        var path = Path.Combine(FindRepoRoot(), ".taskmaster", "tasks", "tasks_gameplay.json");
        using var document = JsonDocument.Parse(File.ReadAllText(path));

        foreach (var task in document.RootElement.EnumerateArray())
        {
            if (task.TryGetProperty("taskmaster_id", out var id) && id.GetInt32() == TaskId)
            {
                return task.Clone();
            }
        }

        throw new InvalidOperationException("Task 197 was not found in tasks_gameplay.json.");
    }

    private static string FindRepoRoot()
    {
        var current = new DirectoryInfo(Directory.GetCurrentDirectory());
        while (current is not null)
        {
            if (Directory.Exists(Path.Combine(current.FullName, ".taskmaster")))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        throw new DirectoryNotFoundException("Unable to locate repository root containing .taskmaster.");
    }

    private static string[] GetStringArray(JsonElement task, string propertyName)
    {
        task.TryGetProperty(propertyName, out var property).Should().BeTrue();
        property.ValueKind.Should().Be(JsonValueKind.Array);
        return property.EnumerateArray().Select(item => item.GetString() ?? string.Empty).ToArray();
    }
}
