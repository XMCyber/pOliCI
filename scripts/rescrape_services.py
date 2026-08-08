#!/usr/bin/env python3
"""Re-scrape specific services from correct/override URLs and update the JSON.

Some OCI services have their policy-reference documentation hosted outside
the main index page (e.g. autonomous database, digital assistant, database
migration).  This script fetches those override URLs, runs the standard
extractors, and merges the results back into
``data/policy_reference_scraped.json``.

Usage::

    python scripts/rescrape_services.py              # re-scrape with cache
    python scripts/rescrape_services.py --no-cache   # bypass HTML cache
    python scripts/rescrape_services.py --dry-run    # preview without writing
"""
import json
import sys
from dataclasses import asdict
from pathlib import Path

import click

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bs4 import BeautifulSoup

from modules.scraper import (
    _extract_api_permissions,
    _extract_resource_types,
    _extract_service_variables,
    _extract_verb_resource_permissions,
    fetch_page,
)

DATA_PATH = Path("data/policy_reference_scraped.json")
CACHE_DIR = Path("data/scrape_cache")

# URL overrides: service_id → list of URLs to fetch and merge from.
URL_OVERRIDES: dict[str, list[str]] = {
    "give_users_permissions_to_manage_analytics_cloud_instances": [
        "https://docs.oracle.com/en-us/iaas/analytics-cloud/doc/permissions-manage-analytics-cloud-instances.html",
    ],
    "database": [
        "https://docs.oracle.com/en/cloud/paas/autonomous-database/serverless/adbsb/autonomous-database-iam-policies.html",
        "https://docs.oracle.com/en/cloud/paas/autonomous-database/dedicated/adbdf/index.html",
        "https://docs.oracle.com/en/cloud/paas/bm-and-vm-dbs-cloud/tfffs/index.html",
        "https://docs.oracle.com/en/engineered-systems/exadata-cloud-service/ecscm/ecs-policy-details.html",
        "https://docs.oracle.com/iaas/exadata/doc/ecc-policy-details.html",
        "https://docs.oracle.com/en/engineered-systems/exadata-database-exascale/exdxs/exadb-xs-policy-details.html",
        "https://docs.oracle.com/iaas/external-database/doc/policy-details-external-database.html",
    ],
    "database_management": [
        "https://docs.oracle.com/en-us/iaas/database-management/doc/policy-details-database-management.html",
    ],
    "database_migration_policies": [
        "https://docs.oracle.com/en-us/iaas/database-migration/doc/policies.html",
        "https://docs.oracle.com/en-us/iaas/database-migration/doc/verb_resource-type_odms-migration.html",
        "https://docs.oracle.com/en-us/iaas/database-migration/doc/verb_resource-type_odms-connection.html",
        "https://docs.oracle.com/en-us/iaas/database-migration/doc/verb_resource-type_odms-agent.html",
        "https://docs.oracle.com/en-us/iaas/database-migration/doc/verb_resource-type_odms-job.html",
    ],
    "digital_assistant_policies": [
        "https://docs.oracle.com/en/cloud/paas/digital-assistant/rest-api-oci/permissions.html",
        "https://docs.oracle.com/en-us/iaas/digital-assistant/doc/users-groups-and-policies1.html",
    ],
    "iam_policies": [
        "https://docs.oracle.com/en-us/iaas/mysql-database/doc/iam-policies.html",
        "https://docs.oracle.com/en-us/iaas/mysql-database/doc/resource-types.html",
    ],
    "network_policy_rules_and_rule_components": [
        "https://docs.oracle.com/en-us/iaas/Content/network-firewall/iam-policy-reference.htm",
    ],
    "oracle_cloud_migration_policies": [
        "https://docs.oracle.com/en-us/iaas/Content/cloud-migration/cloud-migration-servicepolicies.htm",
        "https://docs.oracle.com/en-us/iaas/Content/cloud-migration/cloud-migration-resource-types-permissions-discovery.htm",
    ],
    "os_management_hub_policies": [
        "https://docs.oracle.com/en-us/iaas/osmh/doc/policies.htm",
        "https://docs.oracle.com/en-us/iaas/osmh/doc/policies-reference.htm",
    ],
    "create_iam_policies_for_oracle_data_safe_users": [
        "https://docs.oracle.com/en/cloud/paas/data-safe/dsiad/datasafe_iam.html",
    ],
    "understand_big_data_service_resources_and_permissions_in_iam_policies": [
        "https://docs.oracle.com/en-us/iaas/Content/bigdata/policies-permissions.htm",
    ],
    "globally_distributed_autonomous_ai_database_policies": [
        "https://docs.oracle.com/en/cloud/paas/globally-distributed-autonomous-database/user/policies.html",
    ],
    "see_policies_and_permissions": [
        "https://docs.oracle.com/en-us/iaas/wlms/doc/policies.htm",
        "https://docs.oracle.com/en-us/iaas/wlms/doc/set-up-policies.htm",
    ],
}

