using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task1ToolchainVersionChecksTests
{
    [Fact]
    public void ShouldPersistExpectedToolchainAndRestoreContracts_WhenTask1PreflightHasRun()
    {
        if (!Task1PreflightEvidenceGuard.TryGetLatestArtifact(out var artifact, out var reason))
        {
            Task1PreflightEvidenceGuard.EnsureOrSkip(reason);
            return;
        }

        using var document = JsonDocument.Parse(File.ReadAllText(artifact.TaskJsonPath));
        var root = document.RootElement;

        root.GetProperty("godot_version").GetString().Should().Be("4.5.1");

        var sdkVersions = root.GetProperty("dotnet_sdk_versions").EnumerateArray().Select(x => x.GetString() ?? string.Empty).ToArray();
        sdkVersions.Should().NotBeEmpty();
        sdkVersions.Should().Contain(version => version.StartsWith("8.", StringComparison.Ordinal));

        var sdkCheck = root.GetProperty("dotnet_sdk_check");
        sdkCheck.GetProperty("command").GetString().Should().Be("dotnet --list-sdks");
        sdkCheck.GetProperty("has_dotnet8_sdk").GetBoolean().Should().BeTrue();

        var restore = root.GetProperty("dotnet_restore");
        restore.GetProperty("command").GetString().Should().Be(@"dotnet restore .\Game.sln");
        restore.GetProperty("exit_code").GetInt32().Should().Be(0);

        var restoreEvidence = restore.GetProperty("evidence_file").GetString();
        restoreEvidence.Should().NotBeNullOrWhiteSpace();
        File.Exists(Path.Combine(artifact.RepoRoot, restoreEvidence!.Replace('/', Path.DirectorySeparatorChar))).Should().BeTrue();

        var lockFileExists = File.Exists(Path.Combine(artifact.RepoRoot, "packages.lock.json"));
        root.GetProperty("packages_lock_exists").GetBoolean().Should().Be(lockFileExists);
    }
}
