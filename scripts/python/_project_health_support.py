#!/usr/bin/env python3
"""Thin compatibility facade for project-health helpers."""

from __future__ import annotations

from _project_health_checks import (
    check_directory_boundaries,
    detect_project_stage,
    doctor_project,
    project_health_scan,
)
from _project_health_common import refresh_dashboard, write_project_health_record

__all__ = [
    "detect_project_stage",
    "doctor_project",
    "check_directory_boundaries",
    "project_health_scan",
    "refresh_dashboard",
    "write_project_health_record",
]
