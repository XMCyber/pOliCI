"""
Effective permission resolver and AWS IAM-like policy document generator.

Given a list of :class:`PermissionGrant` objects (from statement_eval) and a
:class:`UserContext` describing a specific principal, computes the effective
(net) permissions per compartment scope after Allow/Deny resolution, and can
emit the result as an AWS IAM-style JSON policy document.
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from modules.statement_eval import PermissionGrant

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class UserContext:
    """Describes a principal for whom we compute effective permissions."""

    user_id: str = ""                  # OCID of the user
    user_name: str = ""                # Display / login name
    groups: set[str] = field(default_factory=set)        # group *names*
    group_ocids: set[str] = field(default_factory=set)   # group OCIDs
    dynamic_groups: set[str] = field(default_factory=set) # dynamic-group names
    dynamic_group_ocids: set[str] = field(default_factory=set)
    compartment_ancestry: dict[str, list[str]] = field(default_factory=dict)
    # compartment_ancestry: mapping of compartment_name → list of ancestor
    # names (from child to root).  Used for scope inheritance.
    # E.g. {"Dev": ["Projects", "tenancy"], "Projects": ["tenancy"]}


@dataclass
class EffectivePermissions:
    """Result of resolving grants for a single user."""

    user: UserContext

    # compartment → set of allowed permission strings
    allowed: dict[str, frozenset[str]] = field(default_factory=dict)

    # compartment → set of denied permission strings
    denied: dict[str, frozenset[str]] = field(default_factory=dict)

    # compartment → effective (allowed − denied) permission strings
    effective: dict[str, frozenset[str]] = field(default_factory=dict)

    # The grants that matched this user (for traceability / audit)
    matching_grants: list[PermissionGrant] = field(default_factory=list)

    # Conditional grants that matched but couldn't be fully resolved
    # (conditions carried forward as metadata)
    conditional_grants: list[PermissionGrant] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"EffectivePermissions for {self.user.user_name or self.user.user_id}",
            f"  matching grants     : {len(self.matching_grants)}",
            f"  conditional grants  : {len(self.conditional_grants)}",
            f"  compartment scopes  : {len(self.effective)}",
        ]
        for comp in sorted(self.effective):
            n_eff = len(self.effective[comp])
            n_allow = len(self.allowed.get(comp, frozenset()))
            n_deny = len(self.denied.get(comp, frozenset()))
            lines.append(
                f"    {comp}: {n_eff} effective "
                f"({n_allow} allowed, {n_deny} denied)"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Principal matching
# ---------------------------------------------------------------------------

def _grant_matches_user(grant: PermissionGrant, user: UserContext) -> bool:
    """Return True if *grant* applies to the given *user*."""
    pt = grant.principal_type.lower()

    # any-user / any-group: matches everyone
    if pt in ("any-user", "any-group"):
        return True

    if pt == "group":
        for p in grant.principals:
            # Match by name (case-insensitive) or by OCID
            if p.lower() in {g.lower() for g in user.groups}:
                return True
            if p in user.group_ocids:
                return True
        return False

    if pt == "dynamic-group":
        for p in grant.principals:
            if p.lower() in {dg.lower() for dg in user.dynamic_groups}:
                return True
            if p in user.dynamic_group_ocids:
                return True
        return False

    # service principals, etc. — don't match normal users
    return False


# ---------------------------------------------------------------------------
# Scope resolution
# ---------------------------------------------------------------------------

def _compartments_in_scope(
    grant: PermissionGrant,
    user: UserContext,
    all_compartments: set[str] | None = None,
) -> set[str]:
    """Return the set of compartment names where *grant* is in scope.

    * ``tenancy`` / ``any-tenancy`` → every known compartment.
    * ``compartment X`` → X and all descendants of X.
    """
    loc = grant.location_type.lower()
    comp = grant.compartment

    if loc in ("tenancy", "any-tenancy"):
        # Applies everywhere
        if all_compartments:
            return all_compartments | {"tenancy"}
        return {"tenancy"}

    if loc == "compartment" and comp:
        # The compartment itself + descendants
        result = {comp}
        if user.compartment_ancestry:
            # Find all compartments that have `comp` in their ancestry chain
            for c, ancestors in user.compartment_ancestry.items():
                if comp in ancestors or c == comp:
                    result.add(c)
        return result

    # Fallback: just the literal compartment value
    if comp:
        return {comp}
    return {"tenancy"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_effective(
    grants: list[PermissionGrant],
    user: UserContext,
    all_compartments: set[str] | None = None,
) -> EffectivePermissions:
    """Compute effective permissions for *user* given a list of *grants*.

    Parameters
    ----------
    grants:
        All :class:`PermissionGrant` objects produced from the environment's
        policy statements.
    user:
        The principal to evaluate.
    all_compartments:
        Optional set of all known compartment names (used to expand
        tenancy-scoped grants).  If not provided, tenancy grants are recorded
        under the key ``"tenancy"``.

    Returns
    -------
    EffectivePermissions
    """
    allow_map: dict[str, set[str]] = defaultdict(set)
    deny_map: dict[str, set[str]] = defaultdict(set)
    matching: list[PermissionGrant] = []
    conditional: list[PermissionGrant] = []

    for grant in grants:
        if not _grant_matches_user(grant, user):
            continue

        matching.append(grant)

        # Track conditional grants separately
        has_conditions = bool(grant.conditions)
        if has_conditions:
            conditional.append(grant)

        scopes = _compartments_in_scope(grant, user, all_compartments)
        effect = grant.effect.lower()

        for scope in scopes:
            if effect in ("allow", "endorse", "admit"):
                allow_map[scope].update(grant.permissions)
            elif effect == "deny":
                deny_map[scope].update(grant.permissions)

    # Compute effective = allowed − denied per compartment
    all_scopes = set(allow_map) | set(deny_map)
    allowed: dict[str, frozenset[str]] = {}
    denied: dict[str, frozenset[str]] = {}
    effective: dict[str, frozenset[str]] = {}

    for scope in all_scopes:
        a = frozenset(allow_map.get(scope, set()))
        d = frozenset(deny_map.get(scope, set()))
        allowed[scope] = a
        denied[scope] = d
        effective[scope] = a - d

    return EffectivePermissions(
        user=user,
        allowed=allowed,
        denied=denied,
        effective=effective,
        matching_grants=matching,
        conditional_grants=conditional,
    )


def resolve_effective_all_users(
    grants: list[PermissionGrant],
    users: list[UserContext],
    all_compartments: set[str] | None = None,
) -> list[EffectivePermissions]:
    """Batch-resolve effective permissions for multiple users."""
    return [
        resolve_effective(grants, user, all_compartments)
        for user in users
    ]


# ---------------------------------------------------------------------------
# OCI condition → structured Condition block
# ---------------------------------------------------------------------------

# Matches:  variable = 'value'   variable != 'value'   variable = /pattern/
_COND_RE = re.compile(
    r"""
    ^\s*
    (?P<var>[A-Za-z_.]+(?:\.[A-Za-z_.*-]+)*)   # variable path
    \s*
    (?P<op>!=|=)                                # operator
    \s*
    (?P<val>.+?)                                # value (quoted or regex)
    \s*$
    """,
    re.VERBOSE,
)


def _parse_single_condition(raw: str) -> dict[str, Any] | None:
    """Parse one OCI condition expression into ``{operator, variable, value}``.

    Returns ``None`` if the expression cannot be parsed.
    """
    m = _COND_RE.match(raw)
    if not m:
        return None

    var = m.group("var")
    op = m.group("op")
    val = m.group("val")

    # Determine the operator name and clean the value
    if val.startswith("/") and val.endswith("/"):
        # Regex / glob pattern
        pattern = val[1:-1]
        if op == "=":
            return {"operator": "StringLike", "variable": var, "values": [pattern]}
        else:
            return {"operator": "StringNotLike", "variable": var, "values": [pattern]}

    # Strip surrounding quotes
    if (val.startswith("'") and val.endswith("'")) or \
       (val.startswith('"') and val.endswith('"')):
        val = val[1:-1]

    if op == "=":
        return {"operator": "StringEquals", "variable": var, "values": [val]}
    else:
        return {"operator": "StringNotEquals", "variable": var, "values": [val]}


def _build_condition_block(
    conditions: tuple[str, ...],
    selector: str,
) -> dict[str, Any]:
    """Convert a tuple of OCI condition strings into an AWS-like Condition dict.

    OCI ``all`` selector → AND (AWS default: all conditions must match).
    OCI ``any`` selector → OR  (modeled via ``"ConditionOperator": "Any"``).

    Returns
    -------
    dict
        AWS IAM-like Condition block, e.g.::

            {
              "StringEquals": {"target.group.name": ["A-Users"]},
              "StringNotEquals": {"request.principal.id": ["ocid1..."]}
            }

        If the ``any`` selector is active, an extra key ``"_ConditionLogic": "Any"``
        is included (non-standard, for consumers that need to know).

        Unparseable conditions are placed under the ``"_Raw"`` key.
    """
    if not conditions:
        return {}

    block: dict[str, dict[str, list[str]]] = {}
    unparsed: list[str] = []

    for raw_cond in conditions:
        parsed = _parse_single_condition(raw_cond)
        if parsed is None:
            unparsed.append(raw_cond)
            continue
        op = parsed["operator"]
        var = parsed["variable"]
        vals = parsed["values"]
        block.setdefault(op, {})
        block[op].setdefault(var, [])
        block[op][var].extend(vals)

    result: dict[str, Any] = dict(block)

    if selector == "any":
        result["_ConditionLogic"] = "Any"

    if unparsed:
        result["_Raw"] = unparsed

    return result


# ---------------------------------------------------------------------------
# AWS IAM-like policy document generation
# ---------------------------------------------------------------------------

def _resource_arn(grant: PermissionGrant) -> str:
    """Build a pseudo-ARN for the grant's resource scope."""
    loc = grant.location_type.lower()
    comp = grant.compartment

    if loc == "tenancy":
        return "oci:compartment:tenancy:*"
    if loc == "any-tenancy":
        return "oci:compartment:any-tenancy:*"
    if loc == "compartment" and comp:
        return f"oci:compartment:{comp}:*"
    if comp:
        return f"oci:compartment:{comp}:*"
    return "oci:compartment:*:*"


