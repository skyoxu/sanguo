namespace Game.Core.Domain.Threading;

/// <summary>
/// Per-instance guard to enforce single-threaded access to mutable domain objects.
/// </summary>
/// <remarks>
/// Uses a per-thread token to avoid rare managed thread id reuse edge cases.
/// </remarks>
public readonly record struct ThreadAccessGuard(int ThreadId, object ThreadToken)
{
    private static readonly System.Threading.ThreadLocal<object> _threadToken = new(() => new object());

    public static ThreadAccessGuard CaptureCurrentThread()
        => new(Environment.CurrentManagedThreadId, _threadToken.Value!);

    public void AssertCurrentThread()
    {
        if (!ReferenceEquals(_threadToken.Value, ThreadToken))
        {
            throw new InvalidOperationException(
                $"Thread access violation. Expected thread {ThreadId} but was {Environment.CurrentManagedThreadId}.");
        }
    }
}
