# -*- coding: utf-8 -*-
"""
Convert all files in docs directory to UTF-8 encoding.
Windows-compatible script with full backup and safety checks.
"""

import os
import sys
import glob
import shutil
import chardet
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict

def create_backup(docs_path: str, backup_path: str) -> bool:
    """Create a complete backup of docs directory."""
    try:
        print(f"Creating backup: {backup_path}")
        if os.path.exists(backup_path):
            print(f"Warning: Backup directory already exists, removing old backup...")
            shutil.rmtree(backup_path)

        shutil.copytree(docs_path, backup_path)
        print(f"Backup created successfully!")
        return True
    except Exception as e:
        print(f"Error creating backup: {e}")
        return False

def detect_encoding(file_path: str) -> Tuple[str, float]:
    """
    Detect file encoding using chardet.
    Returns: (encoding, confidence)
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding'] if result['encoding'] else 'unknown'
            confidence = result['confidence'] if result['confidence'] else 0.0
            return encoding, confidence
    except Exception as e:
        print(f"Error detecting encoding for {file_path}: {e}")
        return 'error', 0.0

def verify_file_content(file_path: str, original_size: int) -> bool:
    """Verify file after conversion - check size hasn't changed dramatically."""
    try:
        new_size = os.path.getsize(file_path)
        # Allow up to 10% size difference (UTF-8 BOM might add bytes)
        size_diff_percent = abs(new_size - original_size) / original_size * 100
        return size_diff_percent < 10
    except Exception as e:
        print(f"Error verifying file: {e}")
        return False

def convert_to_utf8(file_path: str, source_encoding: str) -> bool:
    """Convert file from source_encoding to UTF-8 with verification."""
    try:
        # Store original size
        original_size = os.path.getsize(file_path)

        # Read with source encoding
        with open(file_path, 'r', encoding=source_encoding, errors='replace') as f:
            content = f.read()

        # Write as UTF-8 (with BOM for better Windows compatibility)
        with open(file_path, 'w', encoding='utf-8-sig', errors='replace') as f:
            f.write(content)

        # Verify conversion
        if not verify_file_content(file_path, original_size):
            print(f"    [WARNING] File size changed significantly")
            return False

        return True
    except Exception as e:
        print(f"Error converting {file_path}: {e}")
        return False

def scan_and_report(docs_path: str) -> Dict[str, List[str]]:
    """
    Scan all files and generate report.
    Returns dict with keys: 'utf8', 'need_convert', 'errors'
    """
    report = {
        'utf8': [],
        'need_convert': [],
        'errors': []
    }

    # File extensions to process
    extensions = ['*.md', '*.txt', '*.xml', '*.json', '*.yaml', '*.yml']

    print("Scanning files...")
    print("=" * 80)

    for ext in extensions:
        pattern = os.path.join(docs_path, '**', ext)
        files = glob.glob(pattern, recursive=True)

        for file_path in files:
            encoding, confidence = detect_encoding(file_path)
            rel_path = os.path.relpath(file_path, docs_path)

            if encoding == 'error':
                report['errors'].append(rel_path)
                print(f"[ERROR] {rel_path} - Detection failed")
            elif encoding and encoding.lower() in ['utf-8', 'utf-8-sig', 'utf8', 'ascii']:
                report['utf8'].append(rel_path)
                print(f"[OK] {rel_path} - Already {encoding}")
            else:
                report['need_convert'].append((rel_path, encoding, confidence))
                print(f"[CONVERT] {rel_path} - {encoding} (confidence: {confidence:.2%})")

    print("=" * 80)
    return report

