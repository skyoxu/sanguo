#nullable enable

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task48SecurityTests
{
    private readonly record struct Decision(bool IsAllowed, string Reason);

    // ACC:T48.1
    // External URL security entry point: enforce https + host allowlist; deny dangerous schemes.
    [Fact]
    public void ShouldDenyExternalUrl_WhenSchemeIsFileOrJavascript()
    {
        var allowlist = "example.com";

        var fileDecision = SecurityUrlPolicy.Validate(
            url: "file:///C:/Windows/system.ini",
            allowedHostsCsv: allowlist,
            allowInsecureDefaults: false);

        fileDecision.IsAllowed.Should().BeFalse();
        fileDecision.Reason.Should().NotBeNullOrWhiteSpace();

        var jsDecision = SecurityUrlPolicy.Validate(
            url: "javascript:alert(1)",
            allowedHostsCsv: allowlist,
            allowInsecureDefaults: false);

        jsDecision.IsAllowed.Should().BeFalse();
        jsDecision.Reason.Should().NotBeNullOrWhiteSpace();
    }

    // ACC:T48.2
    // Default policy must be deny when allowlist is not configured.
    [Fact]
    public void ShouldDenyExternalUrl_WhenAllowListNotConfigured()
    {
        var decision = SecurityUrlPolicy.Validate(
            url: "https://example.com/path",
            allowedHostsCsv: null,
            allowInsecureDefaults: false);

        decision.IsAllowed.Should().BeFalse();
        decision.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public void ShouldAllowExternalUrl_WhenHostIsAllowlistedAndHttps()
    {
        var decision = SecurityUrlPolicy.Validate(
            url: "https://example.com/path",
            allowedHostsCsv: ".example.com,",
            allowInsecureDefaults: false);

        decision.IsAllowed.Should().BeTrue();
        decision.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public void ShouldAllowExternalUrl_WhenSubdomainIsAllowlistedSuffixAndHttps()
    {
        var decision = SecurityUrlPolicy.Validate(
            url: "https://sub.example.com/path",
            allowedHostsCsv: "example.com",
            allowInsecureDefaults: false);

        decision.IsAllowed.Should().BeTrue();
        decision.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public void ShouldDenyExternalUrl_WhenHostNotAllowlisted()
    {
        var decision = SecurityUrlPolicy.Validate(
            url: "https://evil.com/path",
            allowedHostsCsv: "example.com",
            allowInsecureDefaults: false);

        decision.IsAllowed.Should().BeFalse();
        decision.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public void ShouldAllowExternalUrl_WhenInsecureDefaultsEnabledAndAllowListMissing()
    {
        var decision = SecurityUrlPolicy.Validate(
            url: "https://example.com/path",
            allowedHostsCsv: null,
            allowInsecureDefaults: true);

        decision.IsAllowed.Should().BeTrue();
        decision.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public void ShouldDenyExternalUrl_WhenUrlIsInvalid()
    {
        var decision = SecurityUrlPolicy.Validate(
            url: "not a url",
            allowedHostsCsv: "example.com",
            allowInsecureDefaults: false);

        decision.IsAllowed.Should().BeFalse();
        decision.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public void ShouldDenyExternalUrl_WhenUrlIsEmpty()
    {
        var decision = SecurityUrlPolicy.Validate(
            url: "",
            allowedHostsCsv: "example.com",
            allowInsecureDefaults: false);

        decision.IsAllowed.Should().BeFalse();
        decision.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public void ShouldDenyExternalUrl_WhenHostIsMissing()
    {
        var decision = SecurityUrlPolicy.Validate(
            url: "https:///path",
            allowedHostsCsv: "example.com",
            allowInsecureDefaults: false);

        decision.IsAllowed.Should().BeFalse();
        decision.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public void ShouldTreatDotOnlyAllowListAsEmpty_WhenValidatingExternalUrl()
    {
        var decision = SecurityUrlPolicy.Validate(
            url: "https://example.com/path",
            allowedHostsCsv: ".",
            allowInsecureDefaults: false);

        decision.IsAllowed.Should().BeFalse();
        decision.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public void ShouldAllowExternalUrl_WhenAllowListItemHasLeadingAndTrailingDots()
    {
        var decision = SecurityUrlPolicy.Validate(
            url: "https://example.com/path",
            allowedHostsCsv: ".example.com.",
            allowInsecureDefaults: false);

        decision.IsAllowed.Should().BeTrue();
        decision.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public void ShouldDenyExternalUrl_WhenSchemeIsNotHttps()
    {
        var decision = SecurityUrlPolicy.Validate(
            url: "http://example.com/path",
            allowedHostsCsv: "example.com",
            allowInsecureDefaults: false);

        decision.IsAllowed.Should().BeFalse();
        decision.Reason.Should().NotBeNullOrWhiteSpace();
    }

    // ACC:T48.3
    // Godot path policy: read allows res:// and user://; write allows user:// only; deny absolute/traversal.
    [Fact]
    public void ShouldEnforceGodotPathAccessPolicy_WhenResolvingReadAndWritePaths()
    {
        var readRes = SecureSavePathPolicy.ValidateForRead("res://data/config.json");
        readRes.IsAllowed.Should().BeTrue();
        readRes.Reason.Should().NotBeNullOrWhiteSpace();

        var writeRes = SecureSavePathPolicy.ValidateForWrite("res://data/config.json");
        writeRes.IsAllowed.Should().BeFalse();
        writeRes.Reason.Should().NotBeNullOrWhiteSpace();

        var readUser = SecureSavePathPolicy.ValidateForRead("user://saves/slot1.sav");
        readUser.IsAllowed.Should().BeTrue();
        readUser.Reason.Should().NotBeNullOrWhiteSpace();

        var writeUser = SecureSavePathPolicy.ValidateForWrite("user://saves/slot1.sav");
        writeUser.IsAllowed.Should().BeTrue();
        writeUser.Reason.Should().NotBeNullOrWhiteSpace();

        var traversal = SecureSavePathPolicy.ValidateForRead("user://../secrets.txt");
        traversal.IsAllowed.Should().BeFalse();
        traversal.Reason.Should().NotBeNullOrWhiteSpace();

        var absoluteWindows = SecureSavePathPolicy.ValidateForRead("C:\\Windows\\system.ini");
        absoluteWindows.IsAllowed.Should().BeFalse();
        absoluteWindows.Reason.Should().NotBeNullOrWhiteSpace();

        var unsupported = SecureSavePathPolicy.ValidateForRead("relative/path.txt");
        unsupported.IsAllowed.Should().BeFalse();
        unsupported.Reason.Should().NotBeNullOrWhiteSpace();

        var badResTraversal = SecureSavePathPolicy.ValidateForRead("res://../evil.txt");
        badResTraversal.IsAllowed.Should().BeFalse();
        badResTraversal.Reason.Should().NotBeNullOrWhiteSpace();
    }

    // ACC:T48.4
    // Process execution must be disabled by default; allow only in dev/CI and via explicit allowlist.
    [Fact]
    public void ShouldDenyProcessExecution_WhenDefaultsAndAllowOnlyInDevOrCi()
    {
        var args = new[] { "/c", "echo", "hello" };

        var prodDecision = SecurityProcessPolicy.ValidateExecute(
            fileName: "cmd.exe",
            args: args,
            isDevOrCi: false,
            allowedCommandsCsv: "cmd.exe");

        prodDecision.IsAllowed.Should().BeFalse();
        prodDecision.Reason.Should().NotBeNullOrWhiteSpace();

        var devMissingAllowlist = SecurityProcessPolicy.ValidateExecute(
            fileName: "cmd.exe",
            args: args,
            isDevOrCi: true,
            allowedCommandsCsv: null);

        devMissingAllowlist.IsAllowed.Should().BeFalse();
        devMissingAllowlist.Reason.Should().NotBeNullOrWhiteSpace();

        var devAllowed = SecurityProcessPolicy.ValidateExecute(
            fileName: "cmd.exe",
            args: args,
            isDevOrCi: true,
            allowedCommandsCsv: "cmd.exe,powershell.exe");

        devAllowed.IsAllowed.Should().BeTrue();
        devAllowed.Reason.Should().NotBeNullOrWhiteSpace();

        var devNotAllowlisted = SecurityProcessPolicy.ValidateExecute(
            fileName: "cmd.exe",
            args: args,
            isDevOrCi: true,
            allowedCommandsCsv: "powershell.exe");
        devNotAllowlisted.IsAllowed.Should().BeFalse();
        devNotAllowlisted.Reason.Should().NotBeNullOrWhiteSpace();

        var devPathNotAllowed = SecurityProcessPolicy.ValidateExecute(
            fileName: "C:\\Windows\\System32\\cmd.exe",
            args: args,
            isDevOrCi: true,
            allowedCommandsCsv: "cmd.exe");
        devPathNotAllowed.IsAllowed.Should().BeFalse();
        devPathNotAllowed.Reason.Should().NotBeNullOrWhiteSpace();

        var devEmptyCommand = SecurityProcessPolicy.ValidateExecute(
            fileName: "",
            args: args,
            isDevOrCi: true,
            allowedCommandsCsv: "cmd.exe");
        devEmptyCommand.IsAllowed.Should().BeFalse();
        devEmptyCommand.Reason.Should().NotBeNullOrWhiteSpace();
    }

    // ACC:T48.5
    // Security audit JSONL lines must be valid JSON and include required fields.
    [Fact]
    public void ShouldValidateSecurityAuditJsonl_WhenLinesHaveRequiredFields()
    {
        var validLine = "{\"ts\":\"2026-01-01T00:00:00Z\",\"action\":\"url.open\",\"reason\":\"deny\",\"target\":\"https://example.com\",\"caller\":\"unit-test\"}";
        var invalidJson = "{not-json";
        var missingFields = "{\"ts\":\"2026-01-01T00:00:00Z\",\"action\":\"url.open\",\"target\":\"https://example.com\",\"caller\":\"unit-test\"}";

        var ok = SecurityAuditJsonlValidator.TryValidateLine(validLine);
        ok.IsAllowed.Should().BeTrue();
        ok.Reason.Should().NotBeNullOrWhiteSpace();

        var badJson = SecurityAuditJsonlValidator.TryValidateLine(invalidJson);
        badJson.IsAllowed.Should().BeFalse();
        badJson.Reason.Should().NotBeNullOrWhiteSpace();

        var badFields = SecurityAuditJsonlValidator.TryValidateLine(missingFields);
        badFields.IsAllowed.Should().BeFalse();
        badFields.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public void ShouldDenySecurityAuditJsonl_WhenNotJsonObject()
    {
        var decision = SecurityAuditJsonlValidator.TryValidateLine("[]");
        decision.IsAllowed.Should().BeFalse();
        decision.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public void ShouldDenySecurityAuditJsonl_WhenTimestampInvalid()
    {
        var line = "{\"ts\":\"not-a-date\",\"action\":\"url.open\",\"reason\":\"deny\",\"target\":\"https://example.com\",\"caller\":\"unit-test\"}";
        var decision = SecurityAuditJsonlValidator.TryValidateLine(line);
        decision.IsAllowed.Should().BeFalse();
        decision.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Theory]
    [InlineData("{\"action\":\"url.open\",\"reason\":\"deny\",\"target\":\"https://example.com\",\"caller\":\"unit-test\"}")]
    [InlineData("{\"ts\":\"2026-01-01T00:00:00Z\",\"reason\":\"deny\",\"target\":\"https://example.com\",\"caller\":\"unit-test\"}")]
    [InlineData("{\"ts\":\"2026-01-01T00:00:00Z\",\"action\":\"url.open\",\"target\":\"https://example.com\",\"caller\":\"unit-test\"}")]
    [InlineData("{\"ts\":\"2026-01-01T00:00:00Z\",\"action\":\"url.open\",\"reason\":\"deny\",\"caller\":\"unit-test\"}")]
    [InlineData("{\"ts\":\"2026-01-01T00:00:00Z\",\"action\":\"url.open\",\"reason\":\"deny\",\"target\":\"https://example.com\"}")]
    [InlineData("{\"ts\":123,\"action\":\"url.open\",\"reason\":\"deny\",\"target\":\"https://example.com\",\"caller\":\"unit-test\"}")]
    public void Should_DenySecurityAuditJsonl_When_MissingOrInvalidRequiredFields(string json)
    {
        var decision = SecurityAuditJsonlValidator.TryValidateLine(json);
        decision.IsAllowed.Should().BeFalse();
        decision.Reason.Should().NotBeNullOrWhiteSpace();
    }

    // ACC:T48.6
    // GdUnit4 hard tests must exist and be maintained as gate evidence.
    [Fact]
    public void ShouldRequireGdUnit4SecurityHardTestsExist_WhenTask48IsValidated()
    {
        var repoRoot = RepoFiles.FindRepoRoot();

        RepoFiles.AssertExists(repoRoot, "Tests.Godot/tests/Integration/Security/test_security_http_allowed_audit.gd");
        RepoFiles.AssertExists(repoRoot, "Tests.Godot/tests/Integration/Security/test_security_http_audit.gd");
        RepoFiles.AssertExists(repoRoot, "Tests.Godot/tests/Integration/Security/test_security_http_block_signal.gd");
    }

    // ACC:T48.7
    // Migration reference docs must exist in-repo.
    [Fact]
    public void ShouldRequireMigrationDocsExist_WhenTask48IsValidated()
    {
        var repoRoot = RepoFiles.FindRepoRoot();

        RepoFiles.AssertExists(repoRoot, "docs/migration/Phase-14-Godot-Security-Backlog.md");
        RepoFiles.AssertExists(repoRoot, "docs/migration/Phase-14-Godot-Security-Baseline.md");
    }

    private static class SecurityUrlPolicy
    {
        public static Decision Validate(string url, string? allowedHostsCsv, bool allowInsecureDefaults)
        {
            var policyType = Reflection.RequiredType(
                "Game.Core.Security.SecurityUrlPolicy",
                "Game.Core.Security.SecurityUrlAdapter",
                "Game.Core.Security.ExternalUrlPolicy",
                "Game.Core.Utilities.SecurityUrlPolicy");

            var method = Reflection.RequiredStaticMethod(
                policyType,
                new[] { "TryValidateExternalUrl", "TryValidateUrl", "TryValidate" },
                new[]
                {
                    new[] { typeof(string), typeof(string), typeof(bool), typeof(string).MakeByRefType() },
                });

            var args = new object?[] { url, allowedHostsCsv, allowInsecureDefaults, null };
            var allowed = (bool)(method.Invoke(null, args) ?? throw new InvalidOperationException("Policy method returned null."));
            var reason = args[3] as string ?? string.Empty;

            return new Decision(allowed, reason);
        }
    }

    private static class SecureSavePathPolicy
    {
        public static Decision ValidateForRead(string godotPath)
        {
            return Validate(godotPath, intent: "read");
        }

        public static Decision ValidateForWrite(string godotPath)
        {
            return Validate(godotPath, intent: "write");
        }

        private static Decision Validate(string godotPath, string intent)
        {
            var policyType = Reflection.RequiredType("Game.Core.Utilities.SecureSavePathPolicy");

            var method = Reflection.RequiredStaticMethod(
                policyType,
                new[] { intent == "read" ? "TryResolveForRead" : "TryResolveForWrite" },
                new[]
                {
                    new[] { typeof(string), typeof(string).MakeByRefType(), typeof(string).MakeByRefType() },
                });

            var args = new object?[] { godotPath, null, null };
            var allowed = (bool)(method.Invoke(null, args) ?? throw new InvalidOperationException("Policy method returned null."));
            var reason = args[2] as string ?? string.Empty;

            return new Decision(allowed, reason);
        }
    }

    private static class SecurityProcessPolicy
    {
        public static Decision ValidateExecute(string fileName, string[] args, bool isDevOrCi, string? allowedCommandsCsv)
        {
            var policyType = Reflection.RequiredType(
                "Game.Core.Security.SecurityProcessPolicy",
                "Game.Core.Security.SecurityProcessAdapter",
                "Game.Core.Security.ProcessExecutionPolicy",
                "Game.Core.Utilities.SecurityProcessPolicy");

            var method = Reflection.RequiredStaticMethod(
                policyType,
                new[] { "TryValidateExecute", "TryValidateProcess", "TryValidate" },
                new[]
                {
                    new[] { typeof(string), typeof(string[]), typeof(bool), typeof(string), typeof(string).MakeByRefType() },
                });

            var invokeArgs = new object?[] { fileName, args, isDevOrCi, allowedCommandsCsv, null };
            var allowed = (bool)(method.Invoke(null, invokeArgs) ?? throw new InvalidOperationException("Policy method returned null."));
            var reason = invokeArgs[4] as string ?? string.Empty;

            return new Decision(allowed, reason);
        }
    }

    private static class SecurityAuditJsonlValidator
    {
        public static Decision TryValidateLine(string jsonlLine)
        {
            var validatorType = Reflection.RequiredType(
                "Game.Core.Security.SecurityAuditJsonlValidator",
                "Game.Core.Security.SecurityAuditLineValidator",
                "Game.Core.Utilities.SecurityAuditJsonlValidator");

            var method = Reflection.RequiredStaticMethod(
                validatorType,
                new[] { "TryValidateLine", "TryValidate" },
                new[]
                {
                    new[] { typeof(string), typeof(string).MakeByRefType() },
                });

            var invokeArgs = new object?[] { jsonlLine, null };
            var ok = (bool)(method.Invoke(null, invokeArgs) ?? throw new InvalidOperationException("Validator method returned null."));
            var reason = invokeArgs[1] as string ?? string.Empty;

            return new Decision(ok, reason);
        }
    }

    private static class Reflection
    {
        public static Type RequiredType(params string[] fullNames)
        {
            foreach (var fullName in fullNames)
            {
                var type = FindType(fullName);
                if (type is not null)
                {
                    return type;
                }
            }

            throw new InvalidOperationException(
                "Required type not found. Expected one of: " + string.Join(", ", fullNames));
        }

        public static MethodInfo RequiredStaticMethod(
            Type type,
            IReadOnlyList<string> candidateNames,
            IReadOnlyList<Type[]> candidateParameterSets)
        {
            foreach (var name in candidateNames)
            {
                foreach (var parameterSet in candidateParameterSets)
                {
                    var method = type.GetMethod(
                        name,
                        BindingFlags.Public | BindingFlags.Static,
                        binder: null,
                        types: parameterSet,
                        modifiers: null);

                    if (method is not null)
                    {
                        return method;
                    }
                }
            }

            var signatures = candidateParameterSets
                .Select(ps => $"({string.Join(", ", ps.Select(p => p.IsByRef ? p.GetElementType()?.Name + "&" : p.Name))})")
                .ToArray();

            throw new InvalidOperationException(
                "Required static method not found on type '" + type.FullName + "'. Expected name(s): "
                + string.Join(", ", candidateNames)
                + " and signature(s): "
                + string.Join(" | ", signatures));
        }

        private static Type? FindType(string fullName)
        {
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                var type = assembly.GetType(fullName, throwOnError: false, ignoreCase: false);
                if (type is not null)
                {
                    return type;
                }
            }

            try
            {
                var coreAssembly = Assembly.Load("Game.Core");
                var type = coreAssembly.GetType(fullName, throwOnError: false, ignoreCase: false);
                if (type is not null)
                {
                    return type;
                }
            }
            catch
            {
                // Ignore and keep searching.
            }

            return null;
        }
    }

    private static class RepoFiles
    {
        public static string FindRepoRoot()
        {
            var start = new DirectoryInfo(AppContext.BaseDirectory);
            var current = start;

            for (var i = 0; i < 16 && current is not null; i++)
            {
                var marker = Path.Combine(current.FullName, "project.godot");
                if (File.Exists(marker))
                {
                    return current.FullName;
                }

                current = current.Parent;
            }

            throw new InvalidOperationException(
                "Repository root not found. Expected to locate 'project.godot' when walking parents from: " + start.FullName);
        }

        public static void AssertExists(string repoRoot, string relativePath)
        {
            var fullPath = Path.Combine(repoRoot, relativePath.Replace('/', Path.DirectorySeparatorChar));
            File.Exists(fullPath).Should().BeTrue("expected file to exist: {0}", relativePath);
        }
    }
}
