"""
Data catalog validation rules (T50-T65 minimal data set).

Imported by scripts/python/validate_data_catalog.py.
Keep this module <= 400 lines.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ID_RE = re.compile(r"^[a-z0-9_]{1,32}$")
WINDOWS_RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}

ASSET_ALLOWED_EXTS = {".png", ".webp", ".svg"}
MAX_ASSET_BYTES = 1_048_576  # 1MB

EFFECT_KIND_WHITELIST = {
    "economyStepDelta",
    "moneyDelta",
    "transferOwnership",
    "fixedDice",
    "skipNextTurn",
    "teleport",
    "pendingSteal",
    "startCombat",
}

I18N_NAMESPACE_PREFIXES = (
    "ui.",
    "character.",
    "map.",
    "region.",
    "event.",
    "card.",
    "relic.",
    "facility.",
    "building.",
    "tile.",
    "pack.",
    "err.",
)

TILE_KINDS = {"city", "facility", "event", "empty"}
REQUIRED_ECONOMY_KEYS = ("buyPrice", "toll", "incomeSettlement", "buildCost", "upgradeCost")


@dataclass(frozen=True)
class Finding:
    level: str  # fail | warn
    code: str
    target: str
    message: str


def _run_git(repo_root: Path, args: list[str]) -> str:
    p = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if p.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (rc={p.returncode}): {p.stderr.strip()}"
        )
    return p.stdout


def is_tracked(repo_root: Path, rel_path: Path) -> bool:
    try:
        out = _run_git(repo_root, ["ls-files", "--", rel_path.as_posix()])
        return bool(out.strip())
    except Exception:
        return False


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _get_int(d: Any, key: str) -> int | None:
    if not isinstance(d, dict):
        return None
    v = d.get(key)
    if isinstance(v, bool):
        return None
    return v if isinstance(v, int) else None


def _validate_header(obj: Any, path: Path, findings: list[Finding]) -> None:
    schema_version = _get_int(obj, "schemaVersion")
    version = _get_int(obj, "version")
    if schema_version != 1:
        findings.append(
            Finding(
                "fail",
                "DATA_SCHEMA_VERSION_INVALID",
                path.as_posix(),
                'Missing/invalid top-level "schemaVersion" (require int == 1).',
            )
        )
    if version is None or version < 1:
        findings.append(
            Finding(
                "fail",
                "DATA_VERSION_INVALID",
                path.as_posix(),
                'Missing/invalid top-level "version" (require int >= 1).',
            )
        )


def _check_id(id_value: Any, target: str, findings: list[Finding]) -> str | None:
    if not isinstance(id_value, str) or not id_value:
        findings.append(Finding("fail", "DATA_ID_INVALID_FORMAT", target, "id must be a non-empty string."))
        return None
    if not ID_RE.match(id_value):
        findings.append(Finding("fail", "DATA_ID_INVALID_FORMAT", target, "id must match ^[a-z0-9_]{1,32}$."))
        return None
    if id_value.lower() in WINDOWS_RESERVED:
        findings.append(Finding("fail", "DATA_RESERVED_NAME", target, f"id uses a Windows reserved name: {id_value!r}."))
        return None
    return id_value


def _has_meta(obj: Any) -> bool:
    if isinstance(obj, dict):
        if "meta" in obj:
            return True
        return any(_has_meta(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_has_meta(v) for v in obj)
    return False


def _validate_no_meta(obj: Any, path: Path, findings: list[Finding]) -> None:
    if _has_meta(obj):
        findings.append(
            Finding(
                "fail",
                "DATA_META_FORBIDDEN",
                path.as_posix(),
                'The "meta" field is forbidden in Data JSON (avoid content pollution).',
            )
        )


def validate_res_asset_path(repo_root: Path, res_path: Any, target: str, findings: list[Finding]) -> Path | None:
    if not isinstance(res_path, str) or not res_path:
        findings.append(Finding("fail", "DATA_PATH_INVALID", target, "path must be a non-empty string."))
        return None
    if "\\" in res_path:
        findings.append(Finding("fail", "DATA_PATH_INVALID", target, "path must use forward slashes (res://...)."))
        return None
    if not res_path.startswith("res://Assets/"):
        findings.append(Finding("fail", "DATA_PATH_NOT_ALLOWED", target, "path must be under res://Assets/."))
        return None

    lowered = res_path.lower()
    if "%2e" in lowered or ".." in lowered:
        findings.append(Finding("fail", "DATA_PATH_TRAVERSAL", target, "path traversal patterns are not allowed."))
        return None

    rel = res_path.removeprefix("res://")
    fs_path = repo_root / Path(rel)
    try:
        rel_parts = fs_path.relative_to(repo_root).parts
    except Exception:
        findings.append(Finding("fail", "DATA_PATH_NOT_ALLOWED", target, "path must be within repo."))
        return None
    if any(part in ("..", ".") for part in rel_parts):
        findings.append(Finding("fail", "DATA_PATH_TRAVERSAL", target, "path traversal segments are not allowed."))
        return None

    if fs_path.suffix.lower() not in ASSET_ALLOWED_EXTS:
        findings.append(
            Finding(
                "fail",
                "DATA_ASSET_EXTENSION_NOT_ALLOWED",
                target,
                f"asset extension must be one of {sorted(ASSET_ALLOWED_EXTS)}.",
            )
        )
        return None

    if not fs_path.exists():
        findings.append(Finding("fail", "DATA_ASSET_MISSING", target, f"asset file missing: {fs_path.as_posix()}"))
        return None

    size = fs_path.stat().st_size
    if size > MAX_ASSET_BYTES:
        findings.append(
            Finding(
                "fail",
                "DATA_ASSET_TOO_LARGE",
                target,
                f"asset exceeds size limit ({size} bytes > {MAX_ASSET_BYTES}).",
            )
        )
        return None

    if not is_tracked(repo_root, fs_path.relative_to(repo_root)):
        findings.append(Finding("fail", "DATA_NOT_TRACKED", target, "asset file must be tracked by git."))
        return None

    return fs_path


def _validate_i18n_key(key: Any, target: str, i18n: dict[str, str], findings: list[Finding], *, required: bool) -> None:
    if not isinstance(key, str) or not key:
        findings.append(Finding("fail" if required else "warn", "I18N_KEY_MISSING", target, "missing i18n key."))
        return
    if key not in i18n:
        findings.append(
            Finding("fail" if required else "warn", "I18N_KEY_NOT_FOUND", target, f"missing i18n key: {key}")
        )


def _validate_economy_steps(obj: Any, target: str, findings: list[Finding]) -> None:
    if not isinstance(obj, dict):
        findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", target, "economyStepDeltas must be object."))
        return
    for k in REQUIRED_ECONOMY_KEYS:
        v = obj.get(k)
        if not isinstance(v, int):
            findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{target}.{k}", f"{k} must be int."))
            continue
        if v < -6 or v > 6:
            findings.append(Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{target}.{k}", "step delta must be in [-6,6]."))




def _walk_effect_kinds(obj: Any, path: str, out: list[tuple[str, str]]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            if k == "effectKind" and isinstance(v, str):
                out.append((p, v))
            else:
                _walk_effect_kinds(v, p, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk_effect_kinds(v, f"{path}[{i}]", out)


def validate_effect_kind_whitelist(data_dir: Path, findings: list[Finding]) -> None:
    for path in sorted(data_dir.rglob("*.json")):
        try:
            obj = _read_json(path)
        except Exception as e:
            findings.append(Finding("fail", "DATA_JSON_PARSE_ERROR", path.as_posix(), f"invalid json: {e}"))
            continue
        pairs: list[tuple[str, str]] = []
        _walk_effect_kinds(obj, "", pairs)
        for p, v in pairs:
            if v not in EFFECT_KIND_WHITELIST:
                findings.append(
                    Finding(
                        "fail",
                        "EFFECT_KIND_NOT_ALLOWED",
                        f"{path.as_posix()}:{p}",
                        f"effectKind {v!r} not in whitelist.",
                    )
                )




def validate_i18n_file(path: Path, findings: list[Finding], *, expected_locale: str = "zh-CN") -> dict[str, str]:
    try:
        obj = _read_json(path)
    except Exception as e:
        findings.append(Finding("fail", "DATA_JSON_PARSE_ERROR", path.as_posix(), f"invalid json: {e}"))
        return {}
    _validate_no_meta(obj, path, findings)
    _validate_header(obj, path, findings)
    if not isinstance(obj, dict):
        findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", path.as_posix(), "top-level must be an object."))
        return {}

    locale = obj.get("locale")
    if locale != expected_locale:
        findings.append(
            Finding(
                "warn",
                "I18N_LOCALE_UNEXPECTED",
                path.as_posix(),
                f'locale is {locale!r}, expected "{expected_locale}".',
            )
        )

    strings = obj.get("strings")
    if not isinstance(strings, dict):
        findings.append(Finding("fail", "I18N_STRINGS_MISSING", path.as_posix(), 'missing "strings" object.'))
        return {}

    for k in strings.keys():
        if not isinstance(k, str):
            findings.append(Finding("fail", "I18N_KEY_INVALID", f"{path.as_posix()}:strings", "key must be string."))
        elif not k.startswith(I18N_NAMESPACE_PREFIXES):
            findings.append(
                Finding(
                    "warn",
                    "I18N_NAMESPACE_UNEXPECTED",
                    f"{path.as_posix()}:strings.{k}",
                    "key prefix not in recommended namespaces.",
                )
            )

    out: dict[str, str] = {}
    for k, v in strings.items():
        if not isinstance(v, str):
            findings.append(Finding("fail", "I18N_VALUE_INVALID", f"{path.as_posix()}:strings.{k}", "value must be string."))
        else:
            out[k] = v
    return out


def validate_characters(repo_root: Path, path: Path, i18n: dict[str, str], findings: list[Finding]) -> None:
    try:
        obj = _read_json(path)
    except Exception as e:
        findings.append(Finding("fail", "DATA_JSON_PARSE_ERROR", path.as_posix(), f"invalid json: {e}"))
        return
    _validate_no_meta(obj, path, findings)
    _validate_header(obj, path, findings)
    if not isinstance(obj, dict):
        findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", path.as_posix(), "top-level must be an object."))
        return

    chars = obj.get("characters")
    if not isinstance(chars, list):
        findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", path.as_posix(), '"characters" must be an array.'))
        return

    if len(chars) < 8:
        findings.append(Finding("fail", "DATA_INVARIANT_VIOLATION", path.as_posix(), "characters must be >= 8."))

    seen: set[str] = set()
    for idx, c in enumerate(chars):
        loc = f"{path.as_posix()}:characters[{idx}]"
        if not isinstance(c, dict):
            findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", loc, "character must be an object."))
            continue

        cid = _check_id(c.get("characterId"), f"{loc}.characterId", findings)
        if cid:
            if cid in seen:
                findings.append(Finding("fail", "DATA_ID_DUPLICATE", f"{loc}.characterId", f"duplicate characterId: {cid}"))
            seen.add(cid)

        _validate_i18n_key(c.get("nameKey"), f"{loc}.nameKey", i18n, findings, required=True)
        _validate_i18n_key(c.get("descriptionKey"), f"{loc}.descriptionKey", i18n, findings, required=True)

        combat = c.get("combatRating")
        if not isinstance(combat, int) or combat < 0 or combat > 100:
            findings.append(Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.combatRating", "combatRating must be int in [0,100]."))

        validate_res_asset_path(repo_root, c.get("portraitPath"), f"{loc}.portraitPath", findings)

        starting_delta = c.get("startingMoneyStepDelta")
        if not isinstance(starting_delta, int):
            findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.startingMoneyStepDelta", "startingMoneyStepDelta must be int."))
        elif starting_delta < -6 or starting_delta > 6:
            findings.append(Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.startingMoneyStepDelta", "startingMoneyStepDelta must be in [-6,6]."))

        _validate_economy_steps(c.get("economyStepDeltas"), f"{loc}.economyStepDeltas", findings)
