# -*- coding: utf-8 -*-
"""
Simple file restore from backup when garbled text is detected.
"""

import os
import shutil
from pathlib import Path
from typing import List, Tuple

# Known garbled characters
GARBLED_CHARS = {'闁', '鐟', '閻', '濡', '缂', '婵', '鐜', '鍑', '鍑', '鍑', '鍑', '鍑'}

def has_garbled_text(file_path: Path) -> bool:
    """Check if file contains garbled Chinese text."""
    try:
        with open(file_path, 'r', encoding='utf-8-sig', errors='replace') as f:
            content = f.read()
            garbled_count = sum(1 for char in content if char in GARBLED_CHARS)
            return garbled_count > 5  # More than 5 garbled chars = problem
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

def restore_from_backup(current_file: Path, backup_file: Path) -> bool:
    """Restore current file from backup."""
    try:
        # Check if backup also has garbled text
        if has_garbled_text(backup_file):
            return False

        # Copy backup to current
        shutil.copy2(backup_file, current_file)
        return True
    except Exception as e:
        print(f"Error restoring file: {e}")
        return False

def main():
    """Main workflow."""
    project_root = Path(__file__).parent.parent.parent
    docs_path = project_root / 'docs'
    backup_docs_path = project_root / 'backup' / 'docs'

    if not backup_docs_path.exists():
        print(f"Error: Backup directory not found: {backup_docs_path}")
        return 1

    print("=" * 80)
    print("File Restoration from Backup (Garbled Text Detection)")
    print("=" * 80)
    print(f"Docs path: {docs_path}")
    print(f"Backup path: {backup_docs_path}")
    print()

    garbled_files = []
    restored_files = []
    backup_also_garbled = []
    no_backup = []

    # Scan all markdown files
    for current_file in docs_path.rglob('*.md'):
        rel_path = current_file.relative_to(docs_path)

        if has_garbled_text(current_file):
            print(f"[GARBLED] {rel_path}")
            garbled_files.append(rel_path)

            backup_file = backup_docs_path / rel_path

            if not backup_file.exists():
                print(f"  No backup found")
                no_backup.append(rel_path)
                continue

            if has_garbled_text(backup_file):
                print(f"  Backup also garbled, skipping")
                backup_also_garbled.append(rel_path)
                continue

            # Restore from backup
            if restore_from_backup(current_file, backup_file):
                print(f"  [RESTORED] from backup")
                restored_files.append(rel_path)
            else:
                print(f"  [FAILED] Restore failed")

    # Summary
    print("\n" + "=" * 80)
    print("Summary:")
    print("=" * 80)
    print(f"Total garbled files found: {len(garbled_files)}")
    print(f"Successfully restored: {len(restored_files)}")
    print(f"Backup also garbled (skipped): {len(backup_also_garbled)}")
    print(f"No backup available: {len(no_backup)}")
    print()

    if restored_files:
        print("Restored files:")
        for f in restored_files:
            print(f"  - {f}")
        print()

    if backup_also_garbled:
        print("Backup also garbled (manual fix needed):")
        for f in backup_also_garbled:
            print(f"  - {f}")
        print()

    if no_backup:
        print("No backup available (manual fix needed):")
        for f in no_backup:
            print(f"  - {f}")
        print()

    print("=" * 80)

    return 0 if len(backup_also_garbled) + len(no_backup) == 0 else 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
