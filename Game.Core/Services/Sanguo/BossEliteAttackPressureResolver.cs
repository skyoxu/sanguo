using System;
using System.Collections.Generic;
using System.Linq;

namespace Game.Core.Services.Sanguo;

public static class BossEliteAttackPressureResolver
{
    public static int ResolveEliteAttackCount(IReadOnlyList<int> bossDiceOutcomes)
    {
        ArgumentNullException.ThrowIfNull(bossDiceOutcomes);
        return bossDiceOutcomes.Count(outcome => outcome >= 5);
    }
}
