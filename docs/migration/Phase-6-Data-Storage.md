# Phase 6: SQLite 数据层迁移

> 状态: 实施阶段
> 预估工时: 5-7 天
> 风险等级: 中
> 前置条件: Phase 1-5 完成

---

## 目标

将 vitegame 的 better-sqlite3 数据库迁移到 godotgame 的 godot-sqlite，建立类型安全的仓储层和迁移系统。

---

## 技术栈对比

| 功能 | vitegame (Node.js) | godotgame (Godot) |
|-----|-------------------|------------------|
| 库 | better-sqlite3 | godot-sqlite (GDNative) |
| 初始化 | `new Database('game.db')` | `SQLite.new() + open_db()` |
| 查询 | `.prepare().all()` | `.query() + .query_result` |
| 参数化 | `stmt.bind(params)` | 字符串插值（注意注入） |
| 事务 | `.transaction()` | 手动 BEGIN/COMMIT |
| 类型 | JavaScript 对象 | Godot.Collections.Dictionary |

---

## 数据库架构

### 当前 Schema (vitegame)

```sql
-- 用户数据
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    created_at INTEGER NOT NULL,
    last_login INTEGER
);

-- 玩家存档
CREATE TABLE saves (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    slot_number INTEGER NOT NULL,
    data TEXT NOT NULL, -- JSON 序列化
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, slot_number)
);

-- 游戏统计
CREATE TABLE statistics (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    stat_key TEXT NOT NULL,
    stat_value REAL NOT NULL,
    recorded_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Schema 版本控制
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at INTEGER NOT NULL,
    description TEXT
);
```

### 目标 Schema (godotgame)

保持相同结构，但添加：

```sql
-- 新增：成就系统
CREATE TABLE achievements (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    achievement_key TEXT NOT NULL,
    unlocked_at INTEGER NOT NULL,
    progress REAL DEFAULT 0.0,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, achievement_key)
);

-- 新增：设置存储
CREATE TABLE settings (
    user_id TEXT PRIMARY KEY,
    audio_volume REAL DEFAULT 1.0,
    graphics_quality TEXT DEFAULT 'medium',
    language TEXT DEFAULT 'en',
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

> 【Deprecated by ADR-0023】`settings` 表仅作为历史 schema 兼容保留。当前 Settings 的唯一 SSoT 为 ConfigFile（user://settings.cfg），DB 中该表不再作为设置的权威来源，迁移策略与实现见 ADR-0023 与 ADR-0006（Godot 变体）。

---

## IDataStore 实现（Phase 5 接口）

### 接口定义（回顾）

```csharp
// Game.Core/Ports/IDataStore.cs

namespace Game.Core.Ports;

public interface IDataStore
{
    void Open(string dbPath);
    void Close();
    void Execute(string sql, params object[] parameters);
    T? QuerySingle<T>(string sql, params object[] parameters) where T : class;
    List<T> Query<T>(string sql, params object[] parameters) where T : class;
}
```

### Godot SQLite 适配器（增强版）

```csharp
// Game.Godot/Adapters/SqliteDataStore.cs

using Godot;
using Game.Core.Ports;
using System.Reflection;

namespace Game.Godot.Adapters;

/// <summary>
/// 使用 godot-sqlite 插件的适配器（增强版）
/// 支持参数化查询、事务、类型映射
/// </summary>
public class SqliteDataStore : IDataStore
{
    private SQLite? _db;
    private bool _inTransaction = false;

    public void Open(string dbPath)
    {
        _db = new SQLite();
        _db.Path = dbPath;

        if (!_db.OpenDb())
        {
            throw new InvalidOperationException($"Failed to open database: {dbPath}");
        }

        // 启用外键约束
        Execute("PRAGMA foreign_keys = ON;");

        // 性能优化
        Execute("PRAGMA journal_mode = WAL;"); // Write-Ahead Logging
        Execute("PRAGMA synchronous = NORMAL;");
    }

    public void Close()
    {
        _db?.CloseDb();
        _db = null;
    }

