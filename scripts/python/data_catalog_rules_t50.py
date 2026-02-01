"""
Data catalog rules for the T50-T65 minimal data set.

Composes validations from:
- scripts/python/data_catalog_rules.py (common)
- scripts/python/data_catalog_rules_maps.py (maps)

Keep this module <= 400 lines.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import data_catalog_rules as core
import data_catalog_numeric_rules as numeric
import data_catalog_rules_maps as maps


def _read_and_check(path: Path, findings: list[core.Finding]) -> Any | None:
    try:
        obj = core._read_json(path)
    except Exception as e:
        findings.append(core.Finding("fail", "DATA_JSON_PARSE_ERROR", path.as_posix(), f"invalid json: {e}"))
        return None
    core._validate_no_meta(obj, path, findings)
    core._validate_header(obj, path, findings)
    if not isinstance(obj, dict):
        findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", path.as_posix(), "top-level must be an object."))
        return None
    return obj


def _validate_id_list(
    path: Path, array_key: str, id_key: str, findings: list[core.Finding]
) -> list[dict[str, Any]]:
    obj = _read_and_check(path, findings)
    if obj is None:
        return []
    arr = obj.get(array_key)
    if not isinstance(arr, list) or not arr:
        findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", path.as_posix(), f'"{array_key}" must be a non-empty array.'))
        return []
    seen: set[str] = set()
    for idx, item in enumerate(arr):
        loc = f"{path.as_posix()}:{array_key}[{idx}]"
        if not isinstance(item, dict):
            findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", loc, "item must be an object."))
            continue
        iid = core._check_id(item.get(id_key), f"{loc}.{id_key}", findings)
        if iid:
            if iid in seen:
                findings.append(core.Finding("fail", "DATA_ID_DUPLICATE", f"{loc}.{id_key}", f"duplicate {id_key}: {iid}"))
            seen.add(iid)
    return arr


def validate_buildings(path: Path, i18n: dict[str, str], findings: list[core.Finding]) -> set[str]:
    arr = _validate_id_list(path, "buildings", "buildingId", findings)
    ids: set[str] = set()
    for idx, b in enumerate(arr):
        if not isinstance(b, dict):
            continue
        bid = b.get("buildingId")
        if isinstance(bid, str):
            ids.add(bid)
        loc = f"{path.as_posix()}:buildings[{idx}]"
        core._validate_i18n_key(b.get("nameKey"), f"{loc}.nameKey", i18n, findings, required=True)
        core._validate_i18n_key(b.get("descriptionKey"), f"{loc}.descriptionKey", i18n, findings, required=True)
        max_level = b.get("maxLevel")
        if not isinstance(max_level, int) or max_level < 1:
            findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.maxLevel", "maxLevel must be int >= 1."))
        for k in ("buildCostBase", "upgradeCostBase", "settlementIncomeBase"):
            v = b.get(k)
            if not isinstance(v, int) or v < 0:
                findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.{k}", f"{k} must be int >= 0."))
        core._validate_economy_steps(b.get("economyStepDeltas"), f"{loc}.economyStepDeltas", findings)
    if len(ids) < 5:
        findings.append(core.Finding("fail", "DATA_INVARIANT_VIOLATION", path.as_posix(), "buildings must be >= 5."))
    return ids


def validate_regions(path: Path, i18n: dict[str, str], findings: list[core.Finding]) -> set[str]:
    arr = _validate_id_list(path, "regions", "regionId", findings)
    ids: set[str] = set()
    for idx, r in enumerate(arr):
        if not isinstance(r, dict):
            continue
        rid = r.get("regionId")
        if isinstance(rid, str):
            ids.add(rid)
        loc = f"{path.as_posix()}:regions[{idx}]"
        core._validate_i18n_key(r.get("nameKey"), f"{loc}.nameKey", i18n, findings, required=True)
        core._validate_i18n_key(r.get("descriptionKey"), f"{loc}.descriptionKey", i18n, findings, required=True)
        if r.get("effectKind") != "economyStepDelta":
            findings.append(core.Finding("fail", "EFFECT_KIND_NOT_ALLOWED", f"{loc}.effectKind", "region effectKind must be economyStepDelta."))
        core._validate_economy_steps(r.get("economyStepDeltas"), f"{loc}.economyStepDeltas", findings)
    return ids


def validate_facilities(
    repo_root: Path, path: Path, i18n: dict[str, str], findings: list[core.Finding]
) -> tuple[set[str], dict[str, set[str]]]:
    arr = _validate_id_list(path, "facilities", "facilityId", findings)
    ids: set[str] = set()
    facility_action_ids_by_facility: dict[str, set[str]] = {}
    for index, facility in enumerate(arr):
        if not isinstance(facility, dict):
            continue
        facility_id = facility.get("facilityId")
        if isinstance(facility_id, str):
            ids.add(facility_id)
        loc = f"{path.as_posix()}:facilities[{index}]"
        if not isinstance(facility.get("facilityKind"), str) or not facility.get("facilityKind"):
            findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.facilityKind", "facilityKind must be non-empty string."))
        core._validate_i18n_key(facility.get("nameKey"), f"{loc}.nameKey", i18n, findings, required=True)
        core._validate_i18n_key(facility.get("descriptionKey"), f"{loc}.descriptionKey", i18n, findings, required=True)
        actions = facility.get("actions")
        if not isinstance(actions, list):
            findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.actions", "actions must be array."))
            if isinstance(facility_id, str):
                facility_action_ids_by_facility[facility_id] = set()
            continue
        if not actions:
            if isinstance(facility_id, str):
                facility_action_ids_by_facility[facility_id] = set()
            continue
        action_ids: set[str] = set()
        for action_index, action in enumerate(actions):
            aloc = f"{loc}.actions[{action_index}]"
            if not isinstance(action, dict):
                findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", aloc, "action must be object."))
                continue
            action_id = core._check_id(action.get("actionId"), f"{aloc}.actionId", findings)
            if action_id:
                if action_id in action_ids:
                    findings.append(core.Finding("fail", "DATA_ID_DUPLICATE", f"{aloc}.actionId", f"duplicate actionId: {action_id}"))
                action_ids.add(action_id)
            core.validate_res_asset_path(repo_root, action.get("iconResPath"), f"{aloc}.iconResPath", findings)
            action_kind = action.get("actionKind")
            effect_kind = action.get("effectKind")
            if effect_kind == "teleport":
                params = action.get("params")
                if not isinstance(params, dict):
                    findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{aloc}.params", "teleport params must be object."))
                else:
                    mode = params.get("targetMode")
                    if mode not in ("random", "tileId"):
                        findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{aloc}.params.targetMode", 'targetMode must be "random" or "tileId".'))
                    if mode == "tileId" and not isinstance(params.get("tileId"), str):
                        findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{aloc}.params.tileId", "tileId must be string when targetMode=tileId."))
                if action_kind is not None:
                    findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{aloc}.actionKind", "teleport action must not define actionKind."))
            else:
                if effect_kind is not None:
                    findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{aloc}.effectKind", "only teleport effectKind is allowed for facilities."))
                if not isinstance(action_kind, str) or not action_kind:
                    findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{aloc}.actionKind", "actionKind must be non-empty string."))
                else:
                    if action_kind not in ("openShop", "startCombat", "hospital", "jail", "job", "wilderness"):
                        findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{aloc}.actionKind", "actionKind not allowed."))
        if isinstance(facility_id, str):
            facility_action_ids_by_facility[facility_id] = action_ids
    return ids, facility_action_ids_by_facility


def validate_random_events(path: Path, i18n: dict[str, str], findings: list[core.Finding]) -> set[str]:
    obj = _read_and_check(path, findings)
    if obj is None:
        return set()
    pools = obj.get("eventPools")
    if not isinstance(pools, list) or not pools:
        findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", path.as_posix(), '"eventPools" must be non-empty array.'))
        return set()
    pool_ids: set[str] = set()
    global_pool_event_ids: set[str] = set()
    pool_event_ids_by_pool: dict[str, list[str]] = {}
    for index, pool in enumerate(pools):
        loc = f"{path.as_posix()}:eventPools[{index}]"
        if not isinstance(pool, dict):
            findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", loc, "eventPool must be object."))
            continue
        pool_id = core._check_id(pool.get("poolId"), f"{loc}.poolId", findings)
        if pool_id:
            if pool_id in pool_ids:
                findings.append(core.Finding("fail", "DATA_ID_DUPLICATE", f"{loc}.poolId", f"duplicate poolId: {pool_id}"))
            pool_ids.add(pool_id)
        core._validate_i18n_key(pool.get("nameKey"), f"{loc}.nameKey", i18n, findings, required=True)
        event_ids = pool.get("eventIds")
        if not isinstance(event_ids, list) or not all(isinstance(x, str) for x in event_ids):
            findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.eventIds", "eventIds must be array of strings."))
        else:
            normalized = [event_id for event_id in event_ids if isinstance(event_id, str) and event_id]
            if not normalized:
                findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.eventIds", "eventIds must be non-empty."))
            else:
                seen_pool_events: set[str] = set()
                for event_id in normalized:
                    if event_id in seen_pool_events:
                        findings.append(core.Finding("fail", "DATA_ID_DUPLICATE", f"{loc}.eventIds", f"duplicate eventId in pool: {event_id}"))
                    seen_pool_events.add(event_id)
            if isinstance(pool_id, str):
                pool_event_ids_by_pool[pool_id] = normalized
            if pool_id == "global":
                global_pool_event_ids.update(normalized)
    events = obj.get("events")
    if not isinstance(events, list) or not events:
        findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", path.as_posix(), '"events" must be non-empty array.'))
        return pool_ids
    seen_events: set[str] = set()
    event_effect_kinds: dict[str, str] = {}
    for index, event in enumerate(events):
        loc = f"{path.as_posix()}:events[{index}]"
        if not isinstance(event, dict):
            findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", loc, "event must be object."))
            continue
        event_id = core._check_id(event.get("eventId"), f"{loc}.eventId", findings)
        if event_id:
            if event_id in seen_events:
                findings.append(core.Finding("fail", "DATA_ID_DUPLICATE", f"{loc}.eventId", f"duplicate eventId: {event_id}"))
            seen_events.add(event_id)
        core._validate_i18n_key(event.get("nameKey"), f"{loc}.nameKey", i18n, findings, required=True)
        core._validate_i18n_key(event.get("descriptionKey"), f"{loc}.descriptionKey", i18n, findings, required=True)
        if not isinstance(event.get("uniqueOnce"), bool):
            findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.uniqueOnce", "uniqueOnce must be bool."))
        cooldown = event.get("cooldownRounds")
        if not isinstance(cooldown, int) or cooldown < 0 or cooldown > 1000:
            findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.cooldownRounds", "cooldownRounds must be int in [0,1000]."))
        effect_kind = event.get("effectKind")
        if isinstance(event_id, str) and isinstance(effect_kind, str):
            event_effect_kinds[event_id] = effect_kind
        if effect_kind == "moneyDelta":
            money_delta = event.get("moneyDelta")
            if not isinstance(money_delta, int):
                findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.moneyDelta", "moneyDelta must be int."))
            elif money_delta < -10000 or money_delta > 10000:
                findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.moneyDelta", "moneyDelta must be in [-10000,10000]."))
        elif effect_kind == "economyStepDelta":
            step_delta = event.get("stepDelta")
            if not isinstance(step_delta, int):
                findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.stepDelta", "stepDelta must be int."))
            elif step_delta < -6 or step_delta > 6:
                findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.stepDelta", "stepDelta must be in [-6,6]."))
        elif effect_kind == "startCombat":
            enc_id = event.get("encounterId")
            if not isinstance(enc_id, str) or not enc_id.strip():
                findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.encounterId", "encounterId must be non-empty string."))
            enc_target = event.get("encounterTarget")
            if not isinstance(enc_target, int) or enc_target < 0 or enc_target > 1000:
                findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.encounterTarget", "encounterTarget must be int in [0,1000]."))
        else:
            findings.append(core.Finding("fail", "EFFECT_KIND_NOT_ALLOWED", f"{loc}.effectKind", "event effectKind not supported by minimal gate."))

    for pool_id, pool_event_ids in pool_event_ids_by_pool.items():
        for event_id in pool_event_ids:
            if event_id not in seen_events:
                findings.append(
                    core.Finding(
                        "fail",
                        "DATA_ID_NOT_FOUND",
                        f"{path.as_posix()}:eventPools[poolId={pool_id}].eventIds",
                        f"eventId not found in events: {event_id}",
                    )
                )

    for eid in sorted(global_pool_event_ids, key=str):
        if event_effect_kinds.get(eid) == "startCombat":
            findings.append(
                core.Finding(
                    "fail",
                    "DATA_INVARIANT_VIOLATION",
                    f"{path.as_posix()}:eventPools[poolId=global].eventIds",
                    "startCombat is only allowed for tile random events (poolId=default).",
                )
            )
    total_events = len(event_effect_kinds)
    money_events = sum(1 for v in event_effect_kinds.values() if v == "moneyDelta")
    economy_events = sum(1 for v in event_effect_kinds.values() if v == "economyStepDelta")
    combat_events = sum(1 for v in event_effect_kinds.values() if v == "startCombat")
    if total_events < 9:
        findings.append(core.Finding("fail", "DATA_INVARIANT_VIOLATION", path.as_posix(), "events must be >= 9."))
    if money_events < 3:
        findings.append(core.Finding("fail", "DATA_INVARIANT_VIOLATION", path.as_posix(), "events must include >= 3 moneyDelta."))
    if economy_events < 3:
        findings.append(core.Finding("fail", "DATA_INVARIANT_VIOLATION", path.as_posix(), "events must include >= 3 economyStepDelta."))
    if combat_events < 2:
        findings.append(core.Finding("fail", "DATA_INVARIANT_VIOLATION", path.as_posix(), "events must include >= 2 startCombat."))
    return pool_ids


def validate_cards_or_relics(path: Path, array_key: str, id_key: str, i18n: dict[str, str], findings: list[core.Finding]) -> set[str]:
    arr = _validate_id_list(path, array_key, id_key, findings)
    ids: set[str] = set()
    effect_counts: dict[str, int] = {"economyStepDelta": 0, "moneyDelta": 0, "transferOwnership": 0}
    for idx, c in enumerate(arr):
        if not isinstance(c, dict):
            continue
        cid = c.get(id_key)
        if isinstance(cid, str):
            ids.add(cid)
        loc = f"{path.as_posix()}:{array_key}[{idx}]"
        core._validate_i18n_key(c.get("nameKey"), f"{loc}.nameKey", i18n, findings, required=True)
        core._validate_i18n_key(c.get("descriptionKey"), f"{loc}.descriptionKey", i18n, findings, required=True)
        ek = c.get("effectKind")
        if array_key == "cards" and ek == "moneyDelta":
            findings.append(core.Finding("fail", "EFFECT_KIND_NOT_ALLOWED", f"{loc}.effectKind", "cards do not support moneyDelta."))
            continue
        if ek == "economyStepDelta":
            step_delta = c.get("stepDelta")
            if not isinstance(step_delta, int):
                findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.stepDelta", "stepDelta must be int."))
            elif step_delta < -6 or step_delta > 6:
                findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.stepDelta", "stepDelta must be in [-6,6]."))
            elif array_key == "relics" and step_delta == 0:
                findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.stepDelta", "relic stepDelta must be non-zero."))
            effect_counts["economyStepDelta"] += 1
        elif ek == "moneyDelta":
            money_delta = c.get("moneyDelta")
            if not isinstance(money_delta, int):
                findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.moneyDelta", "moneyDelta must be int."))
            elif money_delta < -10000 or money_delta > 10000:
                findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.moneyDelta", "moneyDelta must be in [-10000,10000]."))
            elif array_key == "relics" and money_delta <= 0:
                findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.moneyDelta", "relic moneyDelta must be > 0."))
            effect_counts["moneyDelta"] += 1
        elif array_key == "cards" and ek == "transferOwnership":
            step_delta = c.get("stepDelta")
            if not isinstance(step_delta, int):
                findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.stepDelta", "stepDelta must be int."))
            elif step_delta < -6 or step_delta > 6:
                findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.stepDelta", "stepDelta must be in [-6,6]."))
            effect_counts["transferOwnership"] += 1
        else:
            findings.append(core.Finding("fail", "EFFECT_KIND_NOT_ALLOWED", f"{loc}.effectKind", f"{array_key} effectKind not supported by minimal gate."))
        if array_key == "cards":
            duration = c.get("durationRounds")
            if not isinstance(duration, int) or duration < 1 or duration > 1000:
                findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.durationRounds", "durationRounds must be int in [1,1000]."))
    if array_key == "cards":
        if len(ids) < 6:
            findings.append(core.Finding("fail", "DATA_INVARIANT_VIOLATION", path.as_posix(), "cards must be >= 6."))
        if effect_counts["economyStepDelta"] < 4:
            findings.append(core.Finding("fail", "DATA_INVARIANT_VIOLATION", path.as_posix(), "cards must include >= 4 economyStepDelta."))
        if effect_counts["transferOwnership"] < 1:
            findings.append(core.Finding("fail", "DATA_INVARIANT_VIOLATION", path.as_posix(), "cards must include >= 1 transferOwnership."))
    if array_key == "relics":
        if len(ids) < 4:
            findings.append(core.Finding("fail", "DATA_INVARIANT_VIOLATION", path.as_posix(), "relics must be >= 4."))
        if effect_counts["moneyDelta"] < 2:
            findings.append(core.Finding("fail", "DATA_INVARIANT_VIOLATION", path.as_posix(), "relics must include >= 2 moneyDelta."))
        if effect_counts["economyStepDelta"] < 2:
            findings.append(core.Finding("fail", "DATA_INVARIANT_VIOLATION", path.as_posix(), "relics must include >= 2 economyStepDelta."))
    return ids


def collect_findings(repo_root: Path) -> list[core.Finding]:
    data_dir = repo_root / "Data"
    if not data_dir.exists():
        return [core.Finding("fail", "DATA_DIR_MISSING", "Data/", "Data directory missing.")]

    findings: list[core.Finding] = []
    required = [
        Path("Data/characters.json"),
        Path("Data/i18n/zh_cn.json"),
        Path("Data/i18n/en_us.json"),
        Path("Data/maps/_index.json"),
        Path("Data/facilities.json"),
        Path("Data/random_events.json"),
        Path("Data/action_cards.json"),
        Path("Data/buildings.json"),
        Path("Data/relics.json"),
        Path("Data/regions.json"),
    ]
    for rel in required:
        abs_path = repo_root / rel
        if not abs_path.exists():
            findings.append(core.Finding("fail", "DATA_MISSING_FILE", rel.as_posix(), "required file missing."))
        elif not core.is_tracked(repo_root, rel):
            findings.append(core.Finding("fail", "DATA_NOT_TRACKED", rel.as_posix(), "required file must be tracked by git."))

    i18n_zh: dict[str, str] = {}
    if (repo_root / "Data/i18n/zh_cn.json").exists():
        i18n_zh = core.validate_i18n_file(repo_root / "Data/i18n/zh_cn.json", findings, expected_locale="zh-CN")
    i18n_en: dict[str, str] = {}
    if (repo_root / "Data/i18n/en_us.json").exists():
        i18n_en = core.validate_i18n_file(repo_root / "Data/i18n/en_us.json", findings, expected_locale="en-US")
    i18n = {k: v for k, v in i18n_zh.items() if k in i18n_en}
    if (repo_root / "Data/characters.json").exists():
        core.validate_characters(repo_root, repo_root / "Data/characters.json", i18n, findings)

    building_ids = validate_buildings(repo_root / "Data/buildings.json", i18n, findings) if (repo_root / "Data/buildings.json").exists() else set()
    region_ids = validate_regions(repo_root / "Data/regions.json", i18n, findings) if (repo_root / "Data/regions.json").exists() else set()
    if (repo_root / "Data/facilities.json").exists():
        facility_ids, facility_action_ids_by_facility = validate_facilities(
            repo_root, repo_root / "Data/facilities.json", i18n, findings
        )
    else:
        facility_ids = set()
        facility_action_ids_by_facility = {}

    event_pool_ids: set[str] = set()
    if (repo_root / "Data/random_events.json").exists():
        event_pool_ids = validate_random_events(repo_root / "Data/random_events.json", i18n, findings)

    if (repo_root / "Data/action_cards.json").exists():
        validate_cards_or_relics(repo_root / "Data/action_cards.json", "cards", "cardId", i18n, findings)
    if (repo_root / "Data/relics.json").exists():
        validate_cards_or_relics(repo_root / "Data/relics.json", "relics", "relicId", i18n, findings)

    if (repo_root / "Data/maps/_index.json").exists():
        maps.validate_maps_index(
            repo_root,
            repo_root / "Data/maps/_index.json",
            i18n=i18n,
            building_ids=building_ids,
            facility_ids=facility_ids,
            facility_action_ids_by_facility=facility_action_ids_by_facility,
            region_ids=region_ids,
            event_pool_ids=event_pool_ids,
            findings=findings,
        )

    core.validate_effect_kind_whitelist(data_dir, findings)
    numeric.validate_probability_and_weight(data_dir, findings)
    return findings

