using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task1EnvironmentEvidencePersistenceTests
{
    private static readonly string[] RequiredEvidenceFiles =
    {
        "godot-bin-env.txt",
        "godot-version.txt",
        "godot-bin-version.txt",
        "dotnet-version.txt",
        "dotnet-sdks.txt",
        "dotnet-restore.txt",
        "packages-lock-exists.txt",
        "windows-only-check.txt",
        "utf8-check.txt",
    };

    private const string ChecklistRelativePath = "docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md";

    // ACC:T206.5
    [Fact]
    public void ShouldPersistExpectedEvidenceFilesAndTaskJson_WhenTask1PreflightHasRun()
    {
        if (!Task1PreflightEvidenceGuard.TryGetLatestArtifact(out var artifact, out var reason))
        {
            Task1PreflightEvidenceGuard.EnsureOrSkip(reason);
            return;
        }

        using var document = JsonDocument.Parse(File.ReadAllText(artifact.TaskJsonPath));
        var root = document.RootElement;

        root.GetProperty("evidence_paths").EnumerateArray()
            .Select(x => x.GetString())
            .Should()
            .Contain(path => !string.IsNullOrWhiteSpace(path) && path.EndsWith("env-evidence/utf8-check.txt", StringComparison.OrdinalIgnoreCase));

        foreach (var fileName in RequiredEvidenceFiles)
        {
            File.Exists(Path.Combine(artifact.EvidenceDirectory, fileName))
                .Should()
                .BeTrue($"required evidence file should exist: {fileName}");
        }

        var evidencePaths = root.GetProperty("evidence_paths").EnumerateArray().Select(x => x.GetString() ?? string.Empty).ToArray();
        evidencePaths.Should().HaveCount(RequiredEvidenceFiles.Length);
        foreach (var relPath in evidencePaths)
        {
            File.Exists(Path.Combine(artifact.RepoRoot, relPath.Replace('/', Path.DirectorySeparatorChar)))
                .Should()
                .BeTrue($"machine-readable evidence path should exist: {relPath}");
        }

        root.GetProperty("godot_bin").GetString().Should().NotBeNullOrWhiteSpace();
        File.Exists(root.GetProperty("godot_bin").GetString()!).Should().BeTrue();

        var utf8CheckedFiles = root.GetProperty("utf8_check").GetProperty("checked_files").EnumerateArray().Select(x => x.GetString()).ToArray();
        utf8CheckedFiles.Should().Contain(ChecklistRelativePath);
        File.Exists(Path.Combine(artifact.RepoRoot, ChecklistRelativePath.Replace('/', Path.DirectorySeparatorChar))).Should().BeTrue();

        var adrRefs = root.GetProperty("adr_refs").EnumerateArray().Select(x => x.GetString()).ToArray();
        adrRefs.Should().Contain(new[] { "ADR-0005", "ADR-0011", "ADR-0018" });
    }
}
