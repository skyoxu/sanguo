#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch docs/testing-framework.auto.test-org-naming-refs.zh.md to add acceptance anchor rules,
then regenerate docs/testing-framework.md.

This script is deterministic and uses UTF-8 for all reads/writes.

Windows:
  py -3 scripts/python/patch_testing_framework_add_acceptance_anchors.py
"""

from __future__ import annotations

from pathlib import Path


FRAGMENT = "docs/testing-framework.auto.test-org-naming-refs.zh.md"
TARGET = "docs/testing-framework.md"
UPDATER = "scripts/python/update_testing_framework_from_fragments.py"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def _insert_block_text() -> str:
    # Keep this file ASCII-only (repo rule). The actual inserted text is UTF-8.
    import base64

    b64 = (
        "IyMjIyAzLjEuMSBgUmVmczpgIOeahOivreS5iee7keWumu+8mmBBQ0M6VDxpZD4uPG4+YO+8iOehrOmXqOemge+8iQoK"
        "YFJlZnM6YCDop6PlhrPigJzmjIflkJHlk6rkuKrmlofku7bigJ3vvIzkvYbml6Dms5Xkv53or4HigJzor6Xmlofku7bl"
        "hoXlrrnnnJ/nmoTopobnm5bor6XmnaEgYWNjZXB0YW5jZeKAneOAguS4uumZjeS9juKAnOWBhyBkb25l4oCd77yM5pys"
        "5LuT5bqT5byV5YWlIGFjY2VwdGFuY2UgYW5jaG9y77yaCgotIOWvueS6juS7u+WKoSBgVDxpZD5gIOeahOesrCBgbmAg"
        "5p2hIGFjY2VwdGFuY2XvvIgqKjEtYmFzZWQqKu+8jOS4i+agh+aMieivpeS7u+WKoeinhuWbvueahCBgYWNjZXB0YW5j"
        "ZVtdYCDmlbDnu4Tpobrluo/vvInvvIzlhbYgYW5jaG9yIOS4uu+8mmBBQ0M6VDxpZD4uPG4+YAotIOivpeadoSBhY2Nl"
        "cHRhbmNlIOeahCBgUmVmczpgIOaMh+WQkeeahOa1i+ivleaWh+S7tuS4re+8jOiHs+WwkeacieS4gOS4quaWh+S7tuW/"
        "hemhu+WMheWQq+ivpSBhbmNob3Ig5a2X56ym5Liy77yI5Lu75oSP5L2N572u5Z2H5Y+v77yJ44CCCiAgLSB4VW5pdCDl"
        "u7rorq7lhpnlnKggYFtUcmFpdCgiYWNjZXB0YW5jZSIsICJBQ0M6VDxpZD4uPG4+IildYCDmiJbmtYvor5Xmlofku7bm"
        "s6jph4rlnZfkuK3jgIIKICAtIEdkVW5pdDQg5bu66K6u5YaZ5Zyo5rWL6K+V5Ye95pWw5rOo6YeK77yI5aaCIGAjIGFj"
        "Y2VwdGFuY2U6IEFDQzpUPGlkPi48bj5g77yJ5oiW5paH5Lu25aS05rOo6YeK5Z2X5Lit44CCCi0g6K+l6KeE5YiZ5Y+q"
        "5ZyoICoqcmVmYWN0b3IqKiDpmLbmrrXkvZzkuLrnoazpl6jnpoHmiafooYzjgIIKCuWvueW6lOmXqOemge+8iOiHquWK"
        "qOi/kOihjO+8jOaXoOmcgOaJi+W3peiusO+8ie+8miAgCi0gYHB5IC0zIHNjcmlwdHMvcHl0aG9uL3ZhbGlkYXRlX2Fj"
        "Y2VwdGFuY2VfYW5jaG9ycy5weSAtLXRhc2staWQgPGlkPiAtLXN0YWdlIHJlZmFjdG9yIC4uLmAK"
    )
    return base64.b64decode(b64).decode("utf-8")


def insert_once(fragment_text: str) -> str:
    if "ACC:T<id>.<n>" in fragment_text:
        return fragment_text

    marker = "#### 3.2 `test_refs[]`\uff08\u4efb\u52a1\u7ea7\u6c47\u603b\uff09\u5982\u4f55\u7ef4\u62a4"
    idx = fragment_text.find(marker)
    if idx < 0:
        raise ValueError(f"Insert marker not found in fragment: {marker}")

    before = fragment_text[:idx].rstrip() + "\n"
    after = fragment_text[idx:].lstrip()
    insert_block = _insert_block_text().lstrip("\n").rstrip()
    return before + insert_block + "\n\n" + after


def main() -> int:
    root = repo_root()
    fragment_path = root / FRAGMENT
    target_path = root / TARGET
    updater_path = root / UPDATER

    if not fragment_path.exists():
        raise FileNotFoundError(f"Missing fragment: {FRAGMENT}")
    if not target_path.exists():
        raise FileNotFoundError(f"Missing target: {TARGET}")
    if not updater_path.exists():
        raise FileNotFoundError(f"Missing updater: {UPDATER}")

    original = read_text(fragment_path)
    patched = insert_once(original)
    if patched != original:
        write_text(fragment_path, patched)

    # Regenerate docs/testing-framework.md from fragments (keeps SSoT).
    import subprocess

    proc = subprocess.run(
        ["py", "-3", str(updater_path.relative_to(root))],
        cwd=str(root),
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    return int(proc.returncode or 0)


if __name__ == "__main__":
    raise SystemExit(main())
