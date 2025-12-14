# Serena MCP 常用命令参考

> Serena MCP 是基于 LSP（Language Server Protocol）的符号级代码检索与重构工具，专为 C# 项目优化。

---

## 核心命令分类

### 1. 符号检索命令

#### `find_symbol` - 查找符号定义

**用途**：按名称路径模式查找类、方法、接口、字段等符号。

**基础语法**：
```bash
find_symbol "<name_path_pattern>" [选项]
```

**核心参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name_path_pattern` | string | 必需 | 符号名称路径模式 |
| `--relative_path` | string | 空（全仓库） | 限定搜索的文件或目录路径 |
| `--substring_matching` | bool | false | 启用子串模糊匹配 |
| `--depth` | int | 0 | 递归深度（0=仅符号本身，1=含直接子成员） |
| `--include_body` | bool | false | 是否包含符号源代码体 |
| `--include_kinds` | int[] | 全部 | LSP 符号类型白名单（5=Class, 12=Function） |
| `--exclude_kinds` | int[] | 空 | LSP 符号类型黑名单 |

**名称路径模式规则**：

| 模式 | 匹配范围 | 示例 |
|------|---------|------|
| `"MyClass"` | 任何名为 MyClass 的符号 | 类 MyClass、方法 MyClass() |
| `"MyClass/MyMethod"` | MyClass 内的 MyMethod | MyClass.MyMethod() |
| `"/MyClass/MyMethod"` | 从文件根的绝对路径 | 必须完整匹配 |
| `"MyClass/MyMethod[0]"` | 重载方法的第一个版本 | MyMethod 的第 0 个重载 |

**LSP 符号类型代码（常用）**：
- `5` = Class
- `6` = Method
- `10` = Enum
- `11` = Interface
- `12` = Function
- `13` = Variable

**使用场景**：

##### 场景 1：模糊探索 - 发现所有相关代码

```bash
# 查找所有包含 "Guild" 的符号（类、接口、方法等）
find_symbol "Guild" --substring_matching=true --depth=1

# 返回示例：
# - GuildService.cs（类）
# - IGuildRepository.cs（接口）
# - GuildCreated.cs（事件记录）
# - CreateGuild()（方法）
```

**适用时机**：
- 任务开始前的上下文收集
- 不确定具体符号名称
- 需要了解某个领域的全部相关代码

##### 场景 2：精确定位 - 查看具体实现

```bash
# 精确查找 GuildCreated 事件的定义
find_symbol "GuildCreated" --relative_path "Game.Core/Contracts/Guild/" --include_body=true

# 返回示例：
# namespace Game.Core.Contracts.Guild;
# public sealed record GuildCreated(string GuildId, ...)
# {
#     public const string EventType = "core.guild.created";
# }
```

**适用时机**：
- 已知确切符号名称
- 需要查看完整源代码
- 理解契约定义细节

##### 场景 3：接口探索 - 只看方法签名

```bash
# 查找 IGuildService 接口及其方法（不含方法体）
find_symbol "IGuildService" --depth=1 --include_body=false

# 返回示例：
# interface IGuildService
# {
#     Task<Guild> CreateGuild(string name);  // 签名
#     Task<bool> DeleteGuild(string id);     // 签名
# }
```

**适用时机**：
- 理解接口设计
- 规划新方法扩展点
- 避免重复定义

##### 场景 4：类型过滤 - 只找特定类型符号

```bash
# 只查找接口（LSP kind=11）
find_symbol "Guild" --include_kinds=[11] --substring_matching=true

# 只查找类（LSP kind=5）
find_symbol "Service" --include_kinds=[5] --substring_matching=true
```

**适用时机**：
- 只关心接口设计
- 分析类层次结构
- 过滤掉方法/字段噪音

---

#### `find_referencing_symbols` - 查找符号引用

**用途**：找到所有引用指定符号的代码位置（调用者、使用者）。

**基础语法**：
```bash
find_referencing_symbols "<name_path>" --relative_path "<file_path>" [选项]
```

**核心参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name_path` | string | 必需 | 符号名称路径 |
| `relative_path` | string | 必需 | **符号所在的文件路径**（必须精确） |
| `--include_kinds` | int[] | 全部 | 过滤引用者的符号类型 |
| `--exclude_kinds` | int[] | 空 | 排除引用者的符号类型 |

