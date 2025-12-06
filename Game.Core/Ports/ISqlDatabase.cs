using System.Collections.Generic;

namespace Game.Core.Ports;

// Minimal SQL database port for Phase 6.
// Note: Actual implementation in Godot requires the godot-sqlite plugin.
public interface ISqlDatabase
{
    void Open(string dbPath);
    void Close();

    // Returns affected rows if applicable
    int Execute(string sql, params object[] parameters);

    // Returns raw rows as dictionary (column -> value). Mapping to DTOs is caller's job.
    List<Dictionary<string, object?>> Query(string sql, params object[] parameters);

    // Optional transaction helpers
    void BeginTransaction();
    void CommitTransaction();
    void RollbackTransaction();
}