    public void Execute(string sql, params object[] parameters)
    {
        if (_db == null)
            throw new InvalidOperationException("Database not opened");

        // 参数化查询（简化版，生产环境需更严格）
        string parameterizedSql = FormatSqlWithParameters(sql, parameters);

        var success = _db.Query(parameterizedSql);
        if (!success)
        {
            throw new InvalidOperationException($"SQL execution failed: {sql}");
        }
    }

    public T? QuerySingle<T>(string sql, params object[] parameters) where T : class
    {
        var results = Query<T>(sql, parameters);
        return results.FirstOrDefault();
    }

    public List<T> Query<T>(string sql, params object[] parameters) where T : class
    {
        if (_db == null)
            throw new InvalidOperationException("Database not opened");

        string parameterizedSql = FormatSqlWithParameters(sql, parameters);
        _db.Query(parameterizedSql);

        var results = new List<T>();

        for (int i = 0; i < _db.QueryResult.Length; i++)
        {
            var row = _db.QueryResult[i].As<Godot.Collections.Dictionary>();
            var instance = MapToObject<T>(row);
            if (instance != null)
            {
                results.Add(instance);
            }
        }

        return results;
    }

    /// <summary>
    /// 开始事务
    /// </summary>
    public void BeginTransaction()
    {
        if (_inTransaction)
            throw new InvalidOperationException("Transaction already in progress");

        Execute("BEGIN TRANSACTION;");
        _inTransaction = true;
    }

    /// <summary>
    /// 提交事务
    /// </summary>
    public void CommitTransaction()
    {
        if (!_inTransaction)
            throw new InvalidOperationException("No transaction in progress");

        Execute("COMMIT;");
        _inTransaction = false;
    }

    /// <summary>
    /// 回滚事务
    /// </summary>
    public void RollbackTransaction()
    {
        if (!_inTransaction)
            throw new InvalidOperationException("No transaction in progress");

        Execute("ROLLBACK;");
        _inTransaction = false;
    }

    /// <summary>
    /// 简化参数化（生产环境需使用 Prepared Statements）
    /// </summary>
    private string FormatSqlWithParameters(string sql, object[] parameters)
    {
        if (parameters == null || parameters.Length == 0)
            return sql;

        // 简单替换（警告：不防 SQL 注入，仅用于演示）
        for (int i = 0; i < parameters.Length; i++)
        {
            var param = parameters[i];
            string value = param switch
            {
                string s => $"'{EscapeSqlString(s)}'",
                int n => n.ToString(),
                long l => l.ToString(),
                double d => d.ToString(System.Globalization.CultureInfo.InvariantCulture),
                bool b => b ? "1" : "0",
                _ => "NULL"
            };

            sql = sql.Replace($"@{i}", value);
        }

        return sql;
    }

#### 安全提示与准备语句建议

> 重要：以上 `FormatSqlWithParameters` 仅为教学示例，无法防御复杂注入场景。生产实现应优先采用“预编译语句/绑定参数”能力；若所用的 `godot-sqlite` 版本支持 Prepared Statement，请参考官方接口使用绑定参数（如 `?1, ?2 ...`），并通过显式类型绑定（字符串转义、数值文化无关格式）写入。

建议做法：
- 在适配层为“只读查询/写入操作”分别提供封装，内部集中做参数绑定与错误处理；
- 为“动态构造 SQL”的场景，统一走“白名单字段名 + 绑定值”的策略，避免直接拼接；
- 使用单元测试覆盖“注入尝试/异常路径/事务回滚”等边界；
- 将“参数化开关/降级策略”暴露为配置项，CI 中禁止降级运行。

    /// <summary>
    /// 转义 SQL 字符串（基础版本）
    /// </summary>
    private string EscapeSqlString(string input)
    {
        return input.Replace("'", "''");
    }