**使用场景**：

##### 场景 1：依赖分析 - 谁在用这个接口

```bash
# 查找所有使用 IGuildRepository 接口的代码
find_referencing_symbols "IGuildRepository" --relative_path "Scripts/Core/Interfaces/IGuildRepository.cs"

# 返回示例（含代码片段）：
# - GuildService.cs:15
#   private readonly IGuildRepository _repo;
# - GuildController.cs:22
#   public GuildController(IGuildRepository repo)
```

**适用时机**：
- 重构前影响分析
- 理解依赖注入模式
- 检查接口使用一致性

##### 场景 2：重命名安全性检查 - 变更影响范围

```bash
# 重命名前检查所有引用点
find_referencing_symbols "GuildService" --relative_path "Scripts/Core/Services/GuildService.cs"

# 返回所有引用位置，确保重命名工具能覆盖所有文件
```

**适用时机**：
- 大规模重命名前的预检
- 确认跨文件引用完整性
- API 破坏性变更评估

##### 场景 3：理解调用链 - 功能流程追踪

```bash
# 查找谁调用了 CreateGuild 方法
find_referencing_symbols "GuildService/CreateGuild" --relative_path "Scripts/Core/Services/GuildService.cs"

# 返回调用链：
# - GuildManager.cs:45 → CreateGuild()
# - GuildTests.cs:12 → CreateGuild()（单元测试）
```

**适用时机**：
- 理解业务流程
- Debug 调用路径
- 确认测试覆盖

---

#### `search_for_pattern` - 正则模式搜索

**用途**：在代码中搜索任意正则表达式模式（类似高级 grep）。

**基础语法**：
```bash
search_for_pattern "<regex_pattern>" [选项]
```

**核心参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `substring_pattern` | string | 必需 | 正则表达式（Python re 模块语法） |
| `--relative_path` | string | 空 | 限定搜索的文件或目录 |
| `--paths_include_glob` | string | 空 | 包含文件的 glob 模式（如 `**/*.cs`） |
| `--paths_exclude_glob` | string | 空 | 排除文件的 glob 模式 |
| `--restrict_search_to_code_files` | bool | false | 只搜索有符号的代码文件 |
| `--context_lines_before` | int | 0 | 匹配前显示 N 行上下文 |
| `--context_lines_after` | int | 0 | 匹配后显示 N 行上下文 |

**正则语法提示**：
- 启用 `DOTALL` 和 `MULTILINE` 标志
- `.` 可匹配换行符
- 使用 `.*?` 非贪婪匹配避免过度匹配

**使用场景**：

##### 场景 1：查找接口定义模式

```bash
# 查找所有 IGuild 开头的接口定义
search_for_pattern "public.*interface.*IGuild" --paths_include_glob "**/*.cs"

# 返回：
# - IGuildService.cs:5
# - IGuildRepository.cs:3
```

**适用时机**：
- 符号工具找不到时的后备方案
- 需要正则表达式灵活性
- 跨文件模式分析

##### 场景 2：查找 TODO/FIXME 注释

```bash
# 查找所有 TODO 注释及其上下文
search_for_pattern "// TODO:.*" --context_lines_after=2

# 返回：
# GuildService.cs:45
# // TODO: Add validation
# public void CreateGuild(string name)
# {
```

**适用时机**：
- 技术债清点
- 代码审查准备
- 待办事项跟踪

##### 场景 3：查找特定命名约定

```bash
# 查找所有 EventType 常量定义
search_for_pattern "public const string EventType = \".*\"" --paths_include_glob "Game.Core/Contracts/**/*.cs"

# 返回所有事件契约的 EventType 定义
```

