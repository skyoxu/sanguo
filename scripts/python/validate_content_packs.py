"""
Content pack validation hard gate.

Validates Data/packs/_index.json and each pack.json for:
  - schema/version
  - id format
  - required fields
  - path safety + existence
  - i18n keys for pack name/desc exist in both locales

Writes evidence under logs/ci/<YYYY-MM-DD>/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import data_catalog_numeric_rules as numeric
import data_catalog_rules as core
import data_catalog_rules_maps as maps
import data_catalog_rules_t50 as t50


ID_RE = re.compile(r"^[a-z0-9_]{1,32}$")
WINDOWS_RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    target: str
    message: str


def _read_json(path: Path, findings: list[Finding]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        findings.append(Finding("fail", "DATA_JSON_PARSE_ERROR", path.as_posix(), f"invalid json: {exc}"))
        return None


def _is_safe_res_path(path: str, pack_id: str | None) -> bool:
    if not isinstance(path, str):
        return False
    if not path.startswith("res://"):
        return False
    lower = path.lower()
    if ".." in path or "%2e" in lower:
        return False
    if pack_id and not path.startswith(f"res://Data/packs/{pack_id}/"):
        return False
    return True


def _to_fs_path(repo_root: Path, res_path: str) -> Path:
    rel = res_path.replace("res://", "").replace("/", "\\")
    return repo_root / rel


def _check_id(value: Any, target: str, findings: list[Finding]) -> str | None:
    if not isinstance(value, str):
        findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", target, "id must be string."))
        return None
    if not ID_RE.match(value):
        findings.append(Finding("fail", "DATA_ID_INVALID", target, "id must match ^[a-z0-9_]{1,32}$."))
        return None
    if value.lower() in WINDOWS_RESERVED:
        findings.append(Finding("fail", "DATA_ID_INVALID", target, "id is Windows reserved name."))
        return None
    return value


def _load_i18n_strings(path: Path, findings: list[Finding]) -> dict[str, str]:
    obj = _read_json(path, findings)
    if not isinstance(obj, dict):
        return {}
    strings = obj.get("strings")
    if not isinstance(strings, dict):
        findings.append(Finding("fail", "I18N_STRINGS_MISSING", path.as_posix(), 'missing "strings" object.'))
        return {}
    out: dict[str, str] = {}
    for k, v in strings.items():
        if isinstance(k, str) and isinstance(v, str):
            out[k] = v
    return out


def _extend_findings(findings: list[Finding], core_findings: list[core.Finding]) -> None:
    for f in core_findings:
        findings.append(Finding(f.level, f.code, f.target, f.message))


def _to_fs_paths(repo_root: Path, paths: Any) -> list[Path]:
    if not isinstance(paths, list):
        return []
    out: list[Path] = []
    for p in paths:
        if isinstance(p, str):
            out.append(_to_fs_path(repo_root, p))
    return out


def _validate_pack_content_fields(repo_root: Path, pack_obj: dict[str, Any], pack_path: str, findings: list[Finding]) -> None:
    core_findings: list[core.Finding] = []

    content = pack_obj.get("content")
    if not isinstance(content, dict):
        return

    i18n = content.get("i18n")
    zh_i18n: dict[str, str] = {}
    en_i18n: dict[str, str] = {}
    if isinstance(i18n, dict):
        zh_path = i18n.get("zh-CN")
        en_path = i18n.get("en-US")
        if isinstance(zh_path, str):
            zh_file = _to_fs_path(repo_root, zh_path)
            if zh_file.exists():
                zh_i18n = core.validate_i18n_file(zh_file, core_findings, expected_locale="zh-CN")
        if isinstance(en_path, str):
            en_file = _to_fs_path(repo_root, en_path)
            if en_file.exists():
                en_i18n = core.validate_i18n_file(en_file, core_findings, expected_locale="en-US")

    i18n_keys = {k: v for k, v in zh_i18n.items() if k in en_i18n}

    building_ids: set[str] = set()
    region_ids: set[str] = set()
    facility_ids: set[str] = set()
    facility_action_ids_by_facility: dict[str, set[str]] = {}
    event_pool_ids: set[str] = set()

    buildings = _to_fs_paths(repo_root, content.get("buildings", []))
    for path in buildings:
        new_ids = t50.validate_buildings(path, i18n_keys, core_findings)
        dup = building_ids.intersection(new_ids)
        if dup:
            core_findings.append(core.Finding("fail", "DATA_ID_DUPLICATE", path.as_posix(), f"duplicate buildingId across files: {sorted(dup)}"))
        building_ids.update(new_ids)

    regions = _to_fs_paths(repo_root, content.get("regions", []))
    for path in regions:
        new_ids = t50.validate_regions(path, i18n_keys, core_findings)
        dup = region_ids.intersection(new_ids)
        if dup:
            core_findings.append(core.Finding("fail", "DATA_ID_DUPLICATE", path.as_posix(), f"duplicate regionId across files: {sorted(dup)}"))
        region_ids.update(new_ids)

    facilities = _to_fs_paths(repo_root, content.get("facilities", []))
    for path in facilities:
        ids, action_map = t50.validate_facilities(repo_root, path, i18n_keys, core_findings)
        dup = facility_ids.intersection(ids)
        if dup:
            core_findings.append(core.Finding("fail", "DATA_ID_DUPLICATE", path.as_posix(), f"duplicate facilityId across files: {sorted(dup)}"))
        facility_ids.update(ids)
        for fid, actions in action_map.items():
            if fid not in facility_action_ids_by_facility:
                facility_action_ids_by_facility[fid] = set(actions)
            else:
                facility_action_ids_by_facility[fid].update(actions)

    events = _to_fs_paths(repo_root, content.get("events", []))
    for path in events:
        event_pool_ids.update(t50.validate_random_events(path, i18n_keys, core_findings))

    cards = _to_fs_paths(repo_root, content.get("cards", []))
    for path in cards:
        t50.validate_cards_or_relics(path, "cards", "cardId", i18n_keys, core_findings)

    relics = _to_fs_paths(repo_root, content.get("relics", []))
    for path in relics:
        t50.validate_cards_or_relics(path, "relics", "relicId", i18n_keys, core_findings)

    characters = _to_fs_paths(repo_root, content.get("characters", []))
    for path in characters:
        core.validate_characters(repo_root, path, i18n_keys, core_findings)

    pack_id = pack_obj.get("packId") if isinstance(pack_obj.get("packId"), str) else None
    map_prefixes = (f"res://Data/packs/{pack_id}/maps/",) if pack_id else ("res://Data/maps/",)

    maps_indexes = _to_fs_paths(repo_root, content.get("maps", []))
    for path in maps_indexes:
        maps.validate_maps_index(
            repo_root,
            path,
            i18n=i18n_keys,
            building_ids=building_ids,
            facility_ids=facility_ids,
            facility_action_ids_by_facility=facility_action_ids_by_facility,
            region_ids=region_ids,
            event_pool_ids=event_pool_ids,
            map_path_prefixes=map_prefixes,
            findings=core_findings,
        )

    pack_root = _to_fs_path(repo_root, pack_path).parent
    if pack_root.exists():
        core.validate_effect_kind_whitelist(pack_root, core_findings)
        numeric.validate_probability_and_weight(pack_root, core_findings)

    _extend_findings(findings, core_findings)


def validate_pack_index(repo_root: Path, findings: list[Finding]) -> list[dict[str, Any]]:
    index_path = repo_root / "Data" / "packs" / "_index.json"
    obj = _read_json(index_path, findings)
    if not isinstance(obj, dict):
        return []
    schema_version = obj.get("schemaVersion")
    version = obj.get("version")
    if schema_version != 1:
        findings.append(Finding("fail", "DATA_SCHEMA_VERSION_INVALID", index_path.as_posix(), "schemaVersion must be 1."))
    if not isinstance(version, int) or version < 1:
        findings.append(Finding("fail", "DATA_VERSION_INVALID", index_path.as_posix(), "version must be int >= 1."))

    packs = obj.get("packs")
    if not isinstance(packs, list) or not packs:
        findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", index_path.as_posix(), '"packs" must be non-empty array.'))
        return []

    seen: set[str] = set()
    for idx, p in enumerate(packs):
        loc = f"{index_path.as_posix()}:packs[{idx}]"
        if not isinstance(p, dict):
            findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", loc, "pack entry must be object."))
            continue
        pack_id = _check_id(p.get("packId"), f"{loc}.packId", findings)
        if pack_id:
            if pack_id in seen:
                findings.append(Finding("fail", "DATA_ID_DUPLICATE", f"{loc}.packId", f"duplicate packId: {pack_id}"))
            seen.add(pack_id)
        for key in ("nameKey", "descriptionKey", "path"):
            if not isinstance(p.get(key), str) or not p.get(key):
                findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.{key}", f"{key} must be non-empty string."))
        if not isinstance(p.get("order"), int) or p.get("order") < 0:
            findings.append(Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.order", "order must be int >= 0."))
        if not isinstance(p.get("enabled"), bool):
            findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.enabled", "enabled must be bool."))
    return packs


def validate_pack(repo_root: Path, pack_entry: dict[str, Any], findings: list[Finding]) -> None:
    pack_id = pack_entry.get("packId")
    if not isinstance(pack_id, str):
        return
    pack_path = pack_entry.get("path")
    loc = f"Data/packs/_index.json:packId={pack_id}"
    if not isinstance(pack_path, str) or not _is_safe_res_path(pack_path, pack_id):
        findings.append(Finding("fail", "DATA_PATH_INVALID", f"{loc}.path", "pack path must be safe res://Data/packs/<packId>/..."))
        return
    fs_pack_path = _to_fs_path(repo_root, pack_path)
    if not fs_pack_path.exists():
        findings.append(Finding("fail", "DATA_MISSING_FILE", pack_path, "pack.json not found."))
        return

    pack_obj = _read_json(fs_pack_path, findings)
    if not isinstance(pack_obj, dict):
        return

    if pack_obj.get("schemaVersion") != 1:
        findings.append(Finding("fail", "DATA_SCHEMA_VERSION_INVALID", pack_path, "schemaVersion must be 1."))
    if not isinstance(pack_obj.get("version"), int) or pack_obj.get("version") < 1:
        findings.append(Finding("fail", "DATA_VERSION_INVALID", pack_path, "version must be int >= 1."))
    if pack_obj.get("packId") != pack_id:
        findings.append(Finding("fail", "DATA_ID_MISMATCH", pack_path, "packId must match index packId."))
    if not isinstance(pack_obj.get("nameKey"), str) or not pack_obj.get("nameKey"):
        findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{pack_path}:nameKey", "nameKey must be string."))
    if not isinstance(pack_obj.get("descriptionKey"), str) or not pack_obj.get("descriptionKey"):
        findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{pack_path}:descriptionKey", "descriptionKey must be string."))
    if not isinstance(pack_obj.get("enabledByDefault"), bool):
        findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{pack_path}:enabledByDefault", "enabledByDefault must be bool."))

    compat = pack_obj.get("compatibility")
    if not isinstance(compat, dict):
        findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{pack_path}:compatibility", "compatibility must be object."))
    else:
        if not isinstance(compat.get("minGameVersion"), str) or not compat.get("minGameVersion"):
            findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{pack_path}:compatibility.minGameVersion", "minGameVersion must be string."))
        max_gv = compat.get("maxGameVersion")
        if max_gv is not None and (not isinstance(max_gv, str) or not max_gv):
            findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{pack_path}:compatibility.maxGameVersion", "maxGameVersion must be string or null."))

    deps = pack_obj.get("dependencies", [])
    if deps is not None and not isinstance(deps, list):
        findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{pack_path}:dependencies", "dependencies must be array."))
    elif isinstance(deps, list):
        for i, dep in enumerate(deps):
            dloc = f"{pack_path}:dependencies[{i}]"
            if not isinstance(dep, dict):
                findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", dloc, "dependency must be object."))
                continue
            _check_id(dep.get("packId"), f"{dloc}.packId", findings)
            if not isinstance(dep.get("minVersion"), int) or dep.get("minVersion") < 1:
                findings.append(Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{dloc}.minVersion", "minVersion must be int >= 1."))

    content = pack_obj.get("content")
    if not isinstance(content, dict):
        findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{pack_path}:content", "content must be object."))
        return

    required_lists = [
        "maps",
        "characters",
        "events",
        "cards",
        "buildings",
        "relics",
        "regions",
        "facilities",
    ]
    for key in required_lists:
        vals = content.get(key)
        if not isinstance(vals, list):
            findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{pack_path}:content.{key}", f"{key} must be array."))
            continue
        seen_paths: set[str] = set()
        for idx, p in enumerate(vals):
            loc = f"{pack_path}:content.{key}[{idx}]"
            if not isinstance(p, str) or not _is_safe_res_path(p, pack_id):
                findings.append(Finding("fail", "DATA_PATH_INVALID", loc, "path must be safe res://Data/packs/<packId>/..."))
                continue
            if p in seen_paths:
                findings.append(Finding("fail", "DATA_ID_DUPLICATE", loc, f"duplicate path: {p}"))
                continue
            seen_paths.add(p)
            if not _to_fs_path(repo_root, p).exists():
                findings.append(Finding("fail", "DATA_MISSING_FILE", loc, "content file not found."))

    i18n = content.get("i18n")
    if not isinstance(i18n, dict):
        findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{pack_path}:content.i18n", "i18n must be object."))
        return
    zh_path = i18n.get("zh-CN")
    en_path = i18n.get("en-US")
    if not isinstance(zh_path, str) or not _is_safe_res_path(zh_path, pack_id):
        findings.append(Finding("fail", "DATA_PATH_INVALID", f"{pack_path}:content.i18n.zh-CN", "zh-CN path invalid."))
    if not isinstance(en_path, str) or not _is_safe_res_path(en_path, pack_id):
        findings.append(Finding("fail", "DATA_PATH_INVALID", f"{pack_path}:content.i18n.en-US", "en-US path invalid."))
    if isinstance(zh_path, str) and _is_safe_res_path(zh_path, pack_id):
        if not _to_fs_path(repo_root, zh_path).exists():
            findings.append(Finding("fail", "DATA_MISSING_FILE", f"{pack_path}:content.i18n.zh-CN", "zh-CN file missing."))
    if isinstance(en_path, str) and _is_safe_res_path(en_path, pack_id):
        if not _to_fs_path(repo_root, en_path).exists():
            findings.append(Finding("fail", "DATA_MISSING_FILE", f"{pack_path}:content.i18n.en-US", "en-US file missing."))

    if isinstance(zh_path, str) and isinstance(en_path, str):
        zh_file = _to_fs_path(repo_root, zh_path)
        en_file = _to_fs_path(repo_root, en_path)
        if zh_file.exists() and en_file.exists():
            zh_strings = _load_i18n_strings(zh_file, findings)
            en_strings = _load_i18n_strings(en_file, findings)
            for key in (pack_obj.get("nameKey"), pack_obj.get("descriptionKey")):
                if isinstance(key, str) and key:
                    if key not in zh_strings or key not in en_strings:
                        findings.append(
                            Finding(
                                "fail",
                                "I18N_KEY_MISSING",
                                f"{pack_path}:{key}",
                                "pack i18n key missing in zh/en.",
                            )
                        )

    _validate_pack_content_fields(repo_root, pack_obj, pack_path, findings)


def _write_logs(findings: list[Finding], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    txt = out_dir / "content-pack-validate.log"
    js = out_dir / "content-pack-validate.json"

    failures = [f.__dict__ for f in findings if f.level == "fail"]
    warnings = [f.__dict__ for f in findings if f.level == "warn"]
    payload = {"failures": failures, "warnings": warnings, "counts": {"fail": len(failures), "warn": len(warnings)}}

    js.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    lines = [f"CONTENT_PACK_VALIDATE failures={len(failures)} warnings={len(warnings)}"]
    for f in findings:
        lines.append(f"{f.level.upper():7} {f.code} target={f.target} msg={f.message}")
    txt.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="Fail on warnings as well.")
    args = ap.parse_args()

    repo_root = Path(".")
    findings: list[Finding] = []

    packs = validate_pack_index(repo_root, findings)
    for p in packs:
        if isinstance(p, dict):
            validate_pack(repo_root, p, findings)

    today = dt.date.today().strftime("%Y-%m-%d")
    out_dir = repo_root / "logs" / "ci" / today
    _write_logs(findings, out_dir)

    fail_count = sum(1 for f in findings if f.level == "fail")
    warn_count = sum(1 for f in findings if f.level == "warn")
    if fail_count > 0:
        return 1
    if args.strict and warn_count > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