def process_conversions(docs_path: str, files_to_convert: List[Tuple[str, str, float]]) -> Tuple[int, int]:
    """
    Process file conversions.
    Returns: (success_count, failed_count)
    """
    success_count = 0
    failed_count = 0

    print("\nStarting conversion...")
    print("=" * 80)

    for rel_path, encoding, confidence in files_to_convert:
        file_path = os.path.join(docs_path, rel_path)
        print(f"\n[CONVERTING] {rel_path}")
        print(f"  Detected: {encoding} (confidence: {confidence:.2%})")

        if convert_to_utf8(file_path, encoding):
            # Verify new encoding
            new_encoding, new_confidence = detect_encoding(file_path)
            if new_encoding and new_encoding.lower() in ['utf-8', 'utf-8-sig', 'utf8']:
                print(f"  [SUCCESS] Now: {new_encoding}")
                success_count += 1
            else:
                print(f"  [FAILED] Verification failed - detected as: {new_encoding}")
                failed_count += 1
        else:
            print(f"  [FAILED] Conversion error")
            failed_count += 1

    print("=" * 80)
    return success_count, failed_count

def main():
    """Main entry point with full backup."""
    # Get paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    docs_path = project_root / 'docs'

    # Create backup directory with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = project_root / f'docs_backup_{timestamp}'

    if not docs_path.exists():
        print(f"Error: docs directory not found at {docs_path}")
        sys.exit(1)

    print("=" * 80)
    print("UTF-8 Conversion Tool with Full Backup")
    print("=" * 80)
    print(f"Project root: {project_root}")
    print(f"Docs path: {docs_path}")
    print(f"Backup path: {backup_path}")
    print("=" * 80)
    print()

    # Check if chardet is installed
    try:
        import chardet
    except ImportError:
        print("Error: chardet module not found.")
        print("Install it with: py -3 -m pip install chardet")
        sys.exit(1)

    # Step 1: Create backup
    print("Step 1: Creating full backup...")
    if not create_backup(str(docs_path), str(backup_path)):
        print("Failed to create backup. Aborting for safety.")
        sys.exit(1)
    print()

    # Step 2: Scan and report
    print("Step 2: Scanning files and generating report...")
    report = scan_and_report(str(docs_path))
    print()

    # Print summary
    total_files = len(report['utf8']) + len(report['need_convert']) + len(report['errors'])
    print("Scan Summary:")
    print(f"  Total files: {total_files}")
    print(f"  Already UTF-8: {len(report['utf8'])}")
    print(f"  Need conversion: {len(report['need_convert'])}")
    print(f"  Errors: {len(report['errors'])}")
    print()

    if report['errors']:
        print("Warning: Some files had detection errors:")
        for f in report['errors']:
            print(f"  - {f}")
        print()

    if not report['need_convert']:
        print("All files are already UTF-8. No conversion needed.")
        print(f"\nBackup created at: {backup_path}")
        print("You can delete the backup if not needed.")
        sys.exit(0)

    # Step 3: Ask for confirmation
    print("Files that will be converted:")
    for rel_path, encoding, confidence in report['need_convert']:
        print(f"  {rel_path} ({encoding}, {confidence:.2%})")
    print()

    response = input("Proceed with conversion? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Conversion cancelled.")
        print(f"Backup is kept at: {backup_path}")
        sys.exit(0)

    # Step 4: Convert files
    success, failed = process_conversions(str(docs_path), report['need_convert'])

    # Final summary
    print("\n" + "=" * 80)
    print("Conversion Summary:")
    print(f"  Successfully converted: {success}")
    print(f"  Failed: {failed}")
    print(f"  Backup location: {backup_path}")
    print("=" * 80)

    if failed > 0:
        print("\nWarning: Some files failed to convert.")
        print("You can restore from backup if needed:")
        print(f"  1. Delete current docs: rmdir /s /q \"{docs_path}\"")
        print(f"  2. Restore backup: xcopy /e /i /h \"{backup_path}\" \"{docs_path}\"")
        sys.exit(1)
    else:
        print("\nAll files converted successfully!")
        print("You can delete the backup after verifying the results:")
        print(f"  rmdir /s /q \"{backup_path}\"")
        sys.exit(0)

if __name__ == '__main__':
    main()
