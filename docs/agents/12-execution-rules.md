# Execution Rules

This document preserves the execution-time rules that used to live in the long AGENTS file. Use it when implementing, editing, or splitting work.

## Planning And Tracking
- Keep an explicit live plan for multi-step work.
- Prefer TodoWrite when it is available; otherwise keep the active planning tool updated as steps move from in progress to completed.
- Do not defer task tracking until the end of the session.

## Implementation Stop-Loss
- Remove dead code when changing behavior.
- Do not keep compatibility shims or legacy branches unless the user or an accepted ADR explicitly requires them.
- Deliver complete, runnable behavior.
- Do not leave MVP placeholders, TODO-only branches, or stub implementations as the final state.

## Workstyle
- Work in small, green, deterministic steps.
- Prefer Understand -> Test (red) -> Implement (green) -> Refactor.
- If you are stuck after three real attempts, record the failure mode, list two or three alternatives, and choose the simpler path or narrow the scope.

## Script Size Guardrail
- Keep a single script file under 400 lines when practical.
- Split by responsibility before adding more flags, branches, or mixed concerns.
- If exceeding 400 lines is unavoidable, document the reason and get approval first.

## Old AGENTS Coverage Map
- 任务管理：强制频繁使用 TodoWrite 规划/跟踪；逐项标记进行/完成，不要堆到最后 -> Planning And Tracking
- 删除无用代码，修改功能不保留旧的兼容性代码 -> Implementation Stop-Loss
- 完整实现，禁止MVP/占位/TODO，必须完整可运行 -> Implementation Stop-Loss
- 3 Engineering Workstyle stop-loss rules -> Workstyle
- 单个脚本文件不得超过400行 -> Script Size Guardrail


## Interaction And Test Discipline
- Ask clarifying questions when requirements are ambiguous.
- Ask for confirmation before high-risk operations.
- End substantial work with the most relevant next-step question when a clear follow-up exists.
- Never disable tests to get green; fix the failure instead.