# Services that are hub/overview pages and won't have VRP data
NOT_APPLICABLE = {
    "overview_of_working_with_policies",  # General policy management overview
    "cloud_shell",  # Minimal IAM surface, no VRP tables
}


def extract_all(html: str, url: str) -> dict:
    """Run all extractors on HTML and return a dict of results."""
    soup = BeautifulSoup(html, "html.parser")
    ind, agg = _extract_resource_types(soup)
    variables = _extract_service_variables(soup)
    vrps = _extract_verb_resource_permissions(soup)
    api_perms = _extract_api_permissions(soup)
    return {
        "individual_resource_types": ind,
        "aggregate_resource_types": agg,
        "variables": [asdict(v) for v in variables],
        "verb_resource_permissions": [asdict(v) for v in vrps],
        "api_permissions": [asdict(a) for a in api_perms],
    }


def merge_results(base: dict, new: dict) -> dict:
    """Merge new extraction results into base, preferring non-empty values."""
    for key in ("individual_resource_types", "aggregate_resource_types"):
        if new[key] and not base.get(key):
            base[key] = new[key]
    for key in ("variables", "verb_resource_permissions", "api_permissions"):
        if new[key]:
            existing_set = {json.dumps(v, sort_keys=True) for v in base.get(key, [])}
            for item in new[key]:
                if json.dumps(item, sort_keys=True) not in existing_set:
                    base.setdefault(key, []).append(item)
    return base


@click.command()
@click.option("--no-cache", is_flag=True, default=False, help="Bypass the on-disk HTML cache.")
@click.option("--dry-run", is_flag=True, default=False, help="Preview changes without writing to disk.")
def main(no_cache: bool, dry_run: bool) -> None:
    """Re-scrape services using override URLs and merge into the JSON.

    \b
    Iterates over URL_OVERRIDES (service_id -> list of URLs), fetches
    each page, runs the standard extractors, and merges the results
    back into data/policy_reference_scraped.json.  Services listed in
    NOT_APPLICABLE are marked with an error tag instead.
    """
    use_cache = not no_cache

    data = json.loads(DATA_PATH.read_text())
    services = data["services"]
    updated_count = 0

    for sid, urls in URL_OVERRIDES.items():
        svc = next((s for s in services if s["id"] == sid), None)
        if not svc:
            click.echo(f"  SKIP {sid}: not found in JSON")
            continue

        click.echo(f"\n{'='*60}")
        click.echo(f"Processing: {sid}")
        click.echo(f"  Original URL: {svc.get('source_url', 'N/A')}")

        merged: dict = {
            "individual_resource_types": svc.get("individual_resource_types", []),
            "aggregate_resource_types": svc.get("aggregate_resource_types", []),
            "variables": svc.get("variables", []),
            "verb_resource_permissions": [],
            "api_permissions": [],
        }

        for override_url in urls:
            click.echo(f"  Fetching: {override_url}")
            try:
                html = fetch_page(override_url, cache_dir=CACHE_DIR, use_cache=use_cache)
                result = extract_all(html, override_url)
                click.echo(
                    f"    -> {len(result['verb_resource_permissions'])} VRPs, "
                    f"{len(result['api_permissions'])} APIs, "
                    f"{len(result['individual_resource_types'])} resource types"
                )
                merged = merge_results(merged, result)
            except Exception as e:
                click.echo(f"    ERROR: {e}", err=True)

        vrp_count = len(merged["verb_resource_permissions"])
        api_count = len(merged["api_permissions"])
        empty_rt = sum(1 for v in merged["verb_resource_permissions"] if not v.get("resource_type"))

        click.echo(f"  Result: {vrp_count} VRPs ({empty_rt} empty RT), {api_count} APIs")

        if vrp_count > 0 or api_count > 0:
            for key in merged:
                if merged[key]:
                    svc[key] = merged[key]
            if urls:
                svc["source_url"] = urls[0]
            updated_count += 1
            click.echo("  Updated")
        else:
            click.echo("  No data extracted")

    for sid in NOT_APPLICABLE:
        svc = next((s for s in services if s["id"] == sid), None)
        if svc and not svc.get("verb_resource_permissions"):
            if "not_applicable" not in svc.get("errors", []):
                svc.setdefault("errors", []).append(
                    "not_applicable: overview/hub page without VRP data"
                )
                click.echo(f"\n  Marked {sid} as not applicable")

    if not dry_run:
        DATA_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        click.echo(f"\n{'='*60}")
        click.echo(f"Updated {updated_count} services. Saved to {DATA_PATH}")
    else:
        click.echo(f"\n{'='*60}")
        click.echo(f"DRY RUN: would update {updated_count} services")


if __name__ == "__main__":
    main()
