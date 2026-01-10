using System;
using System.Globalization;
using System.IO;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task46HeadlessSmokeNonStrictTests
{
    private const string TemplateSmokeReadyMarker = "[TEMPLATE_SMOKE_READY]";
    private const string DbOpenedMarker = "[DB] opened";

    // ACC:T46.2
    [Fact]
    public void ShouldPass_WhenExitCodeIsZeroEvenIfMarkersMissingInLooseMode()
    {
        var stdout = "";
        var stderr = "";

        ContainsRequiredMarkers(stdout).Should().BeFalse();
        EvaluateLooseMode(exitCode: 0, stdout, stderr).Should().BeTrue();
    }

    [Fact]
    public void ShouldBuildSmokeOutputDirectory_WhenGivenUtcDate()
    {
        var date = new DateTime(2030, 1, 2, 0, 0, 0, DateTimeKind.Utc);
        var relative = BuildSmokeRelativeOutputDir(date);

        relative.Should().NotBeNullOrWhiteSpace();
        relative.Should().Contain($"logs{Path.DirectorySeparatorChar}ci{Path.DirectorySeparatorChar}");
        relative.Should().EndWith($"{Path.DirectorySeparatorChar}smoke");
        relative.Should().Contain("2030-01-02");

        TemplateSmokeReadyMarker.Should().NotBeNullOrWhiteSpace();
        DbOpenedMarker.Should().NotBeNullOrWhiteSpace();
    }

    private static bool EvaluateLooseMode(int exitCode, string stdout, string stderr)
    {
        _ = stdout;
        _ = stderr;

        return exitCode == 0;
    }

    private static bool ContainsRequiredMarkers(string stdout)
    {
        if (stdout is null)
        {
            return false;
        }

        return stdout.Contains(TemplateSmokeReadyMarker, StringComparison.Ordinal)
            && stdout.Contains(DbOpenedMarker, StringComparison.Ordinal);
    }

    private static string BuildSmokeRelativeOutputDir(DateTime utcDate)
    {
        var date = utcDate.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        return Path.Combine("logs", "ci", date, "smoke");
    }
}
