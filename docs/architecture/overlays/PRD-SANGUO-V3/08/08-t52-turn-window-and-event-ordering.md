---
PRD-ID: PRD-SANGUO-V3
Title: V3 Turn Ordering, Leave-Camp Boundary, and Replay Stability
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
Arch-Refs:
  - CH06
  - CH07
Test-Refs:
  - Game.Core.Tests/Tasks/Task52TurnPhaseWindowTests.cs
  - Game.Core.Tests/Tasks/Task52EventTriggerOrderTests.cs
  - Game.Core.Tests/Tasks/Task52OutOfOrderEventRegressionTests.cs
---

# V3 Turn Ordering, Leave-Camp Boundary, and Replay Stability

Owner page for T75, T87, T88, T96, and T123~T124.

## CampLifecycleEngine Ownership

| Task | Concern | Current extant EventType set |
|---|---|---|
| T75 | engine-level camp sequencing | `core.sanguo.game.saved`, `core.sanguo.game.turn.advanced`, `core.sanguo.boss.challenge.prompted` |
| T87 | camp transition and one-action rule | `core.sanguo.game.turn.advanced` |
| T88 | leave-camp save retry and warning | `core.sanguo.game.saved`, `core.sanguo.boss.challenge.prompted` |
| T96 | campaign round lifecycle state machine integration pack | `core.sanguo.game.turn.started`, `core.sanguo.game.turn.ended`, `core.run.state.transitioned` |
| T123 | camp-pressure-board transition sequencer | `core.sanguo.game.turn.started`, `core.sanguo.game.turn.ended`, `core.run.state.transitioned` |
| T124 | round ordering replay-stability checks | `core.sanguo.game.turn.started`, `core.sanguo.game.turn.ended`, `core.run.state.transitioned` |

## Fixed Order

### Camp Start

1. settle camp building durability and fatal condition
2. settle previous-round objective
3. enter camp free-operation window

### Leave-Camp Boundary

1. run one mandatory final save retry if autosave had already failed
2. allow leave-camp even if the final retry still fails
3. keep persistent risk warning active until next successful save
4. resolve boss reveal or force-challenge branch before board entry
5. publish current-round objective after boss branch completes
6. enter board phase

## Ordering Rules

- Replay and runtime ordering are based on `Tick` and `RoundNumber` only.
- Wall-clock time can be logged for diagnostics but cannot decide sequence.
- Same-frame critical collisions obey the frozen global priority chain.
- If the runtime loop exposes explicit state transitions, `core.run.state.transitioned` is the extant compatibility marker for those boundaries until a Sanguo-specific phase contract lands.

## Pending Additive Contracts

The following names are design targets only until C# contracts land:

- `core.sanguo.camp.entered`
- `core.sanguo.camp.leave_requested`
- `core.sanguo.camp.leave_allowed`

Until then, task views stay anchored on extant save, turn, prompt, and run-state events so contract traceability remains real.

## Assertion Ownership

### A-001 Global Priority Chain

- same-frame collisions must resolve in one frozen order
- save retry, popup, and log side effects cannot outrank crash, hard game-over, or replay stop

### A-002 Logical Time-Only Ordering

- ordering keys are `Tick`, `RoundNumber`, and phase sequence only
- wall-clock is never a truth source for replay or state-machine conflict resolution

### A-003 Camp Save Retry Before Leave

- leave-camp path must always execute one final retry if save state is dirty and failed
- UI cannot bypass this retry step

### A-004 Leave Allowed After Retry Failure

- leave-camp remains allowed even if final retry fails
- save failure cannot deadlock the player inside camp

### A-005 Persistent Save Warning

- warning becomes active on save failure
- warning clears only after a later successful save
- warning state survives UI refresh and phase repaint

## Failure and Lock Boundaries

- Save retry belongs to leave-camp boundary, not arbitrary idle time.
- Boss reveal or force challenge may preempt board entry, but it may not preempt the final retry.
- Warning persistence is stateful and must survive UI rebuilds.
- Turn-start, turn-end, and run-state markers must describe one coherent lifecycle rather than competing timelines.

## Key Outputs

- sequencer checkpoint
- leave-camp retry result
- persistent warning state
- ordered replay trace
- same-frame priority decision record
