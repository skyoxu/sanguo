from __future__ import annotations

import os
from typing import Any


_KNOWN_PROFILES = {"strict", "host-safe"}


def resolve_security_profile(value: str | None = None) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        raw = str(os.environ.get("SECURITY_PROFILE") or "").strip().lower()
    # Default to host-safe to match single-player delivery posture.
    return raw if raw in _KNOWN_PROFILES else "host-safe"


def security_gate_defaults(profile: str) -> dict[str, str]:
    p = resolve_security_profile(profile)
    if p == "host-safe":
        # Host-safe: keep core host boundary protections hard, reduce anti-tamper posture.
        return {
            "path": "require",
            "sql": "require",
            "audit_schema": "warn",
            "ui_event_json_guards": "skip",
            "ui_event_source_verify": "skip",
            "audit_evidence": "skip",
        }

    # strict: full hardening posture for higher-risk delivery contexts.
    return {
        "path": "require",
        "sql": "require",
        "audit_schema": "require",
        "ui_event_json_guards": "require",
        "ui_event_source_verify": "require",
        "audit_evidence": "require",
    }


def normalize_gate_mode(value: str | None, default_value: str) -> str:
    candidate = str(value or "").strip().lower()
    if candidate in {"skip", "warn", "require"}:
        return candidate
    fallback = str(default_value or "").strip().lower()
    if fallback in {"skip", "warn", "require"}:
        return fallback
    return "skip"


def build_security_profile_context(profile: str) -> str:
    p = resolve_security_profile(profile)
    if p == "host-safe":
        lines = [
            "Security Profile:",
            "- profile: host-safe",
            "- intent: protect host/system safety for single-player local game; do not enforce anti-tamper-by-default.",
            "- must-keep: path boundary (res://, user://), reject traversal/absolute escape, no dynamic external code load, OS.execute default off, external URL https+allowlist.",
            "- de-emphasize by default: local save anti-tamper HMAC/signature, strict snapshot integrity hard-reject, chain-hash audit enforcement, trusted publisher hard gate.",
            "- review rule: unless task/acceptance explicitly requires anti-tamper, do not raise needs-fix solely for missing anti-tamper hardening.",
        ]
        return "\n".join(lines)

    lines = [
        "Security Profile:",
        "- profile: strict",
        "- intent: conservative baseline; enforce full repository security checks.",
        "- review rule: apply repository hardening expectations when acceptance/ADR is not explicit.",
    ]
    return "\n".join(lines)


def security_profile_payload(profile: str) -> dict[str, Any]:
    p = resolve_security_profile(profile)
    defaults = security_gate_defaults(p)
    return {
        "profile": p,
        "gate_defaults": defaults,
    }
