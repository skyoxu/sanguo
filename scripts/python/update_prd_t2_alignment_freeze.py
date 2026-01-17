#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UpdateResult:
    path: str
    changed: bool
    bytes_before: int
    bytes_after: int


def _today_ci_dir() -> Path:
    date = dt.date.today().strftime("%Y-%m-%d")
    return Path("logs") / "ci" / date / "prd-alignment-freeze"


def _read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_utf8(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Repo enforces CRLF in working tree via .gitattributes; write CRLF to avoid churn/warnings.
    normalized = text.replace("\r\n", "\n").replace("\n", "\r\n")
    path.write_bytes(normalized.encode("utf-8"))


def _find_section(text: str, start_token: str, end_token: str) -> tuple[int, int]:
    start = text.find(start_token)
    if start < 0:
        raise ValueError(f"Missing start token: {start_token!r}")
    end = text.find(end_token, start + len(start_token))
    if end < 0:
        raise ValueError(f"Missing end token: {end_token!r} (after {start_token!r})")
    return start, end


def _replace_once(text: str, old: str, new: str) -> str:
    if old not in text:
        raise ValueError(f"Missing expected snippet to replace: {old!r}")
    return text.replace(old, new, 1)


def _ensure_bullets(text: str, bullets: list[str]) -> str:
    # Insert bullets right after the first "- 范围：" line if present, else append at end.
    marker = "\n- 范围："
    idx = text.find(marker)
    if idx < 0:
        for b in bullets:
            if b not in text:
                text = text.rstrip() + "\n" + b + "\n"
        return text

    # Find end of the "范围" line (newline after it)
    line_end = text.find("\n", idx + 1)
    if line_end < 0:
        line_end = len(text)

    insert_at = line_end
    to_add = []
    for b in bullets:
        if b not in text:
            to_add.append(b)
    if not to_add:
        return text
    return text[:insert_at] + "\n" + "\n".join(to_add) + text[insert_at:]


def _dedupe_lines_keep_order(lines: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        if line in seen:
            continue
        seen.add(line)
        out.append(line)
    return out


def _normalize_t53_freeze_lines_prd(block: str) -> str:
    # Remove known bad/duplicated freeze line variants, then de-dupe.
    lines = block.splitlines()
    lines = [l for l in lines if "传送点/传送点" not in l]
    lines = _dedupe_lines_keep_order(lines)
    return "\n".join(lines) + ("\n" if block.endswith("\n") else "")


def _normalize_t53_overlay(path_text: str) -> str:
    freeze_lines = [
        "- 口径冻结：Core 只识别 `tile_kind = city | facility | event | empty`；当 `tile_kind=facility` 时必须给出 `facility_kind`（荒野/商店/战场/监狱/医院/职业所/传送点等）。",
        "- 口径冻结：`tile_id` 仅要求 map 内唯一；跨地图允许重复。",
        "- 口径冻结：`layout:{x,y}` 必须在 `[0,1]`（归一化坐标、原点左上）；越界视为数据无效，禁止开始（硬失败）。",
        "- 口径冻结：资源路径必须位于 `res://Assets/...` 子树内，扩展名白名单（.png/.webp/.svg）+ 大小上限（1MB）。",
        "- 口径冻结：`action_id` 在同一 tile 内唯一；事件/日志引用使用 `(map_id, tile_id, action_id)` 组合。",
    ]

    lines = path_text.splitlines()

    # Normalize tile set line first.
    for i, line in enumerate(lines):
        if line.strip() == "- Tile 最小集合：`city` / `pass` / `event` / `empty`。":
            lines[i] = "- Tile 最小集合：`city` / `facility` / `event` / `empty`。"

    # Remove all existing freeze lines (including duplicates), then re-insert exactly once.
    filtered: list[str] = []
    for line in lines:
        if line in freeze_lines:
            continue
        filtered.append(line)
    lines = filtered

    # Insert after the tile set line inside "## 范围".
    inserted = False
    for i, line in enumerate(lines):
        if line.strip() == "- Tile 最小集合：`city` / `facility` / `event` / `empty`。":
            lines = lines[: i + 1] + freeze_lines + lines[i + 1 :]
            inserted = True
            break

    # If the tile set line wasn't found, do a best-effort append near "## 范围".
    if not inserted:
        for i, line in enumerate(lines):
            if line.strip() == "## 范围":
                lines = lines[: i + 1] + freeze_lines + lines[i + 1 :]
                inserted = True
                break
    if not inserted:
        lines.extend([""] + freeze_lines)

    return "\n".join(lines) + ("\n" if path_text.endswith("\n") else "")


def _update_prd(prd_text: str) -> str:
    # T53..T60 are sequential tokens in this PRD.
    # We avoid embedding Chinese tokens in the script logic (stdin encoding hazards) by using ASCII task ids.

    def section(start_id: int, end_id: int) -> tuple[int, int]:
        return _find_section(prd_text, f"\nT{start_id}", f"\nT{end_id}")

    # --- T50 ---
    s50, e51 = section(50, 51)
    t50 = prd_text[s50:e51]
    t50 = _ensure_bullets(
        t50,
        bullets=[
            "- 口径冻结：GameStartConfig 的审计快照必须使用“规范化 JSON”（UTF-8、LF、键排序、稳定字段名；不依赖对象枚举顺序），以保证 diff/复盘稳定。",
            "- 口径冻结：所有域事件必须携带 `CorrelationId`/`CausationId`（ADR-0024）；它们仅用于链路追踪，不得影响任何玩法计算与确定性结果。",
            "- 口径冻结：Data 校验失败属于 `data_invalid`，必须审计记录（至少包含 path/sha256/version/reason），并阻止开始。",
            "- 口径冻结：i18n 统一使用 `message_key + params`；params 必须是扁平键值（仅 string/int/decimal/bool），禁止嵌套对象/数组，降低 UI 解析复杂度。",
        ],
    )
    prd_text = prd_text[:s50] + t50 + prd_text[e51:]

    # Normalize legacy global-event naming: T63 uses the already-defined random_event contract.
    prd_text = prd_text.replace("core.sanguo.global_event.triggered", "core.sanguo.random_event.applied")

    # --- T53 ---
    s53, e54 = section(53, 54)
    t53 = prd_text[s53:e54]
    t53 = t53.replace("city / pass / event / empty", "city / facility / event / empty")
    t53 = t53.replace("Tile 最小集合：city / pass / event / empty。", "Tile 最小集合：city / facility / event / empty。")
    t53 = t53.replace("\n  - pass：", "\n  - facility：")
    t53 = t53.replace("pass/empty", "facility/empty")
    t53 = _ensure_bullets(
        t53,
        bullets=[
            "  - 口径冻结：Core 只识别 `tile_kind = city | facility | event | empty`；当 `tile_kind=facility` 时必须给出 `facility_kind`（荒野/商店/战场/监狱/医院/职业所/传送点等）。",
            "  - 口径冻结：`tile_id` 仅要求 map 内唯一；跨地图允许重复。",
            "  - 口径冻结：`layout:{x,y}` 必须在 `[0,1]`（归一化坐标、原点左上）；越界视为数据无效，禁止开始（硬失败）。",
            "  - 口径冻结：任何资源路径（地图预览、action 图标等）必须位于 `res://Assets/...` 子树内，且扩展名白名单（.png/.webp/.svg）+ 大小上限（1MB）。",
            "  - 口径冻结：`action_id` 在同一 tile 内唯一；事件/日志引用使用 `(map_id, tile_id, action_id)` 组合，避免重排导致语义漂移。",
            "  - 口径冻结：资源路径必须做规范化与绕过拦截：拒绝 `..`、拒绝 percent-encoding 绕过（如 `%2e%2e`），并拒绝任何非 `res://`/`user://` scheme（ADR-0019）。",
            "  - 口径冻结：facility action 参数必须强类型且可校验（例如 teleport 只允许 `target_mode=tile_id|random`；mode=tile_id 时必须给出 `target_tile_id`）。",
            "  - 口径冻结：地图/设施/事件/建筑配置必须包含 `schema_version`；不等于当前支持版本则拒绝加载（不做迁移）。",
        ],
    )
    t53 = _normalize_t53_freeze_lines_prd(t53)
    prd_text = prd_text[:s53] + t53 + prd_text[e54:]

    # --- T54 ---
    s54, e55 = _find_section(prd_text, "\nT54", "\nT55")
    t54 = prd_text[s54:e55]
    t54 = _ensure_bullets(
        t54,
        bullets=[
            "- 口径冻结：默认选中“第一张地图 + 第一个角色”，未选地图/未选角色时禁用开始按钮（但默认会自动选中）。",
            "- 口径冻结：启动超时默认 20 秒（可由环境变量覆盖）；超时/失败必须清理已创建的 GameLoop/状态并回滚到配置界面。",
            "- 口径冻结：启动失败的 error_code 枚举固定为：`data_invalid` / `config_invalid` / `runtime_failed` / `timeout` / `security_denied`；同类原因必须复用同一 code，避免 UI/测试分裂。",
            "- 口径冻结：启动失败回滚必须包含地图/角色/人数/资金档/间隔（全部回滚到默认），并重生 random_seed（你已确认）。",
        ],
    )
    prd_text = prd_text[:s54] + t54 + prd_text[e55:]

    # --- T55 ---
    s55, e56 = _find_section(prd_text, "\nT55", "\nT56")
    t55 = prd_text[s55:e56]
    t55 = t55.replace("res://Data/characters.json（只读）", "res://Data/characters.json（只读，UTF-8）")
    # Ensure avatar constraint exists (1MB + Assets subtree).
    t55 = _ensure_bullets(
        t55,
        bullets=[
            "- 口径冻结：角色头像资源路径必须位于 `res://Assets/...`，扩展名白名单（.png/.webp/.svg），大小上限 1MB；越界/非法则禁止开始。",
            "- 口径冻结：角色配置必须包含 `schema_version`；不等于当前支持版本则拒绝加载（不做迁移）。",
        ],
    )
    prd_text = prd_text[:s55] + t55 + prd_text[e56:]

    # --- T58 ---
    s58, e59 = _find_section(prd_text, "\nT58", "\nT59")
    t58 = prd_text[s58:e59]
    t58 = _ensure_bullets(
        t58,
        bullets=[
            "- 口径冻结：建筑“未建造”= 该 tile 的 building 状态列表中不存在该 `building_id`；首次建造直接落 `level=1`，升级递增直到 `max_level`（不使用 `level=0` 作为哨兵值）。",
            "- 口径冻结：buy/toll/settlement/build/upgrade 的 base 值全部来自配置 JSON，禁止缺省（缺字段=数据无效，禁止开始）。",
        ],
    )
    prd_text = prd_text[:s58] + t58 + prd_text[e59:]

    # --- T59 ---
    s59, e60 = _find_section(prd_text, "\nT59", "\nT60")
    t59 = prd_text[s59:e60]
    t59 = t59.replace("pass 与 event", "facility 与 event")
    t59 = t59.replace("pass", "facility") if "pass" in t59 else t59
    t59 = _ensure_bullets(
        t59,
        bullets=[
            "- 口径冻结：无论是否进入战斗场景，结果计算与事件字段必须一致；AI 一律不进入场景但仍发布 started/ended。",
            "- 口径冻结：`core.sanguo.combat.ended` 结果字段至少包含 `result.outcome` / `result.money_delta` / `result.encounter_target` / `result.effective_combat_rating`，用于复盘。",
            "- 口径冻结：relic_id 同局唯一；重复掉落则重抽，耗尽候选则返回 null 并写入审计（不使用“max_id 兜底”）。",
        ],
    )
    prd_text = prd_text[:s59] + t59 + prd_text[e60:]

    # --- T60 ---
    s60, e61 = _find_section(prd_text, "\nT60", "\nT61")
    t60 = prd_text[s60:e61]
    t60 = _ensure_bullets(
        t60,
        bullets=[
            "- 口径冻结：玩家控制角色资金 <=0 时立刻触发失败并结束游戏；AI 出局可延后到 `turn.advanced` 后统一判定“最后存活者胜利”（你已确认）。",
            "- 口径冻结：出局处理必须发布 `core.sanguo.player.eliminated`（审计）并释放资产为无主；释放/买下/夺取导致的归属变化必须发布 `core.sanguo.city.owner.changed`。",
            "- 口径冻结：`sequence` 仅用于审计落盘/复盘稳定排序，不进入域事件 payload（不依赖 OccurredAt 排序）。",
        ],
    )
    prd_text = prd_text[:s60] + t60 + prd_text[e61:]

    return prd_text


def _update_overlay_file(path: Path) -> str:
    text = _read_utf8(path)
    original = text

    # Minimal targeted updates per file.
    if path.name == "08-t53-map-config.md":
        text = text.replace("`city` / `pass` / `event` / `empty`", "`city` / `facility` / `event` / `empty`")
        text = _normalize_t53_overlay(text)

    if path.name == "08-t50-game-start-config.md":
        if "## 口径冻结" not in text:
            text = text.replace(
                "## 非目标",
                "## 口径冻结\n"
                "- GameStartConfig 的审计快照必须使用“规范化 JSON”（UTF-8、LF、键排序、稳定字段名；不依赖对象枚举顺序）。\n"
                "- 所有域事件必须携带 `CorrelationId`/`CausationId`（ADR-0024）；它们仅用于链路追踪，不得影响任何玩法计算与确定性结果。\n"
                "- Data 校验失败必须审计记录（至少 path/sha256/version/reason），并阻止开始。\n"
                "- i18n 统一使用 `message_key + params`；params 必须是扁平键值（仅 string/int/decimal/bool），禁止嵌套对象/数组。\n\n"
                "## 非目标",
            )

    if path.name == "08-t54-new-game-menu.md":
        if "## 口径冻结" not in text:
            text = text.replace(
                "## 非目标\n- 不做设置持久化与跨次启动记忆（后续任务）。",
                "## 非目标\n- 不做设置持久化与跨次启动记忆（后续任务）。\n\n"
                "## 口径冻结\n"
                "- 默认选中“第一张地图 + 第一个角色”，未选地图/未选角色时禁用开始按钮（但默认会自动选中）。\n"
                "- 启动超时默认 20 秒（可由环境变量覆盖）；超时/失败必须清理已创建的 GameLoop/状态并回滚到配置界面。\n"
                "- 启动失败的 error_code 枚举固定为：`data_invalid` / `config_invalid` / `runtime_failed` / `timeout` / `security_denied`。\n"
                "- 启动失败回滚必须包含地图/角色/人数/资金档/间隔（全部回滚到默认），并重生 random_seed。",
            )

    if path.name == "08-t55-characters.md":
        text = text.replace("08-T55 角色（6 角色）", "08-T55 角色（≥8 角色）")
        text = text.replace("# T55：角色（6 角色）", "# T55：角色（≥8 角色）")
        text = text.replace("（6 角色，全局唯一不可重复）", "（≥8 角色，全局唯一不可重复）")
        text = text.replace("且 6 角色可展示", "且 ≥8 角色可展示")
        if "头像资源路径必须位于" not in text:
            text = text.replace(
                "## 非目标\n- 不实现体力/技能池/装备/成长系统。",
                "## 非目标\n- 不实现体力/技能池/装备/成长系统。\n\n"
                "## 口径冻结\n- 角色头像资源路径必须位于 `res://Assets/...`，扩展名白名单（.png/.webp/.svg），大小上限 1MB；越界/非法则禁止开始。",
            )

    if path.name == "08-t58-buildings.md":
        if "未建造" not in text:
            text = text.replace(
                "## 非目标\n- 不引入复杂建筑树/升级链。",
                "## 非目标\n- 不引入复杂建筑树/升级链。\n\n"
                "## 口径冻结\n- 建筑“未建造”= 该 tile 的 building 状态列表中不存在该 `building_id`；首次建造直接落 `level=1`，升级递增直到 `max_level`（不使用 `level=0` 作为哨兵值）。",
            )

    if path.name == "08-t59-combat-pve.md":
        # Normalize to "combat" naming if already.
        text = text.replace("battle", "combat")
        if "relic_id 同局唯一" not in text:
            text = text.replace(
                "## 非目标\n- 不做 PVP。\n- 不做复杂战斗系统与数值成长。",
                "## 非目标\n- 不做 PVP。\n- 不做复杂战斗系统与数值成长。\n\n"
                "## 口径冻结\n- 无论是否进入战斗场景，结果计算与事件字段必须一致；AI 一律不进入场景但仍发布 started/ended。\n"
                "- `core.sanguo.combat.ended` 结果字段至少包含 `result.outcome` / `result.money_delta` / `result.encounter_target` / `result.effective_combat_rating`。\n"
                "- relic_id 同局唯一；重复掉落则重抽，耗尽候选则返回 null 并写入审计（不使用“max_id 兜底”）。",
            )

    if path.name == "08-t60-game-end-and-settlement.md":
        if "## 口径冻结" not in text:
            text = text.replace(
                "## 非目标\n- 不做胜利条件自定义编辑器。",
                "## 非目标\n- 不做胜利条件自定义编辑器。\n\n"
                "## 口径冻结\n"
                "- 玩家控制角色资金 <=0 时立刻触发失败并结束游戏；AI 出局在 `turn.advanced` 后统一检查终局。\n"
                "- 出局处理必须发布 `core.sanguo.player.eliminated`（审计）并释放资产为无主；城市归属变化如需事件级复盘，后续补充 `core.sanguo.city.owner.changed`（Proposed）。\n"
                "- 主日志/审计建议使用单调递增 `sequence` 作为稳定排序键（不依赖 OccurredAt）。",
            )

    return text if text != original else original


def _check_garbling(paths: list[Path]) -> dict:
    # "语义级乱码"：做可执行的最小检查（不做编码转换）：
    # - UTF-8 strict 可解码
    # - 不含 U+FFFD
    # - 不出现连续 "??"（常见的控制台/编码替换痕迹）
    suspicious = []
    for p in paths:
        b = p.read_bytes()
        try:
            t = b.decode("utf-8", errors="strict")
        except UnicodeDecodeError as e:
            suspicious.append(
                {
                    "path": str(p).replace("\\", "/"),
                    "kind": "utf8_decode_error",
                    "detail": str(e),
                }
            )
            continue

        if "\ufffd" in t:
            suspicious.append(
                {
                    "path": str(p).replace("\\", "/"),
                    "kind": "replacement_char",
                    "count": t.count("\ufffd"),
                }
            )

        # Heuristic for "???" runs (common replacement/garbling symptom)
        if re.search(r"\?{3,}", t):
            # Exclude markdown code blocks (still suspicious but less likely)
            suspicious.append(
                {
                    "path": str(p).replace("\\", "/"),
                    "kind": "question_mark_run",
                }
            )
    return {"suspicious": suspicious, "suspicious_count": len(suspicious)}


def main() -> int:
    out_dir = _today_ci_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[UpdateResult] = []
    changed_paths: list[Path] = []

    # 1) Update PRD
    prd_path = Path(".taskmaster") / "docs" / "prd.txt"
    prd_before = _read_utf8(prd_path)
    prd_after = _update_prd(prd_before)
    if prd_after != prd_before:
        _write_utf8(prd_path, prd_after)
        changed_paths.append(prd_path)
    results.append(
        UpdateResult(
            path=str(prd_path).replace("\\", "/"),
            changed=prd_after != prd_before,
            bytes_before=len(prd_before.encode("utf-8")),
            bytes_after=len(prd_after.encode("utf-8")),
        )
    )

    # 2) Update overlays (targeted files only)
    overlay_paths = [
        Path("docs/architecture/overlays/PRD-SANGUO-T2/08/08-t50-game-start-config.md"),
        Path("docs/architecture/overlays/PRD-SANGUO-T2/08/08-t53-map-config.md"),
        Path("docs/architecture/overlays/PRD-SANGUO-T2/08/08-t54-new-game-menu.md"),
        Path("docs/architecture/overlays/PRD-SANGUO-T2/08/08-t55-characters.md"),
        Path("docs/architecture/overlays/PRD-SANGUO-T2/08/08-t58-buildings.md"),
        Path("docs/architecture/overlays/PRD-SANGUO-T2/08/08-t59-combat-pve.md"),
        Path("docs/architecture/overlays/PRD-SANGUO-T2/08/08-t60-game-end-and-settlement.md"),
    ]
    for p in overlay_paths:
        before = _read_utf8(p)
        after = _update_overlay_file(p)
        if after != before:
            _write_utf8(p, after)
            changed_paths.append(p)
        results.append(
            UpdateResult(
                path=str(p).replace("\\", "/"),
                changed=after != before,
                bytes_before=len(before.encode("utf-8")),
                bytes_after=len(after.encode("utf-8")),
            )
        )

    # 3) Integrity check (PRD + tasks triplet + overlays)
    to_check = [
        prd_path,
        Path(".taskmaster/tasks/tasks.json"),
        Path(".taskmaster/tasks/tasks_back.json"),
        Path(".taskmaster/tasks/tasks_gameplay.json"),
    ] + overlay_paths
    check = _check_garbling(to_check)

    report = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "operation": "update_prd_t2_alignment_freeze",
        "changed_paths": [str(p).replace("\\", "/") for p in changed_paths],
        "results": [r.__dict__ for r in results],
        "integrity_check": check,
    }
    (out_dir / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Hard fail if any suspicious encoding problems.
    if check["suspicious_count"] > 0:
        print(f"PRD_ALIGNMENT status=fail suspicious={check['suspicious_count']} out={out_dir}")
        return 2
    print(f"PRD_ALIGNMENT status=ok changed={len(changed_paths)} out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
