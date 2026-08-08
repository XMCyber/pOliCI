"""
OCI Policy Evaluator — main entry point.

Parses OCI IAM policy statements, expands them against the scraped
permission-reference index, and computes effective permissions per user
in an AWS IAM-like JSON format.

Three evaluation modes are available as Click subcommands:

``local``
    Parse ``data/statements.txt`` offline — no OCI API needed.  Builds
    the permission index, evaluates every statement, and writes
    ``effective_permissions.json`` for a set of demo users.

``oci``
    Connect to OCI via ``~/.oci/config``, enumerate all users, groups,
    compartments, and policies, then compute effective permissions for
    every user.

``user``
    Like *oci* but scoped to a single user looked up by email address.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click
import oci
from oci.auth.signers import InstancePrincipalsSecurityTokenSigner


from modules.permission_index import build_index, PermissionIndex
from modules.policy_parser import (
    parse_statement,
    ParseLogEntry,
    write_parse_log,
)
from modules.statement_eval import evaluate_all, PermissionGrant
from modules.effective_perms import (
    UserContext,
    EffectivePermissions,
    resolve_effective,
    resolve_effective_all_users,
    effective_to_iam_policy,
    all_users_to_iam_policies,
)
from modules.api_to_policy import (
    resolve_apis_to_policy,
    result_to_iam_policy,
    result_to_iam_policy_json,
    print_result,
)

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent
_PARSE_LOG_PATH = _PROJECT_ROOT / "data" / "parse_log.txt"
_REF_PATH = _PROJECT_ROOT / "data" / "policy_reference_scraped.json"

ROOT_COMPARTMENT_ID = None


def _extract_statements(content: str) -> list[str]:
    """Extract policy statements from file content.

    Supports two formats:
    - Plain text: one statement per line (# comments and blanks skipped)
    - JSON (iam_context output): extracts statements from policies[].statements[]
    """
    stripped = content.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            statements = []
            for policy in data.get("policies", []):
                statements.extend(policy.get("statements", []))
            if statements:
                print(f"  Detected JSON input — extracted {len(statements)} statements")
                return statements
        except (json.JSONDecodeError, AttributeError):
            pass

    return [
        line.strip() for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _build_users_from_grants(grants: list[PermissionGrant]) -> list[UserContext]:
    """Build synthetic UserContexts from principals found in grants.

    Creates one UserContext per unique group and dynamic-group, so that
    effective permission resolution shows results for each principal.
    """
    groups: set[str] = set()
    dynamic_groups: set[str] = set()

    for g in grants:
        pt = g.principal_type.lower()
        if pt == "group":
            groups.update(g.principals)
        elif pt == "dynamic-group":
            dynamic_groups.update(g.principals)

    users: list[UserContext] = []

    for group_name in sorted(groups):
        users.append(UserContext(
            user_id=f"synthetic:group:{group_name}",
            user_name=f"[group] {group_name}",
            groups={group_name},
        ))

    for dg_name in sorted(dynamic_groups):
        users.append(UserContext(
            user_id=f"synthetic:dg:{dg_name}",
            user_name=f"[dynamic-group] {dg_name}",
            dynamic_groups={dg_name},
        ))

    return users


# ---------------------------------------------------------------------------
# Mode 1: Local evaluation (no OCI API)
# ---------------------------------------------------------------------------

def main_local() -> None:
    """Parse ``data/statements.txt``, build the permission index, evaluate
    every statement, and print the expanded grants."""

    print("=" * 70)
    print("  Mode: LOCAL — evaluating statements.txt against permission index")
    print("=" * 70)

    # 1. Build permission index
    print("\n[1/3] Building permission index …")
    idx = build_index(_REF_PATH)
    print(idx.summary())

    # 2. Parse statements
    print("\n[2/3] Parsing statements …")
    statements_path = _PROJECT_ROOT / "data" / "statements.txt"
    with open(statements_path, "r") as f:
        content = f.read()

    raw_statements = _extract_statements(content)

    all_log_entries: list[ParseLogEntry] = []
    parsed_list: list[dict] = []
    ok_count = err_count = 0

    for line_num, stmt_text in enumerate(raw_statements, start=1):
        result = parse_statement(stmt_text, log=all_log_entries, line_num=line_num)
        parsed_list.append(result)
        if result.get("statement_type") == "error":
            err_count += 1
        else:
            ok_count += 1

    write_parse_log(all_log_entries, str(_PARSE_LOG_PATH))
    print(f"  Parsed {ok_count} OK, {err_count} errors (log → {_PARSE_LOG_PATH})")

    # 3. Evaluate
    print("\n[3/4] Evaluating statements …")
    grants, defines = evaluate_all(parsed_list, idx)
    if defines:
        print(f"  Defines: {defines}")
    print(f"  Produced {len(grants)} permission grants\n")

    for i, g in enumerate(grants, 1):
        _print_grant(i, g)

    # 4. Resolve effective permissions per principal found in grants
    print("\n[4/4] Generating IAM-like policy documents …")
    users = _build_users_from_grants(grants)
    if not users:
        print("  No principals found in grants — skipping effective permissions.")
        print("\n" + "=" * 70)
        print(f"  Total: {len(grants)} grants from {len(raw_statements)} statements")
        print("=" * 70)
        return
    results = resolve_effective_all_users(grants, users)
    iam_docs = all_users_to_iam_policies(results)

    output_path = _PROJECT_ROOT / "data" / "effective_permissions.json"
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(iam_docs, fh, indent=2)
    print(f"  Written {len(iam_docs)} IAM-like policy documents → {output_path}")

    for ep in results:
        print()
        print(ep.summary())

    print("\n" + "=" * 70)
    print(f"  Total: {len(grants)} grants from {len(raw_statements)} statements")
    print("=" * 70)


def _print_grant(num: int, g: PermissionGrant) -> None:
    print(f"  [{num:>3}] {g.effect:<7} {g.principal_type} {', '.join(g.principals) or '(all)'}")
    print(f"        {len(g.permissions):>5} permissions  |  "
          f"{len(g.resource_types):>4} resource types  |  "
          f"{len(g.api_operations):>5} API ops")
    print(f"        scope: {g.compartment} ({g.location_type})")
    if g.conditions:
        sel = f" ({g.condition_selector})" if g.condition_selector else ""
        print(f"        conditions{sel}: {', '.join(g.conditions)}")
    print()


# ---------------------------------------------------------------------------
# Mode 2: Full OCI API evaluation
# ---------------------------------------------------------------------------

def main_oci() -> None:
    """Fetch users, groups, policies from OCI API; compute per-user effective
    permissions."""

    print("=" * 70)
    print("  Mode: OCI — enumerating users & policies from OCI API")
    print("=" * 70)

    # 1. Build permission index
    print("\n[1/5] Building permission index …")
    idx = build_index(_REF_PATH)
    print(idx.summary())

    # 2. Connect to OCI
    print("\n[2/5] Connecting to OCI …")
    config = oci.config.from_file()
    identity = oci.identity.IdentityClient(config)
    tenancy_id = config["tenancy"]
    print(f"  Tenancy: {tenancy_id}")

    # 3. Enumerate users, groups, memberships, compartments
    print("\n[3/5] Enumerating users, groups, compartments …")
    users = _list_all(identity.list_users, compartment_id=tenancy_id)
    groups = _list_all(identity.list_groups, compartment_id=tenancy_id)
    compartments = _list_all(identity.list_compartments, compartment_id=tenancy_id)

    print(f"  Users: {len(users)}")
    print(f"  Groups: {len(groups)}")
    print(f"  Compartments: {len(compartments)}")

    # Build group membership map: user_ocid → set of (group_name, group_ocid)
    group_by_id: dict[str, str] = {g.id: g.name for g in groups}
    user_groups: dict[str, set[tuple[str, str]]] = {}
    for group in groups:
        members = _list_all(
            identity.list_user_group_memberships,
            compartment_id=tenancy_id,
            group_id=group.id,
        )
        for m in members:
            user_groups.setdefault(m.user_id, set()).add((group.name, group.id))

    # Build compartment ancestry
    comp_name_by_id: dict[str, str] = {c.id: c.name for c in compartments}
    comp_name_by_id[tenancy_id] = "tenancy"
    comp_parent: dict[str, str] = {c.name: comp_name_by_id.get(c.compartment_id, "tenancy")
                                   for c in compartments}
    compartment_ancestry: dict[str, list[str]] = {}
    all_compartment_names: set[str] = {"tenancy"} | {c.name for c in compartments}
    for c_name in all_compartment_names:
        ancestors: list[str] = []
        cur = comp_parent.get(c_name)
        while cur:
            ancestors.append(cur)
            cur = comp_parent.get(cur)
        compartment_ancestry[c_name] = ancestors

    # Build UserContext for each user
    user_contexts: list[UserContext] = []
    for u in users:
        memberships = user_groups.get(u.id, set())
        ctx = UserContext(
            user_id=u.id,
            user_name=u.name,
            groups={name for name, _ in memberships},
            group_ocids={ocid for _, ocid in memberships},
            compartment_ancestry=compartment_ancestry,
        )
        user_contexts.append(ctx)

    # 4. Fetch and parse all policies
    print("\n[4/5] Fetching policies …")
    all_parsed: list[dict] = []
    all_log_entries: list[ParseLogEntry] = []

    # Fetch from tenancy + each compartment
    compartment_ids = [tenancy_id] + [c.id for c in compartments]
    total_policy_count = 0
    for comp_id in compartment_ids:
        try:
            policies = _list_all(identity.list_policies, compartment_id=comp_id)
        except oci.exceptions.ServiceError as e:
            logger.warning("Could not list policies in %s: %s", comp_id, e.message)
            continue
        for policy in policies:
            total_policy_count += 1
            for stmt_text in policy.statements:
                result = parse_statement(stmt_text, log=all_log_entries)
                all_parsed.append(result)

    write_parse_log(all_log_entries, str(_PARSE_LOG_PATH))
    print(f"  Policies: {total_policy_count}")
    print(f"  Statements parsed: {len(all_parsed)}")

    # Evaluate all statements
    grants, defines = evaluate_all(all_parsed, idx)
    print(f"  Grants: {len(grants)}, Defines: {len(defines)}")

    # 5. Compute effective permissions per user
    print("\n[5/5] Computing effective permissions per user …")
    results = resolve_effective_all_users(grants, user_contexts, all_compartment_names)

    for ep in results:
        print()
        print(ep.summary())

    # Write IAM-like policy documents
    output_path = _PROJECT_ROOT / "data" / "effective_permissions.json"
    iam_docs = all_users_to_iam_policies(results)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(iam_docs, fh, indent=2)
    print(f"\n  Written {len(iam_docs)} IAM-like policy documents → {output_path}")

    print("\n" + "=" * 70)
    print(f"  Done. {len(users)} users, {len(grants)} grants evaluated.")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Mode 3: Single user evaluation (OCI API)
# ---------------------------------------------------------------------------

def main_user(email: str) -> None:
    """Fetch a single user by email from OCI, compute their effective
    permissions, and output an IAM-like policy document."""

    print("=" * 70)
    print(f"  Mode: USER — evaluating permissions for {email}")
    print("=" * 70)

    # 1. Build permission index
    print("\n[1/5] Building permission index …")
    idx = build_index(_REF_PATH)
    print(idx.summary())

    # 2. Connect to OCI
    print("\n[2/5] Connecting to OCI …")
    config = oci.config.from_file()
    identity = oci.identity.IdentityClient(config)
    tenancy_id = config["tenancy"]
    print(f"  Tenancy: {tenancy_id}")

    # 3. Find the user & their groups
    print(f"\n[3/5] Looking up user {email!r} …")
    all_users = _list_all(identity.list_users, compartment_id=tenancy_id)
    target_user = None
    for u in all_users:
        if getattr(u, "email", "") == email or u.name == email:
            target_user = u
            break

    if target_user is None:
        print(f"  ERROR: user with email {email!r} not found among {len(all_users)} users.")
        print("  Available users:")
        for u in all_users:
            u_email = getattr(u, "email", "")
            print(f"    {u.name}  ({u_email})  [{u.lifecycle_state}]")
        sys.exit(1)

    print(f"  Found: {target_user.name} (id={target_user.id})")
    print(f"  Email: {getattr(target_user, 'email', 'n/a')}")
    print(f"  State: {target_user.lifecycle_state}")

    # Get groups
    groups = _list_all(identity.list_groups, compartment_id=tenancy_id)
    group_by_id: dict[str, str] = {g.id: g.name for g in groups}

    memberships = _list_all(
        identity.list_user_group_memberships,
        compartment_id=tenancy_id,
        user_id=target_user.id,
    )
    user_group_names: set[str] = set()
    user_group_ocids: set[str] = set()
    for m in memberships:
        gname = group_by_id.get(m.group_id, m.group_id)
        user_group_names.add(gname)
        user_group_ocids.add(m.group_id)

    print(f"  Groups ({len(user_group_names)}): {sorted(user_group_names)}")

    # Build compartment hierarchy
    compartments = _list_all(identity.list_compartments, compartment_id=tenancy_id)
    comp_name_by_id: dict[str, str] = {c.id: c.name for c in compartments}
    comp_name_by_id[tenancy_id] = "tenancy"
    comp_parent: dict[str, str] = {
        c.name: comp_name_by_id.get(c.compartment_id, "tenancy")
        for c in compartments
    }
    all_compartment_names: set[str] = {"tenancy"} | {c.name for c in compartments}
    compartment_ancestry: dict[str, list[str]] = {}
    for c_name in all_compartment_names:
        ancestors: list[str] = []
        cur = comp_parent.get(c_name)
        while cur:
            ancestors.append(cur)
            cur = comp_parent.get(cur)
        compartment_ancestry[c_name] = ancestors

    print(f"  Compartments: {len(compartments)}")

    user_ctx = UserContext(
        user_id=target_user.id,
        user_name=target_user.name,
        groups=user_group_names,
        group_ocids=user_group_ocids,
        compartment_ancestry=compartment_ancestry,
    )

    # 4. Fetch and parse all policies
    print("\n[4/5] Fetching policies …")
    all_parsed: list[dict] = []
    all_log_entries: list[ParseLogEntry] = []

    compartment_ids = [tenancy_id] + [c.id for c in compartments]
    total_policy_count = 0
    for comp_id in compartment_ids:
        try:
            policies = _list_all(identity.list_policies, compartment_id=comp_id)
        except oci.exceptions.ServiceError as e:
            logger.warning("Could not list policies in %s: %s", comp_id, e.message)
            continue
        for policy in policies:
            total_policy_count += 1
            for stmt_text in policy.statements:
                result = parse_statement(stmt_text, log=all_log_entries)
                all_parsed.append(result)

    write_parse_log(all_log_entries, str(_PARSE_LOG_PATH))
    print(f"  Policies: {total_policy_count}")
    print(f"  Statements parsed: {len(all_parsed)}")

    grants, defines = evaluate_all(all_parsed, idx)
    print(f"  Grants: {len(grants)}, Defines: {len(defines)}")

    # 5. Compute effective permissions
    print(f"\n[5/5] Computing effective permissions for {target_user.name} …")
    ep = resolve_effective(grants, user_ctx, all_compartment_names)
    print()
    print(ep.summary())

    # Write IAM-like policy document
    iam_doc = effective_to_iam_policy(ep)
    output_path = _PROJECT_ROOT / "data" / "effective_permissions.json"
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(iam_doc, fh, indent=2)
    print(f"\n  IAM-like policy document → {output_path}")

    # Print summary of matching grants
    print(f"\n  Matching grants ({len(ep.matching_grants)}):")
    for i, g in enumerate(ep.matching_grants, 1):
        cond_str = ""
        if g.conditions:
            sel = f" ({g.condition_selector})" if g.condition_selector else ""
            cond_str = f"  [conditions{sel}: {', '.join(g.conditions)}]"
        print(f"    {i:>3}. {g.effect:<7} via {g.principal_type} "
              f"{', '.join(g.principals) or '(all)'} → "
              f"{len(g.permissions)} perms in {g.compartment}{cond_str}")

    print("\n" + "=" * 70)
    print(f"  Done. Effective permissions for {target_user.name} ({email})")
    print("=" * 70)


# ---------------------------------------------------------------------------
# OCI API helpers
# ---------------------------------------------------------------------------

def _list_all(list_fn, **kwargs) -> list:
    """Paginate through an OCI list operation and return all items."""
    items: list = []
    response = list_fn(**kwargs)
    items.extend(response.data)
    while response.has_next_page:
        response = list_fn(**kwargs, page=response.next_page)
        items.extend(response.data)
    return items


# ---------------------------------------------------------------------------
# Click CLI
# ---------------------------------------------------------------------------

@click.group(invoke_without_command=True)
@click.pass_context
@click.option("-v", "--verbose", is_flag=True, default=False, help="Enable debug-level logging.")
@click.option("-q", "--quiet", is_flag=True, default=False, help="Suppress informational output (errors only).")
def cli(ctx: click.Context, verbose: bool, quiet: bool) -> None:
    """OCI Policy Evaluator.

    \b
    Parse OCI IAM policy statements, expand them against the scraped
    permission-reference index, and compute effective permissions per
    user in an AWS IAM-like JSON format.

    \b
    Subcommands
    -----------
    local        — Evaluate data/statements.txt offline (no OCI API).
    oci          — Enumerate all users & policies from OCI and compute effective
                   permissions for every user.
    user         — Compute effective permissions for a single user by email.
    resolve-apis — Resolve API operation names to the minimal OCI policy.

    Run ``python main.py <command> --help`` for subcommand details.
    """
    if quiet:
        log_level = logging.ERROR
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
def local() -> None:
    """Evaluate data/statements.txt locally (no OCI API required).

    \b
    Builds the permission index from the scraped policy reference,
    parses every statement in data/statements.txt, evaluates them into
    permission grants, and writes effective_permissions.json for a set
    of hard-coded demo users.

    \b
    Example
    -------
      python main.py local
      python main.py -v local          # with debug logging
    """
    main_local()


@cli.command("oci")
def oci_cmd() -> None:
    """Fetch all policies & users from OCI API and compute effective permissions.

    \b
    Connects to OCI using ~/.oci/config, enumerates every user, group,
    compartment, and policy in the tenancy, then resolves effective
    permissions for all users.  Results are written to
    data/effective_permissions.json as IAM-like policy documents.

    \b
    Example
    -------
      python main.py oci
      python main.py -q oci            # errors only
    """
    main_oci()


@cli.command()
@click.argument("email")
def user(email: str) -> None:
    """Evaluate effective permissions for a single user by EMAIL.

    \b
    Looks up the user by email address (or username) via the OCI API,
    fetches all policies in the tenancy, and computes the user's
    effective permissions.  The result is written to
    data/effective_permissions.json.

    \b
    Example
    -------
      python main.py user user@example.com
      python main.py -v user admin@corp.com
    """
    main_user(email)


# ---------------------------------------------------------------------------
# Mode 4: Resolve API names to minimal policy
# ---------------------------------------------------------------------------

def main_resolve_apis(
    api_names: list[str],
    output_path: str | None = None,
) -> None:
    """Given a list of OCI API operation names, resolve the minimal policy
    that grants all of them and output an AWS IAM-style JSON document."""

    print("=" * 70)
    print("  Mode: RESOLVE-APIS — computing minimal policy for API operations")
    print("=" * 70)

    print(f"\n  Input: {len(api_names)} API operation(s)")
    for name in api_names:
        print(f"    - {name}")

    # 1. Build permission index
    print("\n[1/2] Building permission index …")
    idx = build_index(_REF_PATH)
    print(idx.summary())

    # 2. Resolve
    print("\n[2/2] Resolving APIs to minimal policy …")
    result = resolve_apis_to_policy(api_names, index=idx)

    # Console output
    print_result(result)

    # JSON output
    policy_json = result_to_iam_policy_json(result)
    out = Path(output_path) if output_path else _PROJECT_ROOT / "data" / "resolved_policy.json"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(policy_json)
    print(f"  AWS-style policy document → {out}")

    print("\n" + "=" * 70)
    print(f"  Done. {len(result.policy_statements)} policy statements for "
          f"{len(api_names)} APIs.")
    print("=" * 70)


@cli.command("resolve-apis")
@click.argument("api_names_csv", required=False, default="")
@click.option(
    "-f", "--file",
    "api_file",
    type=click.Path(exists=True),
    help="Read API names from a file (one per line, or comma-separated).",
)
@click.option(
    "-o", "--output",
    "output_path",
    type=click.Path(),
    help="Output path for the generated policy JSON (default: data/resolved_policy.json).",
)
def resolve_apis_cmd(
    api_names_csv: str,
    api_file: str | None,
    output_path: str | None,
) -> None:
    """Resolve API operation names to the minimal OCI policy that allows them.

    \b
    Accepts a comma-separated list of API names and/or a file
    (``--file``).  Outputs an AWS IAM-style JSON policy document with
    the minimal set of (verb, resource-type) statements, plus notes
    for any conditional / situational permissions.

    \b
    API names can be optionally service-qualified with a dot prefix
    to disambiguate operations that exist across multiple services
    (e.g. GetWorkRequest).  The service qualifier is substring-matched
    against the service_id field.

    \b
    Examples
    --------
      python main.py resolve-apis "LaunchInstance,GetInstance,TerminateInstance"
      python main.py resolve-apis "file_storage.GetWorkRequest"
      python main.py resolve-apis "LaunchInstance,email_delivery.GetWorkRequest"
      python main.py resolve-apis -f apis.txt
      python main.py resolve-apis -f apis.txt -o my_policy.json
    """
    names: list[str] = [
        n.strip() for n in api_names_csv.split(",") if n.strip()
    ]

    if api_file:
        with open(api_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    for part in line.split(","):
                        part = part.strip()
                        if part:
                            names.append(part)

    if not names:
        raise click.UsageError(
            "Provide at least one API name as a comma-separated argument or via --file."
        )

    main_resolve_apis(names, output_path=output_path)


# ---------------------------------------------------------------------------
# Mode 5: Initialise shared test variables from OCI config
# ---------------------------------------------------------------------------


@cli.command("init-test-vars")
@click.option(
    "--compartment",
    "compartment_name",
    default=None,
    help="Compartment name to use. If omitted, auto-selects (or lists choices).",
)
@click.option(
    "--profile",
    "profile_name",
    default="DEFAULT",
    show_default=True,
    help="OCI config profile to read from ~/.oci/config.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(),
    default=None,
    help="Output path (default: techniques/shared.tfvars.json).",
)
def init_test_vars_cmd(
    compartment_name: str | None,
    profile_name: str,
    output_path: str | None,
) -> None:
    """Populate techniques/shared.tfvars.json from ~/.oci/config and live OCI APIs.

    \b
    Reads your OCI credentials, discovers compartments / availability domains /
    subnets / images, and writes the shared Terraform variables file so that
    ``test-techniques`` can run without manual setup.

    \b
    Examples
    --------
      python main.py init-test-vars
      python main.py init-test-vars --compartment my-compartment
      python main.py init-test-vars --profile STAGING
    """
    import oci as _oci

    dest = Path(output_path) if output_path else _PROJECT_ROOT / "techniques" / "shared.tfvars.json"

    click.echo("\n[1/5] Reading OCI config …")
    try:
        config = _oci.config.from_file(profile_name=profile_name)
    except Exception as exc:
        raise click.ClickException(f"Cannot read OCI config: {exc}")

    tenancy_id = config["tenancy"]
    region = config["region"]
    click.echo(f"  Tenancy: {tenancy_id}")
    click.echo(f"  Region:  {region}")

    identity = _oci.identity.IdentityClient(config)

    # --- Compartment ---
    click.echo("\n[2/5] Discovering compartments …")
    compartments = identity.list_compartments(
        tenancy_id, compartment_id_in_subtree=True, lifecycle_state="ACTIVE"
    ).data

    if not compartments:
        raise click.ClickException(
            "No active compartments found in tenancy. "
            "Create a compartment first, or use the root tenancy OCID."
        )

    selected_comp = None
    if compartment_name:
        for c in compartments:
            if c.name == compartment_name:
                selected_comp = c
                break
        if not selected_comp:
            names = ", ".join(c.name for c in compartments)
            raise click.ClickException(
                f"Compartment '{compartment_name}' not found. Available: {names}"
            )
    elif len(compartments) == 1:
        selected_comp = compartments[0]
    else:
        click.echo("  Multiple compartments found:")
        for i, c in enumerate(compartments, 1):
            click.echo(f"    [{i}] {c.name}  ({c.id})")
        choice = click.prompt(
            "  Select compartment",
            type=click.IntRange(1, len(compartments)),
            default=1,
        )
        selected_comp = compartments[choice - 1]

    comp_ocid = selected_comp.id
    comp_name = selected_comp.name
    click.echo(f"  Using: {comp_name} ({comp_ocid})")

    # --- Availability domains ---
    click.echo("\n[3/5] Listing availability domains …")
    ads = identity.list_availability_domains(tenancy_id).data
    ad_name = ads[0].name if ads else None
    if ad_name:
        click.echo(f"  Using: {ad_name}")
    else:
        click.echo("  ⚠  No availability domains found (compute tests will be skipped).")

    # --- Subnet ---
    click.echo("\n[4/5] Looking for subnets …")
    vn_client = _oci.core.VirtualNetworkClient(config)
    subnets = vn_client.list_subnets(comp_ocid).data
    active_subnets = [s for s in subnets if s.lifecycle_state == "AVAILABLE"]

    subnet_ocid = None
    if active_subnets:
        subnet_ocid = active_subnets[0].id
        click.echo(f"  Using: {active_subnets[0].display_name} ({subnet_ocid})")
    else:
        click.echo(
            "  ⚠  No subnets found in this compartment.\n"
            "     Compute techniques require a subnet. Create a VCN + subnet,\n"
            "     then re-run this command or set subnet_ocid manually."
        )

    # --- Linux image ---
    click.echo("\n[5/5] Finding latest Oracle Linux image …")
    compute_client = _oci.core.ComputeClient(config)
    preferred_shape = "VM.Standard.E4.Flex"
    images = compute_client.list_images(
        comp_ocid,
        operating_system="Oracle Linux",
        shape=preferred_shape,
        sort_by="TIMECREATED",
        sort_order="DESC",
        limit=5,
    ).data
    image_ocid = None
    if images:
        image_ocid = images[0].id
        click.echo(f"  Using: {images[0].display_name} ({image_ocid})")
        click.echo(f"  (compatible with shape {preferred_shape})")
    else:
        click.echo(f"  ⚠  No Oracle Linux images found for {preferred_shape}. Set linux_image_ocid manually.")

    # --- Write ---
    vars_dict: dict[str, str] = {
        "tenancy_ocid": tenancy_id,
        "region": region,
        "compartment_ocid": comp_ocid,
        "compartment_name": comp_name,
    }
    if ad_name:
        vars_dict["availability_domain"] = ad_name
    if subnet_ocid:
        vars_dict["subnet_ocid"] = subnet_ocid
    if image_ocid:
        vars_dict["linux_image_ocid"] = image_ocid

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(vars_dict, indent=2) + "\n")
    click.echo(f"\n✓ Wrote {dest}")
    click.echo(f"  {len(vars_dict)} variable(s) populated.\n")

    missing = {"availability_domain", "subnet_ocid", "linux_image_ocid"} - vars_dict.keys()
    if missing:
        click.echo(
            f"  ⚠  Missing: {', '.join(sorted(missing))}\n"
            f"     These are needed for compute techniques. "
            f"Edit {dest.name} to add them.\n"
        )


# ---------------------------------------------------------------------------
# Mode 6: Technique testing
# ---------------------------------------------------------------------------

@cli.command("test-techniques")
@click.argument("technique_name", required=False, default=None)
@click.option(
    "-c", "--category",
    "category",
    type=click.Choice(["compute", "iam", "storage", "vault", "functions", "container", "other"]),
    default=None,
    help="Run only techniques in this category.",
)
@click.option(
    "--no-destroy",
    is_flag=True,
    default=False,
    help="Keep Terraform environment running after the test (useful for debugging).",
)
@click.option(
    "--list",
    "list_only",
    is_flag=True,
    default=False,
    help="List matching techniques without running them.",
)
@click.option(
    "--vars-file",
    "vars_file",
    type=click.Path(exists=True),
    default=None,
    help=(
        "Path to a JSON file with shared Terraform variables "
        "(default: techniques/shared.tfvars.json)."
    ),
)
def test_techniques_cmd(
    technique_name: str | None,
    category: str | None,
    no_destroy: bool,
    list_only: bool,
    vars_file: str | None,
) -> None:
    """Deploy and verify attack technique scenarios via Terraform.

    \b
    For each matching technique the runner will:
      1. Run ``terraform init && apply`` to provision the attack scenario.
      2. Execute the technique's ``test.py`` using the attacker credentials
         produced by Terraform.
      3. Report PASS / FAIL / SKIP / ERROR.
      4. Run ``terraform destroy`` to clean up (unless --no-destroy).

    \b
    Shared Terraform variables (tenancy_ocid, compartment_ocid, region, …)
    are read from ``techniques/shared.tfvars.json`` by default.  Copy
    ``techniques/shared.tfvars.json.example`` to get started.

    \b
    Examples
    --------
      python main.py test-techniques
      python main.py test-techniques oci_create_api_key
      python main.py test-techniques --category iam
      python main.py test-techniques --category compute --no-destroy
      python main.py test-techniques --list
    """
    from modules.technique_runner import (
        discover_techniques,
        run_technique,
        print_results,
    )

    techniques_root = _PROJECT_ROOT / "techniques"
    if not techniques_root.is_dir():
        raise click.ClickException(
            f"techniques/ directory not found at {techniques_root}"
        )

    techniques = discover_techniques(
        techniques_root, category=category, name=technique_name
    )

    if not techniques:
        click.echo("No matching techniques found.")
        return

    if list_only:
        click.echo(f"\n  {'NAME':<50}  {'CATEGORY':<10}  TF  TEST")
        click.echo("  " + "-" * 72)
        for t in techniques:
            tf_mark = "✓" if t.has_terraform else "✗"
            test_mark = "✓" if t.has_test else "✗"
            click.echo(
                f"  {t.name:<50}  {t.category:<10}  {tf_mark}   {test_mark}"
            )
        click.echo(f"\n  {len(techniques)} technique(s) listed.\n")
        return

    # Load shared vars
    default_vars = techniques_root / "shared.tfvars.json"
    vars_path = Path(vars_file) if vars_file else default_vars
    if not vars_path.exists():
        raise click.ClickException(
            f"Shared variables file not found: {vars_path}\n"
            f"Copy techniques/shared.tfvars.json.example → "
            f"techniques/shared.tfvars.json and fill in your values."
        )
    raw_vars = vars_path.read_text().strip()
    if not raw_vars:
        raise click.ClickException(
            f"Shared variables file is empty: {vars_path}\n"
            f"Copy techniques/shared.tfvars.json.example → "
            f"techniques/shared.tfvars.json and fill in your values."
        )
    try:
        shared_vars: dict = json.loads(raw_vars)
    except json.JSONDecodeError as exc:
        raise click.ClickException(
            f"Invalid JSON in {vars_path}: {exc}"
        )

    results_dir = _PROJECT_ROOT / "test_results"

    _PHASE_ICONS = {"init": "⚙", "apply": "🔨", "test": "🧪", "diagnostics": "🔍", "destroy": "🗑"}
    _last_phase: dict[str, str] = {}

    def _cli_progress(*, phase: str, message: str, done: bool = False) -> None:
        icon = _PHASE_ICONS.get(phase, "·")
        if done:
            click.echo(f"  {icon} {phase}: {message}")
            _last_phase.pop("current", None)
        else:
            if _last_phase.get("current") != phase:
                click.echo(f"  {icon} {phase}: {message}")
                _last_phase["current"] = phase

    results = []
    for t in techniques:
        click.echo(f"\n→ {t.name}  [{t.category}]")
        result = run_technique(
            t,
            shared_vars,
            destroy=not no_destroy,
            results_dir=results_dir,
            progress=_cli_progress,
        )
        results.append(result)
        status_line = f"  {result.status}"
        if result.message:
            status_line += f": {result.message[:120]}"
        click.echo(status_line)

    print_results(results)

    failed = sum(1 for r in results if r.status in ("FAIL", "ERROR"))
    raise SystemExit(1 if failed else 0)



def main() -> None:
    """Entry point for ``python main.py``."""
    cli()


if __name__ == "__main__":
    main()
