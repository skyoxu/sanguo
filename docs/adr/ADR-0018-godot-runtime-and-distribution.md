# ADR-0018: Godot Runtime and Distribution

- Status: Proposed
- Context: Migration Phase-2 (docs/migration/Phase-2-ADR-Updates.md), CH01/CH03 baseline; Windows-only delivery
- Decision: Adopt Godot 4.5.1 (.NET/mono) as the runtime for game UI/rendering/physics; distribute Windows Desktop via standalone .exe with embedded or adjacent .pck; pin .NET 8 LTS runtime for Godot .NET integration
- Consequences: Electron/Chromium stack is fully retired; React-based UI migrates to Godot Control; export/release pipeline is driven by Godot Export Templates; CI must install templates and build headless; size gates apply to .exe/.pck artifacts
- References: docs/migration/Phase-17-Build-System-and-Godot-Export.md, docs/architecture/base/07-dev-build-and-gates-v2.md

