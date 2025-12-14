using System;
using System.Collections.Generic;

namespace Game.Core.Ports;

/// <summary>
/// Reports errors and exceptions for observability.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0003 (Observability and Release Health), ADR-0002 (Security Baseline), ADR-0004 (Event Bus and Contracts)
/// </remarks>
public interface IErrorReporter
{
    void CaptureMessage(string level, string message, IReadOnlyDictionary<string, string>? context = null);
    void CaptureException(string message, Exception ex, IReadOnlyDictionary<string, string>? context = null);
}

