"""
Test Naming Convention Validator for Game.Core.Tests

This script validates that all test methods in Game.Core.Tests follow the repository-approved
test naming conventions and prevents regression to snake_case naming.

Usage:
    py -3 scripts/python/check_test_naming.py
    py -3 scripts/python/check_test_naming.py --style strict
    py -3 scripts/python/check_test_naming.py --task-id 14 --style strict

Exit codes:
    0 - All test methods follow approved conventions
    1 - Violations found (snake_case or other non-approved patterns)

Requirements:
    - Scans all *Tests.cs files in Game.Core.Tests/
    - Checks methods marked with [Fact] or [Theory]
    - Reports violations with file path and line number
"""

import argparse
import json
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


def is_pascal_case_with_underscores(name: str) -> bool:
    """
    Check if a method name follows the PascalCase_With_Underscores convention.

    Examples:
      - Save_load_delete_and_index_flow_works_with_compression  (NOT allowed: starts with lowercase)
      - Save_Load_Delete_And_Index_Flow_WorksWithCompression    (allowed)
      - Advance_WithinBounds_ReturnsCorrectPosition             (allowed)

    Rules:
      - Each segment is PascalCase (no underscores within segments)
      - Segments are separated by a single underscore
    """
    pattern = r'^[A-Z][a-zA-Z0-9]*(?:_[A-Z][a-zA-Z0-9]*)+$'
    return bool(re.match(pattern, name))


def is_should_style(name: str) -> bool:
    """
    Strict style A (Should_):
      - ShouldDoX_WhenY
    """
    return bool(re.match(r'^Should[A-Z][a-zA-Z0-9]*_When[A-Z][a-zA-Z0-9]*$', name))


def is_given_when_then_style(name: str) -> bool:
    """
    Strict style B (Given_When_Then):
      - GivenX_WhenY_ThenZ
    """
    return bool(re.match(r'^Given[A-Z][a-zA-Z0-9]*_When[A-Z][a-zA-Z0-9]*_Then[A-Z][a-zA-Z0-9]*$', name))


def is_allowed_test_method_name(name: str, *, style: str) -> bool:
    if style == "legacy":
        return is_pascal_case(name) or is_pascal_case_with_underscores(name)
    if style == "strict":
        return is_should_style(name) or is_given_when_then_style(name)
    raise ValueError(f"Unknown style: {style}")


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


def scan_test_files(test_dir: Path, *, style: str) -> dict:
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
            if not is_allowed_test_method_name(method_name, style=style):
                file_violations.append((line_num, method_name))

        if file_violations:
            violations[test_file] = file_violations

    return violations


def repo_root() -> Path:
    # scripts/python/* -> repo root
    return Path(__file__).resolve().parents[2]


def load_task_test_refs(*, root: Path, task_id: str) -> List[Path]:
    """
    Resolve task's test_refs from the triplet task views (tasks_back/tasks_gameplay),
    returning filesystem paths under the repository root.
    """
    back_path = root / ".taskmaster" / "tasks" / "tasks_back.json"
    gameplay_path = root / ".taskmaster" / "tasks" / "tasks_gameplay.json"
    if not back_path.exists() or not gameplay_path.exists():
        return []

    try:
        back = json.loads(back_path.read_text(encoding="utf-8"))
        gameplay = json.loads(gameplay_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    try:
        tid_int = int(str(task_id))
    except ValueError:
        return []

    refs: List[str] = []
    for view in (back, gameplay):
        if not isinstance(view, list):
            continue
        for t in view:
            if not isinstance(t, dict):
                continue
            if t.get("taskmaster_id") != tid_int:
                continue
            tr = t.get("test_refs")
            if isinstance(tr, list):
                for r in tr:
                    s = str(r).strip().replace("\\", "/")
                    if s:
                        refs.append(s)

    uniq: List[str] = []
    seen = set()
    for r in refs:
        if r in seen:
            continue
        seen.add(r)
        uniq.append(r)

    # Only C# unit tests are in scope for this validator.
    paths: List[Path] = []
    for r in uniq:
        if not r.endswith(".cs"):
            continue
        paths.append(root / r)
    return paths


def scan_specific_files(*, files: List[Path], style: str) -> dict:
    violations = {}
    for test_file in files:
        if not test_file.exists():
            continue
        test_methods = extract_test_methods(test_file)
        file_violations = []
        for line_num, method_name in test_methods:
            if not is_allowed_test_method_name(method_name, style=style):
                file_violations.append((line_num, method_name))
        if file_violations:
            violations[test_file] = file_violations
    return violations


def main():
    """Main entry point for the script."""
    ap = argparse.ArgumentParser(description="Validate test method naming conventions for Game.Core.Tests.")
    ap.add_argument("--style", choices=["legacy", "strict"], default="legacy", help="Naming style to enforce.")
    ap.add_argument("--task-id", default=None, help="If set, validate only the task's C# test_refs (.cs).")
    args = ap.parse_args()

    project_root = repo_root()
    test_dir = project_root / "Game.Core.Tests"

    if not test_dir.exists():
        print(f"Error: Test directory not found: {test_dir}", file=sys.stderr)
        return 1

    scope = "all Game.Core.Tests"
    if args.task_id:
        scope = f"task-id={args.task_id} (test_refs .cs only)"

    print("Scanning Game.Core.Tests for test method naming violations...")
    print(f"Scope: {scope}")
    print(f"Style: {args.style}")
    print()

    if args.task_id:
        files = load_task_test_refs(root=project_root, task_id=str(args.task_id).split(".", 1)[0])
        violations = scan_specific_files(files=files, style=args.style)
    else:
        violations = scan_test_files(test_dir, style=args.style)

    if not violations:
        print("[OK] All test methods follow approved naming conventions")
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
            print(f"  Line {line_num}: {method_name} (not approved; avoid snake_case)")
            total_violations += 1
        print()

    print(f"Total violations: {total_violations}")
    print()
    print("Fix these violations by renaming methods to an approved pattern:")
    if args.style == "strict":
        print("  - Should_: ShouldReturnZero_WhenMultiplierIsZero")
        print("  - Given_When_Then: GivenEnoughMoney_WhenBuyingCity_ThenCityOwned")
    else:
        print("  - PascalCase: GivenNoState_WhenSaveGame_ThenThrowsInvalidOperationException")
        print("  - PascalCase_With_Underscores: SaveGame_WhenStateMissing_ShouldThrowInvalidOperationException")

    return 1


if __name__ == '__main__':
    sys.exit(main())
