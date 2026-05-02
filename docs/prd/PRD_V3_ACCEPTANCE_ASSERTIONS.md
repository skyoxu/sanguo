# PRD V3 Acceptance Assertions (Deterministic)

## 0. Purpose

- This file defines machine-checkable assertions for `PRD_V3_RULES_FREEZE.md`.
- Assertion IDs are stable references for tests, CI checks, and review evidence.

## 1. Core Assertions

### A-001 Global Priority Chain

- Given multiple same-frame critical signals,
- When resolver runs,
- Then resolution order must match frozen chain in Rules Freeze 2.2.
- Evidence: deterministic unit test with synthetic same-tick collision fixture.

### A-002 Logical Time-Only Ordering

- Given two events with conflicting wall-clock and logical order,
- When log/replay ordering is computed,
- Then ordering follows logical Tick/Round only.
- Evidence: unit test with mocked timestamps.

### A-003 Camp Save Retry Before Leave

- Given camp auto-save failed,
- When player attempts leave-camp,
- Then one mandatory final retry occurs before transition.
- Evidence: unit test + integration trace.

### A-004 Leave Allowed After Retry Failure

- Given mandatory final retry also fails,
- When leave-camp transition is requested,
- Then transition is still allowed.
- Evidence: flow test with storage failure stub.

### A-005 Persistent Save Warning

- Given save failure occurred,
- When no successful save has happened,
- Then hard warning state remains active.
- And it clears only after successful save.
- Evidence: state machine test.

### A-006 Force-Challenge Confirmation Default

- Given clean settings or version-upgraded settings,
- When force challenge is about to trigger,
- Then read-only confirmation page is enabled by default.
- Evidence: settings migration test.

### A-007 Force-Challenge Locking

- Given force challenge enter point reached,
- When battle handover starts,
- Then non-combat interactions are locked immediately.
- Evidence: UI/input integration test.

### A-008 Popup-Log Synchronous Commit

- Given a result-producing action,
- When action resolves,
- Then popup emission and log write belong to same logical action commit.
- Evidence: event transaction test.

### A-009 Popup Overload Summary

- Given popup queue exceeds threshold,
- When overflow handling runs,
- Then popup output is merged summary mode.
- And raw detail remains in log storage.
- Evidence: UI queue stress test.

### A-010 HUD Log Fixed Window + Lazy Load

- Given long-running session logs,
- When HUD renders details,
- Then storage access follows fixed window with lazy loading.
- And unbounded in-memory full-log retention is absent.
- Evidence: perf/memory regression test.

### A-011 Release i18n Key Exposure Ban

- Given missing localization key in release build,
- When explanation text is generated,
- Then raw key token is not exposed to player UI.
- And friendly fallback text is shown.
- Evidence: localization UI test in release mode.

### A-012 Dev i18n Raw-Key Diagnostic

- Given missing localization key in dev build,
- When explanation text is generated,
- Then raw key may be displayed for diagnostics.
- Evidence: localization UI test in dev mode.

### A-013 Replay Integrity Hash Set

- Given replay verification starts,
- When integrity check computes trust,
- Then it includes seed/version/content-pack-hash/key-event-sequence-hash.
- Evidence: replay verifier unit test.

### A-014 save_untrusted Effect

- Given `save_untrusted` is set,
- When deterministic replay is requested,
- Then deterministic replay is disabled for current run context.
- Evidence: replay gate unit test.

### A-015 Replay Mismatch Policy by Mode

- Given replay mismatch detected,
- When build mode is release,
- Then replay stops and returns to main menu.
- When build mode is dev,
- Then replay continuation is allowed.
- Evidence: mode-parameterized integration test.

### A-016 Diagnostic Copy Payload Policy

- Given diagnostics copy action executed,
- When payload is built,
- Then payload is desensitized.
- And mode-based priority applies (release=safety, dev=diagnosability).
- Evidence: privacy filter unit test.

### A-017 Diagnostic Retention Window

- Given settlement completes,
- When retention maintenance runs,
- Then only latest 3 runs are retained.
- Evidence: retention maintenance unit test.

### A-018 Audit Fallback on Write Failure

- Given primary audit sink write fails,
- When fallback handler runs,
- Then runtime continues,
- And in-memory warning is recorded,
- And `user://` fallback file write is attempted.
- Evidence: audit adapter failure integration test.

### A-019 Fallback Rotation Cap

- Given repeated fallback writes,
- When file rotation runs,
- Then rotation respects fixed-size policy (1MB x 5 files baseline).
- Evidence: filesystem rotation test.

### A-020 Contract Evolution Additive-Only

- Given contract update PR,
- When compatibility check runs,
- Then removal/rename without deprecation window is rejected.
- Evidence: contract schema compatibility gate.

## 2. CI Hook Recommendations

- Hook 1: deterministic core assertion suite (`A-001` to `A-007`, `A-013` to `A-020`) as hard gate.
- Hook 2: UI explainability suite (`A-008` to `A-012`) as hard gate for release branches.
- Hook 3: perf/memory check for HUD windowing (`A-010`) with budget threshold.

## 3. Evidence Layout Suggestion

- `logs/ci/<date>/assertions/prd-v3-core.json`
- `logs/ci/<date>/assertions/prd-v3-ui.json`
- `logs/ci/<date>/assertions/prd-v3-replay.json`
- `logs/ci/<date>/assertions/prd-v3-audit.json`

Each summary should include:

- assertion id
- status (pass/fail/skip)
- evidence file path
- failure reason
