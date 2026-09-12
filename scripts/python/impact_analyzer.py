#!/usr/bin/env python3
"""Deterministic, bounded v1 impact analyzer built on Impact Index Core."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
if __package__:
    from .impact_runtime import parse_runtime_bindings
else:
    from impact_runtime import parse_runtime_bindings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    if __package__:
        raise ModuleNotFoundError
    from impact_analysis_handoff import EXIT_CODES
    from impact_analysis_index import (
        FULL_SHA,
        ImpactIndexError,
        GitTreeSnapshot,
        artifact_json_bytes,
        normalize_repository_path,
        validate_index_bytes,
        validate_manifest_bytes,
        validate_aliases,
    )
except ModuleNotFoundError:  # pragma: no cover
    from scripts.python.impact_analysis_handoff import EXIT_CODES
    from scripts.python.impact_analysis_index import (
        FULL_SHA,
        ImpactIndexError,
        GitTreeSnapshot,
        artifact_json_bytes,
        normalize_repository_path,
        validate_index_bytes,
        validate_manifest_bytes,
        validate_aliases,
    )


REPORT_SCHEMA = "newrouge.impact-analysis.v1"
ANALYZER_IMPLEMENTATION_REVISION = "newrouge.impact-analyzer.v1"
RISK_POLICY_REVISION = "newrouge.impact-risk.v1"
RELATIONS = {"references", "implements", "inherits", "consumes", "binds", "tests", "documents"}
TARGET_KINDS = {
    "file", "scene", "resource", "class", "interface", "method", "event", "contract",
    "system", "symbol", "signal", "node", "test_file", "test_symbol", "task", "acceptance", "adr", "decision",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _line_anchor(text: str, start: int, end: int | None = None) -> str:
    return f"line:{start}-{end or start}"


def _safe_rel(root: Path, value: str) -> Path:
    try:
        normalized = normalize_repository_path(value)
        candidate = (root / Path(*normalized.split("/"))).resolve()
        candidate.relative_to(root.resolve())
        return candidate
    except Exception as exc:
        raise ImpactIndexError("path_outside_repository", f"invalid repository-relative path: {value}") from exc


@dataclass(frozen=True)
class Symbol:
    kind: str
    identity: str
    path: str
    line: int
    declaration: str
    end_line: int | None = None


@dataclass(frozen=True)
class ResolvedTarget:
    kind: str
    identity: str
    canonical_path: str
    source_sha256: str
    resolution_method: str

    def as_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "identity": self.identity,
            "canonical_path": self.canonical_path,
            "source_sha256": self.source_sha256,
            "resolution_method": self.resolution_method,
        }


class SymbolIndex:
    """Restricted textual C# symbol view; intentionally not a compiler or call graph."""

    TYPE_RE = re.compile(
        r"\b(class|interface|struct|record)(?:\s+(?:class|struct))?\s+"
        r"([A-Za-z_]\w*)(?:\s*<([^>{};]+)>)?\s*(?::\s*([^\{;]+))?",
        re.MULTILINE,
    )
    EVENT_RE = re.compile(r"\bevent\s+[\w.<>,?\[\]\s]+?\s+([A-Za-z_]\w*)\s*[;={]")
    METHOD_RE = re.compile(
        r"(?:^|[;{}])\s*(?:(?:public|private|protected|internal|static|virtual|override|abstract|async|sealed|partial|new|unsafe|extern)\s+)*"
        r"[A-Za-z_][\w.<>,?\[\]\s]*?\s+([A-Za-z_]\w*)\s*(?:<([^>{}]*)>)?\s*\(([^()]*)\)",
        re.MULTILINE,
    )
    USING_RE = re.compile(r"^\s*using\s+(?:static\s+)?([A-Za-z_][\w.]*)\s*;", re.MULTILINE)
    USING_ALIAS_RE = re.compile(r"^\s*using\s+([A-Za-z_]\w*)\s*=\s*([A-Za-z_][\w.]*)\s*;", re.MULTILINE)
    NAMESPACE_RE = re.compile(r"\bnamespace\s+([A-Za-z_][\w.]*)\s*[;{]")

    _ALIASES = {
        "bool": "System.Boolean", "byte": "System.Byte", "sbyte": "System.SByte",
        "char": "System.Char", "decimal": "System.Decimal", "double": "System.Double",
        "float": "System.Single", "int": "System.Int32", "uint": "System.UInt32",
        "long": "System.Int64", "ulong": "System.UInt64", "short": "System.Int16",
        "ushort": "System.UInt16", "object": "System.Object", "string": "System.String",
        "void": "System.Void",
    }
    _BCL_GENERICS = {
        "Dictionary": "System.Collections.Generic.Dictionary",
        "HashSet": "System.Collections.Generic.HashSet",
        "IEnumerable": "System.Collections.Generic.IEnumerable",
        "IReadOnlyCollection": "System.Collections.Generic.IReadOnlyCollection",
        "IReadOnlyList": "System.Collections.Generic.IReadOnlyList",
        "List": "System.Collections.Generic.List",
        "Nullable": "System.Nullable",
        "Task": "System.Threading.Tasks.Task",
    }

    def __init__(self, sources: dict[str, str], hashes: dict[str, str], *, exploratory: bool = False):
        self.exploratory = exploratory
        self.skipped_methods: list[dict[str, Any]] = []
        self.sources = sources
        self.hashes = hashes
        self.symbols: list[Symbol] = []
        self.usings: dict[str, list[tuple[str, int]]] = {}
        self.using_aliases: dict[str, list[tuple[str, str, int]]] = {}
        self.types_by_path: dict[str, list[Symbol]] = {}
        self.sanitized: dict[str, str] = {
            path: self._mask_non_code(text) for path, text in sources.items()
        }
        self._type_spans: dict[str, list[tuple[int, int, Symbol]]] = {}
        self._method_spans: dict[str, list[tuple[int, int, Symbol]]] = {}
        for path, text in sorted(self.sanitized.items()):
            if not path.lower().endswith(".cs"):
                continue
            self.usings[path] = [
                (match.group(1), text.count("\n", 0, match.start()) + 1)
                for match in self.USING_RE.finditer(text)
            ]
            self.using_aliases[path] = [
                (match.group(1), match.group(2), text.count("\n", 0, match.start()) + 1)
                for match in self.USING_ALIAS_RE.finditer(text)
            ]
            self._parse_types(path, text)
        for path, text in sorted(self.sanitized.items()):
            if not path.lower().endswith(".cs"):
                continue
            self._parse_members(path, text)

    @staticmethod
    def _mask_non_code(text: str) -> str:
        """Replace comments and literals with spaces while preserving offsets and lines."""
        chars = list(text)
        result = list(text)
        index = 0
        length = len(chars)

        def mask(start: int, end: int) -> None:
            for position in range(start, end):
                if result[position] not in "\r\n":
                    result[position] = " "

        while index < length:
            if text.startswith("//", index):
                end = text.find("\n", index + 2)
                end = length if end < 0 else end
                mask(index, end)
                index = end
                continue
            if text.startswith("/*", index):
                end = text.find("*/", index + 2)
                end = length if end < 0 else end + 2
                mask(index, end)
                index = end
                continue

            prefix_length = 0
            verbatim = False
            raw_prefix = 2 if text.startswith('$@', index) or text.startswith('@$', index) else 0
            if chars[index] == '$':
                dollar_end = index
                while dollar_end < length and chars[dollar_end] == '$':
                    dollar_end += 1
                if text.startswith('"""', dollar_end):
                    raw_prefix = dollar_end - index
            raw_start = index + raw_prefix
            if text.startswith('"""', raw_start):
                cursor = raw_start
                while cursor < length and chars[cursor] == '"':
                    cursor += 1
                quote_count = cursor - raw_start
                if quote_count >= 3:
                    delimiter = '"' * quote_count
                    end = text.find(delimiter, cursor)
                    end = length if end < 0 else end + quote_count
                    mask(index, end)
                    index = end
                    continue
            if text.startswith('$@"', index) or text.startswith('@$"', index):
                prefix_length = 3
                verbatim = True
            elif text.startswith('@"', index):
                prefix_length = 2
                verbatim = True
            elif text.startswith('$"', index):
                prefix_length = 2
            elif chars[index] == '"':
                prefix_length = 1
            if prefix_length:
                cursor = index + prefix_length
                while cursor < length:
                    if verbatim and text.startswith('""', cursor):
                        cursor += 2
                        continue
                    if chars[cursor] == '"':
                        cursor += 1
                        break
                    if not verbatim and chars[cursor] == "\\":
                        cursor += 2
                    else:
                        cursor += 1
                mask(index, min(cursor, length))
                index = cursor
                continue
            if chars[index] == "'":
                cursor = index + 1
                while cursor < length:
                    if chars[cursor] == "\\":
                        cursor += 2
                        continue
                    if chars[cursor] == "'":
                        cursor += 1
                        break
                    cursor += 1
                mask(index, min(cursor, length))
                index = cursor
                continue
            index += 1
        return "".join(result)

    @staticmethod
    def _split_top_level(raw: str, delimiter: str = ",") -> list[str]:
        if not raw.strip():
            return []
        parts: list[str] = []
        start = 0
        depth = {"<": 0, "(": 0, "[": 0, "{": 0}
        pairs = {">": "<", ")": "(", "]": "[", "}": "{"}
        for index, char in enumerate(raw):
            if char in depth:
                depth[char] += 1
            elif char in pairs:
                opener = pairs[char]
                if depth[opener] == 0:
                    raise ImpactIndexError("unsupported_target", "unbalanced type or parameter syntax")
                depth[opener] -= 1
            elif char == delimiter and not any(depth.values()):
                parts.append(raw[start:index].strip())
                start = index + 1
        if any(depth.values()):
            raise ImpactIndexError("unsupported_target", "unbalanced type or parameter syntax")
        parts.append(raw[start:].strip())
        return parts

    @staticmethod
    def _matching_brace(text: str, opening: int) -> int | None:
        depth = 0
        for index in range(opening, len(text)):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    return index
        return None

    @staticmethod
    def _namespace(text: str, match_end: int) -> str:
        matches = list(SymbolIndex.NAMESPACE_RE.finditer(text[:match_end]))
        if not matches:
            return ""
        scoped: list[tuple[int, int, str]] = []
        file_scoped: list[tuple[int, str]] = []
        for match in matches:
            if match.end() and text[match.end() - 1] == "{":
                closing = SymbolIndex._matching_brace(text, match.end() - 1)
                if closing is None or match_end <= closing:
                    scoped.append((match.start(), closing or len(text), match.group(1)))
            else:
                file_scoped.append((match.start(), match.group(1)))
        if scoped:
            return ".".join(item[2] for item in sorted(scoped))
        return file_scoped[-1][1] if file_scoped else ""

    def _parse_types(self, path: str, text: str) -> None:
        for m in self.TYPE_RE.finditer(text):
            name, generic, bases = m.group(2), m.group(3), m.group(4)
            ns = self._namespace(text, m.start())
            arity = len(self._split_top_level(generic)) if generic else 0
            identity = f"{ns + '.' if ns else ''}{name}" + (f"`{arity}" if arity else "")
            kind = "interface" if m.group(1) == "interface" else "class"
            normalized_path = path.replace("\\", "/")
            if kind != "interface" and (normalized_path.startswith("Game.Core/Contracts/") or name.endswith("Event")):
                # Event records are a distinct target kind; remaining contract declarations
                # under Contracts are treated as contract symbols.
                kind = "event" if name.endswith("Event") else "contract"
            opening = text.find("{", m.end())
            semicolon = text.find(";", m.end())
            if opening < 0 or (semicolon >= 0 and semicolon < opening):
                closing = m.end()
            else:
                closing = self._matching_brace(text, opening) or len(text)
            line = text.count("\n", 0, m.start()) + 1
            end_line = text.count("\n", 0, closing) + 1
            symbol = Symbol(kind, identity, path, line, m.group(0).strip(), end_line)
            self.symbols.append(symbol)
            self.types_by_path.setdefault(path, []).append(symbol)
            self._type_spans.setdefault(path, []).append((m.start(), closing, symbol))
            if bases:
                generic_params = set(self._split_top_level(generic)) if generic else set()
                for base in self._split_top_level(bases):
                    base_name = self._normalize_type(base, namespace=ns, allowed_generic=generic_params)
                    self.symbols.append(Symbol("__base__", f"{identity}|{base_name}", path, symbol.line, base_name, symbol.line))

    def _parse_members(self, path: str, text: str) -> None:
        for m in self.EVENT_RE.finditer(text):
            ns = self._namespace(text, m.start())
            owner = self._owner_for_offset(path, m.start())
            prefix = owner.identity if owner else ns
            identity = f"{prefix + '::' if owner else prefix + '.' if prefix else ''}{m.group(1)}"
            line = text.count("\n", 0, m.start()) + 1
            self.symbols.append(Symbol("event", identity, path, line, m.group(0).strip(), line))
        for m in self.METHOD_RE.finditer(text):
            if any(start < m.start() < end for start, end, _ in self._method_spans.get(path, [])):
                continue
            owner = self._owner_for_offset(path, m.start())
            if owner:
                generic = m.group(2)
                arity = len(self._split_top_level(generic)) if generic else 0
                try:
                    params = self._normalize_params(m.group(3), owner.identity.rsplit(".", 1)[0])
                except ImpactIndexError as exc:
                    if not self.exploratory or exc.code != 'unsupported_target':
                        raise
                    self.skipped_methods.append({'path': path, 'line': text.count('\n', 0, m.start()) + 1,
                                                 'reason': exc.reason})
                    continue
                identity = f"{owner.identity}::{m.group(1)}" + (f"`{arity}" if arity else "") + f"({','.join(params)})"
                opening = text.find("{", m.end())
                expression = text.find("=>", m.end())
                semicolon = text.find(";", m.end())
                if expression >= 0 and (opening < 0 or expression < opening):
                    closing = semicolon if semicolon >= 0 else m.end()
                elif opening >= 0 and (semicolon < 0 or opening < semicolon):
                    closing = self._matching_brace(text, opening) or m.end()
                else:
                    closing = semicolon if semicolon >= 0 else m.end()
                line = text.count("\n", 0, m.start()) + 1
                end_line = text.count("\n", 0, closing) + 1
                symbol = Symbol("method", identity, path, line, m.group(0).strip(), end_line)
                self.symbols.append(symbol)
                self._method_spans.setdefault(path, []).append((m.start(), closing, symbol))

    def _owner_for_offset(self, path: str, offset: int) -> Symbol | None:
        candidates = [item for item in self._type_spans.get(path, []) if item[0] <= offset <= item[1]]
        if not candidates:
            return None
        return max(candidates, key=lambda item: item[0])[2]

    def symbol_at_line(self, path: str, line: int, *, methods_first: bool = True) -> Symbol | None:
        if methods_first:
            methods = [symbol for _, _, symbol in self._method_spans.get(path, []) if symbol.line <= line <= (symbol.end_line or symbol.line)]
            if methods:
                return max(methods, key=lambda item: item.line)
        types = [symbol for symbol in self.types_by_path.get(path, []) if symbol.line <= line <= (symbol.end_line or symbol.line)]
        return max(types, key=lambda item: item.line) if types else None

    def _resolve_simple_type(self, value: str, namespace: str, allowed_generic: set[str] | None = None) -> str:
        if value in self._ALIASES:
            return self._ALIASES[value]
        if value in self._BCL_GENERICS:
            return self._BCL_GENERICS[value]
        if "." in value or "`" in value:
            return value
        candidates = {
            symbol.identity for symbol in self.symbols
            if symbol.kind in {"class", "interface", "event", "contract"}
            and symbol.identity.rsplit(".", 1)[-1].split("`", 1)[0] == value
        }
        if len(candidates) == 1:
            return next(iter(candidates))
        if allowed_generic and value in allowed_generic:
            return value
        if allowed_generic is None and re.fullmatch(r"[A-Z][A-Za-z0-9_]*", value) and value not in self._ALIASES:
            raise ImpactIndexError("unsupported_target", "unresolved generic parameter is unsupported")
        return f"{namespace}.{value}" if namespace else value

    def _normalize_type(self, raw: str, *, namespace: str = "", allowed_generic: set[str] | None = None) -> str:
        value = re.sub(r"\s+", "", raw.replace("global::", ""))
        if not value or "delegate*" in value or "dynamic" in value or "=>" in value or "*" in value:
            raise ImpactIndexError("unsupported_target", "unsupported parameter type")
        if value.startswith("(") or (value.endswith(")") and "," in value):
            raise ImpactIndexError("unsupported_target", "tuple parameter type is unsupported")
        suffix = ""
        while value.endswith("[]"):
            suffix = "[]" + suffix
            value = value[:-2]
        nullable = value.endswith("?")
        if nullable:
            value = value[:-1]
        generic = value.find("<")
        if generic >= 0:
            if not value.endswith(">"):
                raise ImpactIndexError("unsupported_target", "unbalanced generic type")
            base = value[:generic]
            arguments = self._split_top_level(value[generic + 1:-1])
            base = self._resolve_simple_type(base, namespace, allowed_generic)
            if "`" not in base:
                base = f"{base}`{len(arguments)}"
            value = f"{base}<{','.join(self._normalize_type(argument, namespace=namespace, allowed_generic=allowed_generic) for argument in arguments)}>"
        else:
            value = self._resolve_simple_type(value, namespace, allowed_generic)
        if nullable:
            value = f"System.Nullable`1<{value}>"
        return value + suffix

    def _normalize_params(self, raw: str, namespace: str = "") -> list[str]:
        result: list[str] = []
        for item in self._split_top_level(raw):
            item = re.sub(r"^\s*(?:\[[^\]]+\]\s*)+", "", item).strip()
            item = self._strip_default(item)
            modifier = re.match(r"^(ref|out|in|params)\s+", item)
            by_ref = bool(modifier and modifier.group(1) in {"ref", "out", "in"})
            if modifier:
                item = item[modifier.end():].strip()
            type_text = self._strip_parameter_name(item)
            normalized = self._normalize_type(type_text, namespace=namespace)
            result.append(normalized + ("&" if by_ref else ""))
        return result

    @classmethod
    def _strip_default(cls, value: str) -> str:
        depth = 0
        for index, char in enumerate(value):
            if char in "<([{":
                depth += 1
            elif char in ">)]}":
                depth -= 1
            elif char == "=" and depth == 0:
                return value[:index].strip()
        return value.strip()

    @staticmethod
    def _strip_parameter_name(value: str) -> str:
        depth = 0
        split = -1
        for index, char in enumerate(value):
            if char in "<([":
                depth += 1
            elif char in ">)]":
                depth -= 1
            elif char.isspace() and depth == 0:
                split = index
        if split < 0:
            return value
        candidate = value[split:].strip()
        return value[:split].strip() if re.fullmatch(r"[A-Za-z_]\w*", candidate) else value

    def normalize_method_identity(self, identity: str) -> str:
        if "::" not in identity:
            raise ImpactIndexError("underqualified_target", "method target requires namespace and declaring type")
        owner, member = identity.split("::", 1)
        if "." not in owner:
            raise ImpactIndexError("underqualified_target", "method target requires namespace and declaring type")
        if "(" not in member:
            raise ImpactIndexError("ambiguous_target", "method overload requires a complete parameter signature")
        if not member.endswith(")"):
            raise ImpactIndexError("unsupported_target", "method signature is malformed")
        name, raw_params = member.split("(", 1)
        raw_params = raw_params[:-1]
        if name in {".ctor", ".cctor", owner.rsplit(".", 1)[-1].split("`", 1)[0]}:
            raise ImpactIndexError("unsupported_target", "constructors are unsupported in v1")
        if not re.fullmatch(r"[A-Za-z_]\w*(?:`[1-9]\d*)?", name):
            raise ImpactIndexError("unsupported_target", "method name or generic arity is unsupported")
        normalized_params: list[str] = []
        for item in self._split_top_level(raw_params):
            modifier = re.match(r"^(ref|out|in)\s+", item.strip())
            by_ref = bool(modifier)
            type_text = item.strip()[modifier.end():].strip() if modifier else item.strip()
            if type_text.endswith("&"):
                by_ref = True
                type_text = type_text[:-1]
            namespace = owner.rsplit(".", 1)[0]
            normalized_params.append(self._normalize_type(type_text, namespace=namespace) + ("&" if by_ref else ""))
        return f"{owner}::{name}({','.join(normalized_params)})"

    def find(self, kind: str, identity: str) -> list[Symbol]:
        return [s for s in self.symbols if s.kind == kind and s.identity == identity]


