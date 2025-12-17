# -*- coding: utf-8 -*-
"""
Check UTF-8 files for encoding issues like garbled text.
"""

import os
import re
from pathlib import Path

# Patterns that indicate encoding issues
GARBLED_PATTERNS = [
    r'闁[^a-zA-Z0-9\s]{1,3}',  # 闁 followed by garbled chars
    r'鐟[^a-zA-Z0-9\s]{1,3}',  # 鐟 followed by garbled chars
    r'�',  # Replacement character (U+FFFD)
    r'\?\?\?',  # Multiple question marks in sequence
    r'[\x00-\x08\x0B\x0C\x0E-\x1F]',  # Control characters (except tab, newline, CR)
]

# Files already identified as UTF-8
UTF8_FILES = [
    "PROJECT_DOCUMENTATION_INDEX.md",
    "testing-framework.md",
    "adr/ADR-0001-tech-stack.md",
    "adr/ADR-0002-electron-security.md",
    "adr/ADR-0003-observability-release-health.md",
    "adr/ADR-0004-event-bus-and-contracts.md",
    "adr/ADR-0005-quality-gates.md",
    "adr/ADR-0006-data-storage.md",
    "adr/ADR-0007-ports-adapters.md",
    "adr/ADR-0008-deployment-release.md",
    "adr/ADR-0009-cross-platform.md",
    "adr/ADR-0011-windows-only-platform-and-ci.md",
    "adr/ADR-0015-performance-budgets-and-gates.md",
    "adr/ADR-0016-api-contracts-openapi.md",
    "adr/ADR-0017-quality-intelligence-dashboard-and-governance.md",
    "adr/ADR-0018-godot-runtime-and-distribution.md",
    "adr/ADR-0019-godot-security-baseline.md",
    "adr/ADR-0025-godot-test-strategy.md",
    "adr/ADR-0021-csharp-domain-layer-architecture.md",
    "adr/ADR-0022-godot-signal-system-and-contracts.md",
    "adr/guide.md",
    "adr/addenda/ADR-0005-godot-quality-gates-addendum.md",
    "architecture/ADR_INDEX_GODOT.md",
    "architecture/base/00-README.md",
    "architecture/base/01-introduction-and-goals-v2.md",
    "architecture/base/04-system-context-c4-event-flows-v2.md",
    "architecture/base/07-dev-build-and-gates-v2.md",
    "architecture/base/08-crosscutting-and-feature-slices.base.md",
    "architecture/base/10-i18n-ops-release-v2.md",
    "architecture/base/12-glossary-v2.md",
    "architecture/base/architecture-completeness-checklist.md",
    "architecture/base/ZZZ-encoding-fixture-bad.md",
    "architecture/base/ZZZ-encoding-fixture-clean.md",
    "architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md",
    "architecture/overlays/PRD-SANGUO-T2/08/08-Contracts-CloudEvent.md",
    "architecture/overlays/PRD-SANGUO-T2/08/08-Contracts-CloudEvents-Core.md",
    "architecture/overlays/PRD-SANGUO-T2/08/08-Contracts-Sanguo-GameLoop-Events.md",
    "architecture/overlays/PRD-SANGUO-T2/08/08-Contracts-Preload-Whitelist.md",
    "architecture/overlays/PRD-SANGUO-T2/08/08-Contracts-Quality-Metrics.md",
    "architecture/overlays/PRD-SANGUO-T2/08/08-Contracts-Security.md",
    "architecture/overlays/PRD-SANGUO-T2/08/08-功能纵切-T2-三国大富翁闭环.md",
    "architecture/overlays/PRD-SANGUO-T2/08/08-t2-city-ownership-model.md",
    "architecture/overlays/PRD-SANGUO-T2/08/_index.md",
    "contracts/signals/README.md",
    "migration/CODE_EXAMPLES_VERIFICATION_Phase1-12.md",
    "migration/gdunit4-csharp-runner-integration.md",
    "migration/MIGRATION_FEASIBILITY_SUMMARY.md",
    "migration/MIGRATION_INDEX.md",
    "migration/Phase-1-Prerequisites.md",
    "migration/Phase-10-Unit-Tests.md",
    "migration/Phase-11-Scene-Integration-Tests-REVISED.md",
    "migration/Phase-11-Scene-Integration-Tests.md",
    "migration/Phase-12-Headless-Smoke-Tests.md",
    "migration/Phase-13-22-Planning.md",
    "migration/Phase-13-Quality-Gates-Script.md",
    "migration/Phase-14-Godot-Security-Baseline.md",
    "migration/Phase-15-Performance-Budgets-and-Gates.md",
    "migration/Phase-16-Observability-Sentry-Integration.md",
    "migration/Phase-17-Build-System-and-Godot-Export.md",
    "migration/Phase-17-Export-Checklist.md",
    "migration/Phase-17-Windows-Only-Quickstart-Addendum.md",
    "migration/Phase-17-Windows-Only-Quickstart.md",
    "migration/Phase-18-Staged-Release-and-Canary-Strategy.md",
    "migration/Phase-19-Emergency-Rollback-and-Monitoring.md",
    "migration/Phase-2-ADR-Updates.md",
    "migration/Phase-20-Functional-Acceptance-Testing.md",
    "migration/Phase-21-Performance-Optimization.md",
    "migration/Phase-22-Documentation-and-Release-Notes.md",
    "migration/Phase-3-Project-Structure.md",
    "migration/Phase-4-Domain-Layer.md",
    "migration/Phase-5-Adapter-Layer.md",
    "migration/Phase-6-Data-Storage.md",
    "migration/Phase-6-Quickstart-DB-Setup.md",
    "migration/Phase-7-UI-Migration.md",
    "migration/Phase-8-Scene-Design.md",
    "migration/Phase-9-Signal-System.md",
    "migration/VERIFICATION_REPORT_Phase11-12.md",
    "migration/VERIFICATION_REPORT_Phase13-14.md",
    "release/RELEASE_NOTES_TEMPLATE.md",
    "release/WINDOWS_MANUAL_RELEASE.md",
    "migration/VERIFICATION_SUMMARY.txt",
]

