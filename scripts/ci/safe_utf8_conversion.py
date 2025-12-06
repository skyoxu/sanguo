# -*- coding: utf-8 -*-
"""
Safe UTF-8 conversion with validation and backup.
Converts files to UTF-8 while ensuring content integrity.
"""

import os
import sys
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional

# Files to convert (excluding the 2 corrupted files)
FILES_TO_CONVERT = [
    'adr/ADR-0010-internationalization.md',
    'adr/ADR-0012-pr-template-conditional-rendering.md',
    'adr/addenda/ADR-0006-godot-data-storage-addendum.md',
    'architecture/base/02-security-baseline-electron-v2.md',
    'architecture/base/03-observability-sentry-logging-v2.md',
    'architecture/base/05-data-models-and-storage-ports-v2.md',
    'architecture/base/06-runtime-view-loops-state-machines-error-paths-v2.md',
    'architecture/base/09-performance-and-capacity-v2.md',
    'architecture/base/11-risks-and-technical-debt-v2.md',
    'architecture/base/csp-policy-analysis.md',
    'architecture/base/front-matter-standardization-example.md',
    'architecture/overlays/PRD-Guild-Manager/08/ACCEPTANCE_CHECKLIST.md',
]

def calculate_md5(content: bytes) -> str:
    """Calculate MD5 hash of content."""
    return hashlib.md5(content).hexdigest()

def read_file_safely(file_path: Path) -> Tuple[Optional[str], Optional[str], Optional[bytes]]:
    """
    Read file with multiple encoding attempts.
    Returns: (content_str, encoding_used, raw_bytes)
    """
    encodings_to_try = ['utf-8', 'utf-8-sig', 'gbk', 'gb18030', 'windows-1252', 'latin-1']

    with open(file_path, 'rb') as f:
        raw_bytes = f.read()

    for encoding in encodings_to_try:
        try:
            content = raw_bytes.decode(encoding)
            # Check for replacement characters
            if '\ufffd' in content and encoding != 'latin-1':
                continue
            return content, encoding, raw_bytes
        except (UnicodeDecodeError, LookupError):
            continue

    # Fallback to latin-1 (never fails but might be wrong)
    content = raw_bytes.decode('latin-1')
    return content, 'latin-1', raw_bytes

def validate_content(content: str) -> Tuple[bool, List[str]]:
    """
    Validate content for common issues.
    Returns: (is_valid, issues_list)
    """
    issues = []

    # Check for replacement characters
    if '\ufffd' in content:
        count = content.count('\ufffd')
        issues.append(f"Contains {count} replacement character(s)")

    # Check for common garbled patterns
    garbled_patterns = ['闁', '鐟', '閻', '濡', '缂', '婵']
    for pattern in garbled_patterns:
        if pattern in content:
            count = content.count(pattern)
            if count > 5:  # More than 5 occurrences likely means garbled
                issues.append(f"Possibly garbled: '{pattern}' appears {count} times")

    # Check for null bytes
    if '\x00' in content:
        issues.append("Contains null bytes (binary file?)")

    # Check if file is suspiciously short
    if len(content.strip()) < 10:
        issues.append("File content is suspiciously short")

    return len(issues) == 0, issues

def compare_content(original: str, converted: str) -> Tuple[bool, List[str]]:
    """
    Compare original and converted content.
    Returns: (is_identical, differences_list)
    """
    differences = []

    # Check exact match
    if original == converted:
        return True, []

    # Check length difference
    len_diff = len(converted) - len(original)
    if abs(len_diff) > 10:
        differences.append(f"Length changed by {len_diff} characters")

    # Check line count difference
    orig_lines = len(original.split('\n'))
    conv_lines = len(converted.split('\n'))
    if orig_lines != conv_lines:
        differences.append(f"Line count changed: {orig_lines} -> {conv_lines}")

    # Sample first 500 chars
    if original[:500] != converted[:500]:
        differences.append("First 500 characters differ")

    # Sample last 500 chars
    if original[-500:] != converted[-500:]:
        differences.append("Last 500 characters differ")

    return len(differences) == 0, differences

