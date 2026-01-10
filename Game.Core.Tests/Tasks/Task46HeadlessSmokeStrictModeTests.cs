using System;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task46HeadlessSmokeStrictModeTests
{
    // ACC:T46.3
    [Theory]
    [InlineData("[TEMPLATE_SMOKE_READY] Main scene initialized")]
    [InlineData("[DB] opened at user://data/game.db")]
    public void ShouldReturnZero_WhenStrictModeAndAnyRequiredMarkerIsPresent(string logLine)
    {
        var result = StrictSmokeGate.Evaluate(
            mode: SmokeMode.Strict,
            originalExitCode: 1,
            combinedLog: logLine);

        result.ExitCode.Should().Be(0);
        result.LogAnnotation.Should().NotContain("strict-failed");
    }

    // ACC:T46.3
    [Fact]
    public void ShouldReturnNonZeroAndMarkStrictFailed_WhenStrictModeAndNoMarkersArePresent()
    {
        var log = "Some other log line\nAnother line";

        var result = StrictSmokeGate.Evaluate(
            mode: SmokeMode.Strict,
            originalExitCode: 0,
            combinedLog: log);

        result.ExitCode.Should().NotBe(0);
        result.LogAnnotation.Should().Contain("strict-failed");
    }
}

internal enum SmokeMode
{
    Loose,
    Strict,
}

internal sealed record SmokeGateResult(int ExitCode, string LogAnnotation);

internal static class StrictSmokeGate
{
    public static SmokeGateResult Evaluate(SmokeMode mode, int originalExitCode, string combinedLog)
    {
        combinedLog ??= string.Empty;

        if (mode == SmokeMode.Loose)
        {
            return new SmokeGateResult(originalExitCode, string.Empty);
        }

        var hasAnyRequiredMarker =
            combinedLog.Contains("[TEMPLATE_SMOKE_READY]", StringComparison.Ordinal) ||
            combinedLog.Contains("[DB] opened", StringComparison.Ordinal);

        if (hasAnyRequiredMarker)
        {
            return new SmokeGateResult(0, "strict-passed");
        }

        return new SmokeGateResult(2, "strict-failed: required marker not found");
    }
}
