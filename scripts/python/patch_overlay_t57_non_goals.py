from __future__ import annotations

from pathlib import Path


def main() -> int:
    path = Path("docs/architecture/overlays/PRD-SANGUO-T2/08/08-t57-action-cards.md")
    text = path.read_text(encoding="utf-8")

    needle = "## 非目标\n- 不做多卡连锁与复杂卡牌规则。\n"
    insert = (
        "## 非目标\n"
        "- 不做多卡连锁与复杂卡牌规则。\n"
        "- 不实现跨回合持续效果：`durationRounds` 仅作为前向兼容字段保留并随事件/目录输出，本任务止损版只对当前回合生效。\n"
    )

    if needle not in text:
        raise SystemExit("Target section not found; refusing to patch.")

    updated = text.replace(needle, insert, 1)
    path.write_text(updated, encoding="utf-8", newline="\n")
    print(f"Patched: {path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

