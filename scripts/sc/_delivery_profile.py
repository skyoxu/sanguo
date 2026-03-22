from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


_CONFIG_PATH = Path(__file__).resolve().parent / 'config' / 'delivery_profiles.json'


def _load_config() -> dict[str, Any]:
    return json.loads(_CONFIG_PATH.read_text(encoding='utf-8'))


def known_delivery_profiles() -> set[str]:
    config = _load_config()
    profiles = config.get('profiles') or {}
    return {str(name) for name in profiles.keys()}


def resolve_delivery_profile(value: str | None = None) -> str:
    raw = str(value or '').strip().lower()
    if not raw:
        raw = str(os.environ.get('DELIVERY_PROFILE') or '').strip().lower()
    config = _load_config()
    profiles = {str(name).lower() for name in (config.get('profiles') or {}).keys()}
    default_profile = str(config.get('default_profile') or 'fast-ship').strip().lower() or 'fast-ship'
    return raw if raw in profiles else default_profile


def _profile(profile: str) -> dict[str, Any]:
    config = _load_config()
    profiles = config.get('profiles') or {}
    resolved = resolve_delivery_profile(profile)
    payload = profiles.get(resolved) or {}
    return payload if isinstance(payload, dict) else {}


def profile_build_defaults(profile: str) -> dict[str, Any]:
    return dict((_profile(profile).get('build') or {}))


def profile_test_defaults(profile: str) -> dict[str, Any]:
    return dict((_profile(profile).get('test') or {}))


def profile_acceptance_defaults(profile: str) -> dict[str, Any]:
    return dict((_profile(profile).get('acceptance') or {}))


def profile_gate_bundle_defaults(profile: str) -> dict[str, Any]:
    return dict((_profile(profile).get('gate_bundle') or {}))


def profile_agent_review_defaults(profile: str) -> dict[str, Any]:
    return dict((_profile(profile).get('agent_review') or {}))


def profile_llm_review_defaults(profile: str) -> dict[str, Any]:
    return dict((_profile(profile).get('llm_review') or {}))


def profile_llm_obligations_defaults(profile: str) -> dict[str, Any]:
    return dict((_profile(profile).get('llm_obligations') or {}))


def profile_llm_semantic_gate_all_defaults(profile: str) -> dict[str, Any]:
    return dict((_profile(profile).get('llm_semantic_gate_all') or {}))


def default_security_profile_for_delivery(profile: str) -> str:
    value = str((_profile(profile).get('security_profile_default') or 'host-safe')).strip().lower()
    return value if value in {'strict', 'host-safe'} else 'host-safe'


def delivery_profile_payload(profile: str) -> dict[str, Any]:
    resolved = resolve_delivery_profile(profile)
    return {
        'profile': resolved,
        'security_profile_default': default_security_profile_for_delivery(resolved),
        'build': profile_build_defaults(resolved),
        'test': profile_test_defaults(resolved),
        'acceptance': profile_acceptance_defaults(resolved),
        'gate_bundle': profile_gate_bundle_defaults(resolved),
        'agent_review': profile_agent_review_defaults(resolved),
        'llm_review': profile_llm_review_defaults(resolved),
        'llm_obligations': profile_llm_obligations_defaults(resolved),
        'llm_semantic_gate_all': profile_llm_semantic_gate_all_defaults(resolved),
    }


def build_delivery_profile_context(profile: str) -> str:
    resolved = resolve_delivery_profile(profile)
    if resolved == 'playable-ea':
        lines = [
            'Delivery Profile:',
            '- profile: playable-ea',
            '- intent: optimize for fast playability validation and minimal delivery friction.',
            '- priorities: startup, core loop continuity, no obvious crash/blocker, basic smoke confidence.',
            '- review rule: do not raise Needs-Fix for missing heavy governance, anti-tamper, or documentation rigor unless the issue blocks playability.',
        ]
        return '\n'.join(lines)
    if resolved == 'fast-ship':
        lines = [
            'Delivery Profile:',
            '- profile: fast-ship',
            '- intent: ship quickly with basic maintainability, host safety, and commercial readiness.',
            '- priorities: crash prevention, host boundary safety, core tests, release-blocking defects.',
            '- review rule: focus on issues that threaten shipping, monetization, save safety, or basic maintainability; avoid over-enforcing enterprise-style rigor.',
        ]
        return '\n'.join(lines)
    lines = [
        'Delivery Profile:',
        '- profile: standard',
        '- intent: full repository baseline with stronger governance and consistency gates.',
        '- review rule: apply full task, ADR, contract, and test rigor expected by this repository.',
    ]
    return '\n'.join(lines)
