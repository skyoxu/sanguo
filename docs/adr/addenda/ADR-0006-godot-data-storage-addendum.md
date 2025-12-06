---
adr: ADR-0006
title: Addendum — Data Storage for Godot (SQLite + ConfigFile)
date: 2025-11-08
status: Active
scope: Windows-only runtime, Godot 4.5 (.NET)
---

# Addendum to ADR-0006: Data Storage (Godot Alignment)

## Context
Adopt `godot-sqlite` for structured data and `ConfigFile` for lightweight settings; enforce `user://` writes and resource `res://` reads.

## Decisions
- Database: `godot-sqlite` (GDExtension); WAL mode where applicable; run migrations from a dedicated bootstrap.
- Paths: allow writes only to `user://`; forbid absolute paths in gameplay.
- Preferences: use `ConfigFile` for player settings; keep schema/version in a small section.
- Threading: DB access off main thread for heavy operations; use worker threads with proper synchronization.

## Verification
- GdUnit4 scene tests create a temporary user:// DB; unit tests validate migration/versioning logic.
- CI exports minimal DB integrity logs into `logs/YYYYMMDD/db/`.