    /// <summary>
    /// 映射 Dictionary 到 C# 对象（反射版本）
    /// </summary>
    private T? MapToObject<T>(Godot.Collections.Dictionary row) where T : class
    {
        var instance = Activator.CreateInstance<T>();
        var properties = typeof(T).GetProperties(BindingFlags.Public | BindingFlags.Instance);

        foreach (var prop in properties)
        {
            // 尝试多种命名约定
            string[] possibleKeys = {
                prop.Name,                           // UserId
                ToSnakeCase(prop.Name),              // user_id
                prop.Name.ToLower()                  // userid
            };

            foreach (var key in possibleKeys)
            {
                if (row.ContainsKey(key))
                {
                    try
                    {
                        var value = row[key];

                        // 类型转换
                        if (value != null && prop.CanWrite)
                        {
                            object convertedValue = prop.PropertyType.Name switch
                            {
                                nameof(String) => value.ToString() ?? string.Empty,
                                nameof(Int32) => Convert.ToInt32(value),
                                nameof(Int64) => Convert.ToInt64(value),
                                nameof(Double) => Convert.ToDouble(value),
                                nameof(Boolean) => Convert.ToBoolean(value),
                                nameof(DateTime) => DateTimeOffset.FromUnixTimeSeconds(Convert.ToInt64(value)).DateTime,
                                _ => value
                            };

                            prop.SetValue(instance, convertedValue);
                        }
                    }
                    catch (Exception ex)
                    {
                        GD.PrintErr($"Failed to map property {prop.Name}: {ex.Message}");
                    }

                    break;
                }
            }
        }

        return instance;
    }

    /// <summary>
    /// PascalCase → snake_case
    /// </summary>
    private string ToSnakeCase(string input)
    {
        return string.Concat(input.Select((x, i) =>
            i > 0 && char.IsUpper(x) ? "_" + x.ToString() : x.ToString()
        )).ToLower();
    }
}
```

---

## 领域模型 (C# DTOs)

### 用户实体

```csharp
// Game.Core/Domain/Entities/User.cs

namespace Game.Core.Domain.Entities;

public class User
{
    public string Id { get; set; } = string.Empty;
    public string Username { get; set; } = string.Empty;
    public long CreatedAt { get; set; }
    public long? LastLogin { get; set; }

    public User() { }

    public User(string username)
    {
        Id = Guid.NewGuid().ToString();
        Username = username;
        CreatedAt = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
    }
}
```

### 存档实体

```csharp
// Game.Core/Domain/Entities/SaveGame.cs

namespace Game.Core.Domain.Entities;

public class SaveGame
{
    public string Id { get; set; } = string.Empty;
    public string UserId { get; set; } = string.Empty;
    public int SlotNumber { get; set; }
    public string Data { get; set; } = string.Empty; // JSON
    public long CreatedAt { get; set; }
    public long UpdatedAt { get; set; }

    public SaveGame() { }

    public SaveGame(string userId, int slotNumber, string data)
    {
        Id = Guid.NewGuid().ToString();
        UserId = userId;
        SlotNumber = slotNumber;
        Data = data;
        CreatedAt = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        UpdatedAt = CreatedAt;
    }
}
```

---

## 仓储层实现

### 用户仓储接口

```csharp
// Game.Core/Domain/Repositories/IUserRepository.cs

namespace Game.Core.Domain.Repositories;

public interface IUserRepository
{
    User? GetById(string id);
    User? GetByUsername(string username);
    List<User> GetAll();
    void Create(User user);
    void Update(User user);
    void Delete(string id);
}
```

### 用户仓储实现

```csharp
// Game.Godot/Repositories/UserRepository.cs

using Game.Core.Domain.Entities;
using Game.Core.Domain.Repositories;
using Game.Core.Ports;

namespace Game.Godot.Repositories;

public class UserRepository : IUserRepository
{
    private readonly IDataStore _dataStore;

    public UserRepository(IDataStore dataStore)
    {
        _dataStore = dataStore ?? throw new ArgumentNullException(nameof(dataStore));
    }

    public User? GetById(string id)
    {
        const string sql = "SELECT id, username, created_at, last_login FROM users WHERE id = @0";
        return _dataStore.QuerySingle<User>(sql, id);
    }

    public User? GetByUsername(string username)
    {
        const string sql = "SELECT id, username, created_at, last_login FROM users WHERE username = @0";
        return _dataStore.QuerySingle<User>(sql, username);
    }

    public List<User> GetAll()
    {
        const string sql = "SELECT id, username, created_at, last_login FROM users ORDER BY created_at DESC";
        return _dataStore.Query<User>(sql);
    }

