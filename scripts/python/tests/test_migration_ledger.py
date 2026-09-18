import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from check_migration_ledger import (
    duplicate_pr_errors,
    extract_migration_key,
    find_record_for_pr,
    validate_ledger,
)


def base_doc():
    return {
        "schema_version": "sanguo.upstream-migration-ledger.v1",
        "source_repository": "skyoxu/newrouge",
        "target_repository": "skyoxu/sanguo",
        "records": [
            {
                "id": "migration-a",
                "migration_key": "skyoxu/newrouge@" + "a" * 40 + "->skyoxu/sanguo",
                "source_prs": [1],
                "source_commits": ["a" * 40],
                "target_pr": 10,
                "target_branch": "feat/migration-a",
                "target_base": "b" * 40,
                "status": "open",
                "mode": "adapted",
                "scope": ["mvg"],
                "excluded": [],
            }
        ],
    }


class MigrationLedgerTests(unittest.TestCase):
    def test_valid_ledger_passes(self):
        self.assertEqual([], validate_ledger(base_doc()))

    def test_duplicate_key_and_target_pr_are_rejected(self):
        doc = base_doc()
        duplicate = copy.deepcopy(doc["records"][0])
        duplicate["id"] = "migration-b"
        doc["records"].append(duplicate)
        errors = validate_ledger(doc)
        self.assertTrue(any("duplicate migration_key" in error for error in errors))
        self.assertTrue(any("duplicate target_pr" in error for error in errors))

    def test_same_active_source_commit_cannot_have_two_canonical_records(self):
        doc = base_doc()
        duplicate = copy.deepcopy(doc["records"][0])
        duplicate["id"] = "migration-b"
        duplicate["migration_key"] = "skyoxu/newrouge@" + "c" * 40 + "->skyoxu/sanguo"
        duplicate["source_commits"] = ["a" * 40, "c" * 40]
        duplicate["target_pr"] = 11
        duplicate["target_branch"] = "feat/migration-b"
        doc["records"].append(duplicate)
        errors = validate_ledger(doc)
        self.assertTrue(any("already active" in error for error in errors))

    def test_migration_key_must_bind_latest_source_commit(self):
        doc = base_doc()
        doc["records"][0]["source_commits"].append("c" * 40)
        errors = validate_ledger(doc)
        self.assertTrue(any("bind the latest source commit" in error for error in errors))

    def test_current_pr_maps_by_number_branch_or_marker_but_only_once(self):
        doc = base_doc()
        key = doc["records"][0]["migration_key"]
        pr = {
            "number": 10,
            "body": "Migration-Key: " + key,
            "head": {"ref": "feat/migration-a"},
        }
        self.assertEqual("migration-a", find_record_for_pr(doc, pr)["id"])
        self.assertEqual(key, extract_migration_key(pr["body"]))

    def test_duplicate_open_pr_marker_is_rejected(self):
        doc = base_doc()
        record = doc["records"][0]
        key = record["migration_key"]
        current = {"number": 10, "body": "Migration-Key: " + key}
        open_prs = [
            current,
            {"number": 11, "body": "Migration-Key: " + key},
        ]
        errors = duplicate_pr_errors(record, current, open_prs)
        self.assertTrue(any("exactly one open PR" in error for error in errors))

    def test_current_pr_must_carry_exact_marker(self):
        record = base_doc()["records"][0]
        current = {"number": 10, "body": "no marker"}
        errors = duplicate_pr_errors(record, current, [current])
        self.assertTrue(any("does not match ledger" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
