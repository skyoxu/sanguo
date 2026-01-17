"""
Data catalog validation hard gate (T50-T65 alignment).

Enforces:
- Data JSON files must be committed (tracked by git).
- Required files exist for the current stage (characters + i18n).
- schemaVersion/version presence and basic constraints.
- Character config schema (steps-based) + i18n key coverage for logic-required display.
- effectKind whitelist hard gate.
- i18n namespaces soft gate (warn only).

Writes evidence into logs/ci/<YYYY-MM-DD>/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ID_RE = re.compile(r"^[a-z0-9_]{1,32}$")
WINDOWS_RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}

EFFECT_KIND_WHITELIST = {
    "economyStepDelta",
    "moneyDelta",
    "fixedDice",
    "skipNextTurn",
    "teleport",
    "pendingSteal",
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
    "err.",
)


@dataclass(frozen=True)
class Finding:
    level: str  # fail | warn
    code: str
    target: str
    message: str


def _run_git(args: list[str]) -> str:
    p = subprocess.run(
        ["git", *args],
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


def _is_tracked(path: Path) -> bool:
    try:
        out = _run_git(["ls-files", "--", path.as_posix()])
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
    if isinstance(v, int):
        return v
    return None


def _validate_header(obj: Any, path: Path, findings: list[Finding]) -> None:
    schema_version = _get_int(obj, "schemaVersion")
    version = _get_int(obj, "version")
    if schema_version is None or schema_version < 1:
        findings.append(
            Finding(
                "fail",
                "DATA_SCHEMA_VERSION_INVALID",
                path.as_posix(),
                'Missing/invalid top-level "schemaVersion" (require int >= 1).',
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


def _check_id(id_value: str, target: str, findings: list[Finding]) -> None:
    if not isinstance(id_value, str) or not id_value:
        findings.append(Finding("fail", "DATA_ID_INVALID_FORMAT", target, "id must be a non-empty string."))
        return

    if not ID_RE.match(id_value):
        findings.append(
            Finding(
                "fail",
                "DATA_ID_INVALID_FORMAT",
                target,
                "id must match ^[a-z0-9_]{1,32}$.",
            )
        )
        return

    if id_value.lower() in WINDOWS_RESERVED:
        findings.append(
            Finding(
                "fail",
                "DATA_RESERVED_NAME",
                target,
                f"id uses a Windows reserved name: {id_value!r}.",
            )
        )


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


def _validate_i18n_file(path: Path, findings: list[Finding]) -> dict[str, str]:
    try:
        obj = _read_json(path)
    except Exception as e:
        findings.append(Finding("fail", "DATA_JSON_PARSE_ERROR", path.as_posix(), f"invalid json: {e}"))
        return {}

    _validate_header(obj, path, findings)
    if not isinstance(obj, dict):
        findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", path.as_posix(), "top-level must be an object."))
        return {}

    locale = obj.get("locale")
    if locale != "zh-CN":
        findings.append(Finding("warn", "I18N_LOCALE_UNEXPECTED", path.as_posix(), f'locale is {locale!r}, expected "zh-CN".'))

    strings = obj.get("strings")
    if not isinstance(strings, dict):
        findings.append(Finding("fail", "I18N_STRINGS_MISSING", path.as_posix(), 'missing "strings" object.'))
        return {}

    # Soft gate: namespace prefixes.
    for k in strings.keys():
        if not isinstance(k, str):
            findings.append(Finding("fail", "I18N_KEY_INVALID", f"{path.as_posix()}:strings", "key must be string."))
            continue
        if not k.startswith(I18N_NAMESPACE_PREFIXES):
            findings.append(Finding("warn", "I18N_NAMESPACE_UNEXPECTED", f"{path.as_posix()}:strings.{k}", "key prefix not in recommended namespaces."))

    # Hard: flat key-value strings only.
    out: dict[str, str] = {}
    for k, v in strings.items():
        if not isinstance(v, str):
            findings.append(Finding("fail", "I18N_VALUE_INVALID", f"{path.as_posix()}:strings.{k}", "value must be string."))
            continue
        out[k] = v
    return out


def _validate_characters(path: Path, i18n: dict[str, str], findings: list[Finding]) -> None:
    try:
        obj = _read_json(path)
    except Exception as e:
        findings.append(Finding("fail", "DATA_JSON_PARSE_ERROR", path.as_posix(), f"invalid json: {e}"))
        return

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

    seen_ids: set[str] = set()
    for idx, c in enumerate(chars):
        loc = f"{path.as_posix()}:characters[{idx}]"
        if not isinstance(c, dict):
            findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", loc, "character must be an object."))
            continue

        cid = c.get("characterId")
        if not isinstance(cid, str):
            findings.append(Finding("fail", "DATA_ID_INVALID_FORMAT", f"{loc}.characterId", "characterId must be string."))
        else:
            _check_id(cid, f"{loc}.characterId", findings)
            if cid in seen_ids:
                findings.append(Finding("fail", "DATA_ID_DUPLICATE", f"{loc}.characterId", f"duplicate characterId: {cid}"))
            seen_ids.add(cid)

        name_key = c.get("nameKey")
        desc_key = c.get("descriptionKey")
        if not isinstance(name_key, str) or not name_key:
            findings.append(Finding("fail", "I18N_KEY_MISSING", f"{loc}.nameKey", "missing nameKey (logic-required display)."))
        else:
            if name_key not in i18n:
                findings.append(Finding("fail", "I18N_KEY_NOT_FOUND", f"{loc}.nameKey", f"missing i18n key: {name_key}"))

        if not isinstance(desc_key, str) or not desc_key:
            findings.append(Finding("fail", "I18N_KEY_MISSING", f"{loc}.descriptionKey", "missing descriptionKey (logic-required display)."))
        else:
            if desc_key not in i18n:
                findings.append(Finding("fail", "I18N_KEY_NOT_FOUND", f"{loc}.descriptionKey", f"missing i18n key: {desc_key}"))

        combat = c.get("combatRating")
        if not isinstance(combat, int) or combat < 0 or combat > 100:
            findings.append(Finding("fail", "DATA_VALUE_OUT_OF_RANGE", f"{loc}.combatRating", "combatRating must be int in [0,100]."))

        portrait = c.get("portraitPath")
        if not isinstance(portrait, str) or not portrait.startswith("res://"):
            findings.append(Finding("fail", "DATA_PATH_NOT_ALLOWED", f"{loc}.portraitPath", "portraitPath must be res://..."))

        sm_delta = c.get("startingMoneyStepDelta")
        if not isinstance(sm_delta, int):
            findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.startingMoneyStepDelta", "startingMoneyStepDelta must be int."))

        econ = c.get("economyStepDeltas")
        if not isinstance(econ, dict):
            findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.economyStepDeltas", "economyStepDeltas must be object."))
        else:
            required = ("buyPrice", "toll", "incomeSettlement", "buildCost", "upgradeCost")
            for k in required:
                v = econ.get(k)
                if not isinstance(v, int):
                    findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{loc}.economyStepDeltas.{k}", f"{k} must be int."))


def _validate_effect_kind_whitelist(data_dir: Path, findings: list[Finding]) -> None:
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


def _write_logs(findings: list[Finding], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    txt = out_dir / "data-catalog-validate.log"
    js = out_dir / "data-catalog-validate.json"

    payload = {
        "failures": [f.__dict__ for f in findings if f.level == "fail"],
        "warnings": [f.__dict__ for f in findings if f.level == "warn"],
        "counts": {
            "fail": sum(1 for f in findings if f.level == "fail"),
            "warn": sum(1 for f in findings if f.level == "warn"),
        },
    }
    js.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    lines: list[str] = []
    lines.append(f"DATA_CATALOG_VALIDATE failures={payload['counts']['fail']} warnings={payload['counts']['warn']}")
    for f in findings:
        lines.append(f"{f.level.upper():4} {f.code} target={f.target} msg={f.message}")
    txt.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="Fail on warnings as well (default: false).")
    args = ap.parse_args()

    repo_root = Path(".")
    data_dir = repo_root / "Data"
    required_files = [
        data_dir / "characters.json",
        data_dir / "i18n" / "zh_cn.json",
    ]

    findings: list[Finding] = []

    if not data_dir.exists():
        findings.append(Finding("fail", "DATA_DIR_MISSING", "Data/", "Data directory missing."))
    else:
        # Enforce "Data must be in repo" for required files.
        for f in required_files:
            if not f.exists():
                findings.append(Finding("fail", "DATA_MISSING_FILE", f.as_posix(), "required file missing."))
                continue
            if not _is_tracked(f):
                findings.append(Finding("fail", "DATA_NOT_TRACKED", f.as_posix(), "required Data file must be tracked by git."))

    i18n_map: dict[str, str] = {}
    if required_files[1].exists():
        i18n_map = _validate_i18n_file(required_files[1], findings)

    if required_files[0].exists():
        _validate_characters(required_files[0], i18n_map, findings)

    if data_dir.exists():
        _validate_effect_kind_whitelist(data_dir, findings)

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