    public void Create(User user)
    {
        const string sql = @"
            INSERT INTO users (id, username, created_at, last_login)
            VALUES (@0, @1, @2, @3)";

        _dataStore.Execute(sql, user.Id, user.Username, user.CreatedAt, user.LastLogin ?? (object)DBNull.Value);
    }

    public void Update(User user)
    {
        const string sql = @"
            UPDATE users
            SET username = @0, last_login = @1
            WHERE id = @2";

        _dataStore.Execute(sql, user.Username, user.LastLogin ?? (object)DBNull.Value, user.Id);
    }

    public void Delete(string id)
    {
        const string sql = "DELETE FROM users WHERE id = @0";
        _dataStore.Execute(sql, id);
    }
}
```

---

## 数据库迁移系统

### 迁移管理器

```csharp
// Game.Core/Infrastructure/DatabaseMigration.cs

using Game.Core.Ports;

namespace Game.Core.Infrastructure;

public class DatabaseMigration
{
    private readonly IDataStore _dataStore;
    private readonly ILogger _logger;

    public DatabaseMigration(IDataStore dataStore, ILogger logger)
    {
        _dataStore = dataStore;
        _logger = logger;
    }

    /// <summary>
    /// 运行所有未应用的迁移
    /// </summary>
    public void Migrate()
    {
        EnsureSchemaVersionTable();

        int currentVersion = GetCurrentVersion();
        var migrations = GetMigrations();

        foreach (var migration in migrations.Where(m => m.Version > currentVersion))
        {
            _logger.LogInfo($"Applying migration {migration.Version}: {migration.Description}");

            try
            {
                _dataStore.BeginTransaction();
                migration.Up(_dataStore);
                RecordMigration(migration);
                _dataStore.CommitTransaction();

                _logger.LogInfo($"Migration {migration.Version} applied successfully");
            }
            catch (Exception ex)
            {
                _dataStore.RollbackTransaction();
                _logger.LogError($"Migration {migration.Version} failed", ex);
                throw;
            }
        }
    }

    private void EnsureSchemaVersionTable()
    {
        const string sql = @"
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at INTEGER NOT NULL,
                description TEXT
            )";

        _dataStore.Execute(sql);
    }

    private int GetCurrentVersion()
    {
        const string sql = "SELECT MAX(version) as version FROM schema_version";

        try
        {
            var result = _dataStore.QuerySingle<VersionRow>(sql);
            return result?.Version ?? 0;
        }
        catch
        {
            return 0;
        }
    }

    private void RecordMigration(Migration migration)
    {
        const string sql = @"
            INSERT INTO schema_version (version, applied_at, description)
            VALUES (@0, @1, @2)";

        _dataStore.Execute(sql, migration.Version, DateTimeOffset.UtcNow.ToUnixTimeSeconds(), migration.Description);
    }

    private List<Migration> GetMigrations()
    {
        return new List<Migration>
        {
            new Migration001_InitialSchema(),
            new Migration002_AddAchievements(),
            new Migration003_AddSettings()
        };
    }

    private class VersionRow
    {
        public int Version { get; set; }
    }
}
```

### 迁移基类

```csharp
// Game.Core/Infrastructure/Migration.cs

using Game.Core.Ports;

namespace Game.Core.Infrastructure;

public abstract class Migration
{
    public abstract int Version { get; }
    public abstract string Description { get; }
    public abstract void Up(IDataStore dataStore);
    public abstract void Down(IDataStore dataStore);
}
```

### 具体迁移示例

```csharp
// Game.Core/Infrastructure/Migrations/Migration001_InitialSchema.cs

using Game.Core.Ports;

namespace Game.Core.Infrastructure.Migrations;

public class Migration001_InitialSchema : Migration
{
    public override int Version => 1;
    public override string Description => "Initial database schema";

