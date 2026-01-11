#nullable enable

using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using FluentAssertions;
using Xunit;
using Xunit.Sdk;

namespace Game.Core.Tests.Tasks;

public sealed class Task33BuildWindowsCliContractTests
{
    // ADR references (context): ADR-0008, ADR-0011, ADR-0003, ADR-0015.

    private static readonly Encoding Utf8NoBom = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false);

    // ACC:T33.6
    [Fact]
    public void ShouldShowHelpAndDescribeWindowsExportTarget_WhenInvokedWithHelp()
    {
        var result = RunBuildWindowsCli("--help");

        result.ExitCode.Should().Be(0, $"--help must succeed for a cross-platform CLI. stdout={result.Stdout} stderr={result.Stderr}");
        var output = result.CombinedOutput.ToLowerInvariant();
        output.Should().Contain("usage");
        output.Should().Contain("release");
        output.Should().Contain("debug");
        output.Should().Contain("windows");
    }

    // ACC:T33.6
    [Fact]
    public void ShouldReturnNonZeroAndUsage_WhenArgsAreInvalid()
    {
        var result = RunBuildWindowsCli("--this-flag-should-not-exist");

        result.ExitCode.Should().NotBe(0, $"Invalid arguments must fail with a non-zero exit code. stdout={result.Stdout} stderr={result.Stderr}");
        result.CombinedOutput.ToLowerInvariant().Should().Contain("usage");
    }

    // ACC:T33.6
    [Fact]
    public void ShouldNotRequirePowerShellOrPs1AsCliPrerequisite_WhenReadingScriptSource()
    {
        var repoRoot = FindRepoRoot();
        var scriptPath = Path.Combine(repoRoot, "scripts", "python", "build_windows.py");

        File.Exists(scriptPath).Should().BeTrue($"Build driver script must exist at {scriptPath}");

        var text = File.ReadAllText(scriptPath, Utf8NoBom);
        text.Should().NotContain(".ps1", "the Python CLI must not require OS-specific wrapper scripts as a prerequisite");
        text.Should().NotContain("powershell", "the Python CLI must not require PowerShell as a prerequisite");
        text.Should().Contain("argparse", "the Python CLI must provide --help and argument validation");
        text.Should().Contain("pathlib", "the Python CLI should handle paths in a cross-platform way");
    }

    // ACC:T33.6
    [Fact]
    public void ShouldRefuseWindowsExport_WhenRunningOnNonWindows()
    {
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            return;

        var result = RunBuildWindowsCli("release");

        result.ExitCode.Should().NotBe(0, $"Windows export must refuse on non-Windows hosts. stdout={result.Stdout} stderr={result.Stderr}");
        result.CombinedOutput.ToLowerInvariant().Should().Contain("windows");
    }

    private static CliResult RunBuildWindowsCli(params string[] args)
    {
        var repoRoot = FindRepoRoot();
        var scriptPath = Path.Combine(repoRoot, "scripts", "python", "build_windows.py");

        var invocation = GetPythonInvocation();
        var psi = new ProcessStartInfo
        {
            FileName = invocation.FileName,
            WorkingDirectory = repoRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
            StandardOutputEncoding = Utf8NoBom,
            StandardErrorEncoding = Utf8NoBom,
        };

        foreach (var a in invocation.PrefixArgs)
            psi.ArgumentList.Add(a);

        psi.ArgumentList.Add(scriptPath);

        foreach (var a in args)
            psi.ArgumentList.Add(a);

        psi.Environment["PYTHONIOENCODING"] = "utf-8";
        psi.Environment["PYTHONUTF8"] = "1";

        Process? proc;
        try
        {
            proc = Process.Start(psi);
        }
        catch (Exception ex)
        {
            throw new XunitException($"Unable to start Python interpreter '{invocation.FileName}': {ex.GetType().Name} {ex.Message}");
        }

        proc.Should().NotBeNull($"Python interpreter '{invocation.FileName}' should be runnable");

        var stdout = proc!.StandardOutput.ReadToEnd();
        var stderr = proc.StandardError.ReadToEnd();

        proc.WaitForExit(30_000).Should().BeTrue($"CLI must exit in time. stdout={stdout} stderr={stderr}");

        return new CliResult(proc.ExitCode, stdout, stderr);
    }

    private static PythonInvocation GetPythonInvocation()
    {
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            return new PythonInvocation("py", new[] { "-3" });

        return new PythonInvocation("python3", Array.Empty<string>());
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var tm = Path.Combine(dir.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(tm))
                return dir.FullName;
            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks.json).");
    }

    private readonly record struct PythonInvocation(string FileName, string[] PrefixArgs);

    private readonly record struct CliResult(int ExitCode, string Stdout, string Stderr)
    {
        public string CombinedOutput => (Stdout + "\n" + Stderr).Trim();
    }
}
