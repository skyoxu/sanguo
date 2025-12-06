# -*- coding: utf-8 -*-
"""
Fix encoding for 2 corrupted files using backup originals.
"""

import sys
from pathlib import Path

def fix_file_encoding(backup_path, target_path):
    """
    Read from backup with multiple encoding attempts,
    write to target as UTF-8.
    """
    # Try GBK first (most common for Chinese Windows files)
    encodings_to_try = ['gbk', 'gb18030', 'gb2312', 'windows-1252', 'utf-8']

    print(f"\nProcessing: {backup_path.name}")
    print(f"  Backup: {backup_path}")
    print(f"  Target: {target_path}")

    # Read raw bytes
    with open(backup_path, 'rb') as f:
        raw_data = f.read()

    # Try different encodings
    content = None
    detected_encoding = None
    best_content = None
    best_encoding = None
    min_replacement_chars = float('inf')

    for encoding in encodings_to_try:
        try:
            decoded = raw_data.decode(encoding)
            replacement_count = decoded.count('\ufffd')

            print(f"  Trying {encoding}: {replacement_count} replacement chars")

            # Track the best result
            if replacement_count < min_replacement_chars:
                min_replacement_chars = replacement_count
                best_content = decoded
                best_encoding = encoding

            # If no replacement chars, we found the right encoding
            if replacement_count == 0:
                content = decoded
                detected_encoding = encoding
                print(f"  Successfully decoded with: {encoding} (perfect match)")
                break
        except (UnicodeDecodeError, LookupError) as e:
            print(f"  Failed with {encoding}: {e}")
            continue

    # If no perfect match, use the best one
    if content is None and best_content is not None:
        content = best_content
        detected_encoding = best_encoding
        print(f"  Using best match: {detected_encoding} ({min_replacement_chars} replacement chars)")

    if content is None:
        print(f"  [ERROR] Could not decode file with any encoding")
        return False

    # Show preview
    preview_lines = content.split('\n')[:5]
    print(f"  Preview (first 5 lines):")
    for line in preview_lines:
        print(f"    {line[:80]}")

    # Write as UTF-8 with BOM
    with open(target_path, 'w', encoding='utf-8-sig') as f:
        f.write(content)

    print(f"  [SUCCESS] Written as UTF-8-BOM")
    return True

def main():
    """Fix the 2 corrupted files."""
    project_root = Path(__file__).parent.parent.parent
    backup_dir = project_root / 'backup'
    docs_dir = project_root / 'docs'

    files_to_fix = [
        ('MIGRATION_INDEX.md', 'migration/MIGRATION_INDEX.md'),
        ('Phase-17-Build-System-and-Godot-Export.md', 'migration/Phase-17-Build-System-and-Godot-Export.md'),
    ]

    print("=" * 80)
    print("Fixing encoding for 2 corrupted files from backup")
    print("=" * 80)
    print(f"Backup directory: {backup_dir}")
    print(f"Docs directory: {docs_dir}")
    print()

    success_count = 0
    failed_count = 0

    for backup_file, target_file in files_to_fix:
        backup_path = backup_dir / backup_file
        target_path = docs_dir / target_file

        if not backup_path.exists():
            print(f"\n[ERROR] Backup file not found: {backup_path}")
            failed_count += 1
            continue

        if fix_file_encoding(backup_path, target_path):
            success_count += 1
        else:
            failed_count += 1

    print("\n" + "=" * 80)
    print(f"Summary:")
    print(f"  Successfully fixed: {success_count}")
    print(f"  Failed: {failed_count}")
    print("=" * 80)

    return 0 if failed_count == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
