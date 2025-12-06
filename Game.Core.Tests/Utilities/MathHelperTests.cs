using Game.Core.Utilities;
using Xunit;

namespace Game.Core.Tests.Utilities;

public class MathHelperTests
{
    [Fact]
    public void Clamp_and_Lerp_basic()
    {
        Assert.Equal(5, MathHelper.Clamp(5, 0, 10));
        Assert.Equal(0, MathHelper.Clamp(-1, 0, 10));
        Assert.Equal(10, MathHelper.Clamp(11, 0, 10));

        var v = MathHelper.Lerp(0.0, 10.0, 0.5);
        Assert.Equal(5.0, v, 6);
        Assert.Equal(0.0, MathHelper.Lerp(0.0, 10.0, -1.0), 6);
        Assert.Equal(10.0, MathHelper.Lerp(0.0, 10.0, 2.0), 6);
    }
}

