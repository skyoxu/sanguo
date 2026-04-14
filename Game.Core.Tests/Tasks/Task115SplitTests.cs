using System;
using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Security;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task115SplitTests
{
    private const string PrimarySinkPath = "res://logs/security/security-audit.jsonl";
    private const string FallbackSinkPath = "user://logs/security/security-audit.jsonl";

    // ACC:T115.1
    [Fact]
    [Trait("acceptance", "ACC:T115.1")]
    public void ShouldFallbackToUserSinkWithoutRuntimeAbort_WhenPrimaryWriteFails()
    {
        var writeAttempts = new List<string>();
        var warnings = new List<string>();

        var act = () =>
        {
            var ok = SecurityAuditFallbackPolicy.TryWriteWithFallback(
                primarySinkPath: PrimarySinkPath,
                fallbackSinkPath: FallbackSinkPath,
                tryWrite: path =>
                {
                    writeAttempts.Add(path);
                    return string.Equals(path, FallbackSinkPath, StringComparison.Ordinal);
                },
                warningSink: warnings.Add);

            ok.Should().BeTrue("fallback write to user:// must recover from primary sink failure");
        };

        act.Should().NotThrow("audit fallback path must not abort runtime execution");
        writeAttempts.Should().Equal(PrimarySinkPath, FallbackSinkPath);
        warnings.Should().Contain(message => message.Contains("fallback", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void ShouldReturnFalseWithoutThrowing_WhenPrimaryAndFallbackWritesBothFail()
    {
        var writeAttempts = new List<string>();
        var warnings = new List<string>();

        var act = () =>
        {
            var ok = SecurityAuditFallbackPolicy.TryWriteWithFallback(
                primarySinkPath: PrimarySinkPath,
                fallbackSinkPath: FallbackSinkPath,
                tryWrite: path =>
                {
                    writeAttempts.Add(path);
                    throw new InvalidOperationException($"write failed: {path}");
                },
                warningSink: warnings.Add);

            ok.Should().BeFalse();
        };

        act.Should().NotThrow("failed fallback writes must still preserve runtime continuity");
        writeAttempts.Should().Equal(PrimarySinkPath, FallbackSinkPath);
        warnings.Should().Contain(message => message.Contains("primary audit sink write failed", StringComparison.OrdinalIgnoreCase));
        warnings.Should().Contain(message => message.Contains("fallback audit sink write failed", StringComparison.OrdinalIgnoreCase));
    }
}