**适用时机**：
- 契约一致性检查
- 命名规范审计
- 模式合规性验证

---

### 2. 符号编辑命令

#### `replace_symbol_body` - 替换符号体

**用途**：完整替换类、方法、属性的定义（不含文档注释）。

**基础语法**：
```bash
replace_symbol_body "<name_path>" --relative_path "<file_path>" --body "<new_code>"
```

**核心参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `name_path` | string | 符号名称路径 |
| `relative_path` | string | 符号所在文件路径 |
| `body` | string | 新的符号定义代码（含签名） |

**符号体定义规则**：
- **包含**：签名行 + 方法体/类体
- **不包含**：前置 XML 文档注释、using 语句、命名空间声明

**使用场景**：

##### 场景 1：重构方法实现

```bash
# 替换 CreateGuild 方法的完整实现
replace_symbol_body "GuildService/CreateGuild" \
  --relative_path "Scripts/Core/Services/GuildService.cs" \
  --body "public async Task<Guild> CreateGuild(string name)
{
    // 新的实现逻辑
    ValidateName(name);
    var guild = new Guild { Name = name };
    await _repo.SaveAsync(guild);
    return guild;
}"
```

**适用时机**：
- TDD 绿灯阶段（填充实现）
- 重构整个方法逻辑
- API 签名和实现同时变更

##### 场景 2：更新类定义

```bash
# 替换整个类定义（添加新字段/方法）
replace_symbol_body "GuildService" \
  --relative_path "Scripts/Core/Services/GuildService.cs" \
  --body "public class GuildService : IGuildService
{
    private readonly IGuildRepository _repo;
    private readonly IEventBus _eventBus;  // 新增字段

    public GuildService(IGuildRepository repo, IEventBus eventBus)
    {
        _repo = repo;
        _eventBus = eventBus;  // 新增初始化
    }

    public async Task<Guild> CreateGuild(string name) { ... }
    public async Task PublishEvent(GuildEvent evt) { ... }  // 新增方法
}"
```

**适用时机**：
- 添加新依赖注入
- 扩展类功能
- 大规模重构

---

#### `insert_after_symbol` - 符号后插入

**用途**：在指定符号的定义**之后**插入新代码（如添加新方法）。

**基础语法**：
```bash
insert_after_symbol "<name_path>" --relative_path "<file_path>" --body "<new_code>"
```

**使用场景**：

##### 场景 1：添加新方法到类

```bash
# 在 GuildService 的最后一个方法后添加新方法
insert_after_symbol "GuildService/DeleteGuild" \
  --relative_path "Scripts/Core/Services/GuildService.cs" \
  --body "
    public async Task<bool> ArchiveGuild(string id)
    {
        var guild = await _repo.GetByIdAsync(id);
        guild.Status = GuildStatus.Archived;
        return await _repo.UpdateAsync(guild);
    }"
```

**适用时机**：
- 扩展现有类功能
- 添加新的公共 API
- TDD 红灯阶段（添加占位方法）

##### 场景 2：文件末尾添加新类

```bash
# 在文件最后一个符号后添加新类
insert_after_symbol "GuildService" \
  --relative_path "Scripts/Core/Services/GuildService.cs" \
  --body "
public class GuildValidator
{
    public bool IsValidName(string name) => !string.IsNullOrWhiteSpace(name);
}"
```

**适用时机**：
- 在同一文件添加辅助类
- 增量扩展功能

---

#### `insert_before_symbol` - 符号前插入

**用途**：在指定符号的定义**之前**插入新代码（如添加 using 语句）。

**基础语法**：
```bash
insert_before_symbol "<name_path>" --relative_path "<file_path>" --body "<new_code>"
```

**使用场景**：

##### 场景 1：添加 using 语句

```bash
# 在文件第一个类之前添加 using
insert_before_symbol "GuildService" \
  --relative_path "Scripts/Core/Services/GuildService.cs" \
  --body "using System.Linq;"
```

