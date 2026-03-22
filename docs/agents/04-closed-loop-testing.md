# Closed-Loop Testing

Current first-phase loop:
1. Run `scripts/sc/run_review_pipeline.py`.
2. If it fails, open `repair-guide.md`.
3. Fix the first hard failure only.
4. Rerun the narrowest step first.
5. Rerun the full review pipeline only after the narrow step is green.

Stop-loss rules:
- Do not rerun the full pipeline before isolating the failing step.
- Do not lower hard gates before identifying the failing contract.
- Do not let `llm_review` become the first diagnostic tool when `sc-test` or `sc-acceptance-check` already failed.
