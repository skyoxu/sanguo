# ADR-0022: Godot Signal System and Contracts

- Status: Proposed
- Context: Migration Phase-2; CH04 system context and event flows; replace CloudEvents bus with Godot Signals for in-process events
- Decision: Use Godot Signals for intra-scene and global Autoload events; standardize event naming ${DOMAIN_PREFIX}.<entity>.<action>; centralize event/DTO definitions under Game.Core/Contracts/** and reference (do not duplicate) in docs
- Consequences: Decoupled scene communication; contracts remain SSoT; overlay 08 chapters must cite CH01/02/03 policies rather than copy thresholds
- References: docs/migration/Phase-9-Signal-System.md, docs/architecture/base/04-system-context-c4-event-flows-v2.md, docs/architecture/base/08-功能纵切-template.md

