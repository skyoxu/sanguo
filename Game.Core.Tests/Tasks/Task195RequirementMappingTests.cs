using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task195RequirementMappingTests
{
    private static readonly string[] ExpectedRequirementIds =
    [
        "REQ-5bccd55885c2",
        "REQ-ead8b3e06504",
        "REQ-a6c275967f91",
        "REQ-2afa270c7b7e",
    ];

    private static readonly string[] ExpectedSourceRefs =
    [
        "docs/gdd/ui-gdd-flow.md:480",
        "docs/gdd/ui-gdd-flow.md:487",
        "docs/gdd/ui-gdd-flow.md:488",
        "docs/gdd/ui-gdd-flow.md:498",
    ];

    private static readonly string[] ExpectedTestRefs =
    [
        "Tests.Godot/tests/Adapters/Config/test_audio_player_adapter_nodes.gd",
        "Tests.Godot/tests/Adapters/test_data_store_adapter.gd",
        "Tests.Godot/tests/Adapters/test_event_bus_adapter.gd",
        "Tests.Godot/tests/Adapters/test_input_time_adapter.gd",
        "Tests.Godot/tests/Adapters/test_resource_loader_adapter.gd",
        "Tests.Godot/tests/UI/A11y/test_visible_labels.gd",
        "Game.Core.Tests/Tasks/Task195RequirementMappingTests.cs",
    ];

    // ACC:T195.1
    // ACC:T195.2
    // ACC:T195.3
    // ACC:T195.4
    // ACC:T195.5
    [Fact]
    public void ShouldRecordVisibleRequirementMappings_WhenTask195IsLoaded()
    {
        var task = LoadTask195();

        GetStringArray(task, "requirement_ids").Should().Equal(ExpectedRequirementIds);
        GetStringArray(task, "source_refs").Should().Equal(ExpectedSourceRefs);
        GetStringArray(task, "adr_refs").Should().Contain(["ADR-0007", "ADR-0024"]);
        GetStringArray(task, "chapter_refs").Should().Contain(["CH01", "CH05", "CH06", "CH07"]);
        GetStringArray(task, "overlay_refs").Should().Contain("docs/architecture/overlays/PRD-SANGUO-V4/08/_index.md");

        var acceptance = GetStringArray(task, "acceptance");
        for (var i = 0; i < ExpectedRequirementIds.Length; i++)
        {
            acceptance[i].Should().Contain(ExpectedRequirementIds[i]);
            acceptance[i].Should().Contain(ExpectedSourceRefs[i]);
            acceptance[i].Should().Contain("Refs:");
        }
    }

    // ACC:T195.6
    // ACC:T195.7
    // ACC:T195.8
    // ACC:T195.9
    // ACC:T195.10
    [Fact]
    public void ShouldRejectInvalidRequirementMappings_WhenMappingIsMutated()
    {
        ValidateRequirementMapping(ExpectedRequirementIds, ExpectedSourceRefs).Should().BeEmpty();

        ValidateRequirementMapping(ExpectedRequirementIds.Skip(1), ExpectedSourceRefs)
            .Should().Contain("missing-requirement");

        ValidateRequirementMapping(ExpectedRequirementIds.Concat([ExpectedRequirementIds[0]]), ExpectedSourceRefs)
            .Should().Contain("duplicate-requirement");

        ValidateRequirementMapping(ExpectedRequirementIds, ExpectedSourceRefs.Select((value, index) => index == 0 ? "docs/gdd/ui-gdd-flow.md:999" : value))
            .Should().Contain("untraceable-source");
    }

    // ACC:T195.11
    // ACC:T195.12
    // ACC:T195.13
    // ACC:T195.14
    // ACC:T195.15
    [Fact]
    public void ShouldPreserveCoreBoundaryAndChapterAuditEvidence_WhenTask195IsLoaded()
    {
        var acceptance = GetStringArray(LoadTask195(), "acceptance");

        acceptance.Should().Contain(item => item.Contains("[OBL:T195.O10]", StringComparison.Ordinal)
            && item.Contains("Game.Core.Tests/Utilities/NoGodotDependencyTests.cs", StringComparison.Ordinal));
        acceptance.Should().Contain(item => item.Contains("[OBL:T195.O11]", StringComparison.Ordinal)
            && item.Contains("Chapter 3 coverage audit", StringComparison.Ordinal)
            && item.Contains("Refs:", StringComparison.Ordinal));
        acceptance.Should().Contain(item => item.Contains("[OBL:T195.O12]", StringComparison.Ordinal)
            && item.Contains("Chapter 3.8 triplet baseline validators", StringComparison.Ordinal)
            && item.Contains("Refs:", StringComparison.Ordinal));
    }

    // ACC:T195.16
    // ACC:T195.17
    // ACC:T195.18
    [Fact]
    public void ShouldPreserveFullAdapterTestRefs_WhenTask195IsLoaded()
    {
        var task = LoadTask195();

        GetStringArray(task, "test_refs").Should().Contain(ExpectedTestRefs);
        GetStringArray(task, "acceptance").Should().Contain(item => item.Contains("[OBL:T195.O13]", StringComparison.Ordinal)
            && ExpectedTestRefs.Take(6).All(item.Contains));
    }

    private static JsonElement LoadTask195()
    {
        var repoRoot = FindRepoRoot();
        var jsonPath = Path.Combine(repoRoot, ".taskmaster", "tasks", "tasks_gameplay.json");
        using var document = JsonDocument.Parse(File.ReadAllText(jsonPath));

        foreach (var task in document.RootElement.EnumerateArray())
        {
            if (task.TryGetProperty("taskmaster_id", out var id) && id.GetInt32() == 195)
            {
                return task.Clone();
            }
        }

        throw new InvalidOperationException("Task 195 was not found in tasks_gameplay.json.");
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

    private static IReadOnlyList<string> ValidateRequirementMapping(IEnumerable<string> requirementIds, IEnumerable<string> sourceRefs)
    {
        var errors = new List<string>();
        var reqs = requirementIds.ToArray();
        var sources = sourceRefs.ToArray();

        if (!ExpectedRequirementIds.All(reqs.Contains))
        {
            errors.Add("missing-requirement");
        }

        if (reqs.Length != reqs.Distinct(StringComparer.Ordinal).Count())
        {
            errors.Add("duplicate-requirement");
        }

        if (!sources.SequenceEqual(ExpectedSourceRefs))
        {
            errors.Add("untraceable-source");
        }

        return errors;
    }
}
