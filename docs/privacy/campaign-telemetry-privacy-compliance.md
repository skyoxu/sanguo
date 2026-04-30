# Privacy Compliance

## Data Minimization
Collect only aggregate campaign telemetry counters and anonymized runtime diagnostics required for balancing and stability analysis.
No direct personal identifiers, free-text payloads, or persistent device fingerprints are permitted.

## Retention Bounds
Raw telemetry snapshots must be retained for no more than 30 days.
Derived aggregate reports may be retained for trend comparison when source snapshots are already purged.
Retention policy changes require ADR update and CI policy gate review.

## Non-Crash Feedback Suppression Linkage
When non-crash feedback suppression is enabled, telemetry exporters and feedback upload pipelines must not transmit non-crash feedback artifacts.
CI policy checks must fail if suppression linkage evidence is missing or contradictory.
