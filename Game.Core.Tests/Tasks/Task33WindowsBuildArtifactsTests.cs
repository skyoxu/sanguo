using System;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task33WindowsBuildArtifactsTests
{
    private static readonly string[] VersionKeys = { "version", "appVersion", "buildVersion" };
    private static readonly string[] ChannelKeys = { "channel", "releaseChannel" };
    private static readonly string[] BuildTimeKeys = { "buildTimeUtc", "buildTime", "builtAt" };
    private static readonly string[] CommitShaKeys = { "commitSha", "gitSha", "gitCommit" };

    private static readonly Regex CommitShaPattern = new("^[0-9a-fA-F]{7,40}$", RegexOptions.Compiled);

    // ACC:T33.1
    [Fact]
    public void ShouldProvideStableArtifactFileNames_WhenScaffoldingWindowsBuildArtifactsContract()
    {
        var jsonArtifacts = new[]
        {
            "build/build-info.json",
            "build/release-profile.json",
        };

        var sha256Artifacts = jsonArtifacts.Select(Sha256For).ToArray();

        jsonArtifacts.Should().AllSatisfy(p => p.Should().StartWith("build/").And.EndWith(".json"));
        sha256Artifacts.Should().AllSatisfy(p => p.Should().StartWith("build/").And.EndWith(".sha256"));
        Sha256For("build/build-info.json").Should().Be("build/build-info.json.sha256");
    }

    // ACC:T33.1
    // ACC:T33.7
    [Fact]
    public void ShouldGenerateBuildMetadataAndSha256_WhenRunningMetadataCommandInIsolatedRepoRoot()
    {
        var root = new DirectoryInfo(AppContext.BaseDirectory);
        while (root is not null && !File.Exists(Path.Combine(root.FullName, ".taskmaster", "tasks", "tasks.json")))
            root = root.Parent;

        root.Should().NotBeNull("repo root should be discoverable from the test base directory");

        var tempRoot = Path.Combine(Path.GetTempPath(), "sanguo-task33-meta-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(tempRoot);

        try
        {
            var scriptPath = Path.Combine(root!.FullName, "scripts", "python", "build_windows.py");
            File.Exists(scriptPath).Should().BeTrue("build_windows.py must exist for Task 33");

            var python = OperatingSystem.IsWindows() ? "py" : "python3";
            var args = OperatingSystem.IsWindows()
                ? new[] { "-3", scriptPath, "metadata", "--repo-root", tempRoot, "--version", "0.0.0", "--channel", "dev" }
                : new[] { scriptPath, "metadata", "--repo-root", tempRoot, "--version", "0.0.0", "--channel", "dev" };

            var psi = new System.Diagnostics.ProcessStartInfo
            {
                FileName = python,
                WorkingDirectory = root.FullName,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
                StandardOutputEncoding = new UTF8Encoding(false),
                StandardErrorEncoding = new UTF8Encoding(false),
            };

            foreach (var a in args)
                psi.ArgumentList.Add(a);

            psi.Environment["PYTHONIOENCODING"] = "utf-8";
            psi.Environment["PYTHONUTF8"] = "1";

            using var proc = System.Diagnostics.Process.Start(psi);
            proc.Should().NotBeNull("Python must be runnable in test environment");

            var stdout = proc!.StandardOutput.ReadToEnd();
            var stderr = proc.StandardError.ReadToEnd();
            proc.WaitForExit(30_000).Should().BeTrue($"metadata command must exit quickly. stdout={stdout} stderr={stderr}");
            proc.ExitCode.Should().Be(0, $"metadata command must succeed. stdout={stdout} stderr={stderr}");

            var buildInfo = Path.Combine(tempRoot, "build", "build-info.json");
            var releaseProfile = Path.Combine(tempRoot, "build", "release-profile.json");
            File.Exists(buildInfo).Should().BeTrue("build-info.json must be created under build/");
            File.Exists(releaseProfile).Should().BeTrue("release-profile.json must be created under build/");

            var buildInfoSha = buildInfo + ".sha256";
            var releaseProfileSha = releaseProfile + ".sha256";
            File.Exists(buildInfoSha).Should().BeTrue("build-info.json.sha256 must be created");
            File.Exists(releaseProfileSha).Should().BeTrue("release-profile.json.sha256 must be created");

            VerifySha256File(buildInfo);
            VerifySha256File(releaseProfile);

            var buildInfoJson = File.ReadAllText(buildInfo, Encoding.UTF8);
            var releaseProfileJson = File.ReadAllText(releaseProfile, Encoding.UTF8);

            var parsedBuildInfo = ParseBuildMetadata(buildInfoJson, "build-info.json");
            var parsedReleaseProfile = ParseBuildMetadata(releaseProfileJson, "release-profile.json");

            parsedBuildInfo.Version.Should().Be("0.0.0");
            parsedBuildInfo.Channel.Should().Be("dev");
            CommitShaPattern.IsMatch(parsedBuildInfo.CommitSha).Should().BeTrue();

            parsedReleaseProfile.Version.Should().Be(parsedBuildInfo.Version);
            parsedReleaseProfile.Channel.Should().Be(parsedBuildInfo.Channel);
            parsedReleaseProfile.BuildTimeUtc.Should().Be(parsedBuildInfo.BuildTimeUtc);
            parsedReleaseProfile.CommitSha.Should().Be(parsedBuildInfo.CommitSha);
        }
        finally
        {
            try
            {
                if (Directory.Exists(tempRoot))
                    Directory.Delete(tempRoot, recursive: true);
            }
            catch
            {
                // Best-effort cleanup.
            }
        }
    }

    // ACC:T33.7
    [Fact]
    public void ShouldParseBuildMetadataFields_WhenValidatingSampleBuildInfoAndReleaseProfileJson()
    {
        var buildInfoJson = JsonSerializer.Serialize(new
        {
            version = "0.0.0",
            channel = "dev",
            buildTimeUtc = "2025-01-01T00:00:00Z",
            commitSha = "abcdef1234567",
        });

        var releaseProfileJson = JsonSerializer.Serialize(new
        {
            version = "0.0.0",
            channel = "dev",
            buildTimeUtc = "2025-01-01T00:00:00Z",
            commitSha = "abcdef1234567",
        });

        var buildInfo = ParseBuildMetadata(buildInfoJson, "build-info.json");
        var releaseProfile = ParseBuildMetadata(releaseProfileJson, "release-profile.json");

        buildInfo.Version.Should().NotBeNullOrWhiteSpace();
        buildInfo.Channel.Should().NotBeNullOrWhiteSpace();
        buildInfo.BuildTimeUtc.Year.Should().BeGreaterThanOrEqualTo(2000);
        CommitShaPattern.IsMatch(buildInfo.CommitSha).Should().BeTrue();

        releaseProfile.Version.Should().Be(buildInfo.Version);
        releaseProfile.Channel.Should().Be(buildInfo.Channel);
        releaseProfile.BuildTimeUtc.Should().Be(buildInfo.BuildTimeUtc);
        releaseProfile.CommitSha.Should().Be(buildInfo.CommitSha);
    }

    private static string Sha256For(string artifactPath) => artifactPath + ".sha256";

    private sealed record BuildMetadata(string Version, string Channel, DateTimeOffset BuildTimeUtc, string CommitSha);

    private static void VerifySha256File(string targetFile)
    {
        var shaPath = targetFile + ".sha256";
        var content = File.ReadAllText(shaPath, Encoding.UTF8);
        content.Should().NotBeNullOrWhiteSpace("sha256 file must not be empty");

        var parts = content.Trim().Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
        parts.Should().HaveCountGreaterThanOrEqualTo(1);
        var expectedHex = parts[0];

        using var sha = SHA256.Create();
        var bytes = File.ReadAllBytes(targetFile);
        var actualHex = Convert.ToHexString(sha.ComputeHash(bytes)).ToLowerInvariant();
        expectedHex.ToLowerInvariant().Should().Be(actualHex, $"sha256 must match {Path.GetFileName(targetFile)}");
    }

    private static BuildMetadata ParseBuildMetadata(string json, string documentName)
    {
        using var doc = JsonDocument.Parse(json);
        doc.RootElement.ValueKind.Should().Be(JsonValueKind.Object, $"{documentName} must be a JSON object");

        var root = doc.RootElement;
        var version = GetRequiredNonEmptyString(root, VersionKeys, documentName);
        var channel = GetRequiredNonEmptyString(root, ChannelKeys, documentName);
        var buildTimeUtc = GetRequiredDateTimeOffset(root, BuildTimeKeys, documentName);
        var commitSha = GetRequiredCommitSha(root, CommitShaKeys, documentName);

        return new BuildMetadata(version, channel, buildTimeUtc, commitSha);
    }

    private static string GetRequiredNonEmptyString(JsonElement root, string[] keys, string documentName)
    {
        foreach (var key in keys)
        {
            if (!TryGetPropertyIgnoreCase(root, key, out var value))
            {
                continue;
            }

            value.ValueKind.Should().Be(JsonValueKind.String, $"{documentName} field '{key}' must be a string");
            var str = value.GetString();
            str.Should().NotBeNullOrWhiteSpace($"{documentName} field '{key}' must not be empty");
            return str!;
        }

        var keyList = string.Join(", ", keys.Select(k => "'" + k + "'"));
        false.Should().BeTrue($"{documentName} must contain one of: {keyList}");
        return string.Empty;
    }

    private static DateTimeOffset GetRequiredDateTimeOffset(JsonElement root, string[] keys, string documentName)
    {
        var raw = GetRequiredNonEmptyString(root, keys, documentName);
        var ok = DateTimeOffset.TryParse(
            raw,
            CultureInfo.InvariantCulture,
            DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
            out var dto);

        ok.Should().BeTrue($"{documentName} build time must be parseable as DateTimeOffset");
        return dto;
    }

    private static string GetRequiredCommitSha(JsonElement root, string[] keys, string documentName)
    {
        var sha = GetRequiredNonEmptyString(root, keys, documentName);
        CommitShaPattern.IsMatch(sha).Should().BeTrue($"{documentName} commit SHA must look like a git SHA");
        return sha;
    }

    private static bool TryGetPropertyIgnoreCase(JsonElement root, string name, out JsonElement value)
    {
        foreach (var prop in root.EnumerateObject())
        {
            if (string.Equals(prop.Name, name, StringComparison.OrdinalIgnoreCase))
            {
                value = prop.Value;
                return true;
            }
        }

        value = default;
        return false;
    }
}
