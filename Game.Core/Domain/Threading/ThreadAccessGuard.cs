namespace Game.Core.Domain.Threading;

/// <summary>
/// Per-instance guard to enforce single-threaded access to mutable domain objects.
/// </summary>
public readonly record struct ThreadAccessGuard(int ThreadId)
{
    public static ThreadAccessGuard CaptureCurrentThread()
        => new(Environment.CurrentManagedThreadId);

    public void AssertCurrentThread()
    {
        if (Environment.CurrentManagedThreadId != ThreadId)
            throw new InvalidOperationException(
                $"Thread access violation. Expected thread {ThreadId} but was {Environment.CurrentManagedThreadId}.");
    }
}

