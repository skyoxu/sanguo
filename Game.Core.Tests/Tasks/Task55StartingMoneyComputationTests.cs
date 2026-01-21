using System;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task55StartingMoneyComputationTests
{
    // ACC:T55.2
    [Theory]
    [InlineData(5000, 0, 5000.0)]
    [InlineData(5000, 1, 7500.0)]
    [InlineData(5000, -1, 2500.0)]
    [InlineData(5000, -10, 2500.0)] // clamp to 0.5x
    [InlineData(5000, 10, 15000.0)] // clamp to 3.0x
    public void ShouldComputeStartingMoney_WhenUsingPresetAndCharacterStepDelta(int preset, int startingMoneyStepDelta, double expected)
    {
        var calc = ResolveStartingMoneyCalculatorType();
        var compute = ResolveComputeMethod(calc);

        var result = compute.Invoke(null, new object[] { preset, startingMoneyStepDelta });
        result.Should().NotBeNull();
        Convert.ToDecimal(result).Should().Be(Convert.ToDecimal(expected));
    }

    private static Type ResolveStartingMoneyCalculatorType()
    {
        var asm = typeof(GameStartConfig).Assembly;
        var type = asm.GetType("Game.Core.Domain.SanguoStartingMoneyCalculator");
        type.Should().NotBeNull("T55 requires a deterministic starting money calculator in Game.Core.Domain");
        return type!;
    }

    private static System.Reflection.MethodInfo ResolveComputeMethod(Type type)
    {
        var method = type.GetMethod(
            "ComputeStartingMoney",
            System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static,
            binder: null,
            types: new[] { typeof(int), typeof(int) },
            modifiers: null);

        method.Should().NotBeNull("ComputeStartingMoney(int preset, int startingMoneyStepDelta) must exist");
        return method!;
    }
}
