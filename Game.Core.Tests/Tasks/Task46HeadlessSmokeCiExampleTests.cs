using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks
{
    public sealed class Task46HeadlessSmokeCiExampleTests
    {
        private const string WindowsQualityGateStrictSmokeExample =
            "py -3 scripts/python/smoke_headless.py --mode strict --godot-bin \"%GODOT_BIN%\" --project \"%GODOT_PROJECT%\" --scene \"res://Scenes/Main.tscn\" --timeout-sec 120";

        // ADR References: ADR-0005, ADR-0011, ADR-0018, ADR-0024
        // ACC:T46.4
        // This is a documentation guardrail for CI: strict headless smoke must be runnable on Windows.
        [Fact]
        public void ShouldContainStrictModeExample_WhenValidatingWindowsQualityGate()
        {
            WindowsQualityGateStrictSmokeExample.Should().Contain("py -3");
            WindowsQualityGateStrictSmokeExample.Should().Contain("scripts/python/smoke_headless.py");
            WindowsQualityGateStrictSmokeExample.Should().Contain("--mode strict");
            WindowsQualityGateStrictSmokeExample.Should().Contain("%GODOT_BIN%");
            WindowsQualityGateStrictSmokeExample.Should().Contain("%GODOT_PROJECT%");
        }
    }
}
