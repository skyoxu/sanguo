#nullable enable

using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

namespace Game.Core.Services;

public static class SanguoDeterminism
{
    public static string ComputeCandidatesSortedIdsHash(IEnumerable<string> candidates)
    {
        if (candidates is null)
            throw new ArgumentNullException(nameof(candidates));

        var ids = candidates
            .Where(x => !string.IsNullOrWhiteSpace(x))
            .OrderBy(x => x, StringComparer.Ordinal)
            .ToArray();

        return ComputeSha256Hex(string.Join("\n", ids));
    }

    public static string ComputeCandidatesSortedIdsHash(IReadOnlyList<string> candidates)
        => ComputeCandidatesSortedIdsHash((IEnumerable<string>)candidates);

    public static string ComputeCandidatesSortedIdsHash(string[] candidates)
        => ComputeCandidatesSortedIdsHash((IEnumerable<string>)candidates);

    internal static string ComputeSha256Hex(string value)
    {
        var bytes = Encoding.UTF8.GetBytes(value ?? string.Empty);
        var hash = SHA256.HashData(bytes);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }
}
