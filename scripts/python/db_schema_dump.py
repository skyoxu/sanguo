#!/usr/bin/env python3
"""
Dump schema_version from one or more SQLite databases.

Windows-friendly, UTF-8 output. Best-effort: skips unreadable files.

Usage:
  # PowerShell:
  py -3 scripts/python/db_schema_dump.py --glob "$env:APPDATA\\Godot\\app_userdata\\GodotGame\\*.db" --out logs/ci/<run_id>/schema-dump.json

  # cmd.exe:
  py -3 scripts/python/db_schema_dump.py --glob "%APPDATA%\\Godot\\app_userdata\\GodotGame\\*.db" --out logs/ci/<run_id>/schema-dump.json

  py -3 scripts/python/db_schema_dump.py --db C:\\path\\to\\a.db --db C:\\path\\to\\b.db
"""
import argparse
import datetime as dt
import glob
import json
import os
import sqlite3
import ctypes
import re
import uuid


class _Guid(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _guid_from_str(s: str) -> _Guid:
    g = _Guid()
    raw = uuid.UUID(s).bytes_le
    ctypes.memmove(ctypes.byref(g), raw, ctypes.sizeof(g))
    return g


def _known_folder_path(folder_id: str) -> str:
    """
    Return a known folder path using Windows APIs, independent of environment variables.

    folder_id must be a GUID string, e.g.:
      - RoamingAppData: 3EB685DB-65F9-4CF6-A03A-E3EF65729F3D
      - LocalAppData:   F1B32785-6FBA-4FCF-9D55-7B8E7F157091
      - Profile:        5E6C858F-0E22-4760-9AFE-EA3317B67173
    """
    fid = _guid_from_str(folder_id)
    ppath = ctypes.c_wchar_p()
    shget = ctypes.windll.shell32.SHGetKnownFolderPath
    shget.argtypes = [ctypes.POINTER(_Guid), ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_wchar_p)]
    shget.restype = ctypes.c_long
    hr = shget(ctypes.byref(fid), 0, None, ctypes.byref(ppath))
    if hr != 0:
        raise OSError(f"SHGetKnownFolderPath failed: 0x{hr & 0xFFFFFFFF:08X}")
    try:
        return ppath.value
    finally:
        ctypes.windll.ole32.CoTaskMemFree(ppath)


_ENV_PLACEHOLDER_RE = re.compile(r"%([A-Za-z0-9_]+)%")


def _expand_safe_placeholders(value: str, mapping: dict) -> str:
    """
    Expand %VARNAME% placeholders using a fixed mapping (not os.environ).
    Unknown placeholders are rejected to avoid unintended expansion.
    """

    def repl(m: re.Match) -> str:
        key = m.group(1).upper()
        if key in mapping:
            return mapping[key]
        raise ValueError(f"disallowed_placeholder:{key}")

    return _ENV_PLACEHOLDER_RE.sub(repl, value)


def _norm_abs(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def _is_under(path: str, root: str) -> bool:
    p = _norm_abs(path)
    r = _norm_abs(root)
    if p == r:
        return True
    if not r.endswith(os.sep):
        r = r + os.sep
    return p.startswith(r)


def _abspath_with_repo(path: str, repo_root: str) -> str:
    if os.path.isabs(path):
        return os.path.abspath(path)
    return os.path.abspath(os.path.join(repo_root, path))


def _glob_base_dir(pattern: str) -> str:
    wildcard_chars = ("*", "?", "[")
    idxs = [pattern.find(c) for c in wildcard_chars if c in pattern]
    idxs = [i for i in idxs if i >= 0]
    if not idxs:
        return os.path.dirname(pattern) or "."
    i = min(idxs)
    prefix = pattern[:i]
    if prefix.endswith(("\\", "/", os.sep)):
        return prefix.rstrip("\\/") or "."
    return os.path.dirname(prefix) or "."


def read_version(db_path: str) -> dict:
    rec = {"path": db_path, "version": None, "error": None}
    try:
        if not os.path.isfile(db_path):
            rec["error"] = "not_a_file"
            return rec
        con = sqlite3.connect(db_path)
        try:
            cur = con.cursor()
            cur.execute("SELECT version FROM schema_version WHERE id=1;")
            row = cur.fetchone()
            if row is None:
                rec["error"] = "no_row"
            else:
                rec["version"] = int(row[0])
        finally:
            con.close()
    except Exception as ex:
        rec["error"] = str(ex)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--glob', dest='patterns', action='append', default=[], help='Glob pattern(s) to search for .db files')
    ap.add_argument('--db', dest='dbs', action='append', default=[], help='Explicit .db file(s)')
    ap.add_argument('--out', dest='out', default=None, help='Output json path (default logs/ci/<date>/schema-dump.json)')
    ap.add_argument(
        '--unsafe-allow-any-path',
        dest='unsafe_allow_any_path',
        action='store_true',
        help='Disable path allowlist checks (for local debugging only)',
    )
    args = ap.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
    safe_vars = {
        "APPDATA": _known_folder_path("3EB685DB-65F9-4CF6-A03A-E3EF65729F3D"),  # RoamingAppData
        "LOCALAPPDATA": _known_folder_path("F1B32785-6FBA-4FCF-9D55-7B8E7F157091"),  # LocalAppData
        "USERPROFILE": _known_folder_path("5E6C858F-0E22-4760-9AFE-EA3317B67173"),  # Profile
    }

    allowed_roots = [
        repo_root,
        os.path.join(safe_vars["APPDATA"], "Godot", "app_userdata"),
        os.path.join(safe_vars["LOCALAPPDATA"], "Godot", "app_userdata"),
    ]

    files = []
    for p in args.patterns:
        expanded = _expand_safe_placeholders(p, safe_vars)
        base_dir = _abspath_with_repo(_glob_base_dir(expanded), repo_root)
        if not args.unsafe_allow_any_path and not any(_is_under(base_dir, r) for r in allowed_roots):
            files.append(expanded)
            continue
        files.extend(glob.glob(expanded))
    files.extend(args.dbs)
    # de-dup and filter
    uniq = []
    seen = set()
    for f in files:
        expanded = _expand_safe_placeholders(f, safe_vars)
        f = _abspath_with_repo(expanded, repo_root)
        if not args.unsafe_allow_any_path and not any(_is_under(f, r) for r in allowed_roots):
            # Keep the path but mark it as not allowed at read time.
            pass
        if f not in seen:
            seen.add(f)
            uniq.append(f)

    date = dt.date.today().strftime('%Y-%m-%d')
    out_path = args.out or os.path.join('logs', 'ci', date, 'schema-dump.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    results = []
    for f in uniq:
        if not args.unsafe_allow_any_path and not any(_is_under(f, r) for r in allowed_roots):
            results.append({"path": f, "version": None, "error": "path_not_allowed"})
            continue
        results.append(read_version(f))
    generated_at = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(
            {
                "generated_at": generated_at,
                "allowed_roots": allowed_roots if not args.unsafe_allow_any_path else ["<unsafe_allow_any_path>"],
                "items": results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"SCHEMA_DUMP_OUT={out_path} ITEMS={len(results)}")


if __name__ == '__main__':
    raise SystemExit(main())
