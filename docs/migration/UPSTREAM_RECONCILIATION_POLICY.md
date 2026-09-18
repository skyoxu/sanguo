# Upstream Migration Reconciliation Policy

The canonical machine-readable record is `docs/migration/upstream-sync-ledger.json`.

For every new `skyoxu/newrouge` -> `skyoxu/sanguo` reconciliation:

1. Add exactly one ledger record for the latest functional upstream commit being reconciled.
2. Put the exact line `Migration-Key: <ledger migration_key>` in the canonical pull request body.
3. Classify migrated behavior as `exact-copy`, `adapted`, or `excluded`; generated Knowledge state is rebuilt in Sanguo rather than copied.
4. Keep target-native runtime evidence for adapted behavior. A green generic build alone is not sufficient evidence of semantic parity.
5. Do not keep two open pull requests with the same migration key. The CI duplicate guard fails closed when this happens.
6. Unknown or unmapped impact never authorizes test exclusion; use the full validation route.

Historical PRs #249-#251 predate this ledger. Their follow-up repairs are retained as historical context, while post-reconciliation functional boundaries are recorded explicitly from #253 onward.
