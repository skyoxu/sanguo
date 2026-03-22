#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import re


ANTI_TAMPER_TERMS: tuple[str, ...] = (
    "anti tamper",
    "anti-tamper",
    "tamper",
    "hmac",
    "signature",
    "checksum",
    "hash chain",
    "chain-hash",
    "integrity",
    "trusted publisher",
    "anti cheat",
    "anti-cheat",
)

HOST_SAFETY_TERMS: tuple[str, ...] = (
    "res://",
    "user://",
    "path traversal",
    "absolute path",
    "sql injection",
    "allowlist",
    "https",
    "os.execute",
    "dynamic load",
    "remote debug",
)

MIN_STRIPPED_EXCERPT_LEN = 12
MIN_STRIPPED_EN_WORDS = 3
MIN_STRIPPED_ZH_CHARS = 6


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def strip_prompt_prefix(text: str) -> str:
    stripped = str(text or "").strip()
    if not stripped:
        return stripped
    patterns = (
        r"^Task:\s*T\d+\s*[:\-]?\s*",
        r"^Master\s+title:\s*",
        r"^\u4efb\u52a1[:\uff1a]\s*T?\d+\s*[:\-]?\s*",
        r"^\u4e3b\u6807\u9898[:\uff1a]\s*",
    )
    for pattern in patterns:
        updated = re.sub(pattern, "", stripped, flags=re.IGNORECASE).strip()
        if updated != stripped:
            stripped = updated
    return stripped


def passes_stripped_excerpt_quality(norm_text: str) -> bool:
    text = str(norm_text or "").strip()
    if not text:
        return False
    en_words = len(re.findall(r"[A-Za-z]{2,}", text))
    zh_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    return en_words >= MIN_STRIPPED_EN_WORDS or zh_chars >= MIN_STRIPPED_ZH_CHARS


def contains_excerpt(excerpt: str, raw_corpus: str, norm_corpus: str) -> tuple[bool, bool]:
    if not excerpt:
        return False, False

    def match(candidate: str) -> bool:
        if not candidate:
            return False
        if candidate in raw_corpus:
            return True
        norm_candidate = normalize_ws(candidate)
        return bool(norm_candidate and norm_candidate in norm_corpus)

    if match(excerpt):
        return True, False

    stripped = strip_prompt_prefix(excerpt)
    norm_stripped = normalize_ws(stripped)
    if (
        stripped
        and stripped != excerpt
        and len(norm_stripped) >= MIN_STRIPPED_EXCERPT_LEN
        and passes_stripped_excerpt_quality(norm_stripped)
        and match(stripped)
    ):
        return True, True
    return False, False


def is_anti_tamper_only(text: str) -> bool:
    lower = str(text or "").lower()
    if not lower:
        return False
    has_anti_tamper = any(term in lower for term in ANTI_TAMPER_TERMS)
    if not has_anti_tamper:
        return False
    has_host_safety = any(term in lower for term in HOST_SAFETY_TERMS)
    return not has_host_safety


def dedupe_keep_order(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in items:
        value = str(raw or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def count_uncovered(obj: dict) -> int:
    raw = obj.get("uncovered_obligation_ids") or []
    if not isinstance(raw, list):
        return 0
    return len([item for item in raw if str(item or "").strip()])
