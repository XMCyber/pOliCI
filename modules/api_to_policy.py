"""
API-to-Policy resolver.

Given a list of OCI API operation names, determines the minimal set of
OCI policy statements (expressed as verb + resource-type pairs) needed
to grant all the permissions those APIs require, and outputs the result
as an AWS IAM-style JSON policy document.

Conditional / situational permissions are emitted as human-readable
notes **outside** the generated policy so operators can decide whether
they apply.
"""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from modules.permission_index import (
    PermissionIndex,
    build_index,
    VERB_HIERARCHY,
)

logger = logging.getLogger(__name__)

_VERB_RANK: dict[str, int] = {v: i for i, v in enumerate(VERB_HIERARCHY)}

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_API_PERMS_PATH = _PROJECT_ROOT / "data" / "api_operation_permissions.json"
_REF_PATH = _PROJECT_ROOT / "data" / "policy_reference_scraped.json"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ApiLookupResult:
    """Result of resolving a single API operation."""

    api_name: str
    found: bool = False
    base_permissions: list[str] = field(default_factory=list)
    conditional_permissions: list[str] = field(default_factory=list)
    conditional_note: str | None = None
    service_name: str = ""
    service_id: str = ""
    ambiguous_services: list[str] = field(default_factory=list)
    ambiguous_service_ids: list[str] = field(default_factory=list)


@dataclass
class PolicyStatement:
    """A single minimal OCI policy statement."""

    resource_type: str
    verb: str
    permissions_covered: frozenset[str] = frozenset()


@dataclass
class ConditionalNote:
    """A note about a conditionally required permission."""

    api_operation: str
    conditional_permissions: list[str]
    note: str
    service_name: str = ""


@dataclass
class ResolveResult:
    """Complete result of the API-to-policy resolution."""

    api_lookups: list[ApiLookupResult]
    all_base_permissions: set[str]
    policy_statements: list[PolicyStatement]
    conditional_notes: list[ConditionalNote]
    unresolved_permissions: set[str]
    not_found_apis: list[str]


# ---------------------------------------------------------------------------
# Raw permission text parsing
# ---------------------------------------------------------------------------

_UPPER_SNAKE_RE = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b")

# Matches a broken permission where a linebreak inserted a space before
# the trailing fragment, e.g. "NETWORK_SECURITY_GROUP _UPDATE_MEMBERS"
# or "PRIVATE _IP_CREATE".
_BROKEN_PERM_RE = re.compile(
    r"([A-Z][A-Z0-9_]*[A-Z0-9])\s+(_[A-Z][A-Z0-9_]*)"
)

# Sentence-level conditional start: "If <word>…" or "also need" etc.
# After collapsing newlines to spaces, these appear as mid-text clauses.
# We match "If" preceded by whitespace (or start of string) when followed
# by a non-permission word (lowercase, indicating natural language).
_CONDITIONAL_CLAUSE_RE = re.compile(
    r"(?:^|\s)"
    r"(?:If\s+(?![A-Z]{2,}_)|When\s+(?![A-Z]{2,}_)|[Aa]lso\s+need)",
)


def _rejoin_broken_permissions(text: str) -> str:
    """Fix permissions split across line breaks.

    E.g. ``"NETWORK_SECURITY_GROUP \\n_UPDATE_MEMBERS"`` →
    ``"NETWORK_SECURITY_GROUP_UPDATE_MEMBERS"``.
    """
    # First collapse newlines to spaces
    text = text.replace("\n", " ")
    # Then rejoin fragments like "FOO _BAR" → "FOO_BAR"
    while _BROKEN_PERM_RE.search(text):
        text = _BROKEN_PERM_RE.sub(r"\1\2", text)
    return text


def _extract_all_permissions(text: str) -> list[str]:
    """Extract all UPPER_SNAKE_CASE permission tokens from *text*."""
    text = text.replace("\u200b", "")
    text = _rejoin_broken_permissions(text)
    return _UPPER_SNAKE_RE.findall(text)


def _has_conditional_language(text: str) -> bool:
    """Return True if *text* contains conditional / situational language."""
    patterns = [
        r"\(\s*(?:if|when|for|Use|in|both|new|old)\b",
        r"\bIf\s+(?:creating|deleting|updating|listing|moving|using|writing|putting)\b",
        r"\bwhen\b.*\bas\b",
        r"\bor\b.*\bwhen\b",
        r"\balso\s+need\b",
        r"\bUse\b.*\bwhen\b",
    ]
    return any(re.search(p, text) for p in patterns)