    public override void Up(IDataStore dataStore)
    {
        // Users 表
        dataStore.Execute(@"
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                created_at INTEGER NOT NULL,
                last_login INTEGER
            )");

        // Saves 表
        dataStore.Execute(@"
            CREATE TABLE saves (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                slot_number INTEGER NOT NULL,
                data TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, slot_number)
            )");

        // Statistics 表
        dataStore.Execute(@"
            CREATE TABLE statistics (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                stat_key TEXT NOT NULL,
                stat_value REAL NOT NULL,
                recorded_at INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )");

        // 索引
        dataStore.Execute("CREATE INDEX idx_saves_user_id ON saves(user_id)");
        dataStore.Execute("CREATE INDEX idx_statistics_user_id ON statistics(user_id)");
    }

    public override void Down(IDataStore dataStore)
    {
        dataStore.Execute("DROP TABLE IF EXISTS statistics");
        dataStore.Execute("DROP TABLE IF EXISTS saves");
        dataStore.Execute("DROP TABLE IF EXISTS users");
    }
}
```

```csharp
// Game.Core/Infrastructure/Migrations/Migration002_AddAchievements.cs

using Game.Core.Ports;

namespace Game.Core.Infrastructure.Migrations;

public class Migration002_AddAchievements : Migration
{
    public override int Version => 2;
    public override string Description => "Add achievements system";

    public override void Up(IDataStore dataStore)
    {
        dataStore.Execute(@"
            CREATE TABLE achievements (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                achievement_key TEXT NOT NULL,
                unlocked_at INTEGER NOT NULL,
                progress REAL DEFAULT 0.0,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, achievement_key)
            )");

        dataStore.Execute("CREATE INDEX idx_achievements_user_id ON achievements(user_id)");
    }

    public override void Down(IDataStore dataStore)
    {
        dataStore.Execute("DROP TABLE IF EXISTS achievements");
    }
}
```

---

## 启动时初始化

### ServiceLocator 集成

```csharp
// Game.Godot/Autoloads/ServiceLocator.cs (扩展)

public partial class ServiceLocator : Node
{
    public static ServiceLocator Instance { get; private set; } = null!;

    public IDataStore DataStore { get; private set; } = null!;
    public IUserRepository UserRepository { get; private set; } = null!;
    // ... 其他服务

    public override void _Ready()
    {
        Instance = this;

        // 初始化数据存储
        DataStore = new SqliteDataStore();
        DataStore.Open("user://game.db");

        // 运行迁移
        var logger = new GodotLogger("Migration");
        var migration = new DatabaseMigration(DataStore, logger);
        migration.Migrate();

        // 初始化仓储
        UserRepository = new UserRepository(DataStore);

        GD.Print("Database initialized and migrated successfully");
    }

    public override void _ExitTree()
    {
        DataStore?.Close();
    }
}
```

---

## 测试策略

### 单元测试（内存 SQLite）

```csharp
// Game.Core.Tests/Infrastructure/UserRepositoryTests.cs

using FluentAssertions;
using Game.Core.Domain.Entities;
using Game.Core.Tests.Fakes;
using Game.Godot.Repositories;
using Xunit;

namespace Game.Core.Tests.Infrastructure;

public class UserRepositoryTests : IDisposable
{
    private readonly FakeDataStore _dataStore;
    private readonly UserRepository _repository;

    public UserRepositoryTests()
    {
        _dataStore = new FakeDataStore();
        _dataStore.Open(":memory:");

        // 初始化 Schema
        _dataStore.Execute(@"
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                created_at INTEGER NOT NULL,
                last_login INTEGER
            )");

        _repository = new UserRepository(_dataStore);
    }

    [Fact]
    public void Create_ShouldAddUserToDatabase()
    {
        // Arrange
        var user = new User("test_user");

        // Act
        _repository.Create(user);

        // Assert
        var retrieved = _repository.GetById(user.Id);
        retrieved.Should().NotBeNull();
        retrieved!.Username.Should().Be("test_user");
    }

    [Fact]
    public void GetByUsername_ShouldReturnCorrectUser()
    {
        // Arrange
        var user = new User("alice");
        _repository.Create(user);

        // Act
        var retrieved = _repository.GetByUsername("alice");

        // Assert
        retrieved.Should().NotBeNull();
        retrieved!.Id.Should().Be(user.Id);
    }

    [Fact]
    public void Update_ShouldModifyExistingUser()
    {
        // Arrange
        var user = new User("bob");
        _repository.Create(user);

        // Act
        user.LastLogin = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        _repository.Update(user);

        // Assert
        var retrieved = _repository.GetById(user.Id);
        retrieved!.LastLogin.Should().Be(user.LastLogin);
    }

