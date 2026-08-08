# polci

Research tool for understanding OCI IAM policy evaluation. Parses policy statements, expands them against Oracle's permission reference data, and computes effective permissions per user.

The main output of this research is [`docs/OCI_POLICY_EVALUATION.md`](docs/OCI_POLICY_EVALUATION.md) -- a guide to simulating OCI policy evaluation outside of OCI.

## Setup

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Commands

```bash
uv run main.py local            # Parse data/statements.txt offline (no OCI API needed)
uv run main.py oci              # Full evaluation against a live OCI tenancy
uv run main.py user <email>     # Effective permissions for a single user
uv run main.py resolve-apis "LaunchInstance,GetInstance"  # Minimal policy for given APIs
```

## Scraper

Scrapes Oracle's policy reference documentation into `data/policy_reference_scraped.json`.

```bash
python -m modules.scraper full --services   # Full scrape
python -m modules.scraper index             # Discovery only
python -m modules.scraper url <url>         # Single service page
```

## Regenerating the ANTLR parser

Required after changes to `grammar/OciPolicy.g4`. Needs Java installed.

```bash
./scripts/generate_parser.sh
```

## Project structure

```
grammar/OciPolicy.g4          ANTLR grammar for OCI policy statements
modules/
  policy_parser.py             ANTLR-based parser
  statement_eval.py            Statement -> permission grant expansion
  permission_index.py          Permission index built from scraped reference data
  effective_perms.py           Per-user effective permission resolution
  api_to_policy.py             API operation -> minimal policy resolver
  scraper.py                   Oracle docs scraper
data/
  policy_reference_scraped.json  Scraped VRP tables, resource types, API mappings
  api_operation_permissions.json Flat API-to-permission mappings
  statements.txt               Sample policy statements for local testing
```
