#!/usr/bin/env python3
"""
Run all OCI discovery techniques and dump full API responses.

Calls each of the 12 discovery APIs (ListUsers, ListGroups, ListDynamicGroups,
ListPolicies, ListBuckets, ListInstances, ListVaults, ListKeys, ListSecrets,
ListApplications, ListFunctions, ListContainerRepositories) and writes:
  • Pretty-printed JSON to stdout
  • Per-entity JSON files under  discovery_output/<entity_type>/

Usage:
    python scripts/run_discovery.py                          # use defaults from ~/.oci/config
    python scripts/run_discovery.py --compartment-ocid ocid1.compartment...
    python scripts/run_discovery.py --profile MY_PROFILE
    python scripts/run_discovery.py --output-dir /tmp/disc
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import oci


def _serialize(obj: Any) -> Any:
    """Convert OCI SDK model objects to JSON-friendly dicts."""
    if hasattr(obj, "__dict__"):
        return {k: _serialize(v) for k, v in vars(obj).items() if not k.startswith("_")}
    if isinstance(obj, (list, tuple)):
        return [_serialize(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def _write_entity_files(output_dir: Path, entity_type: str, items: list[dict]) -> Path:
    """Write a combined JSON and individual per-entity files."""
    entity_dir = output_dir / entity_type
    entity_dir.mkdir(parents=True, exist_ok=True)

    combined_path = entity_dir / f"_all_{entity_type}.json"
    combined_path.write_text(json.dumps(items, indent=2, default=str))

    for i, item in enumerate(items):
        name = (
            item.get("display_name")
            or item.get("name")
            or item.get("id", f"item_{i}")
        )
        safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in str(name))
        file_path = entity_dir / f"{safe_name}.json"
        file_path.write_text(json.dumps(item, indent=2, default=str))

    return entity_dir


def _header(title: str) -> None:
    width = 80
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def _paginate(list_fn, **kwargs) -> list:
    """Generic paginator for OCI list_* calls."""
    items: list = []
    page = None
    while True:
        if page:
            kwargs["page"] = page
        resp = list_fn(**kwargs)
        data = resp.data if hasattr(resp, "data") else resp
        if isinstance(data, list):
            items.extend(data)
        else:
            items.append(data)
        page = getattr(resp, "next_page", None) or resp.headers.get("opc-next-page")
        if not page:
            break
    return items


def discover_users(identity: oci.identity.IdentityClient, tenancy_ocid: str) -> list[dict]:
    _header("USERS (ListUsers)")
    items = _paginate(identity.list_users, compartment_id=tenancy_ocid)
    return [_serialize(u) for u in items]


def discover_groups(identity: oci.identity.IdentityClient, tenancy_ocid: str) -> list[dict]:
    _header("GROUPS (ListGroups)")
    items = _paginate(identity.list_groups, compartment_id=tenancy_ocid)
    return [_serialize(g) for g in items]


def discover_dynamic_groups(identity: oci.identity.IdentityClient, tenancy_ocid: str) -> list[dict]:
    _header("DYNAMIC GROUPS (ListDynamicGroups)")
    items = _paginate(identity.list_dynamic_groups, compartment_id=tenancy_ocid)
    return [_serialize(dg) for dg in items]


def discover_policies(identity: oci.identity.IdentityClient, compartment_ocid: str) -> list[dict]:
    _header("POLICIES (ListPolicies)")
    items = _paginate(identity.list_policies, compartment_id=compartment_ocid)
    return [_serialize(p) for p in items]


def discover_buckets(
    os_client: oci.object_storage.ObjectStorageClient,
    namespace: str,
    compartment_ocid: str,
) -> list[dict]:
    _header("OBJECT STORAGE BUCKETS (ListBuckets)")
    items = _paginate(os_client.list_buckets, namespace_name=namespace, compartment_id=compartment_ocid)
    return [_serialize(b) for b in items]


def discover_instances(compute: oci.core.ComputeClient, compartment_ocid: str) -> list[dict]:
    _header("COMPUTE INSTANCES (ListInstances)")
    items = _paginate(compute.list_instances, compartment_id=compartment_ocid)
    return [_serialize(i) for i in items]


def discover_vaults(kms_vault: oci.key_management.KmsVaultClient, compartment_ocid: str) -> list[dict]:
    _header("VAULTS (ListVaults)")
    items = _paginate(kms_vault.list_vaults, compartment_id=compartment_ocid)
    return [_serialize(v) for v in items]


def discover_kms_keys(
    config: dict,
    vaults: list[dict],
    compartment_ocid: str,
) -> list[dict]:
    _header("KMS KEYS (ListKeys)")
    all_keys: list[dict] = []
    for vault in vaults:
        mgmt_endpoint = vault.get("management_endpoint")
        lifecycle = vault.get("lifecycle_state", "")
        if not mgmt_endpoint or lifecycle not in ("ACTIVE", ""):
            continue
        print(f"  Querying vault: {vault.get('display_name')} ({vault.get('id', '')[:40]}...)")
        kms_mgmt = oci.key_management.KmsManagementClient(config, service_endpoint=mgmt_endpoint)
        keys = _paginate(kms_mgmt.list_keys, compartment_id=compartment_ocid)
        serialized = [_serialize(k) for k in keys]
        for k in serialized:
            k["_vault_id"] = vault.get("id")
            k["_vault_name"] = vault.get("display_name")
        all_keys.extend(serialized)
    return all_keys


def discover_secrets(vaults_client: oci.vault.VaultsClient, compartment_ocid: str) -> list[dict]:
    _header("VAULT SECRETS (ListSecrets)")
    items = _paginate(vaults_client.list_secrets, compartment_id=compartment_ocid)
    return [_serialize(s) for s in items]


def discover_function_apps(
    fn_mgmt: oci.functions.FunctionsManagementClient,
    compartment_ocid: str,
) -> list[dict]:
    _header("FUNCTION APPLICATIONS (ListApplications)")
    items = _paginate(fn_mgmt.list_applications, compartment_id=compartment_ocid)
    return [_serialize(a) for a in items]


def discover_functions(
    fn_mgmt: oci.functions.FunctionsManagementClient,
    apps: list[dict],
) -> list[dict]:
    _header("FUNCTIONS (ListFunctions)")
    all_fns: list[dict] = []
    for app in apps:
        app_id = app.get("id")
        if not app_id:
            continue
        lifecycle = app.get("lifecycle_state", "")
        if lifecycle not in ("ACTIVE", ""):
            continue
        print(f"  Querying app: {app.get('display_name')} ({app_id[:40]}...)")
        fns = _paginate(fn_mgmt.list_functions, application_id=app_id)
        serialized = [_serialize(f) for f in fns]
        for f in serialized:
            f["_application_id"] = app_id
            f["_application_name"] = app.get("display_name")
        all_fns.extend(serialized)
    return all_fns


def discover_repositories(
    artifacts: oci.artifacts.ArtifactsClient,
    compartment_ocid: str,
) -> list[dict]:
    _header("CONTAINER REPOSITORIES (ListContainerRepositories)")
    resp = artifacts.list_container_repositories(compartment_id=compartment_ocid)
    items = resp.data.items if hasattr(resp.data, "items") else resp.data
    return [_serialize(r) for r in items]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all OCI discovery techniques")
    parser.add_argument(
        "--profile",
        default=os.environ.get("OCI_CLI_PROFILE", "DEFAULT"),
        help="OCI config profile name (default: DEFAULT)",
    )
    parser.add_argument(
        "--config-file",
        default=os.environ.get("OCI_CLI_CONFIG_FILE", "~/.oci/config"),
        help="Path to OCI config file",
    )
    parser.add_argument(
        "--compartment-ocid",
        default=None,
        help="Compartment OCID to scan (default: tenancy root)",
    )
    parser.add_argument(
        "--output-dir",
        default="discovery_output",
        help="Directory for per-entity JSON output (default: discovery_output/)",
    )
    args = parser.parse_args()

    config = oci.config.from_file(file_location=args.config_file, profile_name=args.profile)
    tenancy_ocid = config["tenancy"]
    compartment_ocid = args.compartment_ocid or tenancy_ocid

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"OCI Discovery Runner")
    print(f"  Profile:     {args.profile}")
    print(f"  Tenancy:     {tenancy_ocid}")
    print(f"  Compartment: {compartment_ocid}")
    print(f"  Output:      {output_dir.resolve()}")

    identity = oci.identity.IdentityClient(config)
    os_client = oci.object_storage.ObjectStorageClient(config)
    compute = oci.core.ComputeClient(config)
    kms_vault_client = oci.key_management.KmsVaultClient(config)
    vaults_client = oci.vault.VaultsClient(config)
    fn_mgmt = oci.functions.FunctionsManagementClient(config)
    artifacts = oci.artifacts.ArtifactsClient(config)

    results: dict[str, list[dict]] = {}
    errors: dict[str, str] = {}

    # --- IAM entities (tenancy-scoped) ---
    for name, fn in [
        ("users", lambda: discover_users(identity, tenancy_ocid)),
        ("groups", lambda: discover_groups(identity, tenancy_ocid)),
        ("dynamic_groups", lambda: discover_dynamic_groups(identity, tenancy_ocid)),
    ]:
        try:
            data = fn()
            results[name] = data
        except oci.exceptions.ServiceError as e:
            errors[name] = f"{e.status} {e.code}: {e.message}"
            print(f"  ERROR: {errors[name]}")

    # --- Compartment-scoped entities ---
    for name, fn in [
        ("policies", lambda: discover_policies(identity, compartment_ocid)),
        ("instances", lambda: discover_instances(compute, compartment_ocid)),
        ("vaults", lambda: discover_vaults(kms_vault_client, compartment_ocid)),
        ("secrets", lambda: discover_secrets(vaults_client, compartment_ocid)),
        ("function_apps", lambda: discover_function_apps(fn_mgmt, compartment_ocid)),
        ("repositories", lambda: discover_repositories(artifacts, compartment_ocid)),
    ]:
        try:
            data = fn()
            results[name] = data
        except oci.exceptions.ServiceError as e:
            errors[name] = f"{e.status} {e.code}: {e.message}"
            print(f"  ERROR: {errors[name]}")

    # --- Bucket discovery (needs namespace) ---
    try:
        ns_resp = os_client.get_namespace(compartment_id=tenancy_ocid)
        namespace = ns_resp.data
        data = discover_buckets(os_client, namespace, compartment_ocid)
        results["buckets"] = data
    except oci.exceptions.ServiceError as e:
        errors["buckets"] = f"{e.status} {e.code}: {e.message}"
        print(f"  ERROR: {errors['buckets']}")

    # --- KMS Keys (needs vault management endpoints) ---
    if "vaults" in results:
        try:
            data = discover_kms_keys(config, results["vaults"], compartment_ocid)
            results["kms_keys"] = data
        except oci.exceptions.ServiceError as e:
            errors["kms_keys"] = f"{e.status} {e.code}: {e.message}"
            print(f"  ERROR: {errors['kms_keys']}")

    # --- Functions (needs application IDs) ---
    if "function_apps" in results:
        try:
            data = discover_functions(fn_mgmt, results["function_apps"])
            results["functions"] = data
        except oci.exceptions.ServiceError as e:
            errors["functions"] = f"{e.status} {e.code}: {e.message}"
            print(f"  ERROR: {errors['functions']}")

    # --- Print results and write files ---
    _header("SUMMARY")

    for entity_type, items in results.items():
        count = len(items)
        entity_dir = _write_entity_files(output_dir, entity_type, items)
        print(f"\n  {entity_type}: {count} item(s)  →  {entity_dir}/")

        if items:
            print(json.dumps(items, indent=2, default=str))

    if errors:
        print(f"\n{'=' * 80}")
        print("  ERRORS")
        print(f"{'=' * 80}")
        for name, err in errors.items():
            print(f"  {name}: {err}")

    # Write a combined manifest
    manifest = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "tenancy_ocid": tenancy_ocid,
        "compartment_ocid": compartment_ocid,
        "counts": {k: len(v) for k, v in results.items()},
        "errors": errors,
    }
    manifest_path = output_dir / "_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n  Manifest: {manifest_path}")

    if errors:
        print(f"\n  {len(errors)} entity type(s) had errors — see above.")
        sys.exit(1)

    print("\n  Done.")


if __name__ == "__main__":
    main()