    [Fact]
    public void Delete_ShouldRemoveUser()
    {
        // Arrange
        var user = new User("charlie");
        _repository.Create(user);

        // Act
        _repository.Delete(user.Id);

        // Assert
        var retrieved = _repository.GetById(user.Id);
        retrieved.Should().BeNull();
    }

    public void Dispose()
    {
        _dataStore.Close();
    }
}
```

### 迁移测试

```csharp
// Game.Core.Tests/Infrastructure/DatabaseMigrationTests.cs

using FluentAssertions;
using Game.Core.Infrastructure;
using Game.Core.Tests.Fakes;
using Xunit;

namespace Game.Core.Tests.Infrastructure;

public class DatabaseMigrationTests : IDisposable
{
    private readonly FakeDataStore _dataStore;
    private readonly FakeLogger _logger;
    private readonly DatabaseMigration _migration;

    public DatabaseMigrationTests()
    {
        _dataStore = new FakeDataStore();
        _dataStore.Open(":memory:");

        _logger = new FakeLogger();
        _migration = new DatabaseMigration(_dataStore, _logger);
    }

    [Fact]
    public void Migrate_ShouldApplyAllMigrations()
    {
        // Act
        _migration.Migrate();

        // Assert
        var tables = _dataStore.Query<TableInfo>("SELECT name FROM sqlite_master WHERE type='table'");
        var tableNames = tables.Select(t => t.Name).ToList();

        tableNames.Should().Contain("users");
        tableNames.Should().Contain("saves");
        tableNames.Should().Contain("achievements");
        tableNames.Should().Contain("schema_version");
    }

    [Fact]
    public void Migrate_ShouldNotReapplyMigrations()
    {
        // Arrange
        _migration.Migrate();

        // Act
        _migration.Migrate();

        // Assert（没有抛出异常）
        var version = _dataStore.QuerySingle<VersionRow>("SELECT MAX(version) as version FROM schema_version");
        version!.Version.Should().BeGreaterThan(0);
    }

    public void Dispose()
    {
        _dataStore.Close();
    }

    private class TableInfo
    {
        public string Name { get; set; } = string.Empty;
    }

    private class VersionRow
    {
        public int Version { get; set; }
    }
}
```

---

## 数据迁移脚本

### 从 vitegame 迁移数据

```csharp
// scripts/MigrateData.cs (CLI 工具)

using Game.Core.Ports;
using Game.Godot.Adapters;

public class DataMigrationTool
{
    public static void Main(string[] args)
    {
        if (args.Length < 2)
        {
            Console.WriteLine("Usage: MigrateData <source.db> <target.db>");
            return;
        }

        string sourcePath = args[0];
        string targetPath = args[1];

        Console.WriteLine($"Migrating data from {sourcePath} to {targetPath}...");

        // 打开源数据库（假设使用 System.Data.SQLite）
        using var sourceConn = new System.Data.SQLite.SQLiteConnection($"Data Source={sourcePath}");
        sourceConn.Open();

        // 打开目标数据库（Godot SQLite 适配器）
        var targetStore = new SqliteDataStore();
        targetStore.Open(targetPath);

        // 迁移用户
        MigrateUsers(sourceConn, targetStore);

        // 迁移存档
        MigrateSaves(sourceConn, targetStore);

        // 迁移统计数据
        MigrateStatistics(sourceConn, targetStore);

        Console.WriteLine("Migration completed successfully!");
    }

    private static void MigrateUsers(System.Data.SQLite.SQLiteConnection source, IDataStore target)
    {
        using var cmd = new System.Data.SQLite.SQLiteCommand("SELECT id, username, created_at, last_login FROM users", source);
        using var reader = cmd.ExecuteReader();

        int count = 0;
        while (reader.Read())
        {
            string id = reader.GetString(0);
            string username = reader.GetString(1);
            long createdAt = reader.GetInt64(2);
            long? lastLogin = reader.IsDBNull(3) ? null : reader.GetInt64(3);

            target.Execute(
                "INSERT INTO users (id, username, created_at, last_login) VALUES (@0, @1, @2, @3)",
                id, username, createdAt, lastLogin ?? (object)DBNull.Value
            );

            count++;
        }

        Console.WriteLine($"Migrated {count} users");
    }

