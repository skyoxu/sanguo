#!/usr/bin/env python3
"""Stable stdout status lines for project-health CLI entrypoints."""

from __future__ import annotations


PROJECT_HEALTH_DASHBOARD_PATH = "logs/ci/project-health/latest.html"


def render_project_health_scan_status_line(*, status: str, url: str = "") -> str:
    line = f"PROJECT_HEALTH_SCAN status={status} dashboard={PROJECT_HEALTH_DASHBOARD_PATH}"
    if str(url or "").strip():
        line += f" url={url}"
    return line


def render_project_health_scan_ci_fail_line() -> str:
    return "PROJECT_HEALTH_SCAN status=fail reason=serve_not_allowed_in_ci"


def render_project_health_server_status_line(*, reused: bool, url: str, server_json: str) -> str:
    return (
        f"PROJECT_HEALTH_SERVER status=ok reused={str(bool(reused)).lower()} "
        f"url={url} server_json={server_json}"
    )


def render_project_health_server_ci_fail_line() -> str:
    return "PROJECT_HEALTH_SERVER status=fail reason=serve_not_allowed_in_ci"
