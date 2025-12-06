# -*- coding: utf-8 -*-
"""
Smart encoding repair using backup files as reference.
Repairs garbled Chinese text by comparing with backup versions.
"""

import os
import re
import difflib
from pathlib import Path
from typing import List, Tuple, Optional, Dict

# Garbled patterns to detect (single characters that commonly appear in garbled text)
GARBLED_CHARS = set(['闁', '鐟', '閻', '濡', '缂', '婵', '鐜', '鍑', '鍑', '鍑', '鍑', '鍑',
                      '鍑', '鍑', '鍑', '鍑', '鍑', '鍑', '鍑', '鍑', '鍑', '鍑', '鍑'])

def is_likely_garbled(text: str) -> bool:
    """Check if text contains likely garbled characters."""
    garbled_count = sum(1 for char in text if char in GARBLED_CHARS)
    return garbled_count > 0

class GarbledTextRepair:
    def __init__(self, current_file: Path, backup_file: Path):
        self.current_file = current_file
        self.backup_file = backup_file
        self.current_content = None
        self.backup_content = None
        self.garbled_positions = []

    def read_files(self) -> bool:
        """Read both current and backup files."""
        try:
            # Read current file
            with open(self.current_file, 'r', encoding='utf-8-sig', errors='replace') as f:
                self.current_content = f.read()

            # Read backup file
            with open(self.backup_file, 'r', encoding='utf-8', errors='replace') as f:
                self.backup_content = f.read()

            return True
        except Exception as e:
            print(f"  Error reading files: {e}")
            return False

    def detect_garbled_text(self) -> List[Tuple[int, int, str]]:
        """
        Detect garbled text positions in current file.
        Returns: [(start_pos, end_pos, garbled_text), ...]
        """
        garbled = []

        for pattern in GARBLED_PATTERNS:
            for match in re.finditer(pattern, self.current_content):
                garbled.append((match.start(), match.end(), match.group()))

        # Sort by position
        garbled.sort(key=lambda x: x[0])
        return garbled

    def find_context_in_backup(self, pos: int, window: int = 50) -> Optional[str]:
        """
        Find the surrounding context of a garbled position in backup file.
        """
        # Get context before and after the garbled text
        context_before = self.current_content[max(0, pos - window):pos]
        context_after = self.current_content[pos + window:min(len(self.current_content), pos + window * 2)]

        # Remove garbled parts from context
        for pattern in GARBLED_PATTERNS:
            context_before = re.sub(pattern, '', context_before)
            context_after = re.sub(pattern, '', context_after)

        # Try to find similar context in backup
        if context_before or context_after:
            # Use difflib to find best match
            matcher = difflib.SequenceMatcher(None, context_before + context_after, self.backup_content)
            match = matcher.find_longest_match(0, len(context_before + context_after), 0, len(self.backup_content))

            if match.size > 10:  # At least 10 chars match
                # Extract the corresponding text from backup
                backup_pos = match.b + len(context_before)
                backup_end = backup_pos + window
                return self.backup_content[backup_pos:backup_end]

        return None

    def repair_content(self) -> Tuple[str, int, int]:
        """
        Repair garbled text using backup as reference.
        Returns: (repaired_content, successful_repairs, skipped_repairs)
        """
        repaired = self.current_content
        successful = 0
        skipped = 0

        garbled_list = self.detect_garbled_text()

        if not garbled_list:
            return repaired, 0, 0

        print(f"  Found {len(garbled_list)} garbled segments")

        # Process from end to start to maintain positions
        for start, end, garbled_text in reversed(garbled_list):
            # Check if backup also has garbled text at similar position
            backup_context = self.find_context_in_backup(start)

            if backup_context:
                # Check if backup context is also garbled
                has_backup_garbled = any(re.search(p, backup_context) for p in GARBLED_PATTERNS)

                if not has_backup_garbled:
                    # Backup has clean text, use it
                    # Extract reasonable replacement text
                    replacement = backup_context.strip()[:len(garbled_text)]
                    repaired = repaired[:start] + replacement + repaired[end:]
                    successful += 1
                    print(f"    Repaired: '{garbled_text}' -> '{replacement}'")
                else:
                    # Backup also garbled, skip
                    skipped += 1
                    print(f"    Skipped: '{garbled_text}' (backup also garbled)")
            else:
                # Cannot find context in backup
                skipped += 1
                print(f"    Skipped: '{garbled_text}' (no backup context)")

        return repaired, successful, skipped

    def verify_repair(self, repaired_content: str) -> Tuple[bool, List[str]]:
        """
        Verify repaired content quality.
        Returns: (is_valid, issues)
        """
        issues = []

        # Check for remaining replacement characters
        if '\ufffd' in repaired_content:
            issues.append(f"Contains {repaired_content.count(chr(0xFFFD))} replacement chars")

        # Check for remaining garbled patterns
        remaining_garbled = 0
        for pattern in GARBLED_PATTERNS:
            matches = re.findall(pattern, repaired_content)
            remaining_garbled += len(matches)

        if remaining_garbled > 0:
            issues.append(f"Still has {remaining_garbled} garbled segments")

        # Check length difference
        len_diff = abs(len(repaired_content) - len(self.backup_content))
        len_diff_pct = (len_diff / len(self.backup_content)) * 100 if self.backup_content else 0

        if len_diff_pct > 20:
            issues.append(f"Length differs by {len_diff_pct:.1f}% from backup")

        return len(issues) == 0, issues

