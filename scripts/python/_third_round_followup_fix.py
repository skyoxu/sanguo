#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected exactly one match in {path}, found {count}")
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text.replace(old, new, 1))


# Empty/no task selection is the full-rebuild mode. Keep it explicit in both
# the library branch and the CLI adapter so stale catalog entries cannot survive.
replace_once(
    "scripts/python/generate_knowledge_links.py",
    "        if task_ids is None:\n            catalog_entries = []\n",
    "        if not task_ids:\n            catalog_entries = []\n",
)
replace_once(
    "scripts/python/generate_knowledge_links.py",
    "    print(json.dumps(generate(args.repo_root.resolve(), set(args.task_ids or []), args.write_task_refs), ensure_ascii=False))\n",
    "    selected = set(args.task_ids) if args.task_ids else None\n    print(json.dumps(generate(args.repo_root.resolve(), selected, args.write_task_refs), ensure_ascii=False))\n",
)
replace_once(
    "scripts/python/tests/test_generate_knowledge_links.py",
    "\n\nif __name__ == \"__main__\":\n    unittest.main()\n",
    '''\n    def test_cli_without_task_ids_requests_full_rebuild(self) -> None:\n        with mock.patch.object(module, "generate", return_value={"status": "ok"}) as generate:\n            self.assertEqual(module.main([]), 0)\n        self.assertIsNone(generate.call_args.args[1])\n\n\nif __name__ == "__main__":\n    unittest.main()\n''',
)

print("full-rebuild follow-up patch staged")
