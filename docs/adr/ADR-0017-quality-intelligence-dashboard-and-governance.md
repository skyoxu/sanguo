# ADR-0017: Quality Intelligence Dashboard and Governance

- Status: Proposed
- Context: We want to evolve from isolated phase gates (Ph2/Ph7/Ph8/Ph9/Ph10) to a unified, explainable quality intelligence that aggregates metrics, enables correlation analysis, provides non-blocking insights in PRs, and supports safe, auditable threshold evolution.
- Decision:
  - Define a minimal, versioned schema for `quality-snapshot.json` written to `logs/<YYYY-MM-DD>/ci` with `schemaVersion`, `timestamp`, optional `prNumber`, and per‑phase summaries (Ph2/7/8/9/10) referencing `src/shared/contracts/quality/metrics.ts`.
  - Privacy & ethics: default team‑level, anonymized trends; individual profiles are opt‑in/by‑owner only; data is used for coaching, not performance management.
  - Threshold strategy: start with non‑blocking insights; run A/B and keep explicit rollback; any threshold changes are reviewed and recorded; keep references to ADR‑0005/ADR‑0015.
  - Storage & retention: keep artifacts under `logs/<date>/ci` and as workflow artifacts; do not commit history snapshots to VCS; external storage (e.g. S3/artifacts retention) can be added later.
  - CI integration: add `scripts/aggregate-quality-metrics.mjs` to produce snapshots and extend PR comments with a non‑blocking “Quality Insights” section.
- Consequences: We gain a single source of truth for cross‑phase quality signals and auditability; we must maintain the minimal schema and avoid scope creep; privacy guardrails must be enforced.
- References: ADR‑0005 (Quality Gates), ADR‑0015 (Performance Budgets), ADR‑0004 (Event Bus & Contracts)