class TargetResolver:
    def __init__(self, index_document: dict[str, Any], sources: dict[str, str], hashes: dict[str, str], aliases: dict[str, Any] | None = None, *, exploratory: bool = False):
        self.index = index_document
        self.sources = sources
        self.hashes = hashes
        self.aliases = aliases or {"aliases": {"event": {}, "contract": {}}}
        try:
            validate_aliases(self.aliases)
        except Exception as exc:
            raise ImpactIndexError("invalid_manifest", f"invalid target alias table: {exc}") from exc
        self.symbol_index = SymbolIndex(sources, hashes, exploratory=exploratory)

    def resolve(self, target: dict[str, Any] | str) -> ResolvedTarget:
        if isinstance(target, str):
            try:
                target = json.loads(target)
            except (TypeError, json.JSONDecodeError) as exc:
                raise ImpactIndexError("unsupported_target", "target must be valid JSON") from exc
        if not isinstance(target, dict) or set(target) != {"type", "id"}:
            raise ImpactIndexError("unsupported_target", "target must be an object with type and id")
        kind = str(target.get("type") or "").strip().lower()
        ident = str(target.get("id") or "").strip()
        if kind not in TARGET_KINDS or not ident:
            raise ImpactIndexError("unsupported_target", "unsupported or empty target kind/id")
        if kind in {"file", "scene", "resource", "task", "adr", "decision", "acceptance"}:
            path = normalize_repository_path(ident)
            if path not in self.hashes:
                raise ImpactIndexError("target_not_found", f"target path not found: {path}")
            return ResolvedTarget(kind, path, path, self.hashes[path], "exact-path")
        if kind == "method":
            ident = self.symbol_index.normalize_method_identity(ident)
        exact = [s for s in self.symbol_index.symbols if s.kind == kind and s.identity == ident]
        if exact:
            if len(exact) > 1:
                raise ImpactIndexError("ambiguous_target", f"target resolves to multiple symbols: {ident}")
            item = exact[0]
            return ResolvedTarget(kind, item.identity, item.path, self.hashes[item.path], "exact-index-symbol")

        lookup = ident
        resolution_method = "exact-index-symbol"
        kind_aliases = self.aliases.get("aliases", {}).get(kind, {}) if isinstance(self.aliases, dict) else {}
        if kind in {"event", "contract"} and ident in kind_aliases:
            lookup = kind_aliases[ident]
            resolution_method = "kind-scoped-alias"
            candidates_any_kind = [s for s in self.symbol_index.symbols if s.identity == lookup]
            candidates = [
                s for s in candidates_any_kind
                if s.kind == kind and s.path.replace("\\", "/").startswith("Game.Core/Contracts/")
            ]
            if len(candidates) != 1 or len(candidates_any_kind) != 1:
                raise ImpactIndexError("invalid_manifest", f"alias does not resolve to one trusted {kind}: {ident}")
        else:
            candidates = [s for s in self.symbol_index.symbols if s.kind == kind and s.identity == lookup]
        if not candidates and kind != "method" and "." not in lookup:
            raise ImpactIndexError("underqualified_target", f"{kind} target requires a qualified identity")
        if not candidates:
            raise ImpactIndexError("target_not_found", f"target symbol not found: {ident}")
        if len(candidates) > 1:
            raise ImpactIndexError("ambiguous_target", f"target resolves to multiple symbols: {ident}")
        item = candidates[0]
        return ResolvedTarget(kind, item.identity, item.path, self.hashes[item.path], resolution_method)


