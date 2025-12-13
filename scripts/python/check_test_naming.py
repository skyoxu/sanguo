"""
Test Naming Convention Validator for Game.Core.Tests

This script validates that all test methods in Game.Core.Tests follow PascalCase naming convention
and prevents regression to snake_case naming.

Usage:
    py -3 scripts/python/check_test_naming.py

Exit codes:
    0 - All test methods follow PascalCase convention
    1 - Violations found (snake_case or other non-PascalCase patterns)

Requirements:
    - Scans all *Tests.cs files in Game.Core.Tests/
    - Checks methods marked with [Fact] or [Theory]
    - Reports violations with file path and line number
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def is_pascal_case(name: str) -> bool:
    """
    Check if a method name follows PascalCase convention.

    PascalCase rules:
    - Starts with uppercase letter
    - No underscores
    - Can contain digits

    Args:
        name: Method name to check

    Returns:
        True if name is PascalCase, False otherwise
    """
    # PascalCase pattern: starts with uppercase, no underscores
    pattern = r'^[A-Z][a-zA-Z0-9]*$'
    return bool(re.match(pattern, name))


def extract_test_methods(file_path: Path) -> List[Tuple[int, str]]:
    """
    Extract test method names and their line numbers from a C# test file.

    Args:
        file_path: Path to the test file

    Returns:
        List of tuples (line_number, method_name)
    """
    test_methods = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Look for [Fact] or [Theory] attributes followed by method definition
        for i, line in enumerate(lines, start=1):
            line = line.strip()

            # Check if this line has [Fact] or [Theory] attribute
            if line.startswith('[Fact]') or line.startswith('[Theory]'):
                # Next non-empty line should be the method definition
                for j in range(i, min(i + 5, len(lines) + 1)):  # Check next few lines
                    next_line = lines[j - 1].strip()
                    if not next_line or next_line.startswith('//') or next_line.startswith('['):
                        continue

                    # Extract method name from method signature
                    # Pattern: public void MethodName() or public async Task MethodName()
                    method_match = re.search(r'\b(?:public|private|internal)\s+(?:async\s+)?(?:void|Task(?:<[^>]+>)?)\s+(\w+)\s*\(', next_line)
                    if method_match:
                        method_name = method_match.group(1)
                        test_methods.append((j, method_name))
                        break

    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)

    return test_methods


def scan_test_files(test_dir: Path) -> dict:
    """
    Scan all test files and find naming violations.

    Args:
        test_dir: Root directory containing test files

    Returns:
        Dictionary mapping file paths to list of violations (line_number, method_name)
    """
    violations = {}

    # Find all *Tests.cs files
    test_files = list(test_dir.rglob('*Tests.cs'))

    for test_file in test_files:
        test_methods = extract_test_methods(test_file)
        file_violations = []

        for line_num, method_name in test_methods:
            if not is_pascal_case(method_name):
                file_violations.append((line_num, method_name))

        if file_violations:
            violations[test_file] = file_violations

    return violations


def main():
    """Main entry point for the script."""
    # Determine project root (script is in scripts/python/)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    test_dir = project_root / 'Game.Core.Tests'

    if not test_dir.exists():
        print(f"Error: Test directory not found: {test_dir}", file=sys.stderr)
        return 1

    print("Scanning Game.Core.Tests for test method naming violations...")
    print(f"Test directory: {test_dir}")
    print()

    violations = scan_test_files(test_dir)

    if not violations:
        print("[OK] All test methods follow PascalCase naming convention")
        print("[OK] No violations found")
        return 0

    # Report violations
    print("[FAIL] Test naming violations found:")
    print()

    total_violations = 0
    for file_path, file_violations in sorted(violations.items()):
        rel_path = file_path.relative_to(project_root)
        print(f"{rel_path}:")
        for line_num, method_name in file_violations:
            print(f"  Line {line_num}: {method_name} (should be PascalCase, found snake_case or other pattern)")
            total_violations += 1
        print()

    print(f"Total violations: {total_violations}")
    print()
    print("Fix these violations by renaming methods to PascalCase:")
    print("  Example: my_test_method() → MyTestMethod()")

    return 1


if __name__ == '__main__':
    sys.exit(main())
