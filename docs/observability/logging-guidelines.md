# Logging Guidelines Baseline

This baseline is consumed by Task 160 lint-like governance checks.

## Structured Logging

- Production logs must use structured key-value payloads.
- Every event must include stable event names and deterministic severity labels.

## Redaction Rules

- Sensitive fields must be redacted before writing to any sink.
- Minimum redaction coverage includes: `email`, `token`.

## Traceability Fields

- Every emitted record must include: `traceId`, `spanId`, `taskId`.
- These fields must remain present in both success and failure paths.
