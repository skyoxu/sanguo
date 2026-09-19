# Upstream Migration Reconciliation Policy

Sanguo uses two complementary machine-readable controls for `skyoxu/newrouge` -> `skyoxu/sanguo` migrations:

- `docs/migration/upstream-sync-ledger.json` owns the canonical target PR, latest source boundary, duplicate-open-PR rule, coarse migration scope and historical migration chain.
- `docs/migration/reconciliation/*.json` owns per-source-PR changed-file inventory and one classification for every source file.

For every reconciliation:

1. Freeze every merged source PR being consumed, including full 40-character merge SHA and complete changed-file inventory.
2. Classify every source file exactly once as `copy_exact`, `adapt_target_native`, `already_present`, `derived_regenerate`, `business_only_drop`, or `protocol_name_retain`.
3. Keep generated Knowledge state as `derived_regenerate`; rebuild it from Sanguo-owned inputs instead of copying source publication files.
4. Put the exact final-boundary line `Migration-Key: <ledger migration_key>` in the canonical pull request body. The final-boundary reconciliation manifest may bind the same PR number, branch and migration key.
5. Keep target-native runtime or regression evidence for adapted behavior. A generic build alone is not semantic-parity evidence.
6. Do not keep two open pull requests with the same migration key. Both the legacy ledger guard and repository-neutral canonical guard fail closed on duplicates.
7. Unknown or unmapped impact never authorizes test exclusion; use the full target validation route.
8. Run `py -3 scripts/python/check_cross_repo_migration.py --require-manifests` offline in hard gates. Use `--verify-source-github` during creation/review when refreshing source inventories.

Historical PRs #249-#251 predate the ledger. Functional boundaries are recorded explicitly from #253 onward. PR #256 reconciles the final upstream boundary `548af63fb1aa2e220dff0042161671acd23b36d5`, with generated publication PRs represented as regeneration obligations rather than copied state.
