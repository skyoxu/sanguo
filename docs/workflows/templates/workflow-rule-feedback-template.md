# Workflow Rule Feedback Template

Use this template when a business repository wants to propose a reusable workflow 5.1 or Chapter 6 rule back into the template repository.

Create one record per rule candidate.

---

## 1. Rule Identity

- Rule name:
- Workflow family: `5.1` | `chapter6`
- Source repository:
- Source branch:
- Source commit:
- Date:

## 2. Problem Statement

- What repeated waste, ambiguity, false-green risk, timeout pattern, or rerun problem was observed?
- Why is the current template behavior not sufficient?

## 3. Observed Symptoms

- Operator-visible symptom:
- Cost symptom:
- Quality symptom:
- Recovery symptom:

## 4. Artifact Evidence

List stable artifact paths and the concrete signals they contain.

- `summary.json`:
- `latest.json`:
- `execution-context.json`:
- `repair-guide.json`:
- `agent-review.json`:
- `run-events.jsonl`:
- Other:

## 5. Failure / Waste Pattern

- Failure family:
- Trigger condition:
- Repeated how many times:
- Affected lane or step:
- If Chapter 6, affected lane:
  - `run-6.7`
  - `run-6.8`
  - `record-residual`
  - `inspect-first`
  - other:

## 6. Proposed Reusable Rule

- Proposed rule in one sentence:
- Proposed template target:
  - constant table
  - classifier helper
  - producer script
  - consumer script
  - test
  - workflow doc
- Suggested files:

## 7. Classification

- Promotion class:
  - `safe-to-promote`
  - `needs-cross-repo-validation`
  - `business-only`
- Why:

## 8. Cross-Repo Status

- Status:
  - `single-repo`
  - `two-repo-confirmed`
  - `three-plus-repo-confirmed`
- Other repositories checked:
- Matching evidence summary:

## 9. Safety Review

- Does this weaken deterministic gates? `yes|no`
- Could this create a false-green path? `yes|no`
- Could this hide a P1/P0 issue inside residual recording? `yes|no`
- Could this overfit one business repository? `yes|no`
- Safety notes:

## 10. Expected Benefit

- Time saved:
- LLM cost saved:
- Recovery clarity improvement:
- False rerun reduction:

## 11. Validation Plan

- Required regression tests:
- Required workflow docs to update:
- Required business-repo backports after promotion:

## 12. Final Decision

- Decision:
  - `promote-now`
  - `wait-for-cross-repo-validation`
  - `keep-local-only`
- Decision reason:

---

## Short Example Labels

- Workflow 5.1 examples:
  - `extract timeout retry boost`
  - `prompt-trimmed semantic gate classification`
  - `failure-family auto-skip-soft`
- Chapter 6 examples:
  - `repo-noise transport token`
  - `P1 floor acceptance-refs category`
  - `run-6.8 timeout-agents stop-loss`
