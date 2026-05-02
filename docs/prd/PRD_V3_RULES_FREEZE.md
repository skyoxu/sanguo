# PRD V3 Rules Freeze (Baseline)

## 0. Scope and Intent

- This document freezes the current rule decisions for the next implementation phase.
- This freeze focuses on deterministic behavior, explainability, replay trust, and operability.
- Any conflicting implementation must be treated as a bug unless superseded by a new freeze revision.

## 1. Global Constraints

### 1.1 Build/Mode Constraints

- AI system is disabled in this version (do not add AI behavior assumptions in runtime rules).
- Probability tuning belongs to configuration files; freeze only defines behavior boundaries, not probability values.

### 1.2 User Feedback Policy

- Non-crash issues do not trigger user-facing feedback flows.
- Crash remains the only category that can trigger explicit user feedback path.

## 2. Event Time and Ordering

### 2.1 Single Time Base

- Runtime event ordering and replay ordering must use logical Tick/Round only.
- Wall-clock time is not the source of truth for ordering.

### 2.2 Global Conflict Priority (Single Order)

When multiple critical conditions collide in one logical frame, system resolves by one fixed priority chain:

1. Crash / fatal runtime abort
2. Hard game-over condition (including building durability settlement fatal condition)
3. Replay integrity stop (mismatch stop in release mode)
4. Save-path risk state (save failure and retry handling)
5. Non-critical UI/logging side effects

No subsystem is allowed to override this global order.

## 3. Camp Phase, Force Challenge, and Save

### 3.1 Camp Save Retry Rule

- Auto-save failure in camp does not block leaving camp.
- While still in camp, system retries save.
- Before leaving camp, one mandatory final retry is executed.
- If final retry still fails, leaving camp remains allowed.

### 3.2 Persistent Risk Warning

- Save failure enters persistent hard warning state.
- Warning remains active until the next successful save.

### 3.3 Force Challenge Confirmation Page

- Force challenge has read-only confirmation page by default (enabled).
- Confirmation page can be disabled in settings.
- This setting is persisted to local settings.
- On every version upgrade, this setting is reset to enabled.

### 3.4 Interaction Locking

- Once force challenge trigger is accepted (leave-camp edge), non-combat interaction is locked immediately.

## 4. Explainability, HUD, and Logs

### 4.1 Popup and Log Sync

- Result popup and event log write happen in the same logical action.
- Popup queue overload is merged into summary mode.

### 4.2 Summary Merge Strategy

- Summary merge does not discard raw details from log storage.
- Raw details remain available in HUD scrollable log.
- Popup may show summary only; log must retain detail chain.

### 4.3 Performance Guard

- HUD detail log uses fixed window + lazy loading.
- Full in-memory unbounded accumulation is forbidden.

### 4.4 i18n Missing-Key Fallback

- Release build must not expose raw localization keys.
- Dev build may expose raw key for diagnostics.
- Release fallback uses friendly text and writes audit trail.

## 5. Replay Trust and Diagnostics

### 5.1 Replay Integrity Inputs

Replay trust check includes:

- seed
- game/runtime version
- content pack hash
- key event sequence hash

### 5.2 save_untrusted Flag

- If save reliability is compromised, system marks `save_untrusted`.
- `save_untrusted` disables deterministic replay for current run context.
- Current run is marked as non-trustworthy for replay certification.

### 5.3 Mismatch Behavior by Build Mode

- Release build: replay mismatch stops replay and returns to main menu.
- Dev build: replay mismatch can continue for debugging.

### 5.4 Diagnostic Data and Privacy

- Diagnostics support copy action in local runtime.
- Diagnostic payload uses desensitization.
- Desensitization priority is mode-based:
  - Release: safety-first
  - Dev: diagnosability-first

### 5.5 Diagnostic Retention

- Keep diagnostics for last 3 runs.
- Cleanup trigger happens at settlement stage.

## 6. Audit Fallback

- If normal audit write fails, runtime continues.
- Runtime records in-memory warning.
- Secondary fallback writes to `user://` audit fallback file.
- Fallback file uses fixed-size rotation (baseline: 1MB x 5 files, total 5MB).

## 7. Contract Evolution Rules

- Event/DTO contracts follow additive-only evolution in baseline.
- Breaking removal/rename is not allowed without deprecation window.
- Contract changes require explicit versioned migration plan.

## 8. Non-Goals (Current Freeze)

- No new AI behavior design.
- No probability policy hardcoding in freeze text.
- No user-facing non-crash issue reporting flow.

## 9. Change Control

- Any rule change in sections 2-7 requires:
  1. freeze revision update
  2. acceptance assertion update
  3. corresponding test evidence update
