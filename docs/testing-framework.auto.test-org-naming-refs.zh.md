### 2. 测试组织（目录 SSoT）

本仓库测试目录是 **SSoT**，以真实目录为准：

```
Game.Core.Tests/                      # xUnit: 纯 C#（不依赖 Godot）
  Domain/                             # 领域实体/值对象
  Services/                           # 领域服务/用例服务（如 Turn/Economy）
  State/                              # 状态机/状态管理
  Repositories/                       # 仓储/存储适配（纯 C# 的契约或内存实现）
  Engine/                             # 纯 C# 的引擎骨架/胶水（非 Godot）
  Tasks/                              # 任务级别的验收用例（只放稳定 tests，不保留 RedTests）
  Utilities/                          # 通用工具

Tests.Godot/tests/                    # GdUnit4: Godot headless（依赖场景树/节点/信号）
  Scenes/                             # 场景/节点生命周期/可见性/信号连通
  UI/                                 # UI 行为（HUD/MainMenu/Settings）
  Integration/                        # 跨模块集成（导航流/事件流/持久化跨重启等）
  Adapters/                           # Godot 适配层行为（EventBusAdapter/Config/Db）
  Security/                           # 安全烟测（allow/deny/invalid + 审计）
```

### 3. 路径与命名约定（含 `Refs:` 硬门禁）

#### 3.1 `acceptance[]` 必须追加 `Refs:`（硬门禁）

目的：把“任务语义”变成可确定性验证的证据链，避免“done 不真实”。

- 对于“存在该任务条目”的视图（`tasks_back.json` 或 `tasks_gameplay.json`），其 `acceptance[]` 的**每一条**都必须以 `Refs:` 结尾（大小写不敏感）。  
  若某任务只存在于其中一侧视图，另一侧视图允许缺失（warning/skip），但至少必须存在一侧视图。
- `Refs:` 后仅允许写**仓库相对路径**，并且必须指向测试文件：
  - xUnit：`Game.Core.Tests/**/*.cs`
  - GdUnit4：`Tests.Godot/tests/**/*.gd`
- 一个 acceptance 条目可对应多个测试文件（空格或逗号分隔）。
- `Refs:` 里**不要**写绝对路径、不要写带空格的路径、不要写行号锚点（例如 `#L10`）。目前门禁只解析“文件路径”。
- 注意：`Refs:` 使用**仓库根目录**相对路径（例如 `Tests.Godot/tests/...`）；而 GdUnit4 运行器常用的 `--add tests/...` 是以 `--project Tests.Godot` 为根目录的**项目内相对路径**，两者不要混用。

示例（xUnit）：

```
- When treasury deposits, non-negative amount is enforced. Refs: Game.Core.Tests/Domain/SanguoTreasuryTests.cs
```

示例（GdUnit4）：

```
- HUD updates dice result after event. Refs: Tests.Godot/tests/UI/test_hud_updates_on_events.gd
```

对应门禁（自动运行，无需手工记）：  
- `py -3 scripts/python/validate_acceptance_refs.py --task-id <id> --stage refactor ...`  
- `py -3 scripts/python/validate_task_test_refs.py --task-id <id> --require-non-empty ...`
#### 3.1.1 `Refs:` 的语义绑定：`ACC:T<id>.<n>`（硬门禁）

`Refs:` 解决“指向哪个文件”，但无法保证“该文件内容真的覆盖该条 acceptance”。为降低“假 done”，本仓库引入 acceptance anchor：

- 对于任务 `T<id>` 的第 `n` 条 acceptance（**1-based**，下标按该任务视图的 `acceptance[]` 数组顺序），其 anchor 为：`ACC:T<id>.<n>`
- 该条 acceptance 的 `Refs:` 指向的测试文件中，至少有一个文件必须包含该 anchor 字符串（任意位置均可）。
  - xUnit 建议写在 `[Trait("acceptance", "ACC:T<id>.<n>")]` 或测试文件注释块中。
  - GdUnit4 建议写在测试函数注释（如 `# acceptance: ACC:T<id>.<n>`）或文件头注释块中。
