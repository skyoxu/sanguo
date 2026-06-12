using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task211EvidenceResolutionTests
{
    private const int TaskId = 211;
    private const string SelfRef = "Game.Core.Tests/Tasks/Task211EvidenceResolutionTests.cs";

    // ACC:T211.1 ACC:T211.2 ACC:T211.3 ACC:T211.4
    [Fact]
    [Trait("acceptance", "ACC:T211.evidence-resolution")]
    public void ShouldResolveTask211EvidenceRefs_WhenTaskViewAcceptanceIsValidated()
    {
        var repoRoot = FindRepoRoot();
        var task = LoadTask211(repoRoot);
        var acceptance = GetStringArray(task, "acceptance");
        var testRefs = GetStringArray(task, "test_refs").ToHashSet(StringComparer.Ordinal);

        acceptance.Should().HaveCount(8);
        acceptance.Should().OnlyContain(item => item.Contains("Refs:", StringComparison.Ordinal));
        testRefs.Should().Contain(SelfRef);

        var refsByAcceptance = acceptance.Select(ExtractRefs).ToArray();
        refsByAcceptance.Should().OnlyContain(refs => refs.Contains(SelfRef, StringComparer.Ordinal));

        foreach (var refs in refsByAcceptance.SelectMany(refs => refs).Distinct(StringComparer.Ordinal))
        {
            testRefs.Should().Contain(refs, "acceptance refs must be declared in test_refs");
            File.Exists(Path.Combine(repoRoot, refs.Replace('/', Path.DirectorySeparatorChar)))
                .Should()
                .BeTrue($"referenced evidence path should exist: {refs}");
        }
    }

    // ACC:T211.5 ACC:T211.6 ACC:T211.7 ACC:T211.8
    [Fact]
    [Trait("acceptance", "ACC:T211.stable-validation-output")]
    public void ShouldKeepTask211ValidationEvidenceStable_WhenTaskViewInputsAreUnchanged()
    {
        var task = LoadTask211(FindRepoRoot());
        var acceptance = GetStringArray(task, "acceptance");
        var refsByAcceptance = acceptance.Select(ExtractRefs).ToArray();

        acceptance[4].Should().Contain("[OBL:T211.O4]");
        acceptance[5].Should().Contain("[OBL:T211.O4]");
        acceptance[6].Should().Contain("[OBL:T211.O5]");
        acceptance[7].Should().Contain("[OBL:T211.O5]");

        refsByAcceptance[4].Should().Equal(refsByAcceptance[5], "stable-output obligations should use the same evidence set");
        refsByAcceptance[6].Should().Equal(refsByAcceptance[7], "triplet-validator obligations should use the same evidence set");
        acceptance[6].Should().Contain("Chapter 3.8");
        acceptance[7].Should().Contain("Chapter 3.8");
    }

    // ACC:T211.3 ACC:T211.4
    [Fact]
    [Trait("acceptance", "ACC:T211.negative-evidence-validation")]
    public void ShouldRejectInvalidTask211EvidenceRefs_WhenValidatorChecksNegativeFixtures()
    {
        var repoRoot = FindRepoRoot();
        var script = """
from pathlib import Path
from scripts.python.validate_acceptance_refs import validate_view

root = Path.cwd()
valid_ref = "Game.Core.Tests/Tasks/Task211EvidenceResolutionTests.cs"
missing_ref = "Game.Core.Tests/Tasks/Task211MissingEvidenceTests.cs"
unrelated_ref = "scripts/python/validate_acceptance_refs.py"
undeclared_ref = "Game.Core.Tests/Tasks/Task47QualityGatesGdUnitAggregationTests.cs"

cases = [
    (
        "missing",
        {"acceptance": [f"Missing evidence fails. Refs: {missing_ref}"], "test_refs": [missing_ref]},
        "referenced file not found on disk",
    ),
    (
        "undeclared",
        {"acceptance": [f"Undeclared evidence fails. Refs: {undeclared_ref}"], "test_refs": [valid_ref]},
        "ref must be included in test_refs",
    ),
    (
        "unrelated",
        {"acceptance": [f"Unrelated evidence fails. Refs: {unrelated_ref}"], "test_refs": [unrelated_ref]},
        "ref is not an allowed test path",
    ),
]

for name, entry, expected in cases:
    report = validate_view(root=root, label=name, entry=entry, stage="refactor")
    errors = " | ".join(report.get("errors", []))
    if report.get("status") != "fail" or expected not in errors:
        raise SystemExit(f"{name} did not fail with {expected}: {report}")

print("negative-fixtures-ok")
""";

        RunPython(repoRoot, script).Should().Contain("negative-fixtures-ok");
    }

    // ACC:T211.5 ACC:T211.6
    [Fact]
    [Trait("acceptance", "ACC:T211.stable-validator-output")]
    public void ShouldProduceStableTask211ValidationOutput_WhenValidatorRunsTwiceOnSameInput()
    {
        var repoRoot = FindRepoRoot();
        var script = """
import json
from pathlib import Path
from scripts.python.validate_acceptance_refs import validate_view

root = Path.cwd()
tasks = json.loads((root / ".taskmaster" / "tasks" / "tasks_gameplay.json").read_text(encoding="utf-8"))
entry = next(item for item in tasks if item.get("taskmaster_id") == 211)

first = validate_view(root=root, label="tasks_gameplay.json", entry=entry, stage="refactor")
second = validate_view(root=root, label="tasks_gameplay.json", entry=entry, stage="refactor")

first_json = json.dumps(first, sort_keys=True, ensure_ascii=False)
second_json = json.dumps(second, sort_keys=True, ensure_ascii=False)
if first.get("status") != "ok":
    raise SystemExit(f"first validation failed: {first}")
if first_json != second_json:
    raise SystemExit("validator output changed across identical runs")

print("stable-validator-output-ok")
""";

        RunPython(repoRoot, script).Should().Contain("stable-validator-output-ok");
    }

    private static JsonElement LoadTask211(string repoRoot)
    {
        var path = Path.Combine(repoRoot, ".taskmaster", "tasks", "tasks_gameplay.json");
        using var document = JsonDocument.Parse(File.ReadAllText(path));

        foreach (var item in document.RootElement.EnumerateArray())
        {
            if (item.TryGetProperty("taskmaster_id", out var id) && id.GetInt32() == TaskId)
            {
                return item.Clone();
            }
        }

        throw new InvalidOperationException("Task 211 was not found in tasks_gameplay.json.");
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(Directory.GetCurrentDirectory());
        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, ".taskmaster", "tasks", "tasks_gameplay.json");
            if (File.Exists(candidate))
            {
                return dir.FullName;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Repository root with .taskmaster/tasks/tasks_gameplay.json was not found.");
    }

    private static string[] GetStringArray(JsonElement task, string propertyName)
    {
        task.TryGetProperty(propertyName, out var property).Should().BeTrue();
        property.ValueKind.Should().Be(JsonValueKind.Array);
        return property.EnumerateArray().Select(item => item.GetString() ?? string.Empty).ToArray();
    }

    private static string[] ExtractRefs(string acceptance)
    {
        return acceptance
            .Split("Refs:", 2, StringSplitOptions.None)
            .Skip(1)
            .SelectMany(rest => rest.Split(' ', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
            .Where(path => path.Contains('/', StringComparison.Ordinal) || path.Contains('\\', StringComparison.Ordinal))
            .ToArray();
    }

    private static string RunPython(string repoRoot, string script)
    {
        var psi = new ProcessStartInfo
        {
            FileName = "py",
            WorkingDirectory = repoRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        psi.ArgumentList.Add("-3");
        psi.ArgumentList.Add("-c");
        psi.ArgumentList.Add(script);

        using var process = Process.Start(psi) ?? throw new InvalidOperationException("Failed to start Python.");
        var stdout = process.StandardOutput.ReadToEnd();
        var stderr = process.StandardError.ReadToEnd();
        process.WaitForExit();

        process.ExitCode.Should().Be(0, $"python validator failed. stdout: {stdout} stderr: {stderr}");
        return stdout;
    }
}
