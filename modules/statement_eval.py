"""
OCI policy statement evaluator.

Converts a parsed OCI policy statement (dict from policy_parser) into a
:class:`PermissionGrant` that enumerates every concrete permission the
statement confers (or denies), along with scope and conditions.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from modules.permission_index import PermissionIndex

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PermissionGrant:
    """A single, fully-expanded permission grant (or denial).

    Every field is immutable so grants can be stored in sets and used as
    dict keys when needed.
    """

    effect: str                       # "Allow" | "Deny" | "Endorse" | "Admit"
    principal_type: str               # "group" | "dynamic-group" | "any-user" | "any-group"
    principals: tuple[str, ...]       # ("NetworkAdmins",) or ("ocid1.group…",)
    permissions: frozenset[str]       # flat expanded permission strings
    api_operations: frozenset[str]    # API ops these permissions map to
    resource_types: frozenset[str]    # individual resource types covered
    compartment: str                  # "tenancy" | compartment path | "any-tenancy"
    location_type: str                # "tenancy" | "compartment" | "any-tenancy"
    conditions: tuple[str, ...]       # raw condition expressions
    condition_selector: str           # "" | "all" | "any"
    source_statement: dict = field(hash=False, compare=False)  # original parsed dict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CONDITION_SPLIT_RE = re.compile(r",(?![^{]*})")  # split on commas outside braces

# Pattern for parsing a single condition expression into (variable, operator, value).
_COND_PARSE_RE = re.compile(
    r"""
    ^\s*
    (?P<var>[A-Za-z_.]+(?:\.[A-Za-z_.*-]+)*)   # variable path
    \s*
    (?P<op>!=|=)\s*                             # operator
    (?P<val>.+?)                                # value (quoted string or /regex/)
    \s*$
    """,
    re.VERBOSE,
)


def _extract_conditions(parsed: dict[str, Any]) -> tuple[tuple[str, ...], str]:
    """Return (condition_strings, selector) from a parsed statement dict."""
    raw = parsed.get("condition", "")
    selector = parsed.get("condition_selector", "")

    if not raw:
        return (), selector

    # Conditions may be wrapped in { … }
    raw = raw.strip()
    if raw.startswith("{") and raw.endswith("}"):
        raw = raw[1:-1].strip()

    # Split on commas (but not inside nested braces / quotes)
    parts = [c.strip() for c in _CONDITION_SPLIT_RE.split(raw) if c.strip()]
    return tuple(parts), selector


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Convert an OCI glob/fnmatch pattern to a compiled regex.

    OCI uses ``*`` as a wildcard (like fnmatch).
    """
    # Escape everything except *, then replace * with .*
    regex = re.escape(pattern).replace(r"\*", ".*")
    return re.compile(f"^{regex}$")


def _apply_permission_conditions(
    permissions: set[str],
    conditions: tuple[str, ...],
    selector: str,
) -> tuple[set[str], tuple[str, ...]]:
    """Statically evaluate ``request.permission`` conditions against the
    expanded permission set.

    ``request.permission`` is the specific permission being checked at
    request time.  Since we know the full set of permissions a statement
    grants, we can filter the set now instead of deferring to runtime.

    Parameters
    ----------
    permissions:
        The expanded permission set to filter.
    conditions:
        All condition expressions for this statement.
    selector:
        ``"all"`` (AND) or ``"any"`` (OR) or ``""`` (single condition).

    Returns
    -------
    (filtered_permissions, remaining_conditions)
        The permission set after applying ``request.permission`` filters,
        and the conditions that were NOT about ``request.permission``
        (which must still be evaluated at runtime).
    """
    perm_conditions: list[tuple[str, str, str]] = []   # (op, raw_val, cleaned_val)
    remaining: list[str] = []

    for cond in conditions:
        m = _COND_PARSE_RE.match(cond)
        if m and m.group("var").lower() == "request.permission":
            op = m.group("op")
            val = m.group("val").strip()
            perm_conditions.append((op, val, cond))
        else:
            remaining.append(cond)

    if not perm_conditions:
        return permissions, conditions

    # Evaluate each request.permission condition
    # For "all" (AND): permission must satisfy EVERY condition
    # For "any" (OR):  permission must satisfy AT LEAST ONE condition
    # For ""  (single): same as "all" with one condition

    def _matches(perm: str, op: str, val: str) -> bool:
        """Return True if *perm* satisfies one condition expression."""
        if val.startswith("/") and val.endswith("/"):
            # Glob / regex pattern
            pattern = val[1:-1]
            pat_re = _glob_to_regex(pattern)
            matched = pat_re.match(perm) is not None
            if op == "=":
                return matched
            else:  # !=
                return not matched
        else:
            # Exact string comparison (strip quotes)
            clean = val.strip("'\"")
            if op == "=":
                return perm == clean
            else:  # !=
                return perm != clean

    filtered: set[str] = set()
    use_and = selector in ("all", "")

    for perm in permissions:
        if use_and:
            # AND: perm must match ALL request.permission conditions
            if all(_matches(perm, op, val) for op, val, _ in perm_conditions):
                filtered.add(perm)
        else:
            # OR: perm must match AT LEAST ONE request.permission condition
            if any(_matches(perm, op, val) for op, val, _ in perm_conditions):
                filtered.add(perm)

    n_removed = len(permissions) - len(filtered)
    if n_removed:
        logger.info(
            "request.permission filter removed %d/%d permissions",
            n_removed, len(permissions),
        )

    return filtered, tuple(remaining)


