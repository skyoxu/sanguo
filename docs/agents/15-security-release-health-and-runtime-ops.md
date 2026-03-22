# Security, Release Health, And Runtime Ops Rules

Use this document when you need the old AGENTS content for security posture, release health, logs, runtime commands, or CI gate expectations.

## Security Baseline Defaults
- Only allow `res://` for packaged read-only content and `user://` for writable local data.
- Reject absolute paths and path traversal outside approved roots.
- Allow outbound network access only through HTTPS and approved hosts.
- `ALLOWED_EXTERNAL_HOSTS` remains the allowlist input.
- `GD_OFFLINE_MODE=1` must disable outbound network requests.
- Dynamic external code or assembly loading is forbidden.
- `OS.execute` is disabled by default and should stay tightly audited when enabled for development.
- In CI or headless runs, camera, microphone, and file picker permissions default to deny.

## Security Flags
- GD_SECURE_MODE=1 keeps the secure runtime baseline enabled.
- ALLOWED_EXTERNAL_HOSTS=<csv> defines the network allowlist.
- GD_OFFLINE_MODE=1 forces offline behavior.
- SECURITY_TEST_MODE=1 enables deterministic security test posture in CI or local verification.

## Security Profile Interpretation
- This template no longer assumes a permanently strict anti-tamper posture.
- Default runtime posture is derived from `DELIVERY_PROFILE` through `SECURITY_PROFILE`.
- `host-safe` is the default for template-speed delivery: keep host boundary protections hard, keep anti-tamper-only findings advisory unless the task or acceptance contract explicitly demands more.
- `strict` is the tightening posture for stronger integrity and release control.
- CI should always emit `SecurityProfile: <host-safe|strict>` in Step Summary.

## Release Health
- Release health still means Sentry Releases + Sessions, not just error logs.
- The old baseline threshold remains relevant: 24h Crash-Free Sessions >= 99.5 percent before wider release.
- In this repository, treat the threshold and current release-health behavior as owned by accepted ADRs and workflow docs.
- If a copied project introduces a dedicated `release_health_gate.py`, it should write deterministic evidence into `logs/ci/<date>/release-health.json` or an equivalent CI artifact.

## Logs And Artifacts SSoT
- Unit evidence: `logs/unit/<YYYY-MM-DD>/`
- Engine and scene evidence: `logs/e2e/<YYYY-MM-DD>/`
- Performance evidence: `logs/perf/<YYYY-MM-DD>/`
- CI evidence: `logs/ci/<YYYY-MM-DD>/`
- Security audit log naming stays `security-audit.jsonl`.
- Performance summaries should keep explicit fields such as `p95`, `p50`, `samples`, `scene`, and gate mode.

## Runtime Commands In This Repository
- Core unit tests: `dotnet test Game.Core.Tests/Game.Core.Tests.csproj`
- Headless smoke: `py -3 scripts/python/smoke_headless.py --godot-bin "$env:GODOT_BIN" --project . --scene res://Game.Godot/Scenes/Main.tscn`
- Unified gates: `py -3 scripts/python/quality_gates.py`
- Local review pipeline: `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN"`
- Task-scoped execution entry: `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN"`
- Test, acceptance, and review stages are orchestrated behind `run_review_pipeline.py`; keep docs on the unified entry, not the legacy manual triplet.
- When a run fails, inspect the task run sidecars (`summary.json`, `execution-context.json`, `repair-guide.json`, `agent-review.json`) before invoking internal helpers directly.

## CI And Branch Protection Expectations
- Required checks should cover unit tests, smoke or e2e validation, task link validation, and the project-specific release posture.
- Protected branches should require status checks.
- Delivery profile and security profile should both be visible in CI summaries.
- Do not lower a hard gate without either changing the accepted ADR set or explicitly changing the delivery profile.

## Old AGENTS Coverage Map
- `5 Security & Privacy Baseline (Godot 4.5 + C#)` -> this document + `docs/architecture/base/02-security-baseline-godot-v2.md` + ADR-0019 + ADR-0031
- `发布健康门禁（Crash-Free SSoT）` -> this document + ADR-0003 + workflow docs
- `6.3 日志与工件（SSoT）` -> this document + `docs/testing-framework.md`
- `6.6 运行与命令（Windows + Python)` -> this document + `scripts/sc/README.md`
- `7 Quality Gates (CI/CD)` -> this document + `docs/agents/09-quality-gates-and-done.md` + workflow docs