def _edge(from_kind: str, from_id: str, to_kind: str, to_id: str, relation: str, path: str, anchor: str, digest: str, *, indexed_hashes: dict[str, str] | None = None) -> dict[str, str]:
    if relation not in RELATIONS:
        raise ImpactIndexError("unsupported_relation", relation)
    anchor_match = re.fullmatch(r"(?:line:(\d+)-(\d+)|symbol:[^\s]+|json-pointer:/.*|markdown:[^#]+#[^\s]+)", anchor)
    if not anchor_match:
        raise ImpactIndexError("source_read_failure", f"invalid evidence anchor: {anchor}")
    if anchor_match.group(1) and int(anchor_match.group(1)) > int(anchor_match.group(2)):
        raise ImpactIndexError("source_read_failure", f"invalid evidence anchor range: {anchor}")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ImpactIndexError("source_read_failure", "evidence hash must be lowercase SHA-256")
    try:
        normalized_path = normalize_repository_path(path)
    except Exception as exc:
        raise ImpactIndexError("source_read_failure", f"invalid evidence path: {path}") from exc
    allowed = {
        "references": ({"file", "symbol"}, {"file", "symbol"}),
        "implements": ({"class", "interface", "symbol"}, {"interface", "contract", "symbol"}),
        "inherits": ({"class", "interface", "symbol"}, {"class", "interface", "symbol"}),
        "consumes": ({"class", "symbol", "system", "file"}, {"event", "contract", "symbol"}),
        "binds": ({"scene", "node", "script", "resource", "symbol"}, {"node", "script", "signal", "resource", "symbol"}),
        "tests": ({"test_file", "test_symbol"}, {"file", "symbol", "task", "acceptance"}),
        "documents": ({"adr", "task", "contract", "decision"}, {"file", "symbol", "event", "contract", "task"}),
    }
    frm, to = allowed[relation]
    if from_kind not in frm or to_kind not in to:
        raise ImpactIndexError("unsupported_relation", f"invalid endpoint kinds for {relation}: {from_kind}->{to_kind}")
    if not from_id or not to_id:
        raise ImpactIndexError("unsupported_relation", "edge endpoints must be non-empty")
    if indexed_hashes is not None:
        expected_hash = indexed_hashes.get(normalized_path)
        if expected_hash is None:
            raise ImpactIndexError("source_read_failure", f"evidence path is outside indexed source universe: {normalized_path}")
        if expected_hash != digest:
            raise ImpactIndexError("source_read_failure", f"evidence hash does not match indexed source: {normalized_path}")
    return {"from": from_id, "from_kind": from_kind, "to": to_id, "to_kind": to_kind, "relation": relation, "evidence_path": normalized_path, "evidence_anchor": anchor, "evidence_sha256": digest}


