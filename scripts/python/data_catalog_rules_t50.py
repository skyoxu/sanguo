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
        core._validate_i18n_key(b.get("nameKey"), f"{loc}.nameKey", i18n, findings, required=False)
        core._validate_i18n_key(b.get("descriptionKey"), f"{loc}.descriptionKey", i18n, findings, required=False)
        max_level = b.get("maxLevel")
        if not isinstance(max_level, int) or max_level < 1:
            findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.maxLevel", "maxLevel must be int >= 1."))
        for k in ("buildCostBase", "upgradeCostBase", "settlementIncomeBase"):
            v = b.get(k)
            if not isinstance(v, int) or v < 0:
                findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.{k}", f"{k} must be int >= 0."))
        core._validate_economy_steps(b.get("economyStepDeltas"), f"{loc}.economyStepDeltas", findings)
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
        core._validate_i18n_key(r.get("nameKey"), f"{loc}.nameKey", i18n, findings, required=False)
        core._validate_i18n_key(r.get("descriptionKey"), f"{loc}.descriptionKey", i18n, findings, required=False)
        if r.get("effectKind") != "economyStepDelta":
            findings.append(core.Finding("fail", "EFFECT_KIND_NOT_ALLOWED", f"{loc}.effectKind", "region effectKind must be economyStepDelta."))
        core._validate_economy_steps(r.get("economyStepDeltas"), f"{loc}.economyStepDeltas", findings)
    return ids


def validate_facilities(repo_root: Path, path: Path, i18n: dict[str, str], findings: list[core.Finding]) -> set[str]:
    arr = _validate_id_list(path, "facilities", "facilityId", findings)
    ids: set[str] = set()
    for idx, f in enumerate(arr):
        if not isinstance(f, dict):
            continue
        fid = f.get("facilityId")
        if isinstance(fid, str):
            ids.add(fid)
        loc = f"{path.as_posix()}:facilities[{idx}]"
        if not isinstance(f.get("facilityKind"), str) or not f.get("facilityKind"):
            findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.facilityKind", "facilityKind must be non-empty string."))
        core._validate_i18n_key(f.get("nameKey"), f"{loc}.nameKey", i18n, findings, required=False)
        core._validate_i18n_key(f.get("descriptionKey"), f"{loc}.descriptionKey", i18n, findings, required=False)
        actions = f.get("actions")
        if not isinstance(actions, list):
            findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.actions", "actions must be array."))
            continue
        action_ids: set[str] = set()
        for j, a in enumerate(actions):
            aloc = f"{loc}.actions[{j}]"
            if not isinstance(a, dict):
                findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", aloc, "action must be object."))
                continue
            aid = core._check_id(a.get("actionId"), f"{aloc}.actionId", findings)
            if aid:
                if aid in action_ids:
                    findings.append(core.Finding("fail", "DATA_ID_DUPLICATE", f"{aloc}.actionId", f"duplicate actionId: {aid}"))
                action_ids.add(aid)
            core.validate_res_asset_path(repo_root, a.get("iconResPath"), f"{aloc}.iconResPath", findings)
            if a.get("effectKind") == "teleport":
                params = a.get("params")
                if not isinstance(params, dict):
                    findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{aloc}.params", "teleport params must be object."))
                else:
                    mode = params.get("targetMode")
                    if mode not in ("random", "tileId"):
                        findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{aloc}.params.targetMode", 'targetMode must be "random" or "tileId".'))
                    if mode == "tileId" and not isinstance(params.get("tileId"), str):
                        findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{aloc}.params.tileId", "tileId must be string when targetMode=tileId."))
    return ids


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
    for idx, p in enumerate(pools):
        loc = f"{path.as_posix()}:eventPools[{idx}]"
        if not isinstance(p, dict):
            findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", loc, "eventPool must be object."))
            continue
        pid = core._check_id(p.get("poolId"), f"{loc}.poolId", findings)
        if pid:
            if pid in pool_ids:
                findings.append(core.Finding("fail", "DATA_ID_DUPLICATE", f"{loc}.poolId", f"duplicate poolId: {pid}"))
            pool_ids.add(pid)
        ids = p.get("eventIds")
        if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
            findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.eventIds", "eventIds must be array of strings."))
        else:
            if pid == "global":
                global_pool_event_ids.update(x for x in ids if isinstance(x, str) and x)
    events = obj.get("events")
    if not isinstance(events, list) or not events:
        findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", path.as_posix(), '"events" must be non-empty array.'))
        return pool_ids
    seen_events: set[str] = set()
    event_effect_kinds: dict[str, str] = {}
    for idx, e in enumerate(events):
        loc = f"{path.as_posix()}:events[{idx}]"
        if not isinstance(e, dict):
            findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", loc, "event must be object."))
            continue
        eid = core._check_id(e.get("eventId"), f"{loc}.eventId", findings)
        if eid:
            if eid in seen_events:
                findings.append(core.Finding("fail", "DATA_ID_DUPLICATE", f"{loc}.eventId", f"duplicate eventId: {eid}"))
            seen_events.add(eid)
        core._validate_i18n_key(e.get("nameKey"), f"{loc}.nameKey", i18n, findings, required=False)
        core._validate_i18n_key(e.get("descriptionKey"), f"{loc}.descriptionKey", i18n, findings, required=False)
        if not isinstance(e.get("uniqueOnce"), bool):
            findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.uniqueOnce", "uniqueOnce must be bool."))
        cooldown = e.get("cooldownRounds")
        if not isinstance(cooldown, int) or cooldown < 0:
            findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.cooldownRounds", "cooldownRounds must be int >= 0."))
        ek = e.get("effectKind")
        if isinstance(eid, str) and isinstance(ek, str):
            event_effect_kinds[eid] = ek
        if ek == "moneyDelta":
            if not isinstance(e.get("moneyDelta"), int):
                findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.moneyDelta", "moneyDelta must be int."))
        elif ek == "economyStepDelta":
            if not isinstance(e.get("stepDelta"), int):
                findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.stepDelta", "stepDelta must be int."))
        elif ek == "startCombat":
            enc_id = e.get("encounterId")
            if not isinstance(enc_id, str) or not enc_id.strip():
                findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.encounterId", "encounterId must be non-empty string."))
            enc_target = e.get("encounterTarget")
            if not isinstance(enc_target, int) or enc_target < 0 or enc_target > 1000:
                findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.encounterTarget", "encounterTarget must be int in [0,1000]."))
        else:
            findings.append(core.Finding("fail", "EFFECT_KIND_NOT_ALLOWED", f"{loc}.effectKind", "event effectKind not supported by minimal gate."))

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
    return pool_ids


