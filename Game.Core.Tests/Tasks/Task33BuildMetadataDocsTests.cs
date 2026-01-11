#nullable enable

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks
{
    public sealed class Task33BuildMetadataDocsTests
    {
        private static readonly string[] ArtifactPaths =
        {
            "build/build-info.json",
            "build/release-profile.json",
        };

        [Fact]
        public void ShouldHaveStableArtifactPaths_WhenValidated()
        {
            ArtifactPaths.Should().Equal(new[]
            {
                "build/build-info.json",
                "build/release-profile.json",
            });

            ArtifactPaths.Should().OnlyContain(p => !string.IsNullOrWhiteSpace(p));
            ArtifactPaths.Should().OnlyContain(p => p.StartsWith("build/", StringComparison.Ordinal));
            ArtifactPaths.Should().OnlyContain(p => p.EndsWith(".json", StringComparison.Ordinal));
            ArtifactPaths.Should().OnlyContain(p => !p.Contains('\\'));
        }

        // ACC:T33.3
        [Fact]
        public void ShouldFindDocumentationThatReferencesBuildMetadataArtifacts_WhenDocsArePresent()
        {
            var repoRoot = TryFindRepoRoot(AppContext.BaseDirectory);
            repoRoot.Should().NotBeNull("repo root should be discoverable from the test base directory");

            var candidateFiles = EnumerateCandidateDocs(repoRoot!).ToList();
            candidateFiles.Should().NotBeEmpty("docs should exist to reference build metadata artifacts");

            var (matches, readErrors) = ScanForDocumentationMatches(candidateFiles);
            matches.Should().NotBeEmpty(
                "at least one documentation file should mention both build metadata artifacts; readErrors={0}",
                readErrors.Count > 0 ? readErrors[0] : "none");

            var content = File.ReadAllText(matches[0], Encoding.UTF8);

            content.Should().Contain("build/build-info.json");
            content.Should().Contain("build/release-profile.json");

            var hasAnyMetadataHint =
                ContainsOrdinalIgnoreCase(content, "version")
                || ContainsOrdinalIgnoreCase(content, "channel")
                || ContainsOrdinalIgnoreCase(content, "commit")
                || ContainsOrdinalIgnoreCase(content, "sha")
                || ContainsOrdinalIgnoreCase(content, "timestamp")
                || ContainsOrdinalIgnoreCase(content, "time")
                || ContainsOrdinalIgnoreCase(content, "utc")
                || ContainsOrdinalIgnoreCase(content, "build");

            hasAnyMetadataHint.Should().BeTrue();
        }

        private static DirectoryInfo? TryFindRepoRoot(string startDirectory)
        {
            var current = new DirectoryInfo(startDirectory);

            for (var i = 0; i < 12 && current.Exists; i++)
            {
                var projectGodot = Path.Combine(current.FullName, "project.godot");
                var agents = Path.Combine(current.FullName, "AGENTS.md");

                if (File.Exists(projectGodot) || File.Exists(agents))
                {
                    return current;
                }

                if (current.Parent is null)
                {
                    break;
                }

                current = current.Parent;
            }

            return null;
        }

        private static IEnumerable<string> EnumerateCandidateDocs(DirectoryInfo repoRoot)
        {
            var rootCandidates = new[]
            {
                "README.md",
                "README.txt",
                "CHANGELOG.md",
                "CHANGELOG.txt",
                "RELEASE_NOTES.md",
                "RELEASE_NOTES.txt",
                "RELEASENOTES.md",
                "RELEASENOTES.txt",
            };

            foreach (var name in rootCandidates)
            {
                var path = Path.Combine(repoRoot.FullName, name);
                if (File.Exists(path))
                {
                    yield return path;
                }
            }

            foreach (var dirName in new[] { "docs", ".github" })
            {
                var dirPath = Path.Combine(repoRoot.FullName, dirName);
                if (!Directory.Exists(dirPath))
                {
                    continue;
                }

                foreach (var file in EnumerateFilesSafe(dirPath))
                {
                    var ext = Path.GetExtension(file);
                    if (!IsTextDocExtension(ext))
                    {
                        continue;
                    }

                    yield return file;
                }
            }
        }

        private static IEnumerable<string> EnumerateFilesSafe(string rootDirectory)
        {
            var stack = new Stack<string>();
            stack.Push(rootDirectory);

            while (stack.Count > 0)
            {
                var current = stack.Pop();

                IEnumerable<string> subDirs;
                try
                {
                    subDirs = Directory.EnumerateDirectories(current);
                }
                catch
                {
                    continue;
                }

                foreach (var dir in subDirs)
                {
                    var name = Path.GetFileName(dir);
                    if (ShouldSkipDirectory(name))
                    {
                        continue;
                    }

                    stack.Push(dir);
                }

                IEnumerable<string> files;
                try
                {
                    files = Directory.EnumerateFiles(current);
                }
                catch
                {
                    continue;
                }

                foreach (var file in files)
                {
                    yield return file;
                }
            }
        }

        private static (List<string> Matches, List<string> ReadErrors) ScanForDocumentationMatches(IReadOnlyList<string> files)
        {
            var matches = new List<string>();
            var readErrors = new List<string>();

            foreach (var file in files)
            {
                string content;
                try
                {
                    content = File.ReadAllText(file, Encoding.UTF8);
                }
                catch (Exception ex)
                {
                    readErrors.Add($"{file}: {ex.GetType().Name}");
                    continue;
                }

                if (content.Contains(ArtifactPaths[0], StringComparison.Ordinal)
                    && content.Contains(ArtifactPaths[1], StringComparison.Ordinal))
                {
                    matches.Add(file);
                    break;
                }
            }

            return (matches, readErrors);
        }

        private static bool ContainsOrdinalIgnoreCase(string haystack, string needle)
        {
            return haystack.IndexOf(needle, StringComparison.OrdinalIgnoreCase) >= 0;
        }

        private static bool IsTextDocExtension(string? extension)
        {
            return string.Equals(extension, ".md", StringComparison.OrdinalIgnoreCase)
                   || string.Equals(extension, ".txt", StringComparison.OrdinalIgnoreCase)
                   || string.Equals(extension, ".yml", StringComparison.OrdinalIgnoreCase)
                   || string.Equals(extension, ".yaml", StringComparison.OrdinalIgnoreCase);
        }

        private static bool ShouldSkipDirectory(string? directoryName)
        {
            if (string.IsNullOrWhiteSpace(directoryName))
            {
                return false;
            }

            return string.Equals(directoryName, ".git", StringComparison.OrdinalIgnoreCase)
                   || string.Equals(directoryName, ".godot", StringComparison.OrdinalIgnoreCase)
                   || string.Equals(directoryName, "build", StringComparison.OrdinalIgnoreCase)
                   || string.Equals(directoryName, "logs", StringComparison.OrdinalIgnoreCase)
                   || string.Equals(directoryName, "node_modules", StringComparison.OrdinalIgnoreCase);
        }
    }
}
