namespace Game.Core.Services.Sanguo;

public sealed record ReadableLoopSummary(
    string Phase,
    int Pressure,
    int Resources,
    int Hp,
    string Prompt,
    string Outcome,
    string RefusalReason,
    string VisibleText,
    IReadOnlyList<string> EvidenceTags);

public static class ReadableLoopSummaryProjector
{
    private static readonly string[] DefaultEvidenceTags =
    {
        "pure-core",
        "readable-loop",
        "deterministic-summary",
    };

    public static ReadableLoopSummary Project(
        string? phase,
        int pressure,
        int resources,
        int hp,
        string? prompt,
        string? outcome)
    {
        var normalized = new ReadableLoopSummary(
            Phase: Normalize(phase, "unknown"),
            Pressure: Math.Max(0, pressure),
            Resources: Math.Max(0, resources),
            Hp: Math.Max(0, hp),
            Prompt: Normalize(prompt, "none"),
            Outcome: Normalize(outcome, "none"),
            RefusalReason: string.Empty,
            VisibleText: string.Empty,
            EvidenceTags: DefaultEvidenceTags);

        return normalized with { VisibleText = BuildVisibleText(normalized) };
    }

    public static ReadableLoopSummary RefuseAction(ReadableLoopSummary current, string? reason)
    {
        var next = current with
        {
            RefusalReason = Normalize(reason, "refused"),
        };

        return next with { VisibleText = BuildVisibleText(next) };
    }

    private static string BuildVisibleText(ReadableLoopSummary summary)
    {
        var lines = new List<string>
        {
            $"Phase: {summary.Phase}",
            $"Pressure: {summary.Pressure}",
            $"Resources: {summary.Resources}",
            $"HP: {summary.Hp}",
            $"Prompt: {summary.Prompt}",
            $"Outcome: {summary.Outcome}",
        };

        if (!string.IsNullOrWhiteSpace(summary.RefusalReason))
        {
            lines.Add($"Refusal: {summary.RefusalReason}");
        }

        return string.Join("\n", lines);
    }

    private static string Normalize(string? value, string fallback)
    {
        var trimmed = (value ?? string.Empty).Trim();
        return string.IsNullOrWhiteSpace(trimmed) ? fallback : trimmed;
    }
}