def _sort_edges(edges: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[str, ...], dict[str, Any]] = {}
    for edge in edges:
        try:
            key = (edge["from_kind"], edge["from"], edge["to_kind"], edge["to"], edge["relation"], edge["evidence_path"], edge["evidence_anchor"])
        except (KeyError, TypeError) as exc:
            raise ImpactIndexError("invalid_manifest", "edge canonical tuple is incomplete") from exc
        existing = unique.get(key)
        if existing is not None and existing != edge:
            raise ImpactIndexError("invalid_manifest", "conflicting duplicate edge payload")
        unique[key] = edge
    return [unique[k] for k in sorted(unique)]


RISK_RULES = {
    "contract-target": ("high", "contract target"),
    "event-target": ("high", "event target"),
    "save-format-target": ("high", "save format target"),
    "core-domain-target": ("high", "core domain target"),
    "service-target": ("medium", "service target"),
    "system-target": ("medium", "system target"),
    "ui-only-target": ("low", "UI-only target"),
    "insufficient-evidence": ("unknown", "insufficient deterministic evidence"),
}
RISK_RULE_ORDER = tuple(RISK_RULES)
RISK_LEVEL_SCORE = {"unknown": 0, "low": 1, "medium": 2, "high": 3}


def _is_test_path(path: str) -> bool:
    lowered = path.replace("\\", "/").casefold()
    return (
        ".tests/" in lowered
        or lowered.startswith("tests/")
        or lowered.startswith("tests.")
        or lowered.endswith("tests.cs")
        or "/tests/" in lowered
    )