def _find_conditional_boundary(text: str) -> int:
    """Return the character offset where conditional text starts, or -1.

    Looks for parenthetical conditions ``(if …)`` **and** sentence-level
    conditions like ``If putting …``, ``also need …``.
    """
    paren = text.find("(")

    # Look for sentence-level conditional keywords
    clause_match = _CONDITIONAL_CLAUSE_RE.search(text)
    clause_pos = clause_match.start() if clause_match else -1

    if paren > 0 and clause_pos > 0:
        return min(paren, clause_pos)
    if paren > 0:
        return paren
    if clause_pos > 0:
        return clause_pos
    return -1


def _parse_raw_permissions(
    raw: str,
) -> tuple[list[str], list[str], str | None]:
    """Parse a raw permission string into (base, conditional, note).

    Parameters
    ----------
    raw:
        The ``permissions_required_raw`` value from the API permissions JSON.

    Returns
    -------
    (base_permissions, conditional_permissions, note_or_None)
        *base_permissions* are always required.
        *conditional_permissions* are only needed in certain situations.
        *note* is the full human-readable text when conditions exist.
    """
    if not raw or raw.strip().lower().startswith("(no permissions"):
        return [], [], None

    text = _rejoin_broken_permissions(raw)
    text = re.sub(r"\s{2,}", " ", text).strip()

    all_perms = _extract_all_permissions(text)
    if not all_perms:
        return [], [], None

    if not _has_conditional_language(text):
        return all_perms, [], None

    # Find where the conditional section starts
    boundary = _find_conditional_boundary(text)
    if boundary > 0:
        before = text[:boundary]
        base_perms = _extract_all_permissions(before)
        base_set = set(base_perms)
        conditional_perms = [p for p in all_perms if p not in base_set]
    else:
        # No clear boundary — treat the first permission as base
        base_perms = all_perms[:1]
        conditional_perms = all_perms[1:]

    # Every API needs at least one base permission
    if not base_perms and conditional_perms:
        base_perms = [conditional_perms.pop(0)]

    return base_perms, conditional_perms, text


# ---------------------------------------------------------------------------
# Loading the API operation ↔ permissions database
# ---------------------------------------------------------------------------