    private static void MigrateSaves(System.Data.SQLite.SQLiteConnection source, IDataStore target)
    {
        using var cmd = new System.Data.SQLite.SQLiteCommand("SELECT id, user_id, slot_number, data, created_at, updated_at FROM saves", source);
        using var reader = cmd.ExecuteReader();

        int count = 0;
        while (reader.Read())
        {
            string id = reader.GetString(0);
            string userId = reader.GetString(1);
            int slotNumber = reader.GetInt32(2);
            string data = reader.GetString(3);
            long createdAt = reader.GetInt64(4);
            long updatedAt = reader.GetInt64(5);

            target.Execute(
                "INSERT INTO saves (id, user_id, slot_number, data, created_at, updated_at) VALUES (@0, @1, @2, @3, @4, @5)",
                id, userId, slotNumber, data, createdAt, updatedAt
            );

            count++;
        }

        Console.WriteLine($"Migrated {count} save files");
    }

    private static void MigrateStatistics(System.Data.SQLite.SQLiteConnection source, IDataStore target)
    {
        using var cmd = new System.Data.SQLite.SQLiteCommand("SELECT id, user_id, stat_key, stat_value, recorded_at FROM statistics", source);
        using var reader = cmd.ExecuteReader();

        int count = 0;
        while (reader.Read())
        {
            string id = reader.GetString(0);
            string userId = reader.GetString(1);
            string statKey = reader.GetString(2);
            double statValue = reader.GetDouble(3);
            long recordedAt = reader.GetInt64(4);

            target.Execute(
                "INSERT INTO statistics (id, user_id, stat_key, stat_value, recorded_at) VALUES (@0, @1, @2, @3, @4)",
                id, userId, statKey, statValue, recordedAt
            );

            count++;
        }

        Console.WriteLine($"Migrated {count} statistics records");
    }
}
```

---

## CI 集成

### 数据库测试 (GitHub Actions)

```yaml
# .github/workflows/tests.yml

name: Tests

on: [push, pull_request]

jobs:
  database-tests:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup .NET 8
        uses: actions/setup-dotnet@v3
        with:
          dotnet-version: '8.0.x'

      - name: Restore dependencies
        run: dotnet restore Game.Core.Tests/Game.Core.Tests.csproj

      - name: Run database unit tests
        run: |
          dotnet test Game.Core.Tests/Game.Core.Tests.csproj `
            --filter "FullyQualifiedName~Infrastructure" `
            --no-restore `
            --verbosity normal `
            --collect:"XPlat Code Coverage"

      - name: Check migration integrity
        run: |
          # 验证所有迁移都有对应的测试
          $migrations = Get-ChildItem -Path Game.Core/Infrastructure/Migrations/*.cs
          foreach ($migration in $migrations) {
            $testFile = "Game.Core.Tests/Infrastructure/" + $migration.BaseName + "Tests.cs"
            if (-not (Test-Path $testFile)) {
              Write-Error "Missing test for migration: $($migration.Name)"
              exit 1
            }
          }
```

---

## 完成标准

- [ ] IDataStore 适配器完整实现（事务支持）
- [ ] User/SaveGame/Statistics 实体和仓储完成
- [ ] 数据库迁移系统可运行（Migration001-003）
- [ ] 所有仓储通过单元测试（内存 SQLite）
- [ ] 迁移系统通过集成测试
- [ ] 数据迁移脚本可从 vitegame 导入数据
- [ ] ServiceLocator 集成数据库初始化
- [ ] CI 管道包含数据库测试和迁移完整性检查

---

## 性能优化建议

1. **连接池**：Godot SQLite 不支持连接池，考虑使用单例模式
2. **批量插入**：使用事务包裹多条 INSERT 语句
3. **索引策略**：为高频查询字段（user_id, username）建立索引
4. **WAL 模式**：`PRAGMA journal_mode = WAL` 提升并发写入
5. **查询优化**：避免 SELECT \*，仅查询需要的字段

---

## 下一步

完成本阶段后，继续：

➡️ [Phase-7-UI-Migration.md](Phase-7-UI-Migration.md) — React → Godot Control 迁移
