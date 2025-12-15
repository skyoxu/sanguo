from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Iterable, Sequence


def repo_root() -> Path:
    # scripts/sc/_util.py -> scripts/sc -> scripts -> repo root
    return Path(__file__).resolve().parents[2]


def today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def ci_dir(name: str) -> Path:
    root = repo_root()
    out_dir = root / "logs" / "ci" / today_str() / name
    ensure_dir(out_dir)
    return out_dir


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_cmd(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    timeout_sec: int = 900,
) -> tuple[int, str]:
    proc = subprocess.Popen(
        list(args),
        cwd=str(cwd or repo_root()),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    try:
        out, _ = proc.communicate(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        return 124, out
    return proc.returncode or 0, out


def first_existing(*candidates: str) -> str | None:
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def iter_files(
    root: Path,
    *,
    include_exts: set[str],
    skip_dirs: set[str],
    max_bytes: int = 512 * 1024,
) -> Iterable[Path]:
    for cur_root, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for name in files:
            p = Path(cur_root) / name
            if p.suffix.lower() not in include_exts:
                continue
            try:
                if p.stat().st_size > max_bytes:
                    continue
            except OSError:
                continue
            yield p

