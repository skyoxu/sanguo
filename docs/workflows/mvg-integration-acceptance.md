# MVG 集成验收

本入口验证同一版本中多个 Sanguo 功能任务组合后的行为。保留现有功能任务、Chapter 6 review、交付 profile 门禁和 Knowledge/Impact 正式流程；不引入 Epic，也不自动修改任务状态。设计依据见 ADR-0037。

## 在现有章节中接入

| 阶段 | 补充动作 | 产物和检查 |
| --- | --- | --- |
| Chapter 3 任务编排 | 为跨任务链路指定整合责任。已有功能任务能承担就复用；无人承担时才通过现有任务三联流程补集成任务。 | manifest 的 task_ids 和 handoff owner_task 必须引用真实任务。 |
| Chapter 4 契约基线 | 明确每次交接的生产方、消费方、归属任务、契约引用和可观察行为。 | 每条 handoff 至少关联一个测试；引用现有契约，不复制字段正文。 |
| Chapter 5 语义稳定化 | 检查 planned 测试是否有明确行为，补齐已有任务验收引用。 | 继续使用现有 Refs/overlay 校验，不增加第二套任务状态。 |
| Chapter 6 开发和收尾 | 功能实现时逐步落地链路测试；MVG 收尾在整合版本运行完整清单并保存证据。 | 精确提交或工作区摘要、执行命令、原始报告、summary.json。 |
| Chapter 7 UI 接线 | 为关键链路准备真实场景、引擎输入、有界状态等待与清理。 | 区分 scene-method 与 engine-input；视觉、手感和空间可用性仍由人验收。 |

## 清单、Impact 建议与责任

默认样例是 `docs/testing/mvg/boot-pilot.json`。它只覆盖 MainMenu → 新游戏配置 → Sanguo 启动链，不代表整个 MVG。

- flow：可观察 outcome、真实 task_ids、显式 source_paths、handoffs、test_ids。
- handoff：producer_task / consumer_task / owner_task、contract_ref、behavior、test_ids。
- test：唯一 id、kind（dotnet/gdunit）、state、仓库相对 path、evidence_level、min_tests；dotnet 还需精确 class selector。
- planned 允许测试文件暂不存在；run 必须全部 implemented 且文件存在。

`recommend` 比较选定 revision 与 manifest 中的 source_paths、contract_ref、测试路径。明确命中时可以给出 related-first 运行优先级；任何未知文件、未映射变化、无命中或 Git 比较失败都回退 full-mvg。无论哪种推荐，`required_tests` 始终保持完整，`authorizes_test_exclusion=false`。这是一层 MVG 回归建议，不替代正式 Impact Index，也不能把“没有找到映射”解释成“不受影响”。

## Windows 命令

```powershell
py -3 scripts/python/dev_cli.py run-mvg-acceptance --mode plan
py -3 scripts/python/dev_cli.py run-mvg-acceptance --mode recommend --base origin/main
py -3 scripts/python/dev_cli.py run-mvg-acceptance --mode run --snapshot commit --revision HEAD --godot-bin $env:GODOT_BIN --challenge-input
# 开发中的未提交改动
py -3 scripts/python/dev_cli.py run-mvg-acceptance --mode run --snapshot workspace --godot-bin $env:GODOT_BIN
```

可用 `--manifest <repo-relative.json>` 选择其他 MVG。正式收尾优先 commit 模式；workspace 模式记录工作区摘要，不得冒充某个提交的验证。runner 复用 Project Health 的隔离 snapshot，并隔离 Godot user:// 数据。全局预算默认 900 秒。

每次输出到 `logs/ci/mvg-acceptance/<run-id>/`。plan/recommend 成功时 `runtime_verified` 仍为 false。run 只有全部清单测试实际执行、达到 min_tests、零失败、零跳过、精确 suite/class 身份且进程成功时，才会标记 `runtime_verified=true`。缺报告、空报告、计数不一致、重复结果、错误测试选择或 suite setup error 都阻断。

## Sanguo 启动链试点

首个 pilot 复用 Task 50、94、176：

- `boot-core`：Task50 的 xUnit GameStartConfig/validator 证据。
- `boot-setup`：Task94 的真实 MainMenu 配置约束与 scene-method 证据。
- `boot-input`：在真实 `Main.tscn` 中让 Play/Start 控件获得焦点，通过 `InputEventAction(ui_accept)` 激活，等待 `core.sanguo.game.started` 与 `core.sanguo.game.turn.started`。
- `--challenge-input` 会在隔离快照执行基线后断开 Play 的 pressed 接线；只有预期断言 `MVG_MAINMENU_INPUT_DID_NOT_OPEN_CONFIG` 失败才算真正检测到接线缺陷。崩溃、缺 runtime、编译错误或超时都不算。

该试点主动设置按钮焦点，不证明鼠标命中、遮挡、OS 输入、完整焦点导航、保存/读取、视觉与手感，也不证明整局玩法验收。

## 可选测试强度实验

```powershell
py -3 scripts/python/run_mvg_mutation_probe.py --snapshot commit --revision HEAD
```

实验只在隔离快照中对 `GameStartConfigValidator` 的两个输入边界施加已知变异：允许 1 名玩家、允许 0 初始资金。先验证基线，再逐个执行冻结的 Task50 测试并恢复源码。输出 killed / survived / unverified 到 `logs/ci/mvg-mutation/`。这不是全程序 mutation score，也不是默认门禁。

## CI 与人工验收

`.github/workflows/mvg-integration.yml` 对本入口及 pilot 相关改动运行 Windows 启动试点；mutation 仅在手动 dispatch 时可选。它不修改分支保护或既有 profile 门禁。完整 MVG 的范围、视觉/手感、平衡、性能代表性仍需要人确认；机器报告不能替代试玩结论。
