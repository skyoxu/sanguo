#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import inspect
import json
from typing import Any, Callable


def _safe_source_text(fn: Callable[..., Any]) -> str:
    try:
        source = inspect.getsource(fn)
    except Exception:
        module_name = str(getattr(fn, "__module__", "") or "").strip()
        qualname = str(getattr(fn, "__qualname__", "") or "").strip()
        return f"{module_name}:{qualname}"
    return str(source or "")


def build_runtime_code_fingerprint(function_map: dict[str, Callable[..., Any]]) -> tuple[str, dict[str, str]]:
    hashes: dict[str, str] = {}
    for key in sorted(function_map.keys()):
        fn = function_map[key]
        text = _safe_source_text(fn)
        hashes[key] = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
    payload = json.dumps(hashes, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return digest, hashes
