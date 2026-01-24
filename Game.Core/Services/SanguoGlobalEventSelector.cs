#nullable enable

using System;
using System.Buffers.Binary;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

namespace Game.Core.Services;

public sealed class SanguoGlobalEventSelector
{
    public SanguoGlobalEventSelectionResult Select(string rngContextId, int roundNumber, IEnumerable<string> candidates)
    {
        if (string.IsNullOrWhiteSpace(rngContextId))
            throw new ArgumentException("RngContextId must be non-empty.", nameof(rngContextId));

        if (roundNumber <= 0)
            throw new ArgumentOutOfRangeException(nameof(roundNumber), "RoundNumber must be >= 1.");

        if (candidates is null)
            throw new ArgumentNullException(nameof(candidates));

        var orderedCandidates = candidates
            .Where(x => !string.IsNullOrWhiteSpace(x))
            .OrderBy(x => x, StringComparer.Ordinal)
            .ToArray();

        if (orderedCandidates.Length == 0)
            throw new ArgumentException("Candidates must contain at least one non-empty id.", nameof(candidates));

        var candidatesSortedIdsHash = SanguoDeterminism.ComputeCandidatesSortedIdsHash(orderedCandidates);
        var pickedIndex = ComputeDeterministicIndex(rngContextId, roundNumber, candidatesSortedIdsHash, orderedCandidates.Length);
        var pickedId = orderedCandidates[pickedIndex];

        return new SanguoGlobalEventSelectionResult(
            RngContextId: rngContextId,
            CandidatesSortedIdsHash: candidatesSortedIdsHash,
            PickedIndex: pickedIndex,
            PickedId: pickedId);
    }

    private static int ComputeDeterministicIndex(string rngContextId, int roundNumber, string candidatesSortedIdsHash, int count)
    {
        var payload = $"{rngContextId}\n{roundNumber}\n{candidatesSortedIdsHash}";
        var bytes = Encoding.UTF8.GetBytes(payload);
        var hash = SHA256.HashData(bytes);

        var v = BinaryPrimitives.ReadUInt32LittleEndian(hash.AsSpan(0, 4));
        return (int)(v % (uint)count);
    }
}

public sealed record SanguoGlobalEventSelectionResult(
    string RngContextId,
    string CandidatesSortedIdsHash,
    int PickedIndex,
    string PickedId);
