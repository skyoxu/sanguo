"""
Map-related validations for the T50-T65 minimal data set.

Keep this module <= 400 lines.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import data_catalog_rules as core


def _validate_map_file(
    repo_root: Path,
    path: Path,
    *,
    building_ids: set[str],
    facility_ids: set[str],
    facility_action_ids_by_facility: dict[str, set[str]],
    region_ids: set[str],
    event_pool_ids: set[str],
    i18n: dict[str, str],
    expected_map_id: str | None,
    findings: list[core.Finding],
) -> None:
    try:
        obj = core._read_json(path)
    except Exception as e:
        findings.append(core.Finding("fail", "DATA_JSON_PARSE_ERROR", path.as_posix(), f"invalid json: {e}"))
        return
    core._validate_no_meta(obj, path, findings)
    core._validate_header(obj, path, findings)
    if not isinstance(obj, dict):
        findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", path.as_posix(), "top-level must be an object."))
        return
    map_id_value = core._check_id(obj.get("mapId"), f"{path.as_posix()}:mapId", findings)
    if expected_map_id and map_id_value and map_id_value != expected_map_id:
        findings.append(
            core.Finding(
                "fail",
                "DATA_ID_MISMATCH",
                f"{path.as_posix()}:mapId",
                f"mapId {map_id_value!r} does not match index mapId {expected_map_id!r}.",
            )
        )
    track = obj.get("track")
    if not isinstance(track, dict):
        findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{path.as_posix()}:track", "track must be object."))
        return
    length = core._get_int(track, "length")
    start_tile_id = track.get("startTileId") if isinstance(track.get("startTileId"), str) else ""
    if length is None or length < 1:
        findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{path.as_posix()}:track.length", "track.length must be int >= 1."))
        return
    tiles = obj.get("tiles")
    if not isinstance(tiles, list) or not tiles:
        findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{path.as_posix()}:tiles", "tiles must be non-empty array."))
        return
    if len(tiles) != length:
        findings.append(core.Finding("fail", "DATA_INVARIANT_VIOLATION", f"{path.as_posix()}:tiles", f"tiles length ({len(tiles)}) must equal track.length ({length})."))
    seen_tiles: set[str] = set()
    for idx, t in enumerate(tiles):
        loc = f"{path.as_posix()}:tiles[{idx}]"
        if not isinstance(t, dict):
            findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", loc, "tile must be object."))
            continue
        tid = core._check_id(t.get("tileId"), f"{loc}.tileId", findings)
        if tid:
            if tid in seen_tiles:
                findings.append(core.Finding("fail", "DATA_ID_DUPLICATE", f"{loc}.tileId", f"duplicate tileId: {tid}"))
            seen_tiles.add(tid)
        if t.get("tileKind") not in core.TILE_KINDS:
            findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.tileKind", f"tileKind must be one of {sorted(core.TILE_KINDS)}."))
        name_key = t.get("nameKey")
        if not isinstance(name_key, str) or not name_key:
            findings.append(core.Finding("fail", "I18N_KEY_MISSING", f"{loc}.nameKey", "tile must include nameKey."))
        else:
            core._validate_i18n_key(name_key, f"{loc}.nameKey", i18n, findings, required=True)
        layout = t.get("layout")
        if not isinstance(layout, dict):
            findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.layout", "layout must be object."))
        else:
            x, y = layout.get("x"), layout.get("y")
            if not isinstance(x, (int, float)) or not (0.0 <= float(x) <= 1.0):
                findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.layout.x", "layout.x must be number in [0,1]."))
            if not isinstance(y, (int, float)) or not (0.0 <= float(y) <= 1.0):
                findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.layout.y", "layout.y must be number in [0,1]."))
        actions = t.get("actions")
        if not isinstance(actions, list):
            findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.actions", "actions must be array."))
            actions = []
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
        kind = t.get("tileKind")
        if kind == "city":
            region_id = t.get("regionId")
            if not isinstance(region_id, str) or region_id not in region_ids:
                findings.append(core.Finding("fail", "DATA_ID_NOT_FOUND", f"{loc}.regionId", f"regionId not found: {region_id!r}"))
            city = t.get("city")
            if not isinstance(city, dict):
                findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.city", "city must be object."))
            else:
                bp, bt = city.get("basePrice"), city.get("baseToll")
                if not isinstance(bp, int) or bp <= 0:
                    findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.city.basePrice", "basePrice must be int > 0."))
                if not isinstance(bt, int) or bt < 0:
                    findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.city.baseToll", "baseToll must be int >= 0."))
                allowed = city.get("allowedBuildingIds")
                if not isinstance(allowed, list) or not allowed or not all(isinstance(x, str) for x in allowed):
                    findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.city.allowedBuildingIds", "allowedBuildingIds must be non-empty array of strings."))
                else:
                    for bid in allowed:
                        if bid not in building_ids:
                            findings.append(core.Finding("fail", "DATA_ID_NOT_FOUND", f"{loc}.city.allowedBuildingIds", f"buildingId not found: {bid}"))
            if "buy_land" not in action_ids:
                findings.append(core.Finding("fail", "DATA_INVARIANT_VIOLATION", f"{loc}.actions", "city must include buy_land action."))
            for action_id in sorted(action_ids):
                if action_id not in ("buy_land", "build"):
                    findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.actions", f"city actionId not allowed: {action_id}"))
        elif kind == "event":
            pool_id = t.get("eventPoolId")
            if not isinstance(pool_id, str) or pool_id not in event_pool_ids:
                findings.append(core.Finding("fail", "DATA_ID_NOT_FOUND", f"{loc}.eventPoolId", f"eventPoolId not found: {pool_id!r}"))
            if "trigger_event" not in action_ids:
                findings.append(core.Finding("fail", "DATA_INVARIANT_VIOLATION", f"{loc}.actions", "event tile must include trigger_event action."))
            for action_id in sorted(action_ids):
                if action_id != "trigger_event":
                    findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.actions", f"event actionId not allowed: {action_id}"))
        elif kind == "facility":
            fid = t.get("facilityId")
            if not isinstance(fid, str) or fid not in facility_ids:
                findings.append(core.Finding("fail", "DATA_ID_NOT_FOUND", f"{loc}.facilityId", f"facilityId not found: {fid!r}"))
            else:
                facility_action_ids = facility_action_ids_by_facility.get(fid)
                if facility_action_ids is not None:
                    if facility_action_ids and not action_ids:
                        findings.append(
                            core.Finding(
                                "fail",
                                "DATA_INVARIANT_VIOLATION",
                                f"{loc}.actions",
                                f"facility {fid} defines actions but tile has none.",
                            )
                        )
                    elif not facility_action_ids and action_ids:
                        findings.append(
                            core.Finding(
                                "fail",
                                "DATA_INVARIANT_VIOLATION",
                                f"{loc}.actions",
                                f"facility {fid} defines no actions but tile includes {sorted(action_ids)}.",
                            )
                        )
                    else:
                        for action_id in sorted(action_ids):
                            if action_id not in facility_action_ids:
                                findings.append(
                                    core.Finding(
                                        "fail",
                                        "DATA_ID_NOT_FOUND",
                                        f"{loc}.actions",
                                        f"actionId {action_id!r} not defined in facilities.{fid}.actions.",
                                    )
                                )
        elif kind == "empty":
            if action_ids:
                findings.append(core.Finding("fail", "DATA_INVARIANT_VIOLATION", f"{loc}.actions", "empty tile must not define actions."))
    if start_tile_id and start_tile_id not in seen_tiles:
        findings.append(core.Finding("fail", "DATA_ID_NOT_FOUND", f"{path.as_posix()}:track.startTileId", f"startTileId not found: {start_tile_id}"))


def validate_maps_index(
    repo_root: Path,
    path: Path,
    *,
    i18n: dict[str, str],
    building_ids: set[str],
    facility_ids: set[str],
    facility_action_ids_by_facility: dict[str, set[str]],
    region_ids: set[str],
    event_pool_ids: set[str],
    map_path_prefixes: tuple[str, ...] = ("res://Data/maps/",),
    findings: list[core.Finding],
) -> None:
    try:
        obj = core._read_json(path)
    except Exception as e:
        findings.append(core.Finding("fail", "DATA_JSON_PARSE_ERROR", path.as_posix(), f"invalid json: {e}"))
        return
    core._validate_no_meta(obj, path, findings)
    core._validate_header(obj, path, findings)
    if not isinstance(obj, dict):
        findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", path.as_posix(), "top-level must be an object."))
        return
    maps = obj.get("maps")
    if not isinstance(maps, list) or not maps:
        findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", path.as_posix(), '"maps" must be non-empty array.'))
        return
    seen: set[str] = set()
    for idx, m in enumerate(maps):
        loc = f"{path.as_posix()}:maps[{idx}]"
        if not isinstance(m, dict):
            findings.append(core.Finding("fail", "DATA_JSON_SCHEMA_ERROR", loc, "map entry must be object."))
            continue
        mid = core._check_id(m.get("mapId"), f"{loc}.mapId", findings)
        if mid:
            if mid in seen:
                findings.append(core.Finding("fail", "DATA_ID_DUPLICATE", f"{loc}.mapId", f"duplicate mapId: {mid}"))
            seen.add(mid)
        core._validate_i18n_key(m.get("nameKey"), f"{loc}.nameKey", i18n, findings, required=True)
        core._validate_i18n_key(m.get("descriptionKey"), f"{loc}.descriptionKey", i18n, findings, required=True)
        p = m.get("path")
        if not isinstance(p, str) or not p.endswith(".json") or not any(p.startswith(prefix) for prefix in map_path_prefixes):
            allowed = ", ".join(map_path_prefixes)
            findings.append(core.Finding("fail", "DATA_PATH_NOT_ALLOWED", f"{loc}.path", f"path must start with one of: {allowed}"))
            continue
        content_version = m.get("contentVersion")
        if not isinstance(content_version, int) or content_version < 1:
            findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.contentVersion", "contentVersion must be int >= 1."))
        map_abs = repo_root / Path(p.removeprefix("res://"))
        if not map_abs.exists():
            findings.append(core.Finding("fail", "DATA_MISSING_FILE", f"{loc}.path", f"map file missing: {map_abs.as_posix()}"))
            continue
        if not core.is_tracked(repo_root, map_abs.relative_to(repo_root)):
            findings.append(core.Finding("fail", "DATA_NOT_TRACKED", f"{loc}.path", "map file must be tracked by git."))
        _validate_map_file(
            repo_root,
            map_abs,
            building_ids=building_ids,
            facility_ids=facility_ids,
            facility_action_ids_by_facility=facility_action_ids_by_facility,
            region_ids=region_ids,
            event_pool_ids=event_pool_ids,
            i18n=i18n,
            expected_map_id=mid if isinstance(mid, str) else None,
            findings=findings,
        )
        core.validate_res_asset_path(repo_root, m.get("previewImagePath"), f"{loc}.previewImagePath", findings)
        rpmin, rpmax = m.get("recommendedPlayersMin"), m.get("recommendedPlayersMax")
        if not isinstance(rpmin, int) or rpmin < 4 or rpmin > 8:
            findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.recommendedPlayersMin", "recommendedPlayersMin must be int in [4,8]."))
        if not isinstance(rpmax, int) or rpmax < 4 or rpmax > 8:
            findings.append(core.Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.recommendedPlayersMax", "recommendedPlayersMax must be int in [4,8]."))
        if isinstance(rpmin, int) and isinstance(rpmax, int) and rpmin > rpmax:
            findings.append(core.Finding("fail", "DATA_INVARIANT_VIOLATION", f"{loc}.recommendedPlayersMax", "recommendedPlayersMin must be <= recommendedPlayersMax."))