**适用时机**：
- 添加新依赖引用
- 补充缺失的命名空间

##### 场景 2：添加类前注释

```bash
# 在类定义前添加重要说明
insert_before_symbol "GuildService" \
  --relative_path "Scripts/Core/Services/GuildService.cs" \
  --body "// IMPORTANT: This service is thread-safe"
```

---

#### `rename_symbol` - 跨文件重命名

**用途**：安全重命名符号，自动更新所有引用。

**基础语法**：
```bash
rename_symbol "<name_path>" --relative_path "<file_path>" --new_name "<new_name>"
```

**核心参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `name_path` | string | 原符号名称路径 |
| `relative_path` | string | 符号所在文件路径 |
| `new_name` | string | 新符号名称 |

**使用场景**：

##### 场景 1：重命名类（自动更新所有引用）

```bash
# 重命名 GuildService → GuildManagerService
rename_symbol "GuildService" \
  --relative_path "Scripts/Core/Services/GuildService.cs" \
  --new_name "GuildManagerService"

# 自动更新：
# - 文件名：GuildService.cs → GuildManagerService.cs
# - 所有引用：IGuildService → IGuildManagerService
# - 所有构造函数调用
# - 所有类型声明
```

**适用时机**：
- 大规模重命名重构
- 统一命名规范
- 消除命名歧义

##### 场景 2：重命名方法（保持接口一致性）

```bash
# 重命名方法 CreateGuild → CreateNewGuild
rename_symbol "GuildService/CreateGuild" \
  --relative_path "Scripts/Core/Services/GuildService.cs" \
  --new_name "CreateNewGuild"

# 自动更新所有调用点
```

**适用时机**：
- API 清晰化重命名
- 消除方法名冲突

---

### 3. 文件操作命令

#### `read_file` - 读取文件

**用途**：读取文件内容（带行号）。

**基础语法**：
```bash
read_file "<relative_path>" [--start_line=N] [--end_line=M]
```

**核心参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `relative_path` | string | 必需 | 文件相对路径 |
| `start_line` | int | 0 | 起始行号（0-based） |
| `end_line` | int | null | 结束行号（null=读到末尾） |

**使用场景**：

##### 场景 1：查看完整文件

```bash
read_file "Game.Core/Contracts/Guild/GuildCreated.cs"
```

##### 场景 2：只读文件片段

```bash
# 读取第 10-20 行
read_file "Scripts/Core/Services/GuildService.cs" --start_line=10 --end_line=20
```

---

#### `replace_content` - 正则替换文件内容

**用途**：在文件中用正则表达式查找并替换内容。

**基础语法**：
```bash
replace_content --relative_path "<file_path>" --needle "<pattern>" --repl "<replacement>" --mode "<literal|regex>"
```

**核心参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `relative_path` | string | 文件路径 |
| `needle` | string | 查找模式（字面量或正则） |
| `repl` | string | 替换内容 |
| `mode` | string | `literal`（字面量）或 `regex`（正则表达式） |
| `allow_multiple_occurrences` | bool | 是否允许多次匹配（默认 false，防止误替换） |

**正则模式特性**：
- 支持捕获组：`$!1`, `$!2` 引用匹配组
- 非贪婪匹配推荐：`.*?`
- DOTALL + MULTILINE 模式启用

**使用场景**：

##### 场景 1：替换单行代码

```bash
# 字面量模式
replace_content \
  --relative_path "Scripts/Core/Services/GuildService.cs" \
  --needle "private readonly IGuildRepository _repo;" \
  --repl "private readonly IGuildRepository _guildRepo;" \
  --mode literal
```

##### 场景 2：正则批量替换

```bash
# 正则模式：将所有 Logger.Log() 改为 Logger.Info()
replace_content \
  --relative_path "Scripts/Core/Services/GuildService.cs" \
  --needle "Logger\.Log\((.*?)\)" \
  --repl "Logger.Info($!1)" \
  --mode regex \
  --allow_multiple_occurrences=true
```