def grant_to_iam_statement(
    grant: PermissionGrant,
    sid: str | None = None,
) -> dict[str, Any]:
    """Convert a single :class:`PermissionGrant` to an AWS IAM-like Statement dict."""
    stmt: dict[str, Any] = {}

    if sid:
        stmt["Sid"] = sid

    stmt["Effect"] = grant.effect.capitalize()

    # Principal block
    principal: dict[str, Any] = {}
    if grant.principal_type:
        principal["OCI:PrincipalType"] = grant.principal_type
    if grant.principals:
        principal["OCI:Principals"] = list(grant.principals)
    if principal:
        stmt["Principal"] = principal

    # Action — sorted permission strings
    stmt["Action"] = sorted(grant.permissions)

    # Resource
    stmt["Resource"] = _resource_arn(grant)

    # Condition
    if grant.conditions:
        cond_block = _build_condition_block(grant.conditions, grant.condition_selector)
        if cond_block:
            stmt["Condition"] = cond_block

    return stmt


def effective_to_iam_policy(
    ep: EffectivePermissions,
) -> dict[str, Any]:
    """Convert an :class:`EffectivePermissions` result to an AWS IAM-like policy document.

    The output has two sections:

    * ``Statement`` — one entry per matching grant (preserving the original
      OCI policy granularity, including conditions).
    * ``EffectiveSummary`` — pre-computed net permissions per compartment
      (after Allow − Deny), for quick consumption.
    """
    doc: dict[str, Any] = {
        "Version": "oci-effective-v1",
        "EvaluatedAt": datetime.now(timezone.utc).isoformat(),
    }

    # Principal
    doc["Principal"] = {
        "Type": "User",
        "Id": ep.user.user_id,
        "Name": ep.user.user_name,
        "Groups": sorted(ep.user.groups),
    }
    if ep.user.dynamic_groups:
        doc["Principal"]["DynamicGroups"] = sorted(ep.user.dynamic_groups)

    # Statements — one per matching grant
    statements: list[dict[str, Any]] = []
    for i, grant in enumerate(ep.matching_grants, 1):
        sid = f"ocipol-{i}"
        statements.append(grant_to_iam_statement(grant, sid=sid))
    doc["Statement"] = statements

    # Effective summary per compartment
    summary: dict[str, Any] = {}
    for scope in sorted(ep.effective):
        eff = ep.effective[scope]
        allowed = ep.allowed.get(scope, frozenset())
        denied = ep.denied.get(scope, frozenset())
        entry: dict[str, Any] = {
            "EffectiveCount": len(eff),
            "AllowedCount": len(allowed),
            "DeniedCount": len(denied),
        }
        # Include the full effective permission list per scope
        entry["EffectiveActions"] = sorted(eff)
        # Include denied actions separately for auditability
        if denied:
            entry["ExplicitDenyActions"] = sorted(denied)
        summary[scope] = entry
    doc["EffectiveSummary"] = summary

    return doc


def effective_to_iam_policy_json(
    ep: EffectivePermissions,
    indent: int = 2,
) -> str:
    """Return the IAM-like policy document as a formatted JSON string."""
    import json
    return json.dumps(effective_to_iam_policy(ep), indent=indent)


def all_users_to_iam_policies(
    results: list[EffectivePermissions],
) -> list[dict[str, Any]]:
    """Convert a list of user results to a list of IAM-like policy documents."""
    return [effective_to_iam_policy(ep) for ep in results]
