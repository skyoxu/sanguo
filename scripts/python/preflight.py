#!/usr/bin/env python3
"""Local pre-flight checks for Windows development environment.

Checks:
1) dotnet --info
2) dotnet test Game.Core.Tests/Game.Core.Tests.csproj

Usage:
  py -3 scripts/python/preflight.py
  py -3 scripts/python/preflight.py --test-project Game.Core.Tests/Game.Core.Tests.csproj --configuration Debug
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _run_and_log(cmd: list[str], log_path: Path) -> tuple[int, str]:
    """Run command and write merged stdout/stderr to log file."""

    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        output = proc.stdout or ""
        log_path.write_text(output, encoding="utf-8")
        return proc.returncode, output
    except FileNotFoundError as exc:
        message = f"Command not found: {cmd[0]}\n{exc}\n"
        log_path.write_text(message, encoding="utf-8")
        return 127, message


def _today() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _candidate_dotnet_paths() -> list[Path]:
    exe_name = "dotnet.exe" if os.name == "nt" else "dotnet"
    candidates: list[Path] = []

    which_dotnet = shutil.which("dotnet")
    if which_dotnet:
        candidates.append(Path(which_dotnet))

    for env_key in ("DOTNET_ROOT", "DOTNET_HOME"):
        env_val = os.environ.get(env_key)
        if env_val:
            candidates.append(Path(env_val) / exe_name)

    candidates.append(Path.home() / ".dotnet" / exe_name)

    if os.name == "nt":
        for env_key in ("ProgramFiles", "ProgramFiles(x86)"):
            env_val = os.environ.get(env_key)
            if env_val:
                candidates.append(Path(env_val) / "dotnet" / "dotnet.exe")

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = os.path.normcase(os.path.normpath(str(candidate)))
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def _resolve_dotnet() -> Path | None:
    for candidate in _candidate_dotnet_paths():
        if candidate.is_file():
            return candidate
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local pre-flight checks.")
    parser.add_argument(
        "--test-project",
        default="Game.Core.Tests/Game.Core.Tests.csproj",
        help="Path to the dotnet test project file.",
    )
    parser.add_argument(
        "--configuration",
        default="Debug",
        help="dotnet build configuration for tests.",
    )
    parser.add_argument(
        "--out-dir",
        default="",
        help="Optional output directory. Default: logs/ci/<YYYY-MM-DD>/preflight",
    )
    args = parser.parse_args(argv)

    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        out_dir = Path("logs") / "ci" / _today() / "preflight"
    out_dir.mkdir(parents=True, exist_ok=True)

    dotnet_info_log = out_dir / "dotnet-info.log"
    dotnet_test_log = out_dir / "dotnet-test-game-core-tests.log"
    dotnet_bin_log = out_dir / "dotnet-bin.log"
    summary_path = out_dir / "summary.json"

    dotnet_bin = _resolve_dotnet()
    if dotnet_bin is None:
        dotnet_bin_log.write_text("dotnet not found in PATH/DOTNET_ROOT/home/.dotnet\n", encoding="utf-8")
        info_rc, _ = _run_and_log(["dotnet", "--info"], dotnet_info_log)
        test_cmd = [
            "dotnet",
            "test",
            args.test_project,
            "-c",
            args.configuration,
            "--nologo",
        ]
        test_rc, _ = _run_and_log(test_cmd, dotnet_test_log)
    else:
        dotnet_bin_log.write_text(f"resolved={dotnet_bin.as_posix()}\n", encoding="utf-8")
        info_rc, _ = _run_and_log([str(dotnet_bin), "--info"], dotnet_info_log)

        test_cmd = [
            str(dotnet_bin),
            "test",
            args.test_project,
            "-c",
            args.configuration,
            "--nologo",
        ]
        test_rc, _ = _run_and_log(test_cmd, dotnet_test_log)

    status = "ok" if info_rc == 0 and test_rc == 0 else "fail"
    summary = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "action": "local-preflight",
        "status": status,
        "checks": [
            {
                "name": "dotnet-info",
                "command": " ".join(([str(dotnet_bin)] if dotnet_bin else ["dotnet"]) + ["--info"]),
                "rc": info_rc,
                "log": dotnet_info_log.as_posix(),
            },
            {
                "name": "dotnet-test-game-core-tests",
                "command": " ".join(test_cmd),
                "rc": test_rc,
                "log": dotnet_test_log.as_posix(),
            },
            {
                "name": "dotnet-bin",
                "command": "resolve-dotnet",
                "rc": 0 if dotnet_bin else 127,
                "log": dotnet_bin_log.as_posix(),
            },
        ],
    }

    with io.open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(
        f"PRE_FLIGHT status={status} dotnet_info_rc={info_rc} "
        f"dotnet_test_rc={test_rc} out={summary_path.as_posix()}"
    )

    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
