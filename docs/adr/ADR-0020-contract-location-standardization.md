# ADR-0020: Contract Location Standardization

- Status: Accepted
- **Date**: 2025-12-02
- **Supersedes**: None (first formal documentation of contract location)
- **Related**: ADR-0004 (Event Bus and Contracts), ADR-0018 (Ports and Adapters)

## Context

### Problem

Contract files (domain events, DTOs, value objects) were scattered across multiple locations with inconsistent namespaces:

1. **Legacy location**: `scripts/Core/Contracts/` (Godot script directory)
   - Namespace: `Game.Contracts.*`
   - Mixed with GDScript-era files
   - Not part of standalone .NET project

2. **Modern location**: `Game.Core/Contracts/` (Pure .NET project)
   - Namespace: `Game.Core.Contracts.*`
   - Part of testable Core layer
   - Zero Godot dependencies

This **violated SSoT (Single Source of Truth)** and caused:
- Namespace conflicts during compilation
- Confusion about canonical contract location
- Architecture compliance issues (Core layer referencing wrong paths)

### Architecture Evolution

**Phase 1 (Early)**: Godot + GDScript monolith
- Contracts in `Scripts/` directory
- Tightly coupled to Godot engine

**Phase 2 (Migration)**: Godot + C# hybrid
- Introduced `Game.Core/` for domain logic
- Some contracts moved, some remained (duplication)

**Phase 3 (Current)**: Three-layer architecture (ADR-0018)
- **Game.Core/** - Pure C# domain logic (zero Godot dependencies)
- **Game.Godot/Adapters/** - Godot API wrappers (implements Ports/)
- **Scenes/** - UI assembly and signal routing

Contracts must reside in **Game.Core/** to support:
- Fast TDD cycles (no Godot engine startup required)
- Pure unit testing with xUnit
- Interface-based dependency injection
- Reusable domain logic across platforms

## Decision

### Canonical Contract Location (SSoT)

**ALL contracts MUST reside in**:
```
Game.Core/Contracts/<Module>/
  ├── Guild/
  │   ├── GuildCreated.cs
  │   ├── GuildMemberJoined.cs
  │   ├── GuildMemberLeft.cs
  │   ├── GuildDisbanded.cs
  │   └── GuildMemberRoleChanged.cs
  ├── GameLoop/
  │   ├── GameTurnStarted.cs
  │   ├── GameTurnPhaseChanged.cs
  │   └── GameWeekAdvanced.cs
  └── Combat/
      └── ...
```

**Namespace convention**:
```csharp
namespace Game.Core.Contracts.<Module>;

/// <summary>
/// Domain event: core.<entity>.<action>
/// Per ADR-0004 CloudEvents naming convention.
/// </summary>
public sealed record EventName(...)
{
    public const string EventType = "core.<entity>.<action>";
}
```

### Forbidden Locations

**MUST NOT** place contracts in:
- ❌ `Scripts/Core/Contracts/` (legacy Godot script directory)
- ❌ `scripts/Core/Contracts/` (lowercase variant)
- ❌ `Game.Godot/` (adapter layer must not define contracts)
- ❌ `Scenes/` (UI layer must not define contracts)

### Migration Checklist (Completed 2025-12-02)

- [x] Move 8 contract files from `scripts/Core/Contracts/` → `Game.Core/Contracts/`
- [x] Update namespaces: `Game.Contracts.*` → `Game.Core.Contracts.*`
- [x] Fix imports in 4 referencing files:
  - EventEngine.cs
  - GuildContractsTests.cs
  - GameLoopContractsTests.cs
  - GuildManager.cs
- [x] Delete legacy `scripts/Core/Contracts/` directory
- [x] Verify compilation (0 errors, 200 tests passing)
- [x] Update CLAUDE.md documentation (Section 6.0, 6.1)

## Consequences

### Positive

1. **SSoT Restored**: Single canonical location for all contracts
2. **Architecture Compliance**: Contracts in pure .NET layer (no Godot coupling)
3. **TDD Efficiency**: Unit tests run in milliseconds without engine overhead
4. **Namespace Clarity**: `Game.Core.Contracts.*` clearly signals Core layer ownership
5. **CI Automation**: Architecture compliance script (`check_architecture.py`) prevents future violations

### Negative

1. **Migration Effort**: Required one-time file moves and namespace updates
2. **Breaking Changes**: External tools referencing old paths need updates
3. **Documentation Lag**: Old documentation may still reference legacy paths (mitigated by CLAUDE.md update)

### Mitigation Strategies

1. **Architecture CI Check**: `scripts/python/check_architecture.py` validates:
   - Core layer has no Godot dependencies
   - Interfaces reside in `Game.Core/Ports/`
   - All ports have adapter implementations

2. **Pre-commit Hook** (optional future enhancement):
   ```bash
   # Reject commits adding files to legacy paths
   if git diff --cached --name-only | grep -q "scripts/Core/Contracts/"; then
     echo "ERROR: Contracts must be in Game.Core/Contracts/, not scripts/"
     exit 1
   fi
   ```

3. **Documentation Alignment**:
   - CLAUDE.md Section 6.0, 6.1 updated to reflect new paths
   - ADR-0004 references remain valid (namespace updated, location clarified)

### Technical Debt Identified (Non-blocking)

Architecture CI check detected existing violations (not introduced by this ADR):
- 9 interfaces outside `Game.Core/Ports/` (should be moved)
- 1 missing adapter implementation for `IEventCatalog`

These are tracked separately and do not block this ADR.

## References

- **ADR-0004**: Event Bus and Contracts (CloudEvents naming)
- **ADR-0018**: Ports and Adapters Pattern (three-layer architecture)
- **CLAUDE.md Section 6**: Contract templates and directory structure
- **Implementation PR**: [Link to PR with contract migration]

## Compliance Validation

To verify compliance with this ADR:

```bash
# Run architecture compliance check
py -3 scripts/python/check_architecture.py

# Expected output:
# [1/3] Checking Core layer for Godot references... [OK]
# [2/3] Checking interface locations... [FAIL] (existing tech debt)
# [3/3] Checking Adapters layer completeness... [FAIL] (existing tech debt)

# Verify contract files exist in canonical location
ls Game.Core/Contracts/Guild/*.cs
ls Game.Core/Contracts/GameLoop/*.cs

# Verify legacy location is empty
ls scripts/Core/Contracts/ 2>/dev/null || echo "Legacy directory removed (correct)"
```

## Future Considerations

1. **Value Objects**: Follow same pattern as events (e.g., `Game.Core/Contracts/ValueObjects/SafeResourcePath.cs`)
2. **DTOs**: Cross-boundary data structures in `Game.Core/Contracts/Dtos/`
3. **Shared Types**: Enums and constants in `Game.Core/Contracts/Shared/`

All future contract-like structures MUST follow this ADR's location and namespace conventions.
