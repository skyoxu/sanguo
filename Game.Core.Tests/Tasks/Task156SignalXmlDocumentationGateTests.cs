using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task156SignalXmlDocumentationGateTests
{
    private static readonly Encoding Utf8NoBom = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false);

    // ACC:T156.1
    [Fact]
    public void ShouldRejectContracts_WhenAnySignalEventOrSecurityCriticalSignalMissesRequiredXmlDocumentation()
    {
        var fixture = CreateFixture(
            BuildSignalContract(
                relativePath: "Game.Core/Contracts/Signals/FixtureSignalMissingSummary.cs",
                typeName: "FixtureSignalMissingSummary",
                includeSummary: false,
                includeRemarks: true,
                eventTypeValue: "core.fixture.signal.missing.summary"),
            BuildEventContract(
                relativePath: "Game.Core/Contracts/Events/FixtureEventMissingRemarks.cs",
                typeName: "FixtureEventMissingRemarks",
                includeSummary: true,
                includeRemarks: false,
                eventTypeValue: "core.fixture.event.missing.remarks"),
            BuildSignalContract(
                relativePath: "Game.Core/Contracts/Signals/SecurityCriticalSignalMissingRemarks.cs",
                typeName: "SecurityCriticalSignalMissingRemarks",
                includeSummary: true,
                includeRemarks: false,
                eventTypeValue: "core.fixture.security.signal.missing.remarks")
        );

        var result = RunValidateContracts(fixture);

        result.ExitCode.Should().Be(1, "real contracts gate must reject missing XML docs");
        result.Report.Ok.Should().BeFalse();
        result.Report.XmlCommentIssues.Should().Contain(
            issue => issue.File == NormalizePath("Game.Core/Contracts/Signals/FixtureSignalMissingSummary.cs")
                     && issue.Code == "xml_summary_missing");
        result.Report.XmlCommentIssues.Should().Contain(
            issue => issue.File == NormalizePath("Game.Core/Contracts/Events/FixtureEventMissingRemarks.cs")
                     && issue.Code == "xml_remarks_missing");
        result.Report.XmlCommentIssues.Should().Contain(
            issue => issue.File == NormalizePath("Game.Core/Contracts/Signals/SecurityCriticalSignalMissingRemarks.cs")
                     && issue.Code == "xml_remarks_missing");
    }

    // ACC:T156.1
    [Fact]
    public void ShouldPassGate_WhenAllSignalAndEventContractsAreFullyDocumentedAndAdrAligned()
    {
        var fixture = CreateFixture(
            BuildSignalContract(
                relativePath: "Game.Core/Contracts/Signals/FullyDocumentedSignal.cs",
                typeName: "FullyDocumentedSignal",
                includeSummary: true,
                includeRemarks: true,
                eventTypeValue: "core.fixture.signal.documented"),
            BuildEventContract(
                relativePath: "Game.Core/Contracts/Events/FullyDocumentedEvent.cs",
                typeName: "FullyDocumentedEvent",
                includeSummary: true,
                includeRemarks: true,
                eventTypeValue: "core.fixture.event.documented"),
            BuildSignalContract(
                relativePath: "Game.Core/Contracts/Signals/SecurityCriticalSignalDocumented.cs",
                typeName: "SecurityCriticalSignalDocumented",
                includeSummary: true,
                includeRemarks: true,
                eventTypeValue: "core.fixture.security.signal.documented")
        );

        var result = RunValidateContracts(fixture);

        result.ExitCode.Should().Be(0, result.CombinedOutput);
        result.Report.Ok.Should().BeTrue();
        result.Report.XmlCommentIssues.Should().BeEmpty();
        result.Report.EventTypeIssues.Should().BeEmpty();
    }

    // ACC:T156.2
    [Theory]
    [MemberData(nameof(MissingXmlNegativeCases))]
    public void ShouldRejectNegativeFixtureCase_WhenRunningRealContractsGate(
        string caseName,
        ContractFileSpec negativeCase,
        string expectedIssueCode)
    {
        var fixture = CreateFixture(
            BuildSignalContract(
                relativePath: "Game.Core/Contracts/Signals/FixtureBaselineSignal.cs",
                typeName: "FixtureBaselineSignal",
                includeSummary: true,
                includeRemarks: true,
                eventTypeValue: "core.fixture.signal.baseline"),
            BuildEventContract(
                relativePath: "Game.Core/Contracts/Events/FixtureBaselineEvent.cs",
                typeName: "FixtureBaselineEvent",
                includeSummary: true,
                includeRemarks: true,
                eventTypeValue: "core.fixture.event.baseline"),
            negativeCase
        );

        var result = RunValidateContracts(fixture);

        result.ExitCode.Should().Be(1, $"{caseName} should be rejected by validate_contracts.py");
        result.Report.Ok.Should().BeFalse();
        result.Report.XmlCommentIssues.Should().Contain(
            issue => issue.File == NormalizePath(negativeCase.RelativePath) && issue.Code == expectedIssueCode,
            $"negative fixture case '{caseName}' must map to real gate issue '{expectedIssueCode}'");
    }

    public static IEnumerable<object[]> MissingXmlNegativeCases()
    {
        yield return new object[]
        {
            "signal_missing_summary",
            BuildSignalContract(
                relativePath: "Game.Core/Contracts/Signals/FixtureSignalMissingSummaryOnly.cs",
                typeName: "FixtureSignalMissingSummaryOnly",
                includeSummary: false,
                includeRemarks: true,
                eventTypeValue: "core.fixture.signal.missing.summary.only"),
            "xml_summary_missing",
        };

        yield return new object[]
        {
            "event_missing_remarks",
            BuildEventContract(
                relativePath: "Game.Core/Contracts/Events/FixtureEventMissingRemarksOnly.cs",
                typeName: "FixtureEventMissingRemarksOnly",
                includeSummary: true,
                includeRemarks: false,
                eventTypeValue: "core.fixture.event.missing.remarks.only"),
            "xml_remarks_missing",
        };

        yield return new object[]
        {
            "security_signal_missing_remarks",
            BuildSignalContract(
                relativePath: "Game.Core/Contracts/Signals/SecurityCriticalSignalMissingRemarksOnly.cs",
                typeName: "SecurityCriticalSignalMissingRemarksOnly",
                includeSummary: true,
                includeRemarks: false,
                eventTypeValue: "core.fixture.security.signal.missing.remarks.only"),
            "xml_remarks_missing",
        };
    }

    private static ContractFileSpec BuildSignalContract(
        string relativePath,
        string typeName,
        bool includeSummary,
        bool includeRemarks,
        string eventTypeValue)
    {
        var namespaceName = "Game.Core.Contracts.Signals";
        var source = BuildContractSource(namespaceName, typeName, includeSummary, includeRemarks, eventTypeValue);
        return new ContractFileSpec(relativePath, source);
    }

    private static ContractFileSpec BuildEventContract(
        string relativePath,
        string typeName,
        bool includeSummary,
        bool includeRemarks,
        string eventTypeValue)
    {
        var namespaceName = "Game.Core.Contracts.Events";
        var source = BuildContractSource(namespaceName, typeName, includeSummary, includeRemarks, eventTypeValue);
        return new ContractFileSpec(relativePath, source);
    }

    private static string BuildContractSource(
        string namespaceName,
        string typeName,
        bool includeSummary,
        bool includeRemarks,
        string eventTypeValue)
    {
        var parts = new List<string>
        {
            $"namespace {namespaceName};",
            string.Empty,
        };

        if (includeSummary)
        {
            parts.Add("/// <summary>");
            parts.Add($"/// Fixture contract for {typeName}.");
            parts.Add("/// </summary>");
        }

        if (includeRemarks)
        {
            parts.Add("/// <remarks>");
            parts.Add("/// Fixture remarks for XML completeness gate.");
            parts.Add("/// </remarks>");
        }

        parts.Add($"public sealed record {typeName}(string CorrelationId)");
        parts.Add("{");
        parts.Add($"    public const string EventType = \"{eventTypeValue}\";");
        parts.Add("}");

        return string.Join(Environment.NewLine, parts) + Environment.NewLine;
    }

    private static GateFixture CreateFixture(params ContractFileSpec[] contractFiles)
    {
        var repoRoot = FindRepoRoot();
        var root = Path.Combine(
            repoRoot,
            "logs",
            "ci",
            DateTime.UtcNow.ToString("yyyy-MM-dd"),
            "task156-signal-xml-contract-gate",
            Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);

        var allContracts = new List<ContractFileSpec>
        {
            new("Game.Core/Contracts/EventTypes.cs", BuildEventTypesSource()),
        };
        allContracts.AddRange(contractFiles);

        foreach (var contractFile in allContracts)
        {
            var fullPath = Path.Combine(root, contractFile.RelativePath.Replace('/', Path.DirectorySeparatorChar));
            Directory.CreateDirectory(Path.GetDirectoryName(fullPath)!);
            File.WriteAllText(fullPath, contractFile.Source, Utf8NoBom);
        }

        WriteOverlayDoc(root, allContracts.Select(x => NormalizePath(x.RelativePath)).ToArray());

        return new GateFixture(root);
    }

    private static string BuildEventTypesSource()
    {
        return
            "namespace Game.Core.Contracts;" + Environment.NewLine
            + Environment.NewLine
            + "/// <summary>" + Environment.NewLine
            + "/// Fixture event type constants." + Environment.NewLine
            + "/// </summary>" + Environment.NewLine
            + "public static class EventTypes" + Environment.NewLine
            + "{" + Environment.NewLine
            + "    public const string FixtureEvent = \"core.fixture.event.type\";" + Environment.NewLine
            + "}" + Environment.NewLine;
    }

    private static void WriteOverlayDoc(string fixtureRoot, IReadOnlyList<string> contractPaths)
    {
        var overlayDocPath = Path.Combine(
            fixtureRoot,
            "docs",
            "architecture",
            "overlays",
            "PRD-SANGUO-V3",
            "08",
            "08-Contracts-Task156-Fixture.md");
        Directory.CreateDirectory(Path.GetDirectoryName(overlayDocPath)!);

        var lines = new List<string>
        {
            "# Task156 Fixture Contracts",
            string.Empty,
            "## Contract References",
        };
        lines.AddRange(contractPaths.Select(path => $"- `{path}`"));
        lines.Add(string.Empty);

        File.WriteAllText(overlayDocPath, string.Join(Environment.NewLine, lines), Utf8NoBom);
    }

    private static GateRunResult RunValidateContracts(GateFixture fixture)
    {
        var repoRoot = FindRepoRoot();

        var psi = new ProcessStartInfo
        {
            FileName = "py",
            WorkingDirectory = repoRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        psi.ArgumentList.Add("-3");
        psi.ArgumentList.Add("scripts/python/validate_contracts.py");
        psi.ArgumentList.Add("--root");
        psi.ArgumentList.Add(fixture.RootPath);
        psi.Environment["PYTHONIOENCODING"] = "utf-8";
        psi.Environment["PYTHONUTF8"] = "1";

        using var proc = Process.Start(psi);
        proc.Should().NotBeNull();

        var stdout = proc!.StandardOutput.ReadToEnd();
        var stderr = proc.StandardError.ReadToEnd();
        proc.WaitForExit(30_000).Should().BeTrue($"stdout={stdout}{Environment.NewLine}stderr={stderr}");

        var reportPath = ResolveContractsReportPath(fixture.RootPath);
        var report = ReadReport(reportPath);
        return new GateRunResult(proc.ExitCode, report, stdout + Environment.NewLine + stderr);
    }

    private static string ResolveContractsReportPath(string fixtureRoot)
    {
        var ciRoot = Path.Combine(fixtureRoot, "logs", "ci");
        Directory.Exists(ciRoot).Should().BeTrue("validate_contracts.py should emit contracts report under logs/ci");

        var reportPath = Directory
            .EnumerateFiles(ciRoot, "contracts-validate.json", SearchOption.AllDirectories)
            .OrderByDescending(File.GetLastWriteTimeUtc)
            .FirstOrDefault();

        reportPath.Should().NotBeNullOrWhiteSpace($"Expected contracts-validate.json under {ciRoot}");
        return reportPath!;
    }

    private static ContractsReport ReadReport(string reportPath)
    {
        using var doc = JsonDocument.Parse(File.ReadAllText(reportPath, Utf8NoBom));
        var root = doc.RootElement;
        var ok = root.GetProperty("ok").GetBoolean();
        var xmlIssues = ReadIssues(root, "xml_comment_issues");
        var eventTypeIssues = ReadIssues(root, "eventtype_issues");
        return new ContractsReport(ok, xmlIssues, eventTypeIssues);
    }

    private static IReadOnlyList<GateIssue> ReadIssues(JsonElement root, string key)
    {
        if (!root.TryGetProperty(key, out var issuesElement) || issuesElement.ValueKind != JsonValueKind.Array)
        {
            return Array.Empty<GateIssue>();
        }

        var issues = new List<GateIssue>();
        foreach (var issue in issuesElement.EnumerateArray())
        {
            var file = issue.TryGetProperty("file", out var fileElement) && fileElement.ValueKind == JsonValueKind.String
                ? fileElement.GetString() ?? string.Empty
                : string.Empty;
            var code = issue.TryGetProperty("code", out var codeElement) && codeElement.ValueKind == JsonValueKind.String
                ? codeElement.GetString() ?? string.Empty
                : string.Empty;
            issues.Add(new GateIssue(file, code));
        }

        return issues;
    }

    private static string NormalizePath(string path) => path.Replace('\\', '/');

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var marker = Path.Combine(dir.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(marker))
            {
                return dir.FullName;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found.");
    }

    public readonly record struct ContractFileSpec(string RelativePath, string Source);

    private readonly record struct GateFixture(string RootPath);

    private readonly record struct GateIssue(string File, string Code);

    private readonly record struct ContractsReport(
        bool Ok,
        IReadOnlyList<GateIssue> XmlCommentIssues,
        IReadOnlyList<GateIssue> EventTypeIssues);

    private readonly record struct GateRunResult(int ExitCode, ContractsReport Report, string CombinedOutput);
}