**适用时机**：
- 符号工具不适用的场景
- 跨行复杂模式替换
- 批量文本更新

---

### 4. 项目与记忆命令

#### `get_symbols_overview` - 获取文件符号概览

**用途**：快速查看文件的顶层符号结构（不含方法体）。

**基础语法**：
```bash
get_symbols_overview "<relative_path>"
```

**使用场景**：

##### 场景 1：理解新文件结构

```bash
get_symbols_overview "Scripts/Core/Services/GuildService.cs"

# 返回示例：
# - class GuildService
#   - field: _repo
#   - method: CreateGuild
#   - method: DeleteGuild
```

**适用时机**：
- 首次接触新文件
- 规划扩展点
- 快速理解类结构

---

#### `write_memory` / `read_memory` - 会话记忆

**用途**：在 Serena 会话中存储/读取上下文信息（跨会话持久化）。

**基础语法**：
```bash
write_memory "<memory_name>" --content "<information>"
read_memory "<memory_name>"
list_memories
delete_memory "<memory_name>"
```

**使用场景**：

##### 场景 1：保存检索结果

```bash
# 保存当前任务的关键发现
write_memory "task-1.1-findings" --content "
发现：
- GuildService 已存在，需扩展而非新建
- 事件命名遵循 core.guild.* 规范
- 依赖注入已在 GuildRepository 使用
"

# 下次会话恢复
read_memory "task-1.1-findings"
```

**适用时机**：
- 保存任务上下文
- 记录重要决策
- 跨会话工作流

---

## 最佳实践与工作流

### 工作流 1：前置检索（Task 开始前）

```bash
# 步骤 1：模糊探索 - 了解全局
find_symbol "Guild" --substring_matching=true --depth=1

# 步骤 2：精确定位 - 查看契约
find_symbol "GuildCreated" --relative_path "Game.Core/Contracts/Guild/" --include_body=true

# 步骤 3：依赖分析 - 理解使用模式
find_referencing_symbols "IGuildRepository" --relative_path "Scripts/Core/Interfaces/IGuildRepository.cs"

# 步骤 4：保存发现
write_memory "task-context" --content "已有 GuildService, IGuildRepository, GuildCreated 事件"
```

### 工作流 2：TDD 实现

```bash
# 红灯：添加测试方法
insert_after_symbol "GuildServiceTests/TestCreateGuild" \
  --relative_path "Game.Core.Tests/Services/GuildServiceTests.cs" \
  --body "
    [Fact]
    public async Task CreateGuild_should_validate_name()
    {
        // Arrange
        var service = new GuildService(_mockRepo.Object);

        // Act & Assert
        await Assert.ThrowsAsync<ValidationException>(() => service.CreateGuild(\"\"));
    }"

# 绿灯：实现验证逻辑
replace_symbol_body "GuildService/CreateGuild" \
  --relative_path "Scripts/Core/Services/GuildService.cs" \
  --body "public async Task<Guild> CreateGuild(string name)
{
    if (string.IsNullOrWhiteSpace(name))
        throw new ValidationException(\"Name required\");

    var guild = new Guild { Name = name };
    await _repo.SaveAsync(guild);
    return guild;
}"
```

### 工作流 3：重构安全性

```bash
# 步骤 1：检查影响范围
find_referencing_symbols "GuildService" --relative_path "Scripts/Core/Services/GuildService.cs"

# 步骤 2：安全重命名
rename_symbol "GuildService" \
  --relative_path "Scripts/Core/Services/GuildService.cs" \
  --new_name "GuildManagerService"

# 步骤 3：验证引用更新
find_referencing_symbols "GuildManagerService" --relative_path "Scripts/Core/Services/GuildManagerService.cs"
```

---

## 常见错误与排查

### 错误 1：符号未找到

**症状**：`find_symbol "MyClass"` 返回空结果