def _is_ui_path(path: str) -> bool:
    lowered = path.replace("\\", "/").casefold()
    return lowered.startswith("game.ui/") or "/ui/" in f"/{lowered}" or lowered.endswith("ui.cs")


def _is_service_path(path: str) -> bool:
    lowered = path.replace("\\", "/").casefold()
    return "/services/" in f"/{lowered}" or lowered.endswith("service.cs")


def _is_system_path(path: str) -> bool:
    lowered = path.replace("\\", "/").casefold()
    return "/systems/" in f"/{lowered}" or lowered.endswith("system.cs")


def _is_save_path(path: str) -> bool:
    lowered = path.replace("\\", "/").casefold()
    parts = re.split(r"[/_.-]+", lowered)
    return "save" in parts or "saves" in parts or "saveformat" in parts


def _is_core_domain_path(path: str) -> bool:
    lowered = path.replace("\\", "/").casefold()
    return (
        lowered.startswith("game.core/")
        and not lowered.startswith("game.core.tests/")
        and "/contracts/" not in f"/{lowered}"
        and not _is_service_path(lowered)
        and not _is_system_path(lowered)
        and not _is_ui_path(lowered)
    )


def _risk_matches(target: ResolvedTarget, edges: list[dict[str, Any]]) -> list[str]:
    path = target.canonical_path
    matched: set[str] = set()
    if target.kind == "contract" or "/contracts/" in f"/{path.replace('\\', '/').casefold()}":
        matched.add("contract-target")
    if target.kind == "event":
        matched.add("event-target")
    if _is_save_path(path):
        matched.add("save-format-target")
    if _is_core_domain_path(path):
        matched.add("core-domain-target")
    if _is_service_path(target.canonical_path) or target.identity.rsplit(".", 1)[-1].split("`", 1)[0].endswith("Service"):
        matched.add("service-target")
    if target.kind == "system" or _is_system_path(target.canonical_path) or target.identity.rsplit(".", 1)[-1].split("`", 1)[0].endswith("System"):
        matched.add("system-target")
    if _is_ui_path(path):
        matched.add("ui-only-target")
    if not matched:
        matched.add("insufficient-evidence")
    return [rule for rule in RISK_RULE_ORDER if rule in matched]


def classify_risk(target: ResolvedTarget, edges: list[dict[str, Any]]) -> tuple[str, list[str], list[str]]:
    matched = _risk_matches(target, edges)
    level = max((RISK_RULES[rule][0] for rule in matched), key=RISK_LEVEL_SCORE.__getitem__)
    reasons = [RISK_RULES[rule][1] for rule in matched]
    return level, matched, reasons


