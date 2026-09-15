# Project Health: Knowledge + Impact

这是 `workflow.md` 2.4 本地 Project Health 服务下的二级页面 `/knowledge/`。它与首页共享同一个 `127.0.0.1` loopback 服务，不创建第二套服务，也不改变 Chapter 3–7 的调用协议。

## 启动

```powershell
py -3 scripts/python/dev_cli.py serve-project-health
```

打开输出 URL，在首页进入 `Knowledge + Impact`。首次使用先执行 `Scan local main`。

扫描只读取本地 `refs/heads/main` 的受控来源，不 fetch、不 checkout 当前工作分支，也不改 Taskmaster。无 Git 时使用受限目录扫描和内容摘要身份。扫描失败会保留上一次成功结果。

## Godot 场景图投影

Knowledge 页面现在提供只读 Godot 场景图 `/knowledge/scenes`。图从扫描 revision 对应的 `project.godot` `application/run/main_scene` 开始，确定性解析 `.tscn`、`.gd`、`.cs` 以及静态资源路径，并通过 `/api/knowledge/scene-graph` 暴露 revision-bound 结果。

场景边分为两类证据：

- `effective`：显式 PackedScene 实例化或明确 scene switch/instantiate 调用；可用于静态 reachability。
- `possible`：存在场景路径字面量，但没有足够触发证据；不得提升为已确认运行路径。

从 main scene 经 `effective` 边可达的场景标记为 `confirmed-reachable`。其余已扫描场景标记为 `unreachable-candidate`，并集中显示在 `/knowledge/scenes/unreachable`。这个标签表示“静态分析尚未证明入口”，不表示运行时绝对不可达。动态加载无法静态解析时保留为诊断证据，不伪造目标。

场景详情展示 Node、附着脚本、函数、事件、资源和任务知识关联。PNG/JPEG/WebP/SVG/GIF 图片仍通过 revision-bound Git blob 接口读取；用户浏览不会执行游戏或修改源文件。

## 页面能力

1. **Knowledge query**：输入中文需求、英文符号或文件路径，选择 consumer，查看 KCP 候选、实际 query、GDD 补充来源和 main 快照源码。
2. **Impact preview**：从精确 target 进入 Impact 关联文件、场景、测试、风险和解析遗漏。自然语言不会被直接冒充为 symbol id。
3. **Task navigation**：任务列表分页查看配置、代码、场景节点、素材、测试与原始证据。
4. **Godot scene graph**：查看 main scene 的静态 route tree、场景/脚本/资源详情和未确认场景。
5. **Source view**：源码链接绑定扫描 revision；revision 变化时拒绝混用快照。
6. **Runtime verification**：支持 local main 与 workspace 两种副本验证，运行产物只写到 `logs/ci/project-health-knowledge/runtime/`。
7. **Local configuration**：页面可编辑并保存 `scripts/python/project_health_knowledge_config.json`；保存配置与重新扫描是两个独立动作。

PNG/JPEG/WebP/SVG/GIF 相对路径可通过受限图片接口预览；接口只允许已扫描素材清单中的路径，并保持 main revision 绑定。

## Sanguo 默认业务绑定

Project Health 的仓库级默认配置使用 Sanguo 的真实 UI 表面，而不是 upstream 示例：

- task: `192`
- scene: `Game.Godot/Scenes/UI/Task192MainMenuSurface.tscn`
- script: `Game.Godot/Scripts/UI/Task192MainMenuSurface.gd`
- witness: `func get_surface_contract_key() -> String:`

默认查询别名覆盖 `主菜单/MainMenu`、`开始菜单/MainMenu`、`设置/Settings`、`战斗/Battle/SanguoBattle` 与 `三国/Sanguo`。

这些声明只能证明静态接入；不能替代运行时测试或业务验收。

## Knowledge Control Plane 边界

`knowledge/**` 是派生控制面，不是第二 SSoT。正式 repository authority 仍来自 `AGENTS.md`、`workflow.md`、Taskmaster、PRD/GDD、ADR/Base/Overlay、契约、测试规则、execution plans 与 decision logs。

正式 KCP 流程：

```powershell
py -3 scripts/python/publish_knowledge_catalog.py --publish
py -3 scripts/python/publish_knowledge_catalog.py --check
py -3 scripts/python/validate_knowledge_control_plane.py --require-generated
```

页面探索查询不会自动 accept/freeze/publish，也不会把 preview 直接当作正式 handoff。

## Chapter 6 element capture

`chapter6-knowledge` 在现有 task resource capture 之后还会写入：

- `docs/knowledge/generated/chapter6-task-<id>-elements.json`
- `docs/knowledge/generated/chapter6-task-<id>-documentation-gaps.md`

manifest 记录与任务已关联或当前工作树发生变化的 Godot scene、script、config、asset，并使用 `verified`、`inferred`、`unmapped` 状态。已识别的 scene 会附带静态 Node、attached scripts、published events 与 reachability classification。

Documentation gaps 为 non-blocking 后续项：未绑定的 scene/script 记为 `P1`，缺少 confirmed semantic focus 的资源记为 `P2`。它们用于提示下一轮知识沉淀，不把“100% 文档覆盖”误做成 Chapter 6 通过条件。

## Impact 边界

页面 Impact 是探索视图；正式 Impact 仍通过 revision-bound 工具链生成。Sanguo 的 Impact identity 文件必须指向真实根项目 `GodotGame.csproj`，并包含 Game.Core、测试工程、Godot project 与 Impact 工具自身。

正式分析与交接仍使用：

```powershell
py -3 scripts/python/build_impact_index.py --revision <sha>
py -3 scripts/python/analyze_impact.py ...
```

并发分析时，未获得共享输出所有权的 writer 不再尝试先写 winner 的输出目录；其 failure evidence 优先写入独立 run 目录。这保持 `[success, index_identity_collision]` 语义稳定，并避免 failure evidence 自身制造第二次路径竞争。

具体参数以脚本 `--help` 和 Knowledge freeze/handoff 契约为准。

## 安全边界

服务只允许 loopback Host。写操作要求当前 session token；错误 Host 或缺失 token 必须 fail closed。场景图 API 只消费已扫描 revision 与受限文件路径，不接受任意文件系统访问。CI 不会启动持久本地浏览器服务，只执行 HTTP handler 回归测试。

## 回归验证

```powershell
py -3 -m unittest scripts.sc.tests.test_project_health_sanguo_config scripts.sc.tests.test_project_health_http_surface scripts.sc.tests.test_project_health_server scripts.sc.tests.test_project_health_cli_status scripts.sc.tests.test_dev_cli_project_health_commands scripts.sc.tests.test_godot_scene_graph -v
py -3 scripts/python/validate_knowledge_control_plane.py
py -3 -m unittest discover -s scripts/python/tests -p "test_impact*.py" -v
node --check scripts/python/project_health_knowledge.js
node --check scripts/python/project_health_scenes.js
node --check scripts/python/project_health_unreachable.js
```

GitHub Actions 的 `Project Health Behavior` workflow 持续执行这一行为级门禁。
