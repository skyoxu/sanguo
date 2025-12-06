#!/usr/bin/env python3
"""
Dump schema_version from one or more SQLite databases.

Windows-friendly, UTF-8 output. Best-effort: skips unreadable files.

Usage:
  py -3 scripts\python\db_schema_dump.py --glob "%APPDATA%\Godot\app_userdata\GodotGame\*.db" --out logs/ci/<run_id>/schema-dump.json
  py -3 scripts\python\db_schema_dump.py --db C:\path\to\a.db --db C:\path\to\b.db
"""
import argparse
import datetime as dt
import glob
import json
import os
import sqlite3


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
    args = ap.parse_args()

    files = []
    for p in args.patterns:
        files.extend(glob.glob(os.path.expandvars(p)))
    files.extend(args.dbs)
    # de-dup and filter
    uniq = []
    seen = set()
    for f in files:
        f = os.path.abspath(os.path.expandvars(f))
        if f not in seen:
            seen.add(f)
            uniq.append(f)

    date = dt.date.today().strftime('%Y-%m-%d')
    out_path = args.out or os.path.join('logs', 'ci', date, 'schema-dump.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    results = [read_version(f) for f in uniq]
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({"generated_at": dt.datetime.utcnow().isoformat() + 'Z', "items": results}, f, ensure_ascii=False, indent=2)
    print(f"SCHEMA_DUMP_OUT={out_path} ITEMS={len(results)}")


if __name__ == '__main__':
    raise SystemExit(main())