class ImpactAnalyzer:
    @classmethod
    def from_exploratory_sources(cls, sources: dict[str, str], revision: str):
        """Reuse analysis parsers for an isolated, non-handoff source bundle."""
        instance = cls.__new__(cls)
        instance.exploratory = True
        instance.revision = revision
        instance.trusted_ref = 'project-health-local-source'
        instance.manifest = {}
        instance.sources = dict(sources)
        instance.hashes = {path: _sha(text.encode('utf-8')) for path, text in sources.items()}
        identity = _sha(artifact_json_bytes(instance.hashes))
        instance.index = {'index_id': 'exploratory:' + identity,
                          'analysis_config_revision': 'project-health-local-source.v1'}
        instance.index_sha256 = identity
        instance.resolver = TargetResolver(instance.index, instance.sources, instance.hashes,
                                           {'schema_version': 'newrouge.impact-target-aliases.v1',
                                            'alias_table_revision': 'exploratory-empty.v1',
                                            'aliases': {'event': {}, 'contract': {}}},
                                           exploratory=True)
        return instance

    def __init__(self, repository_root: Path, index_path: Path, revision: str, trusted_ref: str | None = None, *, exploratory: bool = False):
        self.exploratory = exploratory
        self.root = repository_root.resolve(); self.revision = revision.lower(); self.trusted_ref = trusted_ref
        try:
            self.index_path = index_path.resolve(); index_bytes = self.index_path.read_bytes()
        except OSError as exc:
            raise ImpactIndexError("missing_index", f"unable to read impact index: {exc}") from exc
        self.index_sha256 = _sha(index_bytes); self.index = validate_index_bytes(index_bytes)
        if self.index["repository_revision"] != self.revision:
            raise ImpactIndexError("revision_mismatch", "index revision differs from requested revision")
        manifest_path = self.index_path.with_name("index-manifest.v1.json")
        if not manifest_path.is_file():
            raise ImpactIndexError("missing_index", "index manifest is missing")
        manifest_bytes = manifest_path.read_bytes(); manifest = validate_manifest_bytes(manifest_bytes, index_bytes=index_bytes, expected_index=self.index)
        if trusted_ref and manifest.get("trusted_ref") != trusted_ref:
            raise ImpactIndexError("revision_mismatch", "trusted ref differs from index manifest")
        self.manifest = manifest
        self.sources: dict[str, str] = {}; self.hashes: dict[str, str] = {}
        snapshot = GitTreeSnapshot(self.root, self.revision, trusted_ref)
        snapshot.verify_worktree(self.index["source_manifest"])
        tree_entries = {entry.path: entry for entry in snapshot.entries}
        for entry in self.index["source_manifest"]:
            if not entry.get("included"): continue
            path = entry["path"]
            try:
                data = snapshot.read_blob(tree_entries[path])
            except Exception as exc: raise ImpactIndexError("source_read_failure", f"unable to read source: {path}") from exc
            digest = _sha(data)
            if digest != entry["sha256"]: raise ImpactIndexError("stale_index", f"source hash differs: {path}")
            self.hashes[path] = digest
            if entry.get("parser_family") != "binary-hash":
                try: self.sources[path] = data.decode("utf-8")
                except UnicodeDecodeError as exc: raise ImpactIndexError("source_read_failure", f"source is not UTF-8: {path}") from exc
        try:
            alias_entry = tree_entries.get("scripts/python/impact_target_aliases.v1.json")
            if alias_entry is None:
                raise FileNotFoundError("alias table blob is missing from trusted tree")
            alias_bytes = snapshot.read_blob(alias_entry)
            aliases = json.loads(alias_bytes.decode("utf-8"))
            validate_aliases(aliases)
            if _sha(alias_bytes) != self.index.get("alias_table_sha256"):
                raise ValueError("alias table hash differs from index")
            if aliases.get("alias_table_revision") != self.index.get("alias_table_revision"):
                raise ValueError("alias table revision differs from index")
        except Exception as exc:
            raise ImpactIndexError("invalid_manifest", f"invalid alias table: {exc}") from exc
        self.resolver = TargetResolver(self.index, self.sources, self.hashes, aliases, exploratory=exploratory)

    def analyze(self, target_input: dict[str, Any] | str, knowledge_binding: dict[str, Any] | None = None, frozen_context: str | None = None, consumer: str | None = None, task_id: str | None = None) -> dict[str, Any]:
        if getattr(self, 'exploratory', False):
            raise ImpactIndexError('unsupported_target', 'Exploratory analyzer cannot produce formal reports')
        report = self._collect(target_input)
        validate_knowledge_binding(knowledge_binding, consumer=consumer, task_id=task_id)
        report["knowledge_binding"] = knowledge_binding
        validate_report_document(report)
        return report

    def explore(self, target_input: dict[str, Any] | str) -> dict[str, Any]:
        """Return investigation evidence that cannot be consumed as a formal handoff."""
        report = self._collect(target_input)
        if hasattr(self, 'resolver'):
            target = self.resolver.resolve(target_input)
            code_edges = [e for e in report['impact_edges'] if e['relation'] != 'binds']
            code_paths = {target.canonical_path, *(e['evidence_path'] for e in code_edges)}
            scenes = {e['evidence_path'] for e in report['runtime_refs']
                      if e['to_kind'] == 'script' and e['to'] in code_paths}
            if target.canonical_path.endswith(('.tscn', '.tres')):
                scenes.add(target.canonical_path)
            runtime = [e for e in report['runtime_refs'] if e['evidence_path'] in scenes]
            report['impact_edges'] = _sort_edges([*code_edges, *runtime])
            report['runtime_refs'] = runtime
            report['affected_files'] = sorted({target.canonical_path, *(e['evidence_path'] for e in report['impact_edges'])})
            risk, rules, reasons = classify_risk(target, report['impact_edges'])
            report.update(risk_level=risk, matched_risk_rules=rules, risk_reasons=reasons)
        report["schema_version"] = "newrouge.project-health-impact-preview.v1"
        report["status"] = "exploratory"
        report["handoff_eligible"] = False
        if hasattr(self, 'resolver'):
            report['skipped_methods'] = self.resolver.symbol_index.skipped_methods
        return report

    def _collect(self, target_input: dict[str, Any] | str) -> dict[str, Any]:
        target = self.resolver.resolve(target_input)
        edges: list[dict[str, Any]] = []
        tests: list[dict[str, Any]] = []
        target_simple = target.identity.rsplit(".", 1)[-1].split("`", 1)[0]
        target_namespace = target.identity.rsplit(".", 1)[0] if "." in target.identity else ""
        simple_candidates = {
            symbol.identity for symbol in self.resolver.symbol_index.symbols
            if symbol.kind == target.kind and symbol.identity.rsplit(".", 1)[-1].split("`", 1)[0] == target_simple
        }
        for path, text in sorted(self.sources.items()):
            if not path.lower().endswith(".cs"): continue
            scan_text = self.resolver.symbol_index.sanitized.get(path, text)
            lines = scan_text.splitlines()
            is_test = _is_test_path(path)
            explicit_test_refs: set[int] = set()
            if is_test:
                original_lines = text.splitlines()
                in_refs = False
                for number, original in enumerate(original_lines, 1):
                    marker = re.search(r"\bRefs\s*:", original, re.I)
                    if marker:
                        in_refs = True
                        remainder = original[marker.end():]
                        if target.identity in remainder or re.search(rf"(?<![A-Za-z0-9_]){re.escape(target_simple)}(?![A-Za-z0-9_])", remainder):
                            explicit_test_refs.add(number)
                        continue
                    if in_refs and original.strip() and not original.lstrip().startswith(("//", "#", "*", "-")):
                        in_refs = False
                    if in_refs and (target.identity in original or target_simple in original):
                        explicit_test_refs.add(number)
            for i, line in enumerate(lines, 1):
                if path == target.canonical_path: continue
                qualified_match = bool(re.search(rf"(?<![A-Za-z0-9_]){re.escape(target.identity)}(?![A-Za-z0-9_])", line))
                path_match = target.canonical_path in line
                simple_match = len(simple_candidates) == 1 and bool(re.search(rf"(?<![A-Za-z0-9_]){re.escape(target_simple)}(?![A-Za-z0-9_])", line))
                token_match = qualified_match or path_match or simple_match
                if is_test and i in explicit_test_refs:
                    token_match = True
                if not token_match and target.identity not in line and target.canonical_path not in line: continue
                digest = self.hashes[path]; anchor = _line_anchor(text, i)
                source_symbol = self.resolver.symbol_index.symbol_at_line(path, i)
                from_kind = "test_symbol" if is_test and source_symbol else ("test_file" if is_test else "file")
                from_id = source_symbol.identity if from_kind == "test_symbol" else path
                if is_test and i in explicit_test_refs:
                    relation = "tests"
                elif target.kind in {"event", "contract"} and re.search(rf"(?:new\s+|[<(]\s*|:\s*){re.escape(target_simple)}\b", line):
                    relation = "consumes"
                    if is_test:
                        continue
                else:
                    relation = "references"
                    if is_test:
                        continue
                    if target.kind in {"event", "contract"}:
                        continue
                to_kind = "symbol" if relation == "tests" else (target.kind if target.kind in {"event", "contract", "symbol"} else "symbol")
                edge = _edge(from_kind, from_id, to_kind, target.identity, relation, path, anchor, digest, indexed_hashes=self.hashes)
                edges.append(edge)
                if relation == "tests":
                    tests.append({"path": path, "target": target.identity, "evidence_path": path, "evidence_anchor": anchor, "evidence_sha256": digest})
            if target_namespace:
                for using_namespace, using_line in self.resolver.symbol_index.usings.get(path, []):
                    if using_namespace == target_namespace and path != target.canonical_path:
                        using_anchor = _line_anchor(text, using_line)
                        edges.append(_edge("file", path, "symbol", target.identity, "references", path, using_anchor, self.hashes[path], indexed_hashes=self.hashes))
            for alias_name, alias_target, alias_line in self.resolver.symbol_index.using_aliases.get(path, []):
                if alias_target == target.identity:
                    edges.append(_edge("file", path, "symbol", target.identity, "references", path, _line_anchor(text, alias_line), self.hashes[path], indexed_hashes=self.hashes))
            if target.kind in {"class", "interface", "contract"}:
                for sym in self.resolver.symbol_index.types_by_path.get(path, []):
                    if sym.identity == target.identity: continue
                    for base in [s for s in self.resolver.symbol_index.symbols if s.kind == "__base__" and s.path == path and s.identity.startswith(sym.identity + "|")]:
                        base_name = base.declaration
                        if base_name == target.identity:
                            rel = "implements" if target.kind in {"interface", "contract"} else "inherits"
                            source_kind = "class" if sym.kind == "contract" else sym.kind
                            edges.append(_edge(source_kind, sym.identity, target.kind, target.identity, rel, path, f"line:{sym.line}-{sym.line}", self.hashes[path], indexed_hashes=self.hashes))
        runtime_edges: list[dict[str, Any]] = []
        bound_scripts = {e["to"] for e in edges if e["relation"] in {"references", "consumes"} and e["to_kind"] in {"symbol", "event", "contract"}}
        for path, text in sorted(self.sources.items()):
            if not path.lower().endswith((".tscn", ".tres")):
                continue
            try:
                parsed = parse_runtime_bindings(path, text, self.hashes, allowed_script_paths=set(self.sources))
            except ValueError as exc:
                raise ImpactIndexError("source_read_failure", f"runtime source parse failed: {path}") from exc
            for item in parsed:
                if item["to_kind"] == "script" and item["to"] not in bound_scripts and target.canonical_path != item["to"]:
                    continue
                runtime_edges.append(item)
        edges.extend(runtime_edges)
        edges = _sort_edges(edges)
        risk, rules, reasons = classify_risk(target, edges)
        affected_files = sorted({target.canonical_path, *(e["evidence_path"] for e in edges)}, key=lambda x: x.encode("utf-8"))
        affected_symbols = sorted({target.identity, *(e["from"] for e in edges if e["from_kind"] in {"class", "interface", "symbol", "method"})}, key=lambda x: x.encode("utf-8"))
        report: dict[str, Any] = {
            "schema_version": REPORT_SCHEMA, "status": "ok", "repository_revision": self.revision,
            "trusted_ref": self.trusted_ref or self.manifest.get("trusted_ref", f"detached:{self.revision}"),
            "index_id": self.index["index_id"], "index_sha256": self.index_sha256,
            "analyzer_implementation_revision": ANALYZER_IMPLEMENTATION_REVISION,
            "analysis_config_revision": self.index["analysis_config_revision"],
            "toolchain": {"python": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"},
            "target": target.as_dict(), "affected_files": affected_files, "affected_symbols": affected_symbols,
            "impact_edges": edges, "tests": sorted(tests, key=lambda x: (x["path"], x["evidence_anchor"])), "runtime_refs": [e for e in edges if e["relation"] == "binds"],
            "knowledge_refs": [e for e in edges if e["relation"] == "documents"], "risk_level": risk,
            "risk_policy_revision": RISK_POLICY_REVISION, "matched_risk_rules": rules, "risk_reasons": reasons,
            "generated_at": _utc(), "failure_reason": None,
        }
        return report


def load_frozen_binding(root: Path, path: str, revision: str, consumer: str | None = None, task_id: str | None = None) -> dict[str, Any]:
    frozen_path = _safe_rel(root, path)
    try: data = frozen_path.read_bytes(); frozen = json.loads(data.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc: raise ImpactIndexError("invalid_kcp_binding", f"unable to read frozen context: {exc}") from exc
    if not isinstance(frozen, dict) or frozen.get("schema_version") != "newrouge.knowledge-frozen-context.v1" or frozen.get("freeze_state") != "frozen":
        raise ImpactIndexError("invalid_kcp_binding", "frozen context is not a valid frozen artifact")
    snap = frozen.get("snapshot") if isinstance(frozen.get("snapshot"), dict) else {}
    if str(snap.get("commit") or "").lower() != revision.lower(): raise ImpactIndexError("revision_mismatch", "frozen context revision differs")
    actual_consumer = consumer or str(frozen.get("consumer") or "")
    if actual_consumer not in {"chapter4", "chapter5", "chapter6", "review"}: raise ImpactIndexError("invalid_kcp_binding", "consumer binding is invalid")
    frozen_task = frozen.get("task_id")
    if consumer and consumer != frozen.get("consumer"): raise ImpactIndexError("invalid_kcp_binding", "consumer mismatch")
    if task_id is not None and task_id != frozen_task: raise ImpactIndexError("invalid_kcp_binding", "task mismatch")
    if actual_consumer in {"chapter4", "chapter5", "chapter6"}:
        task_id = task_id or frozen_task
        if not isinstance(task_id, str) or not task_id.strip(): raise ImpactIndexError("invalid_kcp_binding", "task binding is required")
    # Publication lineage must be explicit; context/source-bundle identifiers are
    # not interchangeable with the published catalog generation or byte hash.
    publication_sha = frozen.get("publication_sha256")
    publication_generation = frozen.get("publication_generation") or frozen.get("generation_id")
    binding = {
        "consumer": actual_consumer, "task_id": None if actual_consumer == "review" else task_id,
        "frozen_context_path": frozen_path.relative_to(root).as_posix(), "frozen_context_sha256": _sha(data),
        "decision_set_sha256": str(frozen.get("decision_set_sha256") or "").removeprefix("sha256:"), "freeze_point": str(frozen.get("freeze_point") or ""),
        "publication_generation": str(publication_generation or ""), "publication_sha256": str(publication_sha or ""),
    }
    if not binding["decision_set_sha256"] or not binding["freeze_point"] or not binding["publication_generation"] or not binding["publication_sha256"]:
        raise ImpactIndexError("invalid_kcp_binding", "frozen context lineage fields are incomplete")
    return binding


def validate_knowledge_binding(binding: dict[str, Any] | None, *, consumer: str | None = None, task_id: str | None = None) -> None:
    if not isinstance(binding, dict):
        raise ImpactIndexError("invalid_kcp_binding", "successful report requires frozen-context knowledge binding")
    required = {"consumer", "task_id", "frozen_context_path", "frozen_context_sha256", "decision_set_sha256", "freeze_point", "publication_generation", "publication_sha256"}
    if set(binding) != required:
        raise ImpactIndexError("invalid_kcp_binding", "knowledge binding fields are invalid")
    actual = binding.get("consumer")
    if actual not in {"chapter4", "chapter5", "chapter6", "review"}:
        raise ImpactIndexError("invalid_kcp_binding", "consumer binding is invalid")
    if consumer and actual != consumer:
        raise ImpactIndexError("invalid_kcp_binding", "consumer binding mismatch")
    if actual == "review":
        if binding.get("task_id") is not None:
            raise ImpactIndexError("invalid_kcp_binding", "review task_id must be null")
    elif not isinstance(binding.get("task_id"), str) or not binding["task_id"].strip():
        raise ImpactIndexError("invalid_kcp_binding", "task binding is required")
    if task_id and binding.get("task_id") != task_id:
        raise ImpactIndexError("invalid_kcp_binding", "task binding mismatch")
    for key in required - {"consumer", "task_id"}:
        if not isinstance(binding.get(key), str) or not binding[key].strip():
            raise ImpactIndexError("invalid_kcp_binding", f"knowledge binding field missing: {key}")
    for key in ("frozen_context_sha256", "decision_set_sha256", "publication_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", binding[key]):
            raise ImpactIndexError("invalid_kcp_binding", f"knowledge binding hash is invalid: {key}")


def validate_report_document(report: dict[str, Any]) -> None:
    required = {"schema_version", "status", "repository_revision", "trusted_ref", "index_id", "index_sha256", "analyzer_implementation_revision", "analysis_config_revision", "toolchain", "target", "affected_files", "affected_symbols", "impact_edges", "tests", "runtime_refs", "knowledge_refs", "risk_level", "risk_policy_revision", "matched_risk_rules", "risk_reasons", "generated_at", "failure_reason", "knowledge_binding"}
    if set(report) != required or report.get("schema_version") != REPORT_SCHEMA or report.get("status") != "ok":
        raise ImpactIndexError("invalid_manifest", "impact report envelope is invalid")
    try:
        if not re.fullmatch(r"[0-9a-f]{40}", str(report["repository_revision"])):
            raise ValueError("repository_revision must be a full lowercase SHA")
        if not isinstance(report["trusted_ref"], str) or not report["trusted_ref"].strip():
            raise ValueError("trusted_ref is required")
        if not re.fullmatch(r"idx-[0-9a-f]{64}", str(report["index_id"])):
            raise ValueError("index_id is invalid")
        for key in ("index_sha256", "target", "analyzer_implementation_revision", "analysis_config_revision", "risk_policy_revision", "generated_at"):
            if key in {"target"}:
                continue
            if not isinstance(report[key], str) or not report[key].strip():
                raise ValueError(f"{key} is required")
        if not re.fullmatch(r"[0-9a-f]{64}", report["index_sha256"]):
            raise ValueError("index_sha256 is invalid")
        toolchain = report["toolchain"]
        if not isinstance(toolchain, dict) or not toolchain or any(not isinstance(key, str) or not isinstance(value, str) or not value.strip() for key, value in toolchain.items()):
            raise ValueError("toolchain is invalid")
        target = report["target"]
        if not isinstance(target, dict) or set(target) != {"kind", "identity", "canonical_path", "source_sha256", "resolution_method"}:
            raise ValueError("target shape is invalid")
        if target["kind"] not in TARGET_KINDS or not all(isinstance(target[key], str) and target[key].strip() for key in target):
            raise ValueError("target values are invalid")
        if not re.fullmatch(r"[0-9a-f]{64}", target["source_sha256"]):
            raise ValueError("target source hash is invalid")
        try:
            target_path = normalize_repository_path(target["canonical_path"])
        except Exception as exc:
            raise ValueError("target canonical path is invalid") from exc
        if target_path != target["canonical_path"]:
            raise ValueError("target canonical path is not normalized")
        for field in ("affected_files", "affected_symbols", "impact_edges", "tests", "runtime_refs", "knowledge_refs", "matched_risk_rules", "risk_reasons"):
            if not isinstance(report[field], list):
                raise ValueError(f"{field} must be an array")
        if report["risk_level"] not in {"high", "medium", "low", "unknown"}:
            raise ValueError("impact report risk level is invalid")
        if report["failure_reason"] is not None:
            raise ValueError("successful report failure_reason must be null")
        if any(not isinstance(path, str) or not path for path in report["affected_files"]):
            raise ValueError("affected_files contains invalid values")
        if report["affected_files"] != sorted(set(report["affected_files"]), key=lambda value: value.encode("utf-8")):
            raise ValueError("affected_files are not canonically ordered")
        if report["affected_symbols"] != sorted(set(report["affected_symbols"]), key=lambda value: value.encode("utf-8")):
            raise ValueError("affected_symbols are not canonically ordered")
        expected = _sort_edges(report["impact_edges"])
        if report["impact_edges"] != expected:
            raise ValueError("impact edges are not canonically ordered")
        edge_keys = {"from", "from_kind", "to", "to_kind", "relation", "evidence_path", "evidence_anchor", "evidence_sha256"}
        for edge in report["impact_edges"]:
            if not isinstance(edge, dict) or set(edge) != edge_keys:
                raise ValueError("impact edge shape is invalid")
            if not isinstance(edge["relation"], str) or edge["relation"] not in RELATIONS:
                raise ValueError("impact edge relation is invalid")
            try:
                _edge(edge["from_kind"], edge["from"], edge["to_kind"], edge["to"], edge["relation"], edge["evidence_path"], edge["evidence_anchor"], edge["evidence_sha256"])
            except ImpactIndexError as exc:
                raise ValueError(str(exc)) from exc
            if edge["evidence_path"] not in report["affected_files"]:
                raise ValueError("edge evidence path is absent from affected_files")
        for item in report["tests"]:
            if not isinstance(item, dict) or set(item) != {"path", "target", "evidence_path", "evidence_anchor", "evidence_sha256"}:
                raise ValueError("test evidence shape is invalid")
            try:
                normalized_test_path = normalize_repository_path(item["path"])
            except Exception as exc:
                raise ValueError("test evidence path is invalid") from exc
            if not isinstance(item["path"], str) or normalized_test_path != item["path"] or item["evidence_path"] != item["path"]:
                raise ValueError("test evidence path is invalid")
            if item["evidence_path"] not in report["affected_files"]:
                raise ValueError("test evidence path is absent from affected_files")
            if item["target"] != target["identity"]:
                raise ValueError("test evidence target is inconsistent")
            _edge("test_symbol", "test", "symbol", item["target"], "tests", item["evidence_path"], item["evidence_anchor"], item["evidence_sha256"])
            if not any(
                edge.get("relation") == "tests"
                and edge.get("to") == item["target"]
                and edge.get("evidence_path") == item["evidence_path"]
                and edge.get("evidence_anchor") == item["evidence_anchor"]
                for edge in report["impact_edges"]
            ):
                raise ValueError("test evidence has no corresponding tests edge")
        for item in report["runtime_refs"] + report["knowledge_refs"]:
            if not isinstance(item, dict) or set(item) != edge_keys:
                raise ValueError("derived evidence shape is invalid")
        expected_runtime = [e for e in report["impact_edges"] if e["relation"] == "binds"]
        if report["runtime_refs"] != expected_runtime:
            raise ValueError("runtime_refs projection is inconsistent")
        if report["knowledge_refs"]:
            raise ValueError("knowledge producer evidence is out of scope")
        if report["matched_risk_rules"] != sorted(set(report["matched_risk_rules"]), key=RISK_RULE_ORDER.index):
            raise ValueError("risk rules are not canonically ordered")
        if len(report["matched_risk_rules"]) != len(report["risk_reasons"]):
            raise ValueError("risk rule and reason lengths differ")
        if any(rule not in RISK_RULES for rule in report["matched_risk_rules"]):
            raise ValueError("unknown risk rule")
        target_value = ResolvedTarget(target["kind"], target["identity"], target["canonical_path"], target["source_sha256"], target["resolution_method"])
        expected_level, expected_rules, expected_reasons = classify_risk(target_value, report["impact_edges"])
        if report["risk_level"] != expected_level or report["matched_risk_rules"] != expected_rules or report["risk_reasons"] != expected_reasons:
            raise ValueError("risk classification is inconsistent")
        validate_knowledge_binding(report["knowledge_binding"])
    except ImpactIndexError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ImpactIndexError("invalid_manifest", f"impact report validation failed: {exc}") from exc


def failure_report(target_input: Any, revision: str | None, reason: ImpactIndexError, index: dict[str, Any] | None = None, index_sha256: str | None = None) -> dict[str, Any]:
    report = {"schema_version": REPORT_SCHEMA, "status": reason.code, "repository_revision": revision or "", "target": target_input if isinstance(target_input, dict) else {"type": "", "id": str(target_input or "")}, "affected_files": [], "affected_symbols": [], "impact_edges": [], "tests": [], "runtime_refs": [], "knowledge_refs": [], "risk_level": "unknown", "risk_policy_revision": RISK_POLICY_REVISION, "matched_risk_rules": ["insufficient-evidence"], "risk_reasons": [reason.reason], "generated_at": _utc(), "failure_reason": {"code": reason.code, "reason": reason.reason}}
    if index: report.update({"index_id": index.get("index_id", ""), "index_sha256": index_sha256 or "", "analyzer_implementation_revision": ANALYZER_IMPLEMENTATION_REVISION, "analysis_config_revision": index.get("analysis_config_revision", "")})
    return report
