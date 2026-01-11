#!/usr/bin/env python3
"""
Windows build/export driver (Godot 4 + C#).

Goals (Task 33):
- Provide a cross-platform Python CLI surface (help/validation/paths/exit codes).
- Perform Windows-only export via Godot headless.
- Generate build metadata artifacts under build/:
  - build/build-info.json (+ .sha256)
  - build/release-profile.json (+ .sha256)
  - build/Game.exe (+ .sha256) and build/Game.pck (+ .sha256) when export succeeds
- Emit evidence under logs/ci/<YYYY-MM-DD>/build-windows/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import pathlib
import platform
import subprocess
import sys


def _utc_now_iso() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _today_yyyy_mm_dd() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _repo_root_from_this_file() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def _ensure_parent_dir(path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_text(path: pathlib.Path, content: str) -> None:
    _ensure_parent_dir(path)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def _write_json(path: pathlib.Path, obj: dict) -> None:
    _ensure_parent_dir(path)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _sha256_hex(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_sha256_file(target: pathlib.Path) -> pathlib.Path:
    sha_path = target.with_name(target.name + ".sha256")
    digest = _sha256_hex(target)
    _write_text(sha_path, f"{digest}  {target.as_posix()}\n")
    return sha_path


def _safe_git_commit_sha(repo_root: pathlib.Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_root),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        sha = (proc.stdout or "").strip()
        if sha and all(c in "0123456789abcdefABCDEF" for c in sha):
            return sha
    except Exception:
        pass
    return "0000000"


def _run_process(
    *,
    argv: list[str],
    cwd: pathlib.Path,
    stdout_path: pathlib.Path,
    stderr_path: pathlib.Path,
    timeout_sec: int,
) -> int:
    _ensure_parent_dir(stdout_path)
    _ensure_parent_dir(stderr_path)
    proc = subprocess.run(
        argv,
        cwd=str(cwd),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout_sec,
    )
    _write_text(stdout_path, proc.stdout or "")
    _write_text(stderr_path, proc.stderr or "")
    return int(proc.returncode)


def _export_windows(
    *,
    godot_bin: pathlib.Path,
    project_dir: pathlib.Path,
    preset: str,
    output_exe: pathlib.Path,
    mode: str,
    logs_dir: pathlib.Path,
    timeout_sec: int,
) -> tuple[int, pathlib.Path, pathlib.Path, pathlib.Path]:
    if mode not in ("release", "debug"):
        raise ValueError("mode must be release|debug")

    _ensure_parent_dir(output_exe)
    output_stdout = logs_dir / "godot_export.out.log"
    output_stderr = logs_dir / "godot_export.err.log"
    combined_log = logs_dir / "godot_export.log"

    cmd = [
        str(godot_bin),
        "--headless",
        "--verbose",
        "--path",
        str(project_dir),
        f"--export-{mode}",
        preset,
        str(output_exe),
    ]

    rc = _run_process(
        argv=cmd,
        cwd=project_dir,
        stdout_path=output_stdout,
        stderr_path=output_stderr,
        timeout_sec=timeout_sec,
    )

    combined = ""
    try:
        combined += output_stdout.read_text(encoding="utf-8")
    except Exception:
        pass
    try:
        combined += "\n" + output_stderr.read_text(encoding="utf-8")
    except Exception:
        pass
    _write_text(combined_log, combined.strip() + "\n")
    return rc, output_stdout, output_stderr, combined_log


def _write_metadata_and_checksums(
    *,
    repo_root: pathlib.Path,
    version: str,
    channel: str,
    commit_sha: str,
    build_time_utc: str,
    output_exe: pathlib.Path,
) -> dict:
    build_dir = repo_root / "build"
    build_info = build_dir / "build-info.json"
    release_profile = build_dir / "release-profile.json"

    payload = {
        "version": version,
        "channel": channel,
        "buildTimeUtc": build_time_utc,
        "commitSha": commit_sha,
        "outputExe": output_exe.as_posix(),
    }

    _write_json(build_info, payload)
    _write_json(release_profile, payload)

    written = {
        "buildInfo": build_info.as_posix(),
        "releaseProfile": release_profile.as_posix(),
        "checksums": [],
    }
    written["checksums"].append(_write_sha256_file(build_info).as_posix())
    written["checksums"].append(_write_sha256_file(release_profile).as_posix())

    pck = output_exe.with_suffix(".pck")
    if output_exe.exists():
        written["checksums"].append(_write_sha256_file(output_exe).as_posix())
    if pck.exists():
        written["checksums"].append(_write_sha256_file(pck).as_posix())

    return written


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="build_windows.py",
        description="Build/export Windows artifacts via Godot headless (Windows only for export).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--repo-root",
            default=None,
            help="Override repo root (default: derived from scripts/python/build_windows.py location).",
        )
        p.add_argument("--godot-bin", required=True, help="Path to Godot mono console executable.")
        p.add_argument("--project-dir", default=".", help="Project directory containing project.godot.")
        p.add_argument("--preset", default="Windows Desktop", help="Export preset name from export_presets.cfg.")
        p.add_argument("--output", default="build/Game.exe", help="Output EXE path.")
        p.add_argument("--version", default=os.environ.get("SC_BUILD_VERSION") or "0.0.0", help="Build version.")
        p.add_argument("--channel", default=os.environ.get("SC_RELEASE_CHANNEL") or "dev", help="Release channel.")
        p.add_argument("--timeout-sec", type=int, default=1200, help="Godot export timeout seconds.")

    add_common(sub.add_parser("release", help="Export Windows Release build (Windows only)."))
    add_common(sub.add_parser("debug", help="Export Windows Debug build (Windows only)."))

    meta = sub.add_parser("metadata", help="Generate build metadata + sha256 files without exporting.")
    meta.add_argument(
        "--repo-root",
        default=None,
        help="Override repo root (default: derived from scripts/python/build_windows.py location).",
    )
    meta.add_argument("--version", default=os.environ.get("SC_BUILD_VERSION") or "0.0.0", help="Build version.")
    meta.add_argument("--channel", default=os.environ.get("SC_RELEASE_CHANNEL") or "dev", help="Release channel.")
    meta.add_argument("--output", default="build/Game.exe", help="Output EXE path to record in metadata.")

    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)

    repo_root = pathlib.Path(args.repo_root).resolve() if getattr(args, "repo_root", None) else _repo_root_from_this_file()
    logs_dir = repo_root / "logs" / "ci" / _today_yyyy_mm_dd() / "build-windows"
    logs_dir.mkdir(parents=True, exist_ok=True)

    build_time_utc = _utc_now_iso()
    commit_sha = _safe_git_commit_sha(repo_root)

    output_exe = pathlib.Path(getattr(args, "output", "build/Game.exe"))
    if not output_exe.is_absolute():
        output_exe = (repo_root / output_exe).resolve()

    if args.command == "metadata":
        written = _write_metadata_and_checksums(
            repo_root=repo_root,
            version=str(args.version),
            channel=str(args.channel),
            commit_sha=commit_sha,
            build_time_utc=build_time_utc,
            output_exe=output_exe,
        )
        summary = {
            "tsUtc": build_time_utc,
            "command": "metadata",
            "outputExe": output_exe.as_posix(),
            "metadata": written,
        }
        _write_json(logs_dir / "summary.json", summary)
        return 0

    if platform.system() != "Windows":
        _write_text(logs_dir / "error.txt", "Windows export is only supported on Windows hosts.\n")
        print("Windows export is only supported on Windows hosts.", file=sys.stderr)
        return 2

    godot_bin = pathlib.Path(args.godot_bin).resolve()
    project_dir = pathlib.Path(args.project_dir).resolve()

    if not godot_bin.exists():
        print(f"Godot binary not found: {godot_bin}", file=sys.stderr)
        return 2
    if not project_dir.exists():
        print(f"Project dir not found: {project_dir}", file=sys.stderr)
        return 2
    if not (project_dir / "project.godot").exists():
        print(f"project.godot not found under: {project_dir}", file=sys.stderr)
        return 2

    mode = "release" if args.command == "release" else "debug"

    rc, out_log, err_log, combined_log = _export_windows(
        godot_bin=godot_bin,
        project_dir=project_dir,
        preset=str(args.preset),
        output_exe=output_exe,
        mode=mode,
        logs_dir=logs_dir,
        timeout_sec=int(args.timeout_sec),
    )

    written = _write_metadata_and_checksums(
        repo_root=repo_root,
        version=str(args.version),
        channel=str(args.channel),
        commit_sha=commit_sha,
        build_time_utc=build_time_utc,
        output_exe=output_exe,
    )

    summary = {
        "tsUtc": build_time_utc,
        "command": args.command,
        "preset": str(args.preset),
        "godotBin": godot_bin.as_posix(),
        "projectDir": project_dir.as_posix(),
        "outputExe": output_exe.as_posix(),
        "outputExists": output_exe.exists(),
        "outputPckExists": output_exe.with_suffix(".pck").exists(),
        "metadata": written,
        "export": {
            "rc": rc,
            "stdout": out_log.as_posix(),
            "stderr": err_log.as_posix(),
            "combined": combined_log.as_posix(),
        },
    }
    _write_json(logs_dir / "summary.json", summary)
    return 0 if rc == 0 and output_exe.exists() else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