def scan_all_files(docs_path: Path, backup_docs_path: Path) -> List[Tuple[Path, Path]]:
    """
    Scan all markdown files and find pairs with backup.
    """
    pairs = []

    for current_file in docs_path.rglob('*.md'):
        rel_path = current_file.relative_to(docs_path)
        backup_file = backup_docs_path / rel_path

        if backup_file.exists():
            pairs.append((current_file, backup_file))

    return pairs

def main():
    """Main repair workflow."""
    project_root = Path(__file__).parent.parent.parent
    docs_path = project_root / 'docs'
    backup_docs_path = project_root / 'backup' / 'docs'

    if not backup_docs_path.exists():
        print(f"Error: Backup directory not found: {backup_docs_path}")
        return 1

    print("=" * 80)
    print("Smart Encoding Repair Using Backup Files")
    print("=" * 80)
    print(f"Docs path: {docs_path}")
    print(f"Backup path: {backup_docs_path}")
    print()

    # Scan all files
    print("Scanning for file pairs...")
    file_pairs = scan_all_files(docs_path, backup_docs_path)
    print(f"Found {len(file_pairs)} file pairs")
    print()

    # Process each file
    results = []

    for current_file, backup_file in file_pairs:
        rel_path = current_file.relative_to(docs_path)
        print(f"Processing: {rel_path}")

        repairer = GarbledTextRepair(current_file, backup_file)

        if not repairer.read_files():
            print(f"  [SKIP] Cannot read files")
            continue

        # Repair
        repaired_content, successful, skipped = repairer.repair_content()

        if successful == 0 and skipped == 0:
            print(f"  [OK] No garbled text found")
            results.append({
                'file': str(rel_path),
                'status': 'clean',
                'repairs': 0,
                'skipped': 0,
            })
            continue

        if successful > 0:
            # Verify repair
            is_valid, issues = repairer.verify_repair(repaired_content)

            if is_valid:
                # Write repaired content
                with open(current_file, 'w', encoding='utf-8-sig') as f:
                    f.write(repaired_content)

                print(f"  [REPAIRED] {successful} repairs, {skipped} skipped")
                results.append({
                    'file': str(rel_path),
                    'status': 'repaired',
                    'repairs': successful,
                    'skipped': skipped,
                })
            else:
                print(f"  [FAILED] Verification failed:")
                for issue in issues:
                    print(f"    - {issue}")
                results.append({
                    'file': str(rel_path),
                    'status': 'failed',
                    'repairs': successful,
                    'skipped': skipped,
                    'issues': issues,
                })
        else:
            print(f"  [SKIP] All garbled segments skipped ({skipped} total)")
            results.append({
                'file': str(rel_path),
                'status': 'skipped',
                'repairs': 0,
                'skipped': skipped,
            })

        print()

    # Summary
    print("=" * 80)
    print("Summary:")
    print("=" * 80)

    clean_files = [r for r in results if r['status'] == 'clean']
    repaired_files = [r for r in results if r['status'] == 'repaired']
    failed_files = [r for r in results if r['status'] == 'failed']
    skipped_files = [r for r in results if r['status'] == 'skipped']

    print(f"Total files processed: {len(results)}")
    print(f"Clean files (no garbled text): {len(clean_files)}")
    print(f"Successfully repaired: {len(repaired_files)}")
    print(f"Failed repairs: {len(failed_files)}")
    print(f"Skipped (backup also garbled): {len(skipped_files)}")
    print()

    if repaired_files:
        print("Repaired files:")
        for r in repaired_files:
            print(f"  - {r['file']} ({r['repairs']} repairs, {r['skipped']} skipped)")

    if failed_files:
        print("\nFailed files:")
        for r in failed_files:
            print(f"  - {r['file']}")

    if skipped_files:
        print("\nSkipped files (backup also garbled):")
        for r in skipped_files:
            print(f"  - {r['file']} ({r['skipped']} garbled segments)")

    print("=" * 80)

    return 0 if len(failed_files) == 0 else 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
