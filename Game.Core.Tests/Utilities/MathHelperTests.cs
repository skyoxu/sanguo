using FluentAssertions;
using Game.Core.Utilities;
using Xunit;

namespace Game.Core.Tests.Utilities;

public class MathHelperTests
{
    [Fact]
    public void ClampAndLerpBasic()
    {
        MathHelper.Clamp(5, 0, 10).Should().Be(5);
        MathHelper.Clamp(-1, 0, 10).Should().Be(0);
        MathHelper.Clamp(11, 0, 10).Should().Be(10);

        var v = MathHelper.Lerp(0.0, 10.0, 0.5);
        v.Should().BeApproximately(5.0, 1e-6);
        MathHelper.Lerp(0.0, 10.0, -1.0).Should().BeApproximately(0.0, 1e-6);
        MathHelper.Lerp(0.0, 10.0, 2.0).Should().BeApproximately(10.0, 1e-6);
    }
}

