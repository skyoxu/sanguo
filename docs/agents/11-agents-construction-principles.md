# AGENTS Construction Principles

This document explains how `AGENTS.md` is built and how to extend it without recreating the old 600-line monolith.

## Design Goal
- `AGENTS.md` is a repository map, not a second source of truth.
- It should help an agent find the next correct document by task stage, problem type, and current run state.
- It should stay short enough to scan quickly during a context reset.

## Placement Rules
- `AGENTS.md`
  - Keep only routing, high-level rules, key commands, and recovery file pointers.
- `docs/agents/`
  - Put agent workflow, recovery, harness, and navigation guidance here.
- `README.md`
  - Keep project background, startup, stack, and human-facing overview here.
- `docs/testing-framework.md`, `DELIVERY_PROFILE.md`, `docs/architecture/**`, `docs/adr/**`
  - Keep detailed rules, thresholds, architecture decisions, and testing policy in their source documents.
- `execution-plans/`, `decision-logs/`, and `logs/`
  - Keep durable intent and run evidence there, not in AGENTS.

## Retrieval Strategy
- Route by task stage:
  - resume, implement, test, review, release, customize
- Route by problem type:
  - startup, architecture, contracts, tests, CI, delivery profile
- Route by directory:
  - code, docs, scripts, workflows, logs

## Maintenance Rules
- When you add a new top-level workflow or recurring problem area:
  - update `AGENTS.md` only if it is a first-class entry point.
- When you add deeper guidance:
  - add or update a document under `docs/agents/`.
- When the content is already owned by a better source:
  - link to that source instead of duplicating it into `AGENTS.md`.
- Keep `AGENTS.md` below the threshold where a fresh session can no longer scan it quickly.

## Practical Test
The structure is healthy only if all of these are true:
- A new session can find startup, repo map, harness recovery, and quality gates in under a minute.
- A task can be routed by phase without opening unrelated docs first.
- Changes to ADRs, testing rules, or delivery profiles do not require copy-editing large duplicated sections in `AGENTS.md`.
