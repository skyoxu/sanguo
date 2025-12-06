using System;
using Godot;

namespace Game.Godot.Adapters.Db;

public partial class DbTestHelper : Node
{
    public void ForceManaged()
    {
        System.Environment.SetEnvironmentVariable("GODOT_DB_BACKEND", "managed");
        System.Environment.SetEnvironmentVariable("GD_DB_JOURNAL", "DELETE");
    }

    private SqliteDataStore GetDb()
    {
        var db = GetNodeOrNull<SqliteDataStore>("/root/SqlDb");
        if (db == null) throw new InvalidOperationException("SqlDb not found at /root/SqlDb");
        return db;
    }

    public void CreateSchema()
    {
        var db = GetDb();
        // Core domain tables
        db.Execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT UNIQUE, created_at INTEGER, last_login INTEGER);");
        db.Execute("CREATE TABLE IF NOT EXISTS saves (id TEXT PRIMARY KEY, user_id TEXT, slot_number INTEGER, data TEXT, created_at INTEGER, updated_at INTEGER);");
        db.Execute("CREATE TABLE IF NOT EXISTS inventory_items (user_id TEXT, item_id TEXT, qty INTEGER, updated_at INTEGER, PRIMARY KEY(user_id, item_id));");
        // Schema versioning meta (single row id=1)
        db.Execute("CREATE TABLE IF NOT EXISTS schema_version (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL);");
        db.Execute("INSERT OR IGNORE INTO schema_version(id,version) VALUES(1,1);");
    }

    public void ClearAll()
    {
        var db = GetDb();
        try { db.Execute("DELETE FROM inventory_items;"); } catch { }
        try { db.Execute("DELETE FROM saves;"); } catch { }
        try { db.Execute("DELETE FROM users;"); } catch { }
    }

    public int GetSchemaVersion()
    {
        var db = GetDb();
        try
        {
            var rows = db.Query("SELECT version FROM schema_version WHERE id=1;");
            if (rows.Count == 0) return -1;
            var v = rows[0]["version"];
            if (v == null) return -1;
            return Convert.ToInt32(v);
        }
        catch
        {
            return -1;
        }
    }

    public void SetEnv(string key, string value)
    {
        System.Environment.SetEnvironmentVariable(key, value);
    }

    public void EnsureMinVersion(int minVersion)
    {
        var db = GetDb();
        // Ensure table exists and row present
        db.Execute("CREATE TABLE IF NOT EXISTS schema_version (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL);");
        db.Execute("INSERT OR IGNORE INTO schema_version(id,version) VALUES(1,1);");
        try
        {
            var rows = db.Query("SELECT version FROM schema_version WHERE id=1;");
            var cur = 0;
            if (rows.Count > 0 && rows[0].ContainsKey("version") && rows[0]["version"] != null)
                cur = Convert.ToInt32(rows[0]["version"]);
            if (cur < minVersion)
            {
                db.Execute("UPDATE schema_version SET version=@0 WHERE id=1;", minVersion);
            }
        }
        catch { }
    }

    // GDScript-friendly helpers to avoid calling C# params methods directly
    public void ExecSql(string sql)
    {
        var db = GetDb();
        db.Execute(sql);
    }

    public void ExecSql2(string sql, object p0, object p1)
    {
        var db = GetDb();
        db.Execute(sql, p0, p1);
    }

    public int QueryScalarInt(string sql)
    {
        var db = GetDb();
        var rows = db.Query(sql);
        if (rows.Count == 0) return 0;
        var row = rows[0];
        foreach (var kv in row)
        {
            if (kv.Value == null) continue;
            try { return Convert.ToInt32(kv.Value); } catch { }
        }
        return 0;
    }

    // Helpers to execute SQL against specific test DB nodes created under /root
    public void ExecOnNode(string nodeName, string sql)
    {
        var db = GetNodeOrNull<SqliteDataStore>("/root/" + nodeName);
        if (db == null) throw new InvalidOperationException($"SqliteDataStore not found at /root/{nodeName}");
        db.Execute(sql);
    }

    public void ExecOnNode2(string nodeName, string sql, object p0, object p1)
    {
        var db = GetNodeOrNull<SqliteDataStore>("/root/" + nodeName);
        if (db == null) throw new InvalidOperationException($"SqliteDataStore not found at /root/{nodeName}");
        db.Execute(sql, p0, p1);
    }

    public int QueryOnNode2(string nodeName, string sql, global::Godot.Variant p0)
    {
        var db = GetNodeOrNull<SqliteDataStore>("/root/" + nodeName);
        if (db == null) throw new InvalidOperationException($"SqliteDataStore not found at /root/{nodeName}");

        var key = (string)p0;
        var rows = db.Query(sql, key);
        if (rows.Count == 0) return 0;
        var row = rows[0];
        foreach (var kv in row)
        {
            if (kv.Value == null) continue;
            try { return Convert.ToInt32(kv.Value); } catch { }
        }
        return 0;
    }
}
