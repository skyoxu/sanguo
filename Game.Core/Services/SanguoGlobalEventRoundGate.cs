#nullable enable

using System;
using System.Collections.Generic;

namespace Game.Core.Services;

public sealed class SanguoGlobalEventRoundGate
{
    private readonly HashSet<int> _checkedRounds = new();

    public bool TryMarkChecked(int roundNumber)
    {
        if (roundNumber <= 0)
            throw new ArgumentOutOfRangeException(nameof(roundNumber), "RoundNumber must be >= 1.");

        return _checkedRounds.Add(roundNumber);
    }
}