def process_file(docs_path: Path, rel_path: str, backup_dir: Path) -> dict:
    """
    Process a single file: backup -> read -> validate -> convert -> verify.
    Returns: result dictionary with status and details.
    """
    result = {
        'file': rel_path,
        'success': False,
        'original_encoding': None,
        'validation_passed': False,
        'comparison_passed': False,
        'issues': [],
        'backup_path': None,
    }

    source_path = docs_path / rel_path
    backup_path = backup_dir / rel_path

    try:
        # Step 1: Create backup
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, backup_path)
        result['backup_path'] = str(backup_path)

        # Step 2: Read original with safe encoding detection
        content_str, encoding_used, raw_bytes = read_file_safely(source_path)
        result['original_encoding'] = encoding_used

        if content_str is None:
            result['issues'].append("Failed to read file with any encoding")
            return result

        # Step 3: Validate content (no garbled text)
        is_valid, validation_issues = validate_content(content_str)
        result['validation_passed'] = is_valid
        if not is_valid:
            result['issues'].extend(validation_issues)
            result['issues'].append("SKIPPED: Content validation failed")
            return result

        # Step 4: Write as UTF-8-BOM
        with open(source_path, 'w', encoding='utf-8-sig', newline='') as f:
            f.write(content_str)

        # Step 5: Read back and verify
        with open(source_path, 'r', encoding='utf-8-sig') as f:
            converted_content = f.read()

        # Step 6: Compare original and converted
        is_identical, differences = compare_content(content_str, converted_content)
        result['comparison_passed'] = is_identical

        if not is_identical:
            result['issues'].extend(differences)
            result['issues'].append("WARNING: Content changed after conversion")
            # Restore from backup
            shutil.copy2(backup_path, source_path)
            result['issues'].append("RESTORED: File restored from backup")
            return result

        # Success!
        result['success'] = True

    except Exception as e:
        result['issues'].append(f"Error: {str(e)}")
        # Try to restore from backup if it exists
        if backup_path.exists():
            try:
                shutil.copy2(backup_path, source_path)
                result['issues'].append("RESTORED: File restored from backup after error")
            except:
                pass

    return result

def main():
    """Main conversion workflow with safety checks."""
    project_root = Path(__file__).parent.parent.parent
    docs_path = project_root / 'docs'

    # Create timestamped backup directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = project_root / f'docs_conversion_backup_{timestamp}'

    print("=" * 80)
    print("Safe UTF-8 Conversion with Validation")
    print("=" * 80)
    print(f"Project root: {project_root}")
    print(f"Docs path: {docs_path}")
    print(f"Backup dir: {backup_dir}")
    print(f"Files to process: {len(FILES_TO_CONVERT)}")
    print()

    # Process each file
    results = []
    for rel_path in FILES_TO_CONVERT:
        print(f"\nProcessing: {rel_path}")
        print("-" * 80)

        result = process_file(docs_path, rel_path, backup_dir)
        results.append(result)

        # Print result
        if result['success']:
            print(f"  [SUCCESS] Converted from {result['original_encoding']} to UTF-8-BOM")
        else:
            print(f"  [FAILED] {result['original_encoding']}")
            for issue in result['issues']:
                print(f"    - {issue}")

    # Summary
    print("\n" + "=" * 80)
    print("Summary:")
    print("=" * 80)

    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    validation_failed = [r for r in results if not r['validation_passed']]
    comparison_failed = [r for r in results if not r['comparison_passed']]

    print(f"Total files: {len(results)}")
    print(f"Successfully converted: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"  - Validation failed: {len(validation_failed)}")
    print(f"  - Comparison failed: {len(comparison_failed)}")
    print()

    if successful:
        print("Successfully converted files:")
        for r in successful:
            print(f"  - {r['file']} ({r['original_encoding']} -> UTF-8-BOM)")
    print()

    if failed:
        print("Failed files (check issues above):")
        for r in failed:
            print(f"  - {r['file']}")
    print()

    print(f"Backup location: {backup_dir}")
    print("You can restore from backup if needed:")
    print(f"  xcopy /e /i /h \"{backup_dir}\\*\" \"{docs_path}\"")
    print("=" * 80)

    return 0 if len(failed) == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
