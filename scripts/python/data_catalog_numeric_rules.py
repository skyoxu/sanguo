"""
Numeric validation helpers for data catalog gates.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from data_catalog_rules import Finding

WEIGHT_KEY = "weight"
PROBABILITY_KEYS = ("probability", "chance", "prob")
WEIGHT_FLOAT_TOL = 1e-6


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _walk_probability_fields(obj: Any, path: str, findings: list[Finding]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            if k in PROBABILITY_KEYS:
                if not _is_number(v):
                    findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", p, "probability must be number."))
                elif v < 0 or v > 1:
                    findings.append(Finding("fail", "DATA_VALUE_OUT_OF_RANGE", p, "probability must be in [0,1]."))
            _walk_probability_fields(v, p, findings)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk_probability_fields(v, f"{path}[{i}]", findings)


def _walk_weight_lists(obj: Any, path: str, findings: list[Finding]) -> None:
    if isinstance(obj, list):
        weights: list[tuple[int, Any]] = []
        for i, item in enumerate(obj):
            if isinstance(item, dict) and WEIGHT_KEY in item:
                weights.append((i, item.get(WEIGHT_KEY)))
        if weights:
            if len(weights) != len(obj):
                missing = [i for i, item in enumerate(obj) if not (isinstance(item, dict) and WEIGHT_KEY in item)]
                findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", path, f"weight missing for items: {missing}"))

            numeric_weights: list[tuple[int, float]] = []
            for i, w in weights:
                if not _is_number(w):
                    findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", f"{path}[{i}].{WEIGHT_KEY}", "weight must be number."))
                else:
                    numeric_weights.append((i, float(w)))

            if numeric_weights:
                all_int = all(isinstance(w, int) and not isinstance(w, bool) for _, w in weights)
                all_float = all(isinstance(w, float) for _, w in weights)
                if not (all_int or all_float):
                    findings.append(Finding("fail", "DATA_JSON_SCHEMA_ERROR", path, "weight types must be all int or all float."))
                elif all_int:
                    for i, w in weights:
                        if isinstance(w, int) and (w < 0 or w > 100):
                            findings.append(
                                Finding(
                                    "fail",
                                    "DATA_VALUE_OUT_OF_RANGE",
                                    f"{path}[{i}].{WEIGHT_KEY}",
                                    "weight must be int in [0,100].",
                                )
                            )
                    total = sum(int(w) for _, w in weights if isinstance(w, int))
                    if total != 100:
                        findings.append(Finding("fail", "DATA_INVARIANT_VIOLATION", path, "weight sum must be 100."))
                else:
                    for i, w in numeric_weights:
                        if w < 0 or w > 1:
                            findings.append(
                                Finding(
                                    "fail",
                                    "DATA_VALUE_OUT_OF_RANGE",
                                    f"{path}[{i}].{WEIGHT_KEY}",
                                    "weight must be float in [0,1].",
                                )
                            )
                    total = sum(w for _, w in numeric_weights)
                    if abs(total - 1.0) > WEIGHT_FLOAT_TOL:
                        findings.append(Finding("fail", "DATA_INVARIANT_VIOLATION", path, "weight sum must be 1.0."))

        for i, v in enumerate(obj):
            _walk_weight_lists(v, f"{path}[{i}]", findings)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            _walk_weight_lists(v, p, findings)


def validate_probability_and_weight(data_dir: Path, findings: list[Finding]) -> None:
    for path in sorted(data_dir.rglob("*.json")):
        try:
            obj = _read_json(path)
        except Exception as e:
            findings.append(Finding("fail", "DATA_JSON_PARSE_ERROR", path.as_posix(), f"invalid json: {e}"))
            continue
        _walk_probability_fields(obj, path.as_posix(), findings)
        _walk_weight_lists(obj, path.as_posix(), findings)