def _resolve_defines(
    conditions: tuple[str, ...],
    defines: dict[str, str],
) -> tuple[str, ...]:
    """Substitute define aliases in condition expressions.

    For example, if defines = {"SourceTenancy": "ocid1.tenancy…"}, then
    a condition referencing ``SourceTenancy`` is replaced with the OCID.
    """
    if not defines:
        return conditions
    resolved: list[str] = []
    for cond in conditions:
        for alias, value in defines.items():
            cond = cond.replace(alias, value)
        resolved.append(cond)
    return tuple(resolved)


# ---------------------------------------------------------------------------
# Single-statement evaluation
# ---------------------------------------------------------------------------

def evaluate_statement(
    parsed: dict[str, Any],
    index: PermissionIndex,
    defines: dict[str, str] | None = None,
) -> PermissionGrant | None:
    """Expand a single parsed OCI policy statement into a :class:`PermissionGrant`.

    Parameters
    ----------
    parsed:
        Dict produced by :func:`modules.policy_parser.parse_statement`.
    index:
        A built :class:`PermissionIndex`.
    defines:
        Optional mapping of define-statement aliases to their values, used
        for alias substitution in conditions.

    Returns
    -------
    PermissionGrant or None
        ``None`` if the statement is a ``define``, an error, or otherwise
        not evaluable as a permission grant.
    """
    stmt_type = parsed.get("statement_type", "")
    if stmt_type in ("define", "error"):
        return None

    effect = parsed.get("effect", "")
    verb = parsed.get("verb", "")
    if not effect or not verb:
        logger.debug("Skipping statement with missing effect/verb: %s", parsed)
        return None

    # --- resource expansion ------------------------------------------------
    resource_name = parsed.get("resource", "all-resources")
    individual_types: frozenset[str] = index.expand_resource(resource_name)

    # --- permission expansion (cumulative via index) -----------------------
    # For Deny statements, OCI cascades the denial *upward* through the
    # verb hierarchy: denying ``inspect`` also blocks ``read``, ``use``,
    # and ``manage``.  We therefore use ``get_deny_permissions`` which
    # returns the union of incremental permissions from the denied verb
    # through ``manage``.
    all_perms: set[str] = set()
    is_deny = effect.lower() == "deny"
    for rt in individual_types:
        if is_deny:
            all_perms |= index.get_deny_permissions(rt, verb.lower())
        else:
            all_perms |= index.get_permissions(rt, verb.lower())

    permissions = frozenset(all_perms)

    # --- API operation mapping ---------------------------------------------
    api_operations = frozenset(index.get_apis_for_permissions(all_perms))

    # --- conditions --------------------------------------------------------
    conditions, selector = _extract_conditions(parsed)
    if defines:
        conditions = _resolve_defines(conditions, defines)

    # --- static request.permission filter ---------------------------------
    # request.permission conditions can be evaluated now since we know the
    # full set of permissions.  Other conditions are kept for runtime.
    if conditions:
        all_perms, conditions = _apply_permission_conditions(
            all_perms, conditions, selector,
        )
        permissions = frozenset(all_perms)
        # Re-map API operations to match the filtered permission set
        api_operations = frozenset(index.get_apis_for_permissions(all_perms))

    # --- principal ---------------------------------------------------------
    principal_type = parsed.get("subject", "")
    principals = tuple(parsed.get("principals", []))

    # --- location ----------------------------------------------------------
    compartment = parsed.get("compartment", "")
    location_type = parsed.get("location_type", "")

    return PermissionGrant(
        effect=effect,
        principal_type=principal_type,
        principals=principals,
        permissions=permissions,
        api_operations=api_operations,
        resource_types=individual_types,
        compartment=compartment,
        location_type=location_type,
        conditions=conditions,
        condition_selector=selector,
        source_statement=parsed,
    )


# ---------------------------------------------------------------------------
# Batch evaluation
# ---------------------------------------------------------------------------

def evaluate_all(
    parsed_statements: list[dict[str, Any]],
    index: PermissionIndex,
) -> tuple[list[PermissionGrant], dict[str, str]]:
    """Evaluate a list of parsed statements, handling ``define`` statements.

    ``define`` statements are collected first and their aliases are
    substituted into conditions of subsequent access statements.

    Parameters
    ----------
    parsed_statements:
        List of dicts from :func:`modules.policy_parser.parse_statement`.
    index:
        A built :class:`PermissionIndex`.

    Returns
    -------
    (grants, defines)
        *grants* — list of :class:`PermissionGrant` for every evaluable
        statement (in input order, skipping defines/errors).
        *defines* — the alias → value mapping extracted from define
        statements.
    """
    # First pass: collect define aliases
    defines: dict[str, str] = {}
    for parsed in parsed_statements:
        if parsed.get("statement_type") == "define":
            alias = parsed.get("alias", "")
            value = parsed.get("value", "")
            if alias and value:
                defines[alias] = value

    # Second pass: evaluate access statements
    grants: list[PermissionGrant] = []
    for parsed in parsed_statements:
        grant = evaluate_statement(parsed, index, defines=defines)
        if grant is not None:
            grants.append(grant)

    return grants, defines
