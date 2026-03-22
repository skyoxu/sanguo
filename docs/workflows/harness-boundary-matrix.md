# Harness Boundary Matrix

## Purpose

This document prevents terminology drift around the local harness.

Use it when a proposal mentions any of these terms:

- JSON-RPC
- daemon
- multi-client
- SSE or reconnect transport
- app server
- platform runtime

## Current Classification

The current repository is:

- a local file-protocol harness
- a single-user, CLI-first orchestration layer
- a deterministic recovery workflow based on sidecar artifacts

It is not:

- a JSON-RPC server
- a long-lived daemon runtime
- a multi-client coordination layer
- a remote streaming runtime
- a platform control plane

## Boundary Matrix

| Capability | Template Repo | Single-Player Business Repo | Platform Repo | Notes |
| --- | --- | --- | --- | --- |
| Stable CLI entrypoints | shipped | keep | keep | `run_review_pipeline.py`, `dev_cli.py`, scaffold commands |
| File-backed sidecars | shipped | keep | keep | `summary.json`, `execution-context.json`, `repair-guide.*`, `agent-review.*` |
| Append-only event stream | shipped | keep | keep | `run-events.jsonl` |
| Task-scoped latest pointer | shipped | keep | keep | `latest.json` |
| Recovery actions (`resume` / `refresh` / `fork` / `abort`) | shipped | keep | keep | local recovery primitive set |
| Agent-to-agent reviewer sidecar | shipped | keep | optional | useful before any server layer exists |
| Git-tracked execution and decision records | shipped | keep | keep | `execution-plans/`, `decision-logs/` |
| Delivery/security profile switching | shipped | keep | keep | local strictness control, not transport control |
| JSON-RPC request/response envelope | not in scope | usually unnecessary | recommended | only useful when multiple tools need a stable RPC contract |
| Local daemon runtime | not in scope | usually unnecessary | recommended | only useful when warm state or queued tasks justify it |
| Multi-client session coordination | not in scope | unnecessary | recommended | template and most business repos do not need this |
| SSE/Web reconnect transport | not in scope | unnecessary | recommended | only meaningful for remote or browser-based runtime observers |
| Remote monitoring/control plane | not in scope | optional | recommended | local artifacts are enough for template and most business repos |

## Default Cutline

For this template and for most Windows-only single-player business repos, stop at:

- stable CLI entrypoints
- durable local sidecars
- deterministic recovery pointers
- local review pipeline
- CI gate bundle

Do not cross into server/runtime/platform work unless the repository actually needs shared orchestration across tools or users.

## Business Repo Guidance

For a typical Windows-only single-player game repo copied from this template:

- keep the local file-protocol harness
- keep recovery sidecars and execution logs
- keep profile-driven gate strictness
- keep CI and local dry-run recovery checks
- do not add JSON-RPC by default
- do not add a daemon by default
- do not add multi-client support by default
- do not add SSE/Web reconnect transport by default

If a business repo later needs faster warm-state iteration, add the thinnest possible local wrapper first. Do not jump directly to a platform design.

## When To Cross The Cutline

Move beyond the current boundary only if at least one of these is true:

1. more than one tool needs the same stable runtime API
2. more than one client must observe or control the same run concurrently
3. queued long-running tasks justify a resident process
4. browser or remote UI requires reconnectable streaming state
5. the repository is intentionally evolving into an internal platform

If none of these are true, stay on the current local harness model.

## Required Terminology

Preferred terms for this repository:

- `local file-protocol harness`
- `CLI-first recovery workflow`
- `sidecar-based deterministic recovery`

Avoid these labels unless the implementation really changes:

- `JSON-RPC server`
- `daemon runtime`
- `multi-client harness`
- `remote orchestration platform`

## Related Docs

- `docs/workflows/run-protocol.md`
- `docs/workflows/template-bootstrap-checklist.md`
- `docs/agents/03-persistent-harness.md`
- `docs/agents/06-harness-marathon.md`
- `DELIVERY_PROFILE.md`