- 该规则只在 **refactor** 阶段作为硬门禁执行。
- 新任务要求：在进入 `tdd --stage refactor` 前，必须把本任务 `Refs:` 指向的测试文件补齐 anchors（否则 refactor 将 fail-fast）。
- 迁移说明：`scripts/python/backfill_acceptance_anchors_in_tests.py` 仅用于“历史任务的一次性迁移”，不应作为新任务的常规流程。

对应门禁（自动运行，无需手工记）：  
- `py -3 scripts/python/validate_acceptance_anchors.py --task-id <id> --stage refactor ...`

#### 3.2 `test_refs[]`（任务级汇总）如何维护

`test_refs` 是任务级证据清单（路径列表），用于：

- 让验收脚本在 refactor 阶段做硬门禁；
- 让后续任务可以“发现/复用”已有测试证据；
- 防止只写了 `Refs:` 但没真正把文件纳入任务证据范围。

规则：

- 对于“存在该任务条目”的视图，其 `test_refs` 必须是非空列表（refactor 硬门禁）。  
  若某任务只存在于其中一侧视图，另一侧视图允许缺失（warning/skip），但至少必须存在一侧视图。
- `test_refs` 至少包含本任务所有 acceptance `Refs:` 的并集（refactor 硬门禁）。

推荐的更新方式（确定性脚本）：

```powershell
py -3 scripts/python/update_task_test_refs_from_acceptance_refs.py --task-id <id> --mode replace --write
```

#### 3.3 默认 Refs 路径约定（Core / xUnit）

优先复用现有目录语义：Domain/Services/State/Repositories/Engine/Utilities。

| 任务类型（倾向） | 推荐 `Refs:` 路径前缀 | 文件命名规范 |
|---|---|---|
| 领域实体/值对象 | `Game.Core.Tests/Domain/` | `{Subject}Tests.cs` |
| 领域服务/回合/经济 | `Game.Core.Tests/Services/` | `{Subject}Tests.cs` |
| 状态机/状态管理 | `Game.Core.Tests/State/` | `{Subject}Tests.cs` |
| 适配器契约/仓储 | `Game.Core.Tests/Repositories/` | `{Subject}Tests.cs` |
| 任务级验收（只在确实跨多个类时） | `Game.Core.Tests/Tasks/` | `Task<id><Topic>Tests.cs` |

约束：

- `Game.Core.Tests/Tasks/Task<id>RedTests.cs` 只允许作为 red 阶段的临时骨架；到 refactor 阶段必须迁移/删除。

#### 3.4 默认 Refs 路径约定（Godot / GdUnit4）

| 任务类型（倾向） | 推荐 `Refs:` 路径前缀 | 文件命名规范（建议） |
|---|---|---|
| 场景/节点行为 | `Tests.Godot/tests/Scenes/<Module>/` | `test_<module>_<scene>_<behavior>.gd` |
| UI 行为 | `Tests.Godot/tests/UI/` | `test_<ui>_<behavior>.gd` |
| 跨模块集成流 | `Tests.Godot/tests/Integration/` | `test_<flow>_<behavior>.gd` |
| 适配器行为 | `Tests.Godot/tests/Adapters/` | `test_<adapter>_<behavior>.gd` |
| 安全烟测 | `Tests.Godot/tests/Security/` | `test_<surface>_<allow|deny|invalid>_audit.gd` |

#### 3.5 测试命名约定（与门禁对齐）

**C#（xUnit）**

- 文件：`{ClassName}Tests.cs`
- 方法名（二选一，均为 PascalCase，禁止 snake_case）：
  - `ShouldDoX_WhenY`
  - `GivenX_WhenY_ThenZ`

示例：

```csharp
[Fact]
public void ShouldDeductMoney_WhenBuyingCity()
{
}

[Fact]
public void GivenEnoughMoney_WhenBuyingCity_ThenCityOwned()
{
}
```

**GdUnit4（GDScript）**

- 文件：`test_<scope>_<behavior>.gd`（与现有 `Tests.Godot/tests/**` 风格一致）
- 方法：`func test_<behavior>() -> void:`

示例：

```gdscript
extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func test_hud_updates_on_dice_rolled_event() -> void:
    pass
```

稳定性约束（避免 flaky）：

- 不要依赖真实时间 `create_timer()` + 窄容差断言；优先用信号/条件等待 + 超时上限。
- headless 下不要依赖真实输入事件链；优先调用公开方法/发最小信号/发布领域事件。
