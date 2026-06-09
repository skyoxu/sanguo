namespace Game.Core.Contracts;

/// <summary>
/// Describes the stable shape of a contract surface before or after an evolution step.
/// </summary>
public sealed record ContractShape(
    string Name,
    IReadOnlyList<string> Fields,
    IReadOnlyList<string> Behaviors)
{
    public static ContractShape Create(string name, IEnumerable<string> fields, IEnumerable<string> behaviors)
    {
        return new ContractShape(name, fields.ToArray(), behaviors.ToArray());
    }
}

/// <summary>
/// Lists later migration evidence that explicitly authorizes otherwise breaking contract changes.
/// </summary>
public sealed record ContractMigrationPlan(string Name, IReadOnlyList<string> AuthorizedChanges)
{
    public static readonly ContractMigrationPlan None = new("none", Array.Empty<string>());
}

/// <summary>
/// Reports whether a candidate contract shape is accepted and why breaking changes were blocked.
/// </summary>
public sealed record ContractEvolutionResult(bool IsAccepted, IReadOnlyList<string> BlockingReasons);

/// <summary>
/// Enforces additive contract evolution unless a later migration plan authorizes a breaking change.
/// </summary>
public static class ContractEvolutionPolicy
{
    public static ContractEvolutionResult Evaluate(
        ContractShape baseline,
        ContractShape candidate,
        ContractMigrationPlan migrationPlan)
    {
        var blockingReasons = new List<string>();

        foreach (var field in baseline.Fields.Except(candidate.Fields, StringComparer.Ordinal))
        {
            blockingReasons.Add($"Removed field: {field}");
        }

        foreach (var behavior in baseline.Behaviors.Except(candidate.Behaviors, StringComparer.Ordinal))
        {
            blockingReasons.Add($"Changed behavior: {behavior}");
        }

        var unauthorizedReasons = blockingReasons
            .Where(reason => !migrationPlan.AuthorizedChanges.Contains(reason, StringComparer.Ordinal))
            .ToArray();

        return new ContractEvolutionResult(unauthorizedReasons.Length == 0, unauthorizedReasons);
    }
}