**排查**：
```bash
# 1. 检查路径限定是否过严
find_symbol "MyClass" --relative_path ""  # 移除路径限定

# 2. 启用模糊匹配
find_symbol "Class" --substring_matching=true

# 3. 使用正则后备方案
search_for_pattern "class.*MyClass" --paths_include_glob "**/*.cs"
```

### 错误 2：重命名失败

**症状**：`rename_symbol` 报错 "Multiple matches found"

**排查**：
```bash
# 使用更精确的路径
rename_symbol "MyClass" \
  --relative_path "Scripts/Core/Services/MyClass.cs" \
  --new_name "MyService"

# 检查是否有重载方法需要指定索引
rename_symbol "MyClass/MyMethod[0]" ...
```

### 错误 3：正则替换过度匹配

**症状**：`replace_content` 替换了不该改的地方

**排查**：
```bash
# 1. 先不允许多次匹配，检查唯一性
replace_content --needle "..." --repl "..." --mode regex --allow_multiple_occurrences=false

# 2. 使用非贪婪匹配
--needle "Logger\.Log\(.*?\)"  # 非贪婪 .*?

# 3. 增加更多上下文
--needle "private.*Logger\.Log\(.*?\)"  # 限定 private 作用域
```

---

## 快速参考卡

### 检索命令速查

| 需求 | 命令 |
|------|------|
| 找所有 Guild 相关代码 | `find_symbol "Guild" --substring_matching=true` |
| 查看 GuildCreated 源码 | `find_symbol "GuildCreated" --include_body=true` |
| 查看类的方法列表 | `find_symbol "MyClass" --depth=1` |
| 找谁调用了这个方法 | `find_referencing_symbols "MyClass/MyMethod" --relative_path "..."` |
| 正则搜索接口定义 | `search_for_pattern "public.*interface.*I"` |

### 编辑命令速查

| 需求 | 命令 |
|------|------|
| 替换方法实现 | `replace_symbol_body "Class/Method" --body "..."` |
| 添加新方法到类末尾 | `insert_after_symbol "Class/LastMethod" --body "..."` |
| 添加 using 语句 | `insert_before_symbol "FirstClass" --body "using ..."` |
| 重命名类 | `rename_symbol "OldName" --new_name "NewName"` |
| 正则批量替换 | `replace_content --mode regex --needle "..." --repl "..."` |

---

## 与其他工具的配合

### 配合 SuperClaude

```bash
# SuperClaude analyze 阶段 → 使用 Serena 前置检索
/sc:analyze --task 1.1 --focus architecture,security
# ↓ 内部自动调用 Serena
# find_symbol "Guild" --substring_matching=true
# find_symbol "GuildCreated" --include_body=true

# SuperClaude build 阶段 → Serena 自动重构
/sc:build --task 1.1 --tdd
# ↓ TDD 绿灯后可能调用 Serena
# replace_symbol_body "GuildService/CreateGuild" --body "..."
```

### 配合 Task Master

```bash
# Task Master 识别任务后 → Serena 检索上下文
npx task-master next  # 输出：Task 1.1 实现公会创建
find_symbol "Guild" --substring_matching=true  # 检索现有代码
write_memory "task-1.1-context" --content "..."  # 保存发现

# 实现完成后 → 更新任务状态
npx task-master set-status 1.1 done
```

---

## 性能提示

1. **优先使用符号工具**：`find_symbol` 比 `search_for_pattern` 快 10-100 倍
2. **限定搜索范围**：使用 `--relative_path` 减少扫描文件数
3. **避免 `--include_body=true` 的滥用**：只在需要源码时启用
4. **正则替换前先验证**：`allow_multiple_occurrences=false` 防止误改
5. **使用记忆缓存**：`write_memory` 避免重复检索

---

## 参考资源

- Serena MCP GitHub: https://github.com/microsoft/serena-mcp
- LSP 符号类型文档: https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#symbolKind
- 项目 CLAUDE.md: 本仓库 Serena 集成指引
- Task Master 工作流: `docs/workflows/task-master-superclaude-integration.md`