def _load_api_permissions(
    path: Path | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Load ``api_operation_permissions.json``.

    Returns a dict mapping **lowercased** API operation name → list of
    entries (multiple entries arise when different services expose the
    same-named API, e.g. ``GetWorkRequest``).
    """
    if path is None:
        path = _API_PERMS_PATH
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in data.get("entries", []):
        api_name = entry.get("api_operation", "").strip()
        if api_name:
            result[api_name.lower()].append(entry)
    return dict(result)


# ---------------------------------------------------------------------------
# Reverse index: permission → minimal (resource_type, verb)
# ---------------------------------------------------------------------------

def _build_reverse_index(
    index: PermissionIndex,
) -> dict[str, list[tuple[str, str, int]]]:
    """permission → [(resource_type, verb, verb_rank)].

    For each permission, lists the (resource_type, verb) pairs that
    grant it.  Only the **minimum** verb per resource_type is kept.
    """
    perm_rt: dict[str, dict[str, tuple[str, int]]] = defaultdict(dict)

    for (rt, verb), perms in index.verb_permissions.items():
        rank = _VERB_RANK.get(verb, 99)
        for perm in perms:
            existing = perm_rt[perm].get(rt)
            if existing is None or rank < existing[1]:
                perm_rt[perm][rt] = (verb, rank)

    result: dict[str, list[tuple[str, str, int]]] = {}
    for perm, rt_map in perm_rt.items():
        result[perm] = [
            (rt, verb, rank) for rt, (verb, rank) in rt_map.items()
        ]
    return result


# ---------------------------------------------------------------------------
# Greedy set-cover for minimal (resource_type, verb) policy
# ---------------------------------------------------------------------------

def _compute_minimal_policy(
    required_permissions: set[str],
    reverse_index: dict[str, list[tuple[str, str, int]]],
) -> tuple[list[PolicyStatement], set[str]]:
    """Greedy set-cover to find the fewest (resource_type, verb) pairs
    that collectively grant all *required_permissions*.

    Returns (statements, unresolved_permissions).
    """
    if not required_permissions:
        return [], set()

    # For each resource_type, record which required permissions it can
    # cover and at what minimum verb level.
    rt_perm_verb: dict[str, dict[str, int]] = defaultdict(dict)
    resolvable: set[str] = set()

    for perm in required_permissions:
        candidates = reverse_index.get(perm, [])
        if candidates:
            resolvable.add(perm)
            for rt, _verb, rank in candidates:
                existing = rt_perm_verb[rt].get(perm)
                if existing is None or rank < existing:
                    rt_perm_verb[rt][perm] = rank

    unresolved = required_permissions - resolvable
    remaining = set(resolvable)
    statements: list[PolicyStatement] = []

    while remaining:
        best_rt: str | None = None
        best_verb = ""
        best_rank = 999
        best_covered: frozenset[str] = frozenset()

        for rt, perm_rank_map in rt_perm_verb.items():
            covered = frozenset(remaining & set(perm_rank_map))
            if not covered:
                continue

            max_rank = max(perm_rank_map[p] for p in covered)
            verb = VERB_HIERARCHY[max_rank] if max_rank < len(VERB_HIERARCHY) else "manage"

            # Prefer: (1) most permissions covered, (2) lowest verb
            if (len(covered) > len(best_covered)) or (
                len(covered) == len(best_covered) and max_rank < best_rank
            ):
                best_rt = rt
                best_verb = verb
                best_rank = max_rank
                best_covered = covered

        if best_rt is None:
            unresolved |= remaining
            break

        statements.append(
            PolicyStatement(
                resource_type=best_rt,
                verb=best_verb,
                permissions_covered=best_covered,
            )
        )
        remaining -= best_covered

    # Sort by resource type for deterministic output
    statements.sort(key=lambda s: (s.resource_type, _VERB_RANK.get(s.verb, 99)))
    return statements, unresolved


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _parse_qualified_name(raw: str) -> tuple[str | None, str]:
    """Parse an optionally service-qualified API name.

    Supports ``service_id.ApiName`` (e.g. ``file_storage.GetWorkRequest``).
    The service qualifier is matched as a **substring** of the
    ``service_id`` field so users don't need the full verbose id.

    Returns ``(service_filter, api_name)`` where *service_filter* is
    ``None`` when no qualifier was given.
    """
    raw = raw.strip()
    # Split on the LAST dot so that service ids containing dots still work.
    # API names are PascalCase and never contain dots, so the last dot is
    # always the separator.
    if "." in raw:
        qualifier, _, api = raw.rpartition(".")
        return qualifier.strip().lower(), api.strip()
    return None, raw


def _filter_entries_by_service(
    entries: list[dict[str, Any]],
    service_filter: str,
) -> list[dict[str, Any]]:
    """Return only entries whose ``service_id`` contains *service_filter*."""
    return [
        e for e in entries
        if service_filter in e.get("service_id", "").lower()
    ]


def resolve_apis_to_policy(
    api_names: list[str],
    index: PermissionIndex | None = None,
    api_perms_path: Path | None = None,
    ref_path: Path | None = None,
) -> ResolveResult:
    """Resolve a list of API operation names to a minimal OCI policy.

    Parameters
    ----------
    api_names:
        API operation names, optionally service-qualified with a dot
        prefix — e.g. ``["LaunchInstance", "file_storage.GetWorkRequest"]``.
        The service qualifier is substring-matched against the
        ``service_id`` field to disambiguate APIs that exist across
        multiple services.
    index:
        Pre-built :class:`PermissionIndex`.  Built automatically if not
        provided.
    api_perms_path:
        Path to ``api_operation_permissions.json``.
    ref_path:
        Path to ``policy_reference_scraped.json``.
    """
    if index is None:
        index = build_index(ref_path or _REF_PATH)

    api_db = _load_api_permissions(api_perms_path)
    reverse_index = _build_reverse_index(index)

    lookups: list[ApiLookupResult] = []
    all_base: set[str] = set()
    cond_notes: list[ConditionalNote] = []
    not_found: list[str] = []

    for api_name in api_names:
        service_filter, bare_name = _parse_qualified_name(api_name)
        display_name = api_name.strip()
        key = bare_name.lower()
        entries = api_db.get(key, [])

        # If a service qualifier was given, narrow the entries
        if service_filter and entries:
            entries = _filter_entries_by_service(entries, service_filter)

        # ---- not in api_operation_permissions.json → try the index --------
        if not entries:
            idx_perms: set[str] | None = None
            for idx_api, idx_p in index.api_to_permissions.items():
                if idx_api.lower() == key:
                    idx_perms = idx_p
                    break

            if idx_perms:
                lookups.append(
                    ApiLookupResult(
                        api_name=display_name,
                        found=True,
                        base_permissions=sorted(idx_perms),
                    )
                )
                all_base.update(idx_perms)
            else:
                lookups.append(ApiLookupResult(api_name=display_name, found=False))
                not_found.append(display_name)
            continue

        # ---- found one or more entries ------------------------------------
        # Aggregate across services that expose the same API name.
        combined_base: list[str] = []
        combined_cond: list[str] = []
        combined_note: str | None = None
        svc_names: list[str] = []
        svc_ids: list[str] = []
        first_svc_name = ""
        first_svc_id = ""

        for entry in entries:
            raw = entry.get("permissions_required_raw", "")
            base, cond, note = _parse_raw_permissions(raw)

            # The pre-parsed permissions_required list is just the raw
            # text split by newlines and may contain broken fragments
            # (e.g. "NETWORK_SECURITY_GROUP" as a fragment of
            # "NETWORK_SECURITY_GROUP_UPDATE_MEMBERS").  Only merge
            # items that are NOT a strict prefix of an already-known
            # permission from the raw parse.
            known = set(base) | set(cond)
            for p in entry.get("permissions_required", []):
                clean = p.strip().replace("\u200b", "")
                if not (_UPPER_SNAKE_RE.fullmatch(clean) and "_" in clean):
                    continue
                if clean in known:
                    continue
                # Skip if it's a prefix fragment of a known permission
                if any(k.startswith(clean + "_") for k in known):
                    continue
                base.append(clean)
                known.add(clean)

            # Also incorporate the index's api→permissions mapping
            for idx_api, idx_p in index.api_to_permissions.items():
                if idx_api.lower() == key:
                    for p in idx_p:
                        if p not in known:
                            base.append(p)
                            known.add(p)
                    break

            combined_base.extend(base)
            combined_cond.extend(cond)
            if note:
                combined_note = note

            svc_name = entry.get("service_name", "")
            svc_id = entry.get("service_id", "")
            svc_names.append(svc_name)
            svc_ids.append(svc_id)
            if not first_svc_name:
                first_svc_name = svc_name
                first_svc_id = svc_id

        # Deduplicate while preserving order
        seen: set[str] = set()
        dedup_base: list[str] = []
        for p in combined_base:
            if p not in seen:
                seen.add(p)
                dedup_base.append(p)
        dedup_cond: list[str] = []
        for p in combined_cond:
            if p not in seen:
                seen.add(p)
                dedup_cond.append(p)

        unique_svc_names = sorted(set(svc_names))
        unique_svc_ids = sorted(set(svc_ids))
        ambiguous = unique_svc_names if len(unique_svc_names) > 1 else []
        ambiguous_ids = unique_svc_ids if len(unique_svc_ids) > 1 else []

        lookups.append(
            ApiLookupResult(
                api_name=display_name,
                found=True,
                base_permissions=dedup_base,
                conditional_permissions=dedup_cond,
                conditional_note=combined_note,
                service_name=first_svc_name,
                service_id=first_svc_id,
                ambiguous_services=ambiguous,
                ambiguous_service_ids=ambiguous_ids,
            )
        )

        all_base.update(dedup_base)

        if dedup_cond and combined_note:
            cond_notes.append(
                ConditionalNote(
                    api_operation=display_name,
                    conditional_permissions=dedup_cond,
                    note=combined_note,
                    service_name=first_svc_name,
                )
            )

    # ---- compute minimal policy -------------------------------------------
    statements, unresolved = _compute_minimal_policy(all_base, reverse_index)

    return ResolveResult(
        api_lookups=lookups,
        all_base_permissions=all_base,
        policy_statements=statements,
        conditional_notes=cond_notes,
        unresolved_permissions=unresolved,
        not_found_apis=not_found,
    )


# ---------------------------------------------------------------------------
# AWS IAM-style output
# ---------------------------------------------------------------------------

def result_to_iam_policy(result: ResolveResult) -> dict[str, Any]:
    """Convert a :class:`ResolveResult` to an AWS IAM-style policy document.

    The ``Statement`` array contains one entry per minimal policy
    statement (resource-type + verb combination).

    Conditional notes, unresolved permissions, and not-found APIs are
    placed in top-level keys **outside** the ``Statement`` array.
    """
    statements: list[dict[str, Any]] = []
    for i, stmt in enumerate(result.policy_statements, 1):
        iam_stmt: dict[str, Any] = {
            "Sid": f"oci-{i}-{stmt.verb}-{stmt.resource_type}",
            "Effect": "Allow",
            "Action": sorted(stmt.permissions_covered),
            "Resource": f"oci:{stmt.resource_type}",
        }
        statements.append(iam_stmt)

    doc: dict[str, Any] = {
        "Version": "oci-policy-v1",
        "GeneratedAt": datetime.now(timezone.utc).isoformat(),
        "Statement": statements,
    }

    # OCI policy equivalents as a human-friendly reference
    doc["OciPolicyStatements"] = [
        f"Allow {{subject}} to {stmt.verb} {stmt.resource_type} in {{compartment}}"
        for stmt in result.policy_statements
    ]

    # ---- notes (outside the policy) ----------------------------------------
    if result.conditional_notes:
        doc["ConditionalNotes"] = [
            {
                "ApiOperation": cn.api_operation,
                "AdditionalPermissions": cn.conditional_permissions,
                "Note": cn.note,
                "Service": cn.service_name,
            }
            for cn in result.conditional_notes
        ]

    if result.unresolved_permissions:
        doc["UnresolvedPermissions"] = sorted(result.unresolved_permissions)

    if result.not_found_apis:
        doc["NotFoundApis"] = result.not_found_apis

    return doc


def result_to_iam_policy_json(
    result: ResolveResult,
    indent: int = 2,
) -> str:
    """Return the IAM-like policy document as a formatted JSON string."""
    return json.dumps(result_to_iam_policy(result), indent=indent)


# ---------------------------------------------------------------------------
# Human-readable console output
# ---------------------------------------------------------------------------

def print_result(result: ResolveResult) -> None:
    """Pretty-print a :class:`ResolveResult` to stdout."""
    print()

    # ---- per-API lookup results -------------------------------------------
    print("API Operation Lookup Results")
    print("-" * 60)
    for lk in result.api_lookups:
        status = "OK" if lk.found else "NOT FOUND"
        print(f"  {lk.api_name:<45} [{status}]")
        if lk.found:
            if lk.base_permissions:
                print(f"    base permissions: {', '.join(lk.base_permissions)}")
            if lk.conditional_permissions:
                print(f"    conditional    : {', '.join(lk.conditional_permissions)}")
            if lk.ambiguous_services:
                bare = lk.api_name.rpartition(".")[-1] or lk.api_name
                print(f"    (ambiguous across {len(lk.ambiguous_services)} services — "
                      f"use service_id.{bare} to disambiguate, e.g. "
                      f"{lk.ambiguous_service_ids[0]}.{bare})")
                for sid in lk.ambiguous_service_ids:
                    print(f"      - {sid}")
    print()

    # ---- minimal policy ---------------------------------------------------
    print("Minimal OCI Policy Statements")
    print("-" * 60)
    if not result.policy_statements:
        print("  (none)")
    for i, stmt in enumerate(result.policy_statements, 1):
        print(f"  {i}. Allow {{subject}} to {stmt.verb} {stmt.resource_type} "
              f"in {{compartment}}")
        print(f"     covers {len(stmt.permissions_covered)} permission(s): "
              f"{', '.join(sorted(stmt.permissions_covered))}")
    print()

    # ---- conditional notes ------------------------------------------------
    if result.conditional_notes:
        print("Conditional Notes (not included in the policy above)")
        print("-" * 60)
        for cn in result.conditional_notes:
            print(f"  {cn.api_operation}:")
            print(f"    additional permissions: {', '.join(cn.conditional_permissions)}")
            print(f"    note: {cn.note}")
        print()

    # ---- unresolved / not found -------------------------------------------
    if result.unresolved_permissions:
        print("Unresolved Permissions (no matching resource-type/verb found)")
        print("-" * 60)
        for p in sorted(result.unresolved_permissions):
            print(f"  - {p}")
        print()

    if result.not_found_apis:
        print("Not Found APIs")
        print("-" * 60)
        for api in result.not_found_apis:
            print(f"  - {api}")
        print()
