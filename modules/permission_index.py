"""
OCI Permission Index — one-time build from policy_reference_scraped.json.

Provides O(1) lookups for:
  * resource name  → set of individual resource types
  * (resource_type, verb) → cumulative permission set
  * permission     → API operations
"""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# OCI verb hierarchy (each level includes all permissions of lower levels)
VERB_HIERARCHY: list[str] = ["inspect", "read", "use", "manage"]
_VERB_RANK: dict[str, int] = {v: i for i, v in enumerate(VERB_HIERARCHY)}

# Known scraping artifacts: services whose individual_resource_types contain
# verb names that should be filtered out.
_VERB_NAMES_SET = frozenset(VERB_HIERARCHY)

_DEFAULT_REF_PATH = Path(__file__).resolve().parent.parent / "data" / "policy_reference_scraped.json"
_DEFAULT_SUPPLEMENT_PATH = Path(__file__).resolve().parent.parent / "data" / "supplemental_resources.json"

# Regex for a valid OCI permission string (UPPER_SNAKE_CASE, possibly with
# embedded lowercase like NFSv3).
_VALID_PERM_RE = re.compile(r"^[A-Z][A-Z0-9_]*(?:[a-z][A-Z0-9_]*)*$")


@dataclass
class PermissionIndex:
    """Pre-computed index for fast OCI permission lookups."""

    # --- core lookup maps --------------------------------------------------

    # Resource name aliases: maps alternate names to canonical names.
    #   "group-membership" → "group-memberships"
    resource_aliases: dict[str, str] = field(default_factory=dict)

    # Resource resolution: any resource name → frozenset of individual types.
    #   "all-resources"      → every known individual type
    #   "api-gateway-family" → {"api-gateways", "api-deployments", …}
    #   "api-gateways"       → {"api-gateways"}
    resource_expand: dict[str, frozenset[str]] = field(default_factory=dict)

    # Cumulative verb→permissions:
    #   ("api-gateways", "manage") → frozenset of ALL permissions (inspect+read+use+manage)
    verb_permissions: dict[tuple[str, str], frozenset[str]] = field(default_factory=dict)

    # Permission → set of API operation names (from apis_fully_covered + apis_partially_covered)
    permission_to_apis: dict[str, set[str]] = field(default_factory=dict)

    # API operation → set of required permission strings
    api_to_permissions: dict[str, set[str]] = field(default_factory=dict)

    # Resource type → list of service ids that declare it
    resource_to_services: dict[str, list[str]] = field(default_factory=dict)

    # --- diagnostics -------------------------------------------------------
    build_warnings: list[str] = field(default_factory=list)

    # --- convenience methods -----------------------------------------------

    def expand_resource(self, resource_name: str) -> frozenset[str]:
        """Resolve *resource_name* to a set of individual resource types.

        Checks aliases first, then falls back to treating the name as a
        single individual type if unknown.
        """
        canonical = self.resource_aliases.get(resource_name, resource_name)
        return self.resource_expand.get(canonical, frozenset({canonical}))

    def get_permissions(self, resource_type: str, verb: str) -> frozenset[str]:
        """Return the *cumulative* permissions for a (resource_type, verb) pair."""
        return self.verb_permissions.get((resource_type, verb), frozenset())

    def get_deny_permissions(self, resource_type: str, verb: str) -> frozenset[str]:
        """Return the permissions that should be denied when *verb* is denied.

        In OCI, denying a verb cascades **upward** through the hierarchy:
        denying ``inspect`` also denies ``read``, ``use``, and ``manage``
        because higher verbs depend on lower ones.  The denied set is the
        union of incremental permissions from the denied verb through
        ``manage``.

        Formally: ``cumulative(manage) - cumulative(verb_below)`` where
        ``verb_below`` is the verb one level below *verb* in the hierarchy.
        For ``inspect`` (the lowest verb) the result equals ``cumulative(manage)``
        — i.e. all permissions for that resource type are denied.
        """
        all_perms = self.verb_permissions.get(
            (resource_type, "manage"), frozenset(),
        )
        rank = _VERB_RANK.get(verb, 0)
        if rank == 0:
            # inspect is the lowest level — deny everything
            return all_perms
        verb_below = VERB_HIERARCHY[rank - 1]
        below_perms = self.verb_permissions.get(
            (resource_type, verb_below), frozenset(),
        )
        return all_perms - below_perms

    def get_apis_for_permissions(self, permissions: set[str] | frozenset[str]) -> set[str]:
        """Given a set of permission strings, return all mapped API operations."""
        apis: set[str] = set()
        for perm in permissions:
            apis.update(self.permission_to_apis.get(perm, set()))
        return apis

    def summary(self) -> str:
        """Return a human-readable build summary."""
        lines = [
            "PermissionIndex build summary",
            f"  resource_expand entries : {len(self.resource_expand)}",
            f"  verb_permissions entries: {len(self.verb_permissions)}",
            f"  unique permissions      : {len({p for ps in self.verb_permissions.values() for p in ps})}",
            f"  permission→api mappings : {len(self.permission_to_apis)}",
            f"  api→permission mappings : {len(self.api_to_permissions)}",
            f"  resource→service entries: {len(self.resource_to_services)}",
            f"  build warnings          : {len(self.build_warnings)}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def _is_valid_permission(s: str) -> bool:
    """Return True if *s* looks like a real OCI permission string.

    Real OCI permissions are UPPER_SNAKE_CASE with at least one underscore
    (e.g. ``API_GATEWAY_CREATE``).  Entries without underscores are either
    garbage (``Note``) or API operation names accidentally in the permission
    field (``CreateApplication``).
    """
    return bool(_VALID_PERM_RE.match(s)) and "_" in s


_KNOWN_NOISE_TOKENS = frozenset({
    "inspect", "read", "use", "manage",
    "inspect +", "read +", "use +", "manage +",
    "-", "\u2013", "\u2014",  # dash, en-dash, em-dash
    ":", "note", "(use both permissions)",
})


def _is_known_noise(raw: str) -> bool:
    """Return True if *raw* is a known scraping artifact that can be silently dropped."""
    s = raw.strip().replace("\u200b", "").lower()
    if s in _KNOWN_NOISE_TOKENS:
        return True
    if s.startswith("inherits from"):
        return True
    if s.startswith("note:") or s.startswith("note :"):
        return True
    # Prose fragments with spaces are clearly not permissions
    if " " in s and not _VALID_PERM_RE.match(s.replace(" ", "")):
        return True
    # Single lowercase words without underscores are prose, not permissions
    if s.isalpha() and s.islower():
        return True
    return False


def _clean_permission(raw: str) -> list[str]:
    """Attempt to clean a raw permission string from scraped data.

    Returns a list of zero or more valid permission strings.  Handles:
    * zero-width spaces (\\u200b)
    * hyphens in otherwise UPPER_SNAKE_CASE strings
    * trailing parenthetical notes, e.g. "PERM_X (optional)"
    * composite entries joined by '+' or ' + '
    * spaces from line-wrap breaks, e.g. "PERM_EVALUAT E"
    """
    # Strip zero-width spaces
    s = raw.replace("\u200b", "")

    # Strip trailing parenthetical notes: "PERM_X (some note)" → "PERM_X"
    s = re.sub(r"\s*\(.*\)\s*$", "", s).strip()

    # Split composite entries ("PERM_A+PERM_B" or "PERM_A + PERM_B")
    parts = re.split(r"\s*\+\s*", s)

    result: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Fix spaces from line-wrap breaks (e.g. "EVALUAT E" → "EVALUATE")
        if " " in part:
            joined = part.replace(" ", "")
            if _is_valid_permission(joined):
                result.append(joined)
                continue

        # Fix hyphens in permission-like strings (e.g. DATAFLOW-SQLENDPOINT_X)
        if "-" in part:
            fixed = part.replace("-", "_")
            if _is_valid_permission(fixed):
                result.append(fixed)
                continue

        # If it matches as-is, keep it
        if _is_valid_permission(part):
            result.append(part)

    return result


def _load_reference(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _is_scraping_artifact(resource_type: str) -> bool:
    """Return True if *resource_type* looks like a verb name accidentally
    scraped as a resource type."""
    return resource_type.lower() in _VERB_NAMES_SET


def build_index(
    reference_path: str | Path | None = None,
    supplement_path: str | Path | None = None,
) -> PermissionIndex:
    """Build a :class:`PermissionIndex` from the scraped policy reference JSON.

    Parameters
    ----------
    reference_path:
        Path to ``policy_reference_scraped.json``.  Defaults to
        ``<project>/data/policy_reference_scraped.json``.
    supplement_path:
        Path to ``supplemental_resources.json``.  If the file exists, its
        services are appended to the reference data and its aliases are
        registered.  Defaults to ``<project>/data/supplemental_resources.json``.
    """
    if reference_path is None:
        reference_path = _DEFAULT_REF_PATH
    if supplement_path is None:
        supplement_path = _DEFAULT_SUPPLEMENT_PATH
    ref = _load_reference(reference_path)

    # Merge supplemental resource definitions if file exists
    resource_aliases: dict[str, str] = {}
    supplement_file = Path(supplement_path)
    if supplement_file.exists():
        supplement = _load_reference(supplement_file)
        resource_aliases = supplement.get("aliases", {})
        ref_services = ref.setdefault("services", [])
        for svc in supplement.get("services", []):
            ref_services.append(svc)
        logger.info(
            "Loaded supplement: %d aliases, %d services",
            len(resource_aliases), len(supplement.get("services", [])),
        )

    warnings: list[str] = []

    # ----- phase 1: collect raw data per service ---------------------------
    # Per-resource-type, per-verb raw (non-cumulative) permission sets
    # Key: (individual_resource_type, verb) → set[str]
    raw_perms: dict[tuple[str, str], set[str]] = defaultdict(set)

    # resource_expand: name → set of individual types
    resource_expand: dict[str, set[str]] = {}

    # resource → service ids
    resource_to_services: dict[str, list[str]] = defaultdict(list)

    # permission → api ops  &  api op → permissions
    perm_to_apis: dict[str, set[str]] = defaultdict(set)
    api_to_perms: dict[str, set[str]] = defaultdict(set)

    all_individual_types: set[str] = set()

    for svc in ref.get("services", []):
        svc_id: str = svc.get("id", "<unknown>")

        # --- individual & aggregate resource types -------------------------
        raw_individual: list[str] = svc.get("individual_resource_types", [])
        aggregates: list[str] = svc.get("aggregate_resource_types", [])

        # Filter scraping artifacts (verb names appearing as resource types)
        individual = [rt for rt in raw_individual if not _is_scraping_artifact(rt)]
        n_filtered = len(raw_individual) - len(individual)
        if n_filtered:
            warnings.append(
                f"Service '{svc_id}': filtered {n_filtered} scraping-artifact "
                f"resource types: {[rt for rt in raw_individual if _is_scraping_artifact(rt)]}"
            )

        all_individual_types.update(individual)

        # Collect the set of resource types that have their own VRP entries.
        # Aggregates WITH VRP entries (e.g. "instances", "drgs") have their
        # own specific permissions and must NOT be expanded to all individual
        # types.  Only pure family aggregates (no VRP entries, e.g.
        # "instance-family") should expand.
        vrp_list: list[dict] = svc.get("verb_resource_permissions", [])
        vrp_resource_types: set[str] = {
            e.get("resource_type", "").strip()
            for e in vrp_list
            if e.get("resource_type", "").strip()
        }

        # Register individual types → themselves
        for rt in individual:
            resource_expand.setdefault(rt, set()).add(rt)
            resource_to_services[rt].append(svc_id)

        # Register aggregate types
        for agg in aggregates:
            if agg in vrp_resource_types:
                # Aggregate has its own VRP entries → map to itself only
                resource_expand.setdefault(agg, set()).add(agg)
            else:
                # Pure family aggregate (no VRP) → expand to all individual types
                resource_expand.setdefault(agg, set()).update(individual)
            resource_to_services[agg].append(svc_id)

        # --- verb_resource_permissions ------------------------------------
        if not vrp_list:
            if individual or aggregates:
                logger.debug(
                    "Service '%s': has resource types but no verb_resource_permissions",
                    svc_id,
                )
            continue

        for entry in vrp_list:
            rt: str = entry.get("resource_type", "").strip()
            verb: str = entry.get("verb", "").strip().lower()
            raw_perms_list: list[str] = entry.get("permissions", [])

            # Pre-process: rejoin fragments broken by line wraps
            # e.g. ["FOO_BAR", "_INSPECT"] → ["FOO_BAR_INSPECT"]
            rejoined_perms: list[str] = []
            for raw_p in raw_perms_list:
                if raw_p.startswith("_") and rejoined_perms:
                    rejoined_perms[-1] = rejoined_perms[-1] + raw_p
                else:
                    rejoined_perms.append(raw_p)

            # Clean permission strings (fix scraping artifacts)
            perms: list[str] = []
            for raw_p in rejoined_perms:
                cleaned = _clean_permission(raw_p)
                if cleaned:
                    perms.extend(cleaned)
                elif not _is_known_noise(raw_p):
                    warnings.append(
                        f"Service '{svc_id}': dropped invalid permission string: {raw_p!r}"
                    )

            if verb not in _VERB_RANK:
                # Handle compound verbs like "read, use" by splitting
                # and processing each sub-verb separately.
                sub_verbs = [
                    v.strip() for v in verb.split(",")
                    if v.strip() in _VERB_RANK
                ]
                if sub_verbs:
                    for sv in sub_verbs:
                        target_types_sv = [rt] if rt else (individual or [f"_svc:{svc_id}"])
                        for target_rt in target_types_sv:
                            raw_perms[(target_rt, sv)].update(perms)
                        for perm in perms:
                            for api_op in entry.get("apis_fully_covered", []):
                                perm_to_apis[perm].add(api_op)
                                api_to_perms[api_op].add(perm)
                            for api_op in entry.get("apis_partially_covered", []):
                                perm_to_apis[perm].add(api_op)
                                api_to_perms[api_op].add(perm)
                    continue
                warnings.append(
                    f"Service '{svc_id}': unknown verb '{verb}' in verb_resource_permissions"
                )
                continue

            # Determine target resource types for this entry
            if rt:
                # Explicit resource type
                target_types = [rt]
            elif individual:
                # Empty resource_type → apply to all individual types of this service
                target_types = individual
            else:
                # No individual types and no resource_type — record under service id
                # as a pseudo-resource so the data isn't lost
                target_types = [f"_svc:{svc_id}"]
                warnings.append(
                    f"Service '{svc_id}': vrp with empty resource_type and no individual "
                    f"resource types; mapped to pseudo-resource '_svc:{svc_id}'"
                )

            for target_rt in target_types:
                raw_perms[(target_rt, verb)].update(perms)

            # Map permissions ↔ API operations from this vrp entry
            for perm in perms:
                for api_op in entry.get("apis_fully_covered", []):
                    perm_to_apis[perm].add(api_op)
                    api_to_perms[api_op].add(perm)
                for api_op in entry.get("apis_partially_covered", []):
                    perm_to_apis[perm].add(api_op)
                    api_to_perms[api_op].add(perm)

        # --- api_permissions (per-API operation → permission) -------------
        for ap in svc.get("api_permissions", []):
            api_op = ap.get("api_operation", "").strip()
            perm_req_raw = ap.get("permissions_required", "").strip()
            if not api_op or not perm_req_raw:
                continue
            for perm_req in _clean_permission(perm_req_raw):
                api_to_perms[api_op].add(perm_req)
                perm_to_apis[perm_req].add(api_op)

    # ----- phase 2: build cumulative verb_permissions ----------------------
    # For each (resource_type, verb), the cumulative set = union of all
    # raw permissions at that verb level and every lower level.
    verb_permissions: dict[tuple[str, str], frozenset[str]] = {}

    # Collect all resource types that appear in raw_perms
    seen_resource_types: set[str] = {rt for (rt, _v) in raw_perms}

    for rt in seen_resource_types:
        cumulative: set[str] = set()
        for verb in VERB_HIERARCHY:
            level_perms = raw_perms.get((rt, verb), set())
            cumulative = cumulative | level_perms
            if cumulative:
                verb_permissions[(rt, verb)] = frozenset(cumulative)

    # ----- phase 3: add "all-resources" to resource_expand -----------------
    resource_expand["all-resources"] = set(all_individual_types)

    # ----- phase 4: freeze mutable sets in resource_expand -----------------
    frozen_expand: dict[str, frozenset[str]] = {
        name: frozenset(types) for name, types in resource_expand.items()
    }

    # ----- assemble the index ---------------------------------------------
    index = PermissionIndex(
        resource_aliases=resource_aliases,
        resource_expand=frozen_expand,
        verb_permissions=verb_permissions,
        permission_to_apis=dict(perm_to_apis),
        api_to_permissions=dict(api_to_perms),
        resource_to_services=dict(resource_to_services),
        build_warnings=warnings,
    )

    logger.info("PermissionIndex built:\n%s", index.summary())
    return index