# Known fixtures intentionally containing encoding issues (do not report as CI issues).
IGNORED_RELATIVE_PATHS = {
    "architecture/base/ZZZ-encoding-fixture-bad.md",
}

def check_file_for_issues(file_path, patterns):
    """Check a single file for encoding issues."""
    issues = []

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

            # Check for replacement character
            if '�' in content:
                count = content.count('�')
                issues.append(f"Contains {count} replacement character(s) (�)")

            # Check for suspicious patterns
            for pattern in patterns:
                matches = re.findall(pattern, content)
                if matches:
                    # Limit to first 5 matches
                    sample = matches[:5]
                    issues.append(f"Pattern '{pattern}': {len(matches)} match(es), samples: {sample}")

            # Check for emoji (optional - might be legitimate)
            emoji_pattern = r'[\U0001F300-\U0001F9FF]'
            emoji_matches = re.findall(emoji_pattern, content)
            if emoji_matches:
                issues.append(f"Contains {len(emoji_matches)} emoji character(s): {emoji_matches[:5]}")

    except Exception as e:
        issues.append(f"Error reading file: {e}")

    return issues

def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent.parent
    docs_path = project_root / 'docs'

    print("=" * 80)
    print(f"Checking {len(UTF8_FILES)} UTF-8 files for encoding issues")
    print("=" * 80)
    print(f"Docs path: {docs_path}")
    print()

    total_files = 0
    files_with_issues = 0

    for rel_path in UTF8_FILES:
        file_path = docs_path / rel_path

        if not file_path.exists():
            print(f"[SKIP] {rel_path} - File not found")
            continue
        if rel_path in IGNORED_RELATIVE_PATHS:
            print(f"[SKIP] {rel_path} - Known fixture")
            continue

        total_files += 1
        issues = check_file_for_issues(file_path, GARBLED_PATTERNS)

        if issues:
            files_with_issues += 1
            print(f"\n[ISSUE] {rel_path}")
            for issue in issues:
                # Use ascii encoding with backslashreplace for console output
                try:
                    print(f"  - {issue}")
                except UnicodeEncodeError:
                    print(f"  - {issue.encode('ascii', 'backslashreplace').decode('ascii')}")
        else:
            print(f"[OK] {rel_path}")

    print("\n" + "=" * 80)
    print(f"Summary:")
    print(f"  Total files checked: {total_files}")
    print(f"  Files with potential issues: {files_with_issues}")
    print(f"  Clean files: {total_files - files_with_issues}")
    print("=" * 80)

if __name__ == '__main__':
    main()