def validate_cards_or_relics(path: Path, array_key: str, id_key: str, i18n: dict[str, str], findings: list[core.Finding]) -> set[str]:
    arr = _validate_id_list(path, array_key, id_key, findings)
    ids: set[str] = set()
    for idx, c in enumerate(arr):
        if not isinstance(c, dict):
            continue
        cid = c.get(id_key)
        if isinstance(cid, str):
            ids.add(cid)
        loc = f"{path.as_posix()}:{array_key}[{idx}]"
        core._validate_i18n_key(c.get("nameKey"), f"{loc}.nameKey", i18n, findings, required=False)
        core._validate_i18n_key(c.get("descriptionKey"), f"{loc}.descriptionKey", i18n, findings, required=False)
        ek = c.get("effectKind")
        if ek == "economyStepDelta":
            if not isinstance(c.get("stepDelta"), int):
                findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.stepDelta", "stepDelta must be int."))
        elif ek == "moneyDelta":
            if not isinstance(c.get("moneyDelta"), int):
                findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.moneyDelta", "moneyDelta must be int."))
        elif array_key == "cards" and ek == "transferOwnership":
            if not isinstance(c.get("stepDelta"), int):
                findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.stepDelta", "stepDelta must be int."))
        else:
            findings.append(core.Finding("fail", "EFFECT_KIND_NOT_ALLOWED", f"{loc}.effectKind", f"{array_key} effectKind not supported by minimal gate."))
        if array_key == "cards":
            duration = c.get("durationRounds")
            if not isinstance(duration, int) or duration < 1 or duration > 1000:
                findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.durationRounds", "durationRounds must be int in [1,1000]."))
    return ids


def collect_findings(repo_root: Path) -> list[core.Finding]:
    data_dir = repo_root / "Data"
    if not data_dir.exists():
        return [core.Finding("fail", "DATA_DIR_MISSING", "Data/", "Data directory missing.")]

    findings: list[core.Finding] = []
    required = [
        Path("Data/characters.json"),
        Path("Data/i18n/zh_cn.json"),
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

    i18n: dict[str, str] = {}
    if (repo_root / required[1]).exists():
        i18n = core.validate_i18n_file(repo_root / required[1], findings)
    if (repo_root / required[0]).exists():
        core.validate_characters(repo_root, repo_root / required[0], i18n, findings)

    building_ids = validate_buildings(repo_root / "Data/buildings.json", i18n, findings) if (repo_root / "Data/buildings.json").exists() else set()
    region_ids = validate_regions(repo_root / "Data/regions.json", i18n, findings) if (repo_root / "Data/regions.json").exists() else set()
    facility_ids = validate_facilities(repo_root, repo_root / "Data/facilities.json", i18n, findings) if (repo_root / "Data/facilities.json").exists() else set()

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
            region_ids=region_ids,
            event_pool_ids=event_pool_ids,
            findings=findings,
        )

    core.validate_effect_kind_whitelist(data_dir, findings)
    return findings

