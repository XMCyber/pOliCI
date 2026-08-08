"""
Scraper for OCI Policy Reference documentation.

Discovers policy reference pages from the main index, fetches them with
caching and rate limiting, and extracts:

- **General variables** — Name, Type, Description for every general IAM
  variable (e.g. ``request.user.id``, ``target.compartment.name``).
- **Verbs** — the four cumulative verb levels: inspect, read, use, manage.
- **Per-service detail** — resource types (individual + aggregate),
  service-specific variables, verb+resource→permission mappings, and
  API-operation→permission mappings.

The scraper operates in several modes selectable from the CLI:

``full`` (default)
    Run link discovery on the policy reference index, extract general
    variables, and (when ``--services`` is given) scrape every service
    detail page.  Produces ``policy_reference_scraped.json`` and, when
    services are scraped, ``api_operation_permissions.json``.

``index``
    Only discover and classify links from the policy reference index
    page.  Writes ``policy_reference_links.json``.

``url``
    Scrape a single service-detail page by URL.  Useful for testing or
    re-scraping one service.  Writes ``single_service_scraped.json``.

See ``python -m modules.scraper --help`` for full option details.

Strategy notes: ``docs/SCRAPING_STRATEGY.md``
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POLICY_REFERENCE_INDEX = (
    "https://docs.oracle.com/en-us/iaas/Content/Identity/"
    "policyreference/policyreference.htm"
)
GENERAL_VARIABLES_URL = (
    "https://docs.oracle.com/en-us/iaas/Content/Identity/"
    "policyreference/policyreference_topic-General_Variables_for_All_Requests.htm"
)
VERBS_URL = (
    "https://docs.oracle.com/en-us/iaas/Content/Identity/"
    "policyreference/policyreference_topic-Verbs.htm"
)

DEFAULT_VERBS = ["inspect", "read", "use", "manage"]

USER_AGENT = "PolciScraper/0.1 (OCI policy reference extraction)"
REQUEST_TIMEOUT = 45.0
RATE_LIMIT_DELAY = 1.5  # seconds between requests
MAX_RETRIES = 3
RETRY_BACKOFF = 3.0

# Link classification constants
LINK_TYPE_VERBS = "verbs"
LINK_TYPE_RESOURCE_TYPES = "resource_types"
LINK_TYPE_GENERAL_VARIABLES = "general_variables"
LINK_TYPE_SERVICE_DETAIL = "service_detail"
LINK_TYPE_EXTERNAL = "external"
LINK_TYPE_OTHER = "other"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class GeneralVariable:
    name: str
    type: str
    description: str


@dataclass
class ServiceVariable:
    resource_types: list[str]
    name: str
    type: str
    description: str


@dataclass
class VerbResourcePermission:
    """Maps verb + resource_type → permissions + covered API operations."""
    resource_type: str
    verb: str
    permissions: list[str]
    apis_fully_covered: list[str]
    apis_partially_covered: list[str]


@dataclass
class ApiPermission:
    """Maps an API operation → required permissions."""
    api_operation: str
    permissions_required: str
    description: str = ""
    resource_type: str = ""
    notes: str = ""


@dataclass
class ServiceDetail:
    id: str
    name: str
    source_url: str
    individual_resource_types: list[str] = field(default_factory=list)
    aggregate_resource_types: list[str] = field(default_factory=list)
    variables: list[dict] = field(default_factory=list)
    verb_resource_permissions: list[dict] = field(default_factory=list)
    api_permissions: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class DiscoveredLink:
    url: str
    link_type: str
    title: str = ""


@dataclass
class ScrapeResult:
    source: str
    scraped_at: str = ""
    verbs: list[str] = field(default_factory=lambda: list(DEFAULT_VERBS))
    general_variables: list[dict] = field(default_factory=list)
    services: list[dict] = field(default_factory=list)
    discovered_urls: list[dict] = field(default_factory=list)

    def to_json(self, path: Path | None = None, *, minimal: bool = True) -> str:
        """Serialise the scrape result to JSON.

        Parameters
        ----------
        path:
            If given, write the JSON to this file.
        minimal:
            When *True* (the default), strip fields that are only needed for
            API-operation mapping (``api_permissions`` per service, and
            ``apis_fully_covered`` / ``apis_partially_covered`` inside each
            ``verb_resource_permissions`` entry).  The minimal output contains
            everything required to parse and evaluate OCI policy statements.
        """
        services = self.services
        if minimal:
            services = [self._strip_api_fields(svc) for svc in services]

        data = {
            "source": self.source,
            "scraped_at": self.scraped_at,
            "verbs": self.verbs,
            "general_variables": self.general_variables,
            "services": services,
            "discovered_urls": self.discovered_urls,
        }
        s = json.dumps(data, indent=2, ensure_ascii=False)
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(s, encoding="utf-8")
        return s

    @staticmethod
    def _strip_api_fields(svc: dict) -> dict:
        """Return a copy of *svc* without API-operation mapping fields."""
        out = {k: v for k, v in svc.items() if k != "api_permissions"}
        if "verb_resource_permissions" in out:
            out["verb_resource_permissions"] = [
                {k: v for k, v in vrp.items()
                 if k not in ("apis_fully_covered", "apis_partially_covered")}
                for vrp in out["verb_resource_permissions"]
            ]
        return out


# ---------------------------------------------------------------------------
# Fetch with cache, rate limit, retries
# ---------------------------------------------------------------------------


def _cache_path(url: str, cache_dir: Path) -> Path:
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    return cache_dir / f"{key}.html"


def fetch_page(
    url: str,
    client: httpx.Client | None = None,
    cache_dir: Path | None = None,
    use_cache: bool = True,
    rate_limit_delay: float = RATE_LIMIT_DELAY,
) -> str:
    """Fetch HTML for *url*. Returns cached copy when possible."""
    cache_file = _cache_path(url, cache_dir) if cache_dir else None
    if use_cache and cache_file and cache_file.exists():
        log.debug("cache hit  %s", url)
        return cache_file.read_text(encoding="utf-8", errors="replace")

    if rate_limit_delay > 0:
        time.sleep(rate_limit_delay)

    def _do_get() -> httpx.Response:
        if client is not None:
            return client.get(url)
        with httpx.Client(
            follow_redirects=True,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        ) as c:
            return c.get(url)

    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            log.info("fetch [%d/%d] %s", attempt + 1, MAX_RETRIES, url)
            resp = _do_get()
            resp.raise_for_status()
            html = resp.text
            if cache_file:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(html, encoding="utf-8")
            return html
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_err = exc
            wait = RETRY_BACKOFF ** attempt
            log.warning("  attempt %d failed (%s), retrying in %.0fs …", attempt + 1, exc, wait)
            if attempt < MAX_RETRIES - 1:
                time.sleep(wait)
    raise last_err or RuntimeError(f"fetch failed for {url}")


# ---------------------------------------------------------------------------
# Discovery: parse the index page and classify links
# ---------------------------------------------------------------------------


def _normalize_url(url: str, base: str) -> str:
    return urljoin(base, url).split("#")[0].rstrip("/")


def _is_oracle_docs(url: str) -> bool:
    return "docs.oracle.com" in urlparse(url).netloc


def _classify_policy_link(url: str, text: str) -> str:
    ul = url.lower()
    tl = (text or "").lower()

    # Canonical topic pages (known URLs)
    if "topic-verbs" in ul:
        return LINK_TYPE_VERBS
    if "topic-resourcetypes" in ul or "topic-resource" in ul:
        return LINK_TYPE_RESOURCE_TYPES
    if "general_variables" in ul:
        return LINK_TYPE_GENERAL_VARIABLES

    # Service detail pages under /policyreference/
    if "/policyreference/" in ul:
        # Skip the known topic- pages and the index itself
        if "topic-" in ul or ul.rstrip("/").endswith("policyreference"):
            return LINK_TYPE_OTHER
        return LINK_TYPE_SERVICE_DETAIL

    # External pages that are clearly policy/permissions references
    if any(
        kw in tl
        for kw in ("policies", "policy reference", "iam policies", "policy details", "permissions")
    ) or any(
        kw in ul
        for kw in ("policy-reference", "policyreference", "iam-policies", "policies.htm")
    ):
        return LINK_TYPE_EXTERNAL

    return LINK_TYPE_OTHER


def discover_links(
    html: str, base_url: str = POLICY_REFERENCE_INDEX
) -> list[DiscoveredLink]:
    """Parse the index page HTML and return classified policy-reference links."""
    soup = BeautifulSoup(html, "html.parser")
    main = (
        soup.find(id="dcoc-content-body")
        or soup.find(class_=re.compile(r"content|main|body"))
    )
    root = main if main else soup

    seen: set[str] = set()
    out: list[DiscoveredLink] = []
    for a in root.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:")):
            continue
        url = _normalize_url(href, base_url)
        if not _is_oracle_docs(url) or url in seen:
            continue
        seen.add(url)
        title = (a.get_text(" ", strip=True) or "").strip()
        link_type = _classify_policy_link(url, title)
        out.append(DiscoveredLink(url=url, link_type=link_type, title=title))
    return out


# ---------------------------------------------------------------------------
# Helpers: HTML / text normalization
# ---------------------------------------------------------------------------


def _cell_text(cell: Tag) -> str:
    """Collapse whitespace in a table cell while preserving meaningful newlines."""
    return re.sub(r"[ \t]+", " ", cell.get_text("\n", strip=True)).strip()


def _code_texts(tag: Tag) -> list[str]:
    """Return all <code> text content under *tag*."""
    return [c.get_text(strip=True) for c in tag.find_all("code") if c.get_text(strip=True)]


_SPLIT_ITEMS_NOISE = frozenset({
    "none", "no extra", "no extras", "n/a", "",
    "-", "\u2013", "\u2014",  # dash, en-dash, em-dash
})


def _split_items(text: str) -> list[str]:
    """Split a cell value that lists multiple items (newline / comma separated)."""
    items: list[str] = []
    for line in re.split(r"[\n,]+", text):
        line = line.strip().strip("+").strip()
        if line and line.lower() not in _SPLIT_ITEMS_NOISE:
            items.append(line)
    return items


def _to_service_id(title: str, url: str) -> str:
    """Derive a short snake_case service id from the page title or URL."""
    # Try from title: "Details for the Foo Bar Service" → "foo_bar"
    m = re.match(
        r"(?:details\s+for\s+(?:the\s+)?)?(.+?)(?:\s+service)?$", title, re.I
    )
    name = (m.group(1) if m else title).strip()
    # If title is a URL or looks like a filename, fall back to URL-based id
    if "/" in name or name.endswith((".htm", ".html")):
        return _id_from_url(url)
    name = re.sub(r"[^\w\s]", "", name).strip()
    sid = re.sub(r"\s+", "_", name).lower()
    return sid or _id_from_url(url)


def _id_from_url(url: str) -> str:
    slug = urlparse(url).path.split("/")[-1].replace(".htm", "").replace(".html", "")
    slug = slug.replace("policyreference", "").strip("-_")
    return slug or "unknown"


def _title_from_html(html: str) -> str:
    """Try to extract a page title from the HTML <h1> or <title>."""
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    t = soup.find("title")
    if t:
        return t.get_text(strip=True)
    return ""


# ---------------------------------------------------------------------------
# Extract: General Variables table
# ---------------------------------------------------------------------------


def extract_general_variables(html: str) -> list[GeneralVariable]:
    """Extract Name / Type / Description from the General Variables table."""
    soup = BeautifulSoup(html, "html.parser")
    variables: list[GeneralVariable] = []

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        header = [_cell_text(c).lower() for c in rows[0].find_all(["th", "td"])]
        name_i = next((i for i, h in enumerate(header) if "name" in h), -1)
        type_i = next((i for i, h in enumerate(header) if "type" in h), -1)
        desc_i = next((i for i, h in enumerate(header) if "desc" in h), -1)
        if name_i < 0 or desc_i < 0:
            continue
        if type_i < 0:
            type_i = 1 if name_i == 0 else 0

        for tr in rows[1:]:
            cells = tr.find_all(["td", "th"])
            if len(cells) <= max(name_i, type_i, desc_i):
                continue
            name_val = _cell_text(cells[name_i]).strip("`")
            # Prefer <code> content for the name
            codes = _code_texts(cells[name_i])
            if codes:
                name_val = codes[0]
            type_val = _cell_text(cells[type_i]) if type_i < len(cells) else ""
            desc_val = _cell_text(cells[desc_i]) if desc_i < len(cells) else ""
            if name_val:
                variables.append(GeneralVariable(name=name_val, type=type_val, description=desc_val))
    return variables


# ---------------------------------------------------------------------------
# Extract: Service detail pages
# ---------------------------------------------------------------------------


def _find_heading(soup: BeautifulSoup | Tag, pattern: str) -> Tag | None:
    """Find the first heading (h1–h6) whose text matches *pattern* (case-insensitive)."""
    for h in soup.find_all(re.compile(r"^h[1-6]$")):
        if re.search(pattern, h.get_text(strip=True), re.I):
            return h
    return None


def _siblings_until_heading(heading: Tag) -> list[Tag]:
    """Collect sibling tags after *heading* until the next same-or-higher heading."""
    level = int(heading.name[1])
    collected: list[Tag] = []
    for sib in heading.find_next_siblings():
        if isinstance(sib, Tag) and re.match(r"^h[1-6]$", sib.name or ""):
            if int(sib.name[1]) <= level:
                break
        collected.append(sib)
    return collected


_VERB_NAMES = frozenset({"inspect", "read", "use", "manage"})


def _is_valid_resource_type(name: str) -> bool:
    """Return True if *name* looks like a real resource-type identifier."""
    if not name or "<" in name or ">" in name:
        return False
    # Reject bare verb names that get scraped as resource types
    if name.lower() in _VERB_NAMES:
        return False
    # Must be lowercase-ish alphanumeric with hyphens
    return bool(re.match(r"^[a-z][a-z0-9_-]*$", name))


def _extract_resource_types(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """Extract individual and aggregate resource-type names from the page."""
    individual: list[str] = []
    aggregate: list[str] = []

    heading = _find_heading(soup, r"resource.?type")
    if not heading:
        return individual, aggregate

    siblings = list(heading.find_next_siblings()) if heading.name == "h1" else _siblings_until_heading(heading)
    current_bucket = individual  # default

    for elem in siblings:
        if not isinstance(elem, Tag):
            continue
        text_full = elem.get_text(strip=True)
        text = text_full.lower()

        # Detect sub-headings that switch between individual / aggregate
        if re.match(r"^h[2-5]$", elem.name or ""):
            if "individual" in text:
                current_bucket = individual
            elif "aggregate" in text or "family" in text:
                current_bucket = aggregate
            continue

        # The content may be wrapped in a single <div> that contains both
        # "Individual" and "Aggregate" sub-sections as inline text.
        # Walk through the div's children to detect section switches.
        if elem.name == "div":
            _walk_resource_div(elem, individual, aggregate)
            continue

        # Collect <code> items from paragraphs or lists
        codes = [c for c in _code_texts(elem) if _is_valid_resource_type(c)]
        current_bucket.extend(codes)
        for li in elem.find_all("li"):
            li_codes = [c for c in _code_texts(li) if _is_valid_resource_type(c)]
            current_bucket.extend(li_codes)

    individual = list(dict.fromkeys(individual))
    aggregate = list(dict.fromkeys(aggregate))
    # Remove from individual anything that also appears in aggregate
    if aggregate:
        agg_set = set(aggregate)
        individual = [r for r in individual if r not in agg_set]
    return individual, aggregate


def _walk_resource_div(
    div: Tag, individual: list[str], aggregate: list[str]
) -> None:
    """Walk children of a wrapping <div> that contains both individual and
    aggregate resource-type sections, switching buckets on section-label text."""
    bucket = individual
    for child in div.descendants:
        if isinstance(child, Tag):
            child_text = child.get_text(strip=True).lower()
            # Section labels
            if re.match(r"^h[2-6]$", child.name or ""):
                if "aggregate" in child_text or "family" in child_text:
                    bucket = aggregate
                elif "individual" in child_text:
                    bucket = individual
            # Also detect bold/strong section labels
            if child.name in ("b", "strong"):
                if "aggregate" in child_text or "family" in child_text:
                    bucket = aggregate
                elif "individual" in child_text:
                    bucket = individual
        # Detect inline text that switches context (e.g. "Aggregate Resource-Type")
        if isinstance(child, str):
            t = child.strip().lower()
            if "aggregate" in t or "family resource" in t:
                bucket = aggregate
            elif "individual" in t:
                bucket = individual
        # Collect <code> resource type names
        if isinstance(child, Tag) and child.name == "code":
            name = child.get_text(strip=True)
            if _is_valid_resource_type(name):
                bucket.append(name)


def _extract_service_variables(soup: BeautifulSoup) -> list[ServiceVariable]:
    """Extract service-specific (supported) variables from tables."""
    variables: list[ServiceVariable] = []
    heading = _find_heading(soup, r"(?:supported|service).?variable")
    if not heading:
        return variables

    siblings = list(heading.find_next_siblings()) if heading.name == "h1" else _siblings_until_heading(heading)

    # Collect all tables under this section (may be inside wrapper divs)
    tables: list[Tag] = []
    for elem in siblings:
        if not isinstance(elem, Tag):
            continue
        if elem.name == "table":
            tables.append(elem)
        else:
            tables.extend(elem.find_all("table"))

    for table in tables:
        rows = table.find_all("tr")
        if not rows:
            continue
        header = [_cell_text(c).lower() for c in rows[0].find_all(["th", "td"])]
        # Flexible column detection
        rt_i = next(
            (i for i, h in enumerate(header) if "resource" in h or "operation" in h), -1
        )
        var_i = next(
            (i for i, h in enumerate(header) if "variable" in h), -1
        )
        # "Variable Type" column — must not collide with the variable-name column
        type_i = next(
            (i for i, h in enumerate(header) if "type" in h and i != var_i), -1
        )
        comment_i = next(
            (i for i, h in enumerate(header) if "comment" in h or "description" in h or "desc" in h), -1
        )
        if var_i < 0:
            continue

        for tr in rows[1:]:
            cells = tr.find_all(["td", "th"])
            if len(cells) <= var_i:
                continue
            rt_codes = _code_texts(cells[rt_i]) if 0 <= rt_i < len(cells) else []
            if not rt_codes and 0 <= rt_i < len(cells):
                rt_text = _cell_text(cells[rt_i])
                rt_codes = [t.strip() for t in re.split(r"\band\b|,", rt_text) if t.strip()]
            var_codes = _code_texts(cells[var_i])
            var_name_str = var_codes[0] if var_codes else _cell_text(cells[var_i]).strip("`")
            type_val = _cell_text(cells[type_i]).replace("\n", " ") if 0 <= type_i < len(cells) else ""
            desc_val = _cell_text(cells[comment_i]) if 0 <= comment_i < len(cells) else ""
            if var_name_str:
                variables.append(
                    ServiceVariable(
                        resource_types=rt_codes,
                        name=var_name_str,
                        type=type_val.strip(),
                        description=desc_val,
                    )
                )
    return variables


_CUMULATIVE_NOISE = {"inspect", "read", "use", "manage", "inspect +", "read +", "use +", "manage +"}
_PERM_NOISE = {"INSPECT", "READ", "USE", "MANAGE", "INSPECT +", "READ +", "USE +", "MANAGE +"}


def _looks_like_api_name(s: str) -> bool:
    """Heuristic: API operation names are PascalCase with no spaces."""
    return bool(s) and s[0].isupper() and " " not in s and len(s) > 2


def _clean_api_list(items: list[str]) -> list[str]:
    """Remove cumulative-verb noise and non-API fragments from an API list."""
    out: list[str] = []
    for item in items:
        stripped = item.strip()
        if stripped.lower() in _CUMULATIVE_NOISE:
            continue
        if stripped in _PERM_NOISE:
            continue
        # Keep items that look like API names (PascalCase, no spaces)
        if _looks_like_api_name(stripped):
            out.append(stripped)
            continue
        # Also keep ALLCAPS permission names that slipped in (they're useful)
        if re.match(r"^[A-Z_]+$", stripped) and len(stripped) > 3:
            out.append(stripped)
            continue
        # Skip other fragments (sentence parts, descriptions, etc.)
    return out


_VALID_PERM_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$")


def _clean_perm_list(items: list[str]) -> list[str]:
    """Validate and clean a scraped permissions list.

    Applies three stages:
    1. Strip whitespace, zero-width spaces, and trailing ``+`` markers.
    2. Rejoin fragments broken by line wraps (e.g. ``"FOO_BAR"`` +
       ``"_INSPECT"`` → ``"FOO_BAR_INSPECT"``).
    3. Positive validation: only keep items matching ``UPPER_SNAKE_CASE``
       with at least one underscore (the canonical OCI permission format).
    """
    # Stage 1: normalize
    normalized: list[str] = []
    for p in items:
        p = p.strip().replace("\u200b", "")
        p = re.sub(r"\s*\+$", "", p).strip()
        if p:
            normalized.append(p)

    # Stage 2: rejoin broken fragments ("FOO_BAR" + "_INSPECT" → "FOO_BAR_INSPECT")
    joined: list[str] = []
    for p in normalized:
        if p.startswith("_") and joined:
            joined[-1] = joined[-1] + p
        else:
            joined.append(p)

    # Stage 3: positive validation — only keep UPPER_SNAKE_CASE with underscore
    return [p for p in joined if _VALID_PERM_RE.match(p)]


def _extract_verb_resource_permissions(
    soup: BeautifulSoup,
) -> list[VerbResourcePermission]:
    """Extract verb + resource-type → permissions + API operations tables."""
    results: list[VerbResourcePermission] = []

    # Try several heading patterns to find the VRP section
    _VRP_HEADING_PATTERNS = [
        r"verb[s]?\s*(?:\+|and|,)\s*resource.?type\s*combination",
        r"details\s+for\s+(?:meta.?)?verb",
        r"details\s+(?:about\s+)?verb",
    ]
    heading = None
    for pat in _VRP_HEADING_PATTERNS:
        heading = _find_heading(soup, pat)
        if heading:
            break
    if not heading:
        # No VRP heading — check if there are standalone VRP-compatible tables
        # on the page (e.g. integration, visual_builder, blockchain pages).
        _headingless_tables: list[Tag] = []
        for tbl in soup.find_all("table"):
            rows = tbl.find_all("tr")
            if not rows:
                continue
            hdr = [c.get_text(strip=True).lower() for c in rows[0].find_all(["th", "td"])]
            # Standard: has "verb(s)" column
            if any("verb" in h for h in hdr):
                _headingless_tables.append(tbl)
            # Verb-section: single-cell verb header
            elif len(hdr) == 1 and hdr[0].strip().rstrip("+").strip() in DEFAULT_VERBS:
                _headingless_tables.append(tbl)
            # Resource-Permission: "Resource-Type | <VERB> Permission" (blockchain style)
            elif any("resource" in h for h in hdr) and any("permission" in h for h in hdr):
                _headingless_tables.append(tbl)
            # Verb-column: verbs as column headers (| Resource | inspect | read | ...)
            elif sum(1 for h in hdr if h.strip().rstrip("+").strip() in DEFAULT_VERBS) >= 2:
                _headingless_tables.append(tbl)
            # Permission-with-verb-sections: header has "permission" and table
            # contains rows where only the first cell is a verb name and rest are
            # empty (database_migration style)
            elif any("permission" in h for h in hdr):
                def _is_verb_row(r):
                    cells = r.find_all(["td", "th"])
                    if not cells:
                        return False
                    first = cells[0].get_text(strip=True).lower().rstrip("+").strip()
                    if first not in DEFAULT_VERBS:
                        return False
                    return len(cells) == 1 or all(
                        not c.get_text(strip=True) for c in cells[1:]
                    )
                if any(_is_verb_row(r) for r in rows[1:6]):
                    _headingless_tables.append(tbl)
        if not _headingless_tables:
            return results
        heading = None  # signal headingless mode

    # If headingless mode, use the discovered tables directly
    if heading is None:
        siblings = list(_headingless_tables)
    elif heading.name == "h1":
        # h1 means the entire page IS the verb+resource section.
        siblings = list(heading.find_next_siblings())
    else:
        siblings = _siblings_until_heading(heading)

    # If the immediate section has no tables, extend to include subsequent
    # same-level headings about resource types / families (common pattern:
    # h2 "Details for Verb..." followed by h2 "For X-family Resource Types").
    def _section_has_tables(elems: list[Tag]) -> bool:
        for e in elems:
            if not isinstance(e, Tag):
                continue
            if e.name == "table":
                return True
            if e.find("table"):
                return True
        return False

    if heading is not None and heading.name != "h1" and not _section_has_tables(siblings):
        _STOP_HEADINGS = re.compile(
            r"permission[s]?\s+required|policy\s+example|supported\s+variable",
            re.I,
        )
        level = int(heading.name[1])
        # Strategy A: extend to same-level sibling headings (flat structure)
        for sib in heading.find_next_siblings():
            if not isinstance(sib, Tag):
                continue
            if re.match(r"^h[1-6]$", sib.name or ""):
                sib_level = int(sib.name[1])
                if sib_level < level:
                    break
                if sib_level == level and _STOP_HEADINGS.search(sib.get_text(strip=True)):
                    break
            siblings.append(sib)

    # Strategy B: when heading is inside an <article>, look at sibling articles
    if heading is not None and not _section_has_tables(siblings):
        parent_article = heading.find_parent("article")
        if parent_article:
            _STOP_HEADINGS_B = re.compile(
                r"permission[s]?\s+required|policy\s+example|supported\s+variable",
                re.I,
            )
            for art_sib in parent_article.find_next_siblings("article"):
                art_heading = art_sib.find(re.compile(r"^h[1-6]$"))
                if art_heading and _STOP_HEADINGS_B.search(art_heading.get_text(strip=True)):
                    break
                siblings.append(art_sib)

    _do_fallback_scan = not _section_has_tables(siblings)

    current_resource_type = ""

    def _process_standard_table(table: Tag, rt: str) -> None:
        """Standard table: Verb | Permissions | APIs Fully Covered | APIs Partially Covered."""
        rows = table.find_all("tr")
        if not rows:
            return
        header = [_cell_text(c).lower() for c in rows[0].find_all(["th", "td"])]
        verb_i = next((i for i, h in enumerate(header) if "verb" in h), -1)
        perm_i = next((i for i, h in enumerate(header) if "permission" in h), -1)
        full_i = next(
            (i for i, h in enumerate(header) if "fully" in h or ("api" in h and "full" in h)),
            -1,
        )
        partial_i = next((i for i, h in enumerate(header) if "partial" in h), -1)
        if verb_i < 0 and perm_i < 0:
            return

        for tr in rows[1:]:
            cells = tr.find_all(["td", "th"])
            n = len(cells)
            verb_val = _cell_text(cells[verb_i]) if 0 <= verb_i < n else ""
            perm_val = _cell_text(cells[perm_i]) if 0 <= perm_i < n else ""
            full_val = _cell_text(cells[full_i]) if 0 <= full_i < n else ""
            partial_val = _cell_text(cells[partial_i]) if 0 <= partial_i < n else ""

            verb_clean = re.sub(r"\s*\+$", "", verb_val.lower().strip()).strip()
            if verb_clean not in DEFAULT_VERBS:
                first = verb_clean.split()[0] if verb_clean else ""
                verb_clean = first if first in DEFAULT_VERBS else verb_clean

            perms = _clean_perm_list(_split_items(perm_val))
            apis_full = _clean_api_list(_split_items(full_val))
            apis_partial = _clean_api_list(_split_items(partial_val))

            # Handle compound verbs like "read, use" by emitting
            # separate VRP entries for each verb.
            verbs_to_emit = [
                v.strip() for v in verb_clean.split(",")
                if v.strip() in DEFAULT_VERBS
            ]
            if not verbs_to_emit:
                verbs_to_emit = [verb_clean]

            if verbs_to_emit[0] or perms or apis_full:
                for v in verbs_to_emit:
                    results.append(
                        VerbResourcePermission(
                            resource_type=rt,
                            verb=v,
                            permissions=perms,
                            apis_fully_covered=apis_full,
                            apis_partially_covered=apis_partial,
                        )
                    )

    def _process_verb_section_table(table: Tag, rt: str) -> None:
        """Alternate (*) table: verbs appear as single-cell section-header rows
        within the table, followed by Permissions | APIs... header + data rows.

        Example structure:
            Row: [INSPECT]                           <- verb header
            Row: [Permissions, APIs Fully, APIs Part] <- column headers
            Row: [PERM_NAME, api1, ...]              <- data
            Row: [READ]                              <- next verb header
            ...
        """
        rows = table.find_all("tr")
        if not rows:
            return

        current_verb = ""
        col_perm_i = -1
        col_full_i = -1
        col_partial_i = -1

        for tr in rows:
            cells = tr.find_all(["td", "th"])
            texts = [_cell_text(c) for c in cells]

            # Verb-section row: single cell OR first cell is a verb with rest empty
            first_val = texts[0].lower().strip().rstrip("+").strip() if texts else ""
            rest_empty = all(not t.strip() for t in texts[1:]) if len(texts) > 1 else True
            if first_val in DEFAULT_VERBS and (len(cells) == 1 or rest_empty):
                current_verb = first_val
                continue
            # Single-cell rows that aren't verbs (e.g., continuation of API
            # names) should be skipped entirely.
            if len(cells) == 1:
                continue
            # Cumulative marker row (e.g., "INSPECT + | INSPECT+ | none")
            cumul_val = texts[0].lower().strip()
            if re.match(r"^(inspect|read|use|manage)\s*\+$", cumul_val, re.I):
                continue

            # Check if this row is a column-header row
            header_lower = [t.lower() for t in texts]
            is_header = any("permission" in h for h in header_lower)
            if is_header:
                col_perm_i = next((i for i, h in enumerate(header_lower) if "permission" in h), -1)
                col_full_i = next(
                    (i for i, h in enumerate(header_lower) if "fully" in h or ("api" in h and "full" in h)),
                    -1,
                )
                col_partial_i = next((i for i, h in enumerate(header_lower) if "partial" in h), -1)
                continue

            # Data row
            if not current_verb or col_perm_i < 0:
                continue
            n = len(cells)
            perm_val = texts[col_perm_i] if col_perm_i < n else ""
            full_val = texts[col_full_i] if 0 <= col_full_i < n else ""
            partial_val = texts[col_partial_i] if 0 <= col_partial_i < n else ""

            perms = _clean_perm_list(_split_items(perm_val))
            apis_full = _clean_api_list(_split_items(full_val))
            apis_partial = _clean_api_list(_split_items(partial_val))

            if perms or apis_full:
                results.append(
                    VerbResourcePermission(
                        resource_type=rt,
                        verb=current_verb,
                        permissions=perms,
                        apis_fully_covered=apis_full,
                        apis_partially_covered=apis_partial,
                    )
                )

    def _process_verb_column_table(table: Tag) -> None:
        """Table where verbs are column headers and rows are resource types.

        Example: | Resource Kind | inspect | read | use | manage |
                 | bds-instances | BDS_INSPECT | ... | ... | ... |
        """
        rows = table.find_all("tr")
        if not rows:
            return
        header = [_cell_text(c).lower() for c in rows[0].find_all(["th", "td"])]
        rt_i = next(
            (i for i, h in enumerate(header) if "resource" in h), -1
        )
        verb_cols: dict[str, int] = {}
        for i, h in enumerate(header):
            h_clean = h.strip().rstrip("+").strip()
            if h_clean in DEFAULT_VERBS:
                verb_cols[h_clean] = i
            else:
                # Handle compound verbs like "read, use" in column headers
                for sub_v in h_clean.split(","):
                    sub_v = sub_v.strip()
                    if sub_v in DEFAULT_VERBS:
                        verb_cols[sub_v] = i
        if rt_i < 0 or not verb_cols:
            return
        for tr in rows[1:]:
            cells = tr.find_all(["td", "th"])
            n = len(cells)
            rt_val = _cell_text(cells[rt_i]).strip() if rt_i < n else ""
            if not rt_val:
                continue
            for verb, ci in verb_cols.items():
                perm_val = _cell_text(cells[ci]) if ci < n else ""
                perms = _clean_perm_list(_split_items(perm_val))
                if perms:
                    results.append(
                        VerbResourcePermission(
                            resource_type=rt_val,
                            verb=verb,
                            permissions=perms,
                            apis_fully_covered=[],
                            apis_partially_covered=[],
                        )
                    )

    def _process_resource_perm_table(table: Tag, rt: str) -> None:
        """Table with Resource-Type | Permission columns (verb in heading/section).

        Alternate (*) structure used by blockchain, analytics:
            INSPECT
            | Resource-Type | INSPECT Permission |
            | res-a         | PERM_A_INSPECT     |
        """
        rows = table.find_all("tr")
        if not rows:
            return
        header = [_cell_text(c).lower() for c in rows[0].find_all(["th", "td"])]
        rt_i = next((i for i, h in enumerate(header) if "resource" in h), -1)
        perm_i = next((i for i, h in enumerate(header) if "permission" in h), -1)
        if rt_i < 0 or perm_i < 0:
            return
        # Detect verb from the permission column header (e.g., "INSPECT Permission")
        perm_header = _cell_text(rows[0].find_all(["th", "td"])[perm_i])
        verb_from_header = ""
        for v in DEFAULT_VERBS:
            if v in perm_header.lower():
                verb_from_header = v
                break

        for tr in rows[1:]:
            cells = tr.find_all(["td", "th"])
            n = len(cells)
            rt_val = _cell_text(cells[rt_i]).strip() if rt_i < n else ""
            perm_val = _cell_text(cells[perm_i]).strip() if perm_i < n else ""
            perms = _clean_perm_list(_split_items(perm_val))
            if rt_val and perms:
                results.append(
                    VerbResourcePermission(
                        resource_type=rt_val,
                        verb=verb_from_header,
                        permissions=perms,
                        apis_fully_covered=[],
                        apis_partially_covered=[],
                    )
                )

    def _classify_and_process_table(table: Tag, rt: str) -> None:
        """Detect table format and dispatch to the appropriate processor."""
        rows = table.find_all("tr")
        if not rows:
            return
        header_cells = rows[0].find_all(["th", "td"])
        header = [_cell_text(c).lower() for c in header_cells]

        # Standard: has a "verb(s)" column
        if any("verb" in h for h in header):
            _process_standard_table(table, rt)
            return

        # Verb-column: verbs are column headers (e.g., | Resource | inspect | read | ...)
        verb_in_header = sum(1 for h in header if h.strip().rstrip("+").strip() in DEFAULT_VERBS)
        if verb_in_header >= 2:
            _process_verb_column_table(table)
            return

        # Resource-Permission: has Resource-Type + Permission columns (verb in header text)
        has_resource = any("resource" in h for h in header)
        has_permission = any("permission" in h for h in header)
        if has_resource and has_permission:
            _process_resource_perm_table(table, rt)
            return

        # Verb-section: first row is a single-cell verb name
        if len(header_cells) == 1 and header[0].strip().rstrip("+").strip() in DEFAULT_VERBS:
            _process_verb_section_table(table, rt)
            return

        # Verb-section with header: first row is a header (Permission | APIs...) but
        # subsequent rows contain verb names with empty trailing cells
        if has_permission:
            def _is_verb_row_c(r):
                cells = r.find_all(["td", "th"])
                if not cells:
                    return False
                first = _cell_text(cells[0]).lower().strip().rstrip("+").strip()
                if first not in DEFAULT_VERBS:
                    return False
                return len(cells) == 1 or all(
                    not _cell_text(c) for c in cells[1:]
                )
            if any(_is_verb_row_c(r) for r in rows[1:6]):
                _process_verb_section_table(table, rt)
                return

        # Fallback: try standard if there's a permission column
        if has_permission:
            _process_standard_table(table, rt)

    def _walk_elements(elements: list[Tag]) -> None:
        nonlocal current_resource_type
        for elem in elements:
            if not isinstance(elem, Tag):
                continue

            # Sub-headings name the resource type
            if re.match(r"^h[2-6]$", elem.name or ""):
                codes = _code_texts(elem)
                candidate = codes[0] if codes else _cell_text(elem)
                # Skip known verbs, markers, and non-resource-type headings
                _cand_lower = candidate.lower().strip().rstrip("+").strip()
                if _cand_lower not in DEFAULT_VERBS and _cand_lower not in {
                    "", "(+)", "no extra", "none",
                } and not re.match(
                    r"permission|policy|api\s+operation|supported\s+variable",
                    _cand_lower,
                ):
                    current_resource_type = candidate
                continue

            # <article> and <section> elements — recurse into children
            if elem.name in ("article", "section"):
                _walk_elements(list(elem.children))
                continue

            # Div wrappers: may contain <a> label + nested <div> with table
            if elem.name == "div":
                # Check for inner divs with id attribute (common pattern)
                inner_divs = elem.find_all("div", id=True)
                if inner_divs:
                    for idiv in inner_divs:
                        anchor = idiv.find("a")
                        if anchor:
                            rt = anchor.get_text(strip=True)
                        else:
                            # Derive resource type from div id
                            rt = (idiv.get("id") or "").replace("_", "-")
                        for tbl in idiv.find_all("table"):
                            _classify_and_process_table(tbl, rt)
                    continue
                # If div contains sections or headings, recurse into
                # children so resource-type labels (h3, etc.) get processed.
                has_inner_structure = (
                    elem.find("section", recursive=False)
                    or elem.find(re.compile(r"^h[2-6]$"), recursive=False)
                )
                if has_inner_structure:
                    _walk_elements(list(elem.children))
                    continue
                # Simple div: try <a> + table pattern
                anchor = elem.find("a", recursive=False)
                if anchor:
                    current_resource_type = anchor.get_text(strip=True)
                for tbl in elem.find_all("table"):
                    _classify_and_process_table(tbl, current_resource_type)
                continue

            # <details><summary> pattern
            if elem.name == "details":
                summ = elem.find("summary")
                if summ:
                    sc = _code_texts(summ)
                    current_resource_type = sc[0] if sc else _cell_text(summ)
                for tbl in elem.find_all("table"):
                    _classify_and_process_table(tbl, current_resource_type)
                continue

            # Standalone <a> or <p> with resource type label before a sibling table
            if elem.name in ("a", "p"):
                codes = _code_texts(elem)
                # Use the first code that looks like a resource type (not a verb
                # or marker).
                for _code_val in codes:
                    _cv = _code_val.lower().strip().rstrip("+").strip()
                    # Resource types are short hyphenated identifiers
                    if (
                        _cv
                        and _cv not in DEFAULT_VERBS
                        and _cv not in {"(+)", "no extra", "none"}
                        and not re.match(r"permission|api\s+operation", _cv)
                        and len(_cv) < 80
                        and "\n" not in _cv
                    ):
                        current_resource_type = _code_val
                        break
                continue

            # Standalone table
            if elem.name == "table":
                _classify_and_process_table(elem, current_resource_type)

    _walk_elements(siblings)

    # Strategy C: fallback — scan the entire document for VRP-compatible tables.
    # Some pages nest tables in deep div structures that heading/article
    # traversal misses.
    if not results and _do_fallback_scan:
        _STOP_ARTICLE_IDS = {"permissions-required-for-api", "examples"}
        for tbl in soup.find_all("table"):
            rows = tbl.find_all("tr")
            if not rows:
                continue
            hdr = [c.get_text(strip=True).lower() for c in rows[0].find_all(["th", "td"])]
            is_vrp = (
                any("verb" in h for h in hdr)
                or (len(hdr) == 1 and hdr[0].rstrip("+").strip() in DEFAULT_VERBS)
            )
            if not is_vrp:
                continue
            parent_art = tbl.find_parent("article", id=True)
            if parent_art and parent_art.get("id", "") in _STOP_ARTICLE_IDS:
                continue
            rt_div = tbl.find_parent("div", id=True)
            rt = (rt_div.get("id", "") or "").replace("_", "-") if rt_div else ""
            _classify_and_process_table(tbl, rt)

    # Post-process: resolve empty resource_types by looking backward from each
    # VRP's source table for the nearest resource-type-like label.
    if any(not v.resource_type for v in results):
        _VERB_SET = set(DEFAULT_VERBS) | {"no extra", "(+)", "none", ""}
        # Build a mapping from table → resource type by scanning the DOM.
        # For each table on the page, find the nearest preceding <code> element
        # or heading that looks like a resource type.
        _table_rt_cache: dict[int, str] = {}

        def _find_rt_for_table(tbl: Tag) -> str:
            tid = id(tbl)
            if tid in _table_rt_cache:
                return _table_rt_cache[tid]

            rt = ""
            # Check nearest parent div with class 'section' for a code element
            parent_div = tbl.find_parent("div")
            while parent_div:
                codes = parent_div.find_all("code", recursive=True)
                for c in codes:
                    ct = c.get_text(strip=True).lower()
                    if ct and ct not in _VERB_SET and "-" in ct:
                        rt = ct
                        break
                if rt:
                    break
                parent_div = parent_div.find_parent("div")

            if not rt:
                # Try headings: prefer h1 (often the resource type on sub-pages),
                # then h2-h6 (nearest preceding heading).
                _SKIP_HEADINGS = {
                    "oracle cloud infrastructure documentation",
                }
                for h_re in [re.compile(r"^h1$"), re.compile(r"^h[2-6]$")]:
                    prev_h = tbl.find_previous(h_re)
                    if prev_h:
                        codes = _code_texts(prev_h)
                        txt = codes[0] if codes else prev_h.get_text(strip=True)
                        txt_lower = txt.lower().strip()
                        if (
                            txt_lower not in _VERB_SET
                            and txt_lower not in _SKIP_HEADINGS
                            and len(txt) < 80
                            and "\n" not in txt
                        ):
                            rt = txt
                            break

            _table_rt_cache[tid] = rt
            return rt

        # Now, for VRPs with empty resource_type, try to find the table they
        # came from.  We can correlate via the permissions: look for tables
        # containing those permission strings.
        all_tables = soup.find_all("table")
        for vrp in results:
            if vrp.resource_type:
                continue
            # Find the table that produced this VRP
            for tbl in all_tables:
                tbl_text = tbl.get_text()
                if vrp.permissions and all(p in tbl_text for p in vrp.permissions[:2]):
                    rt = _find_rt_for_table(tbl)
                    if rt and rt.lower() not in _VERB_SET:
                        vrp.resource_type = rt
                    break

    return results


_API_PERM_HEADING_PATTERNS = [
    # "Permissions Required for Each API Operation"
    r"permission[s]?\s+required\s+(?:for\s+)?(?:each\s+)?(?:(?:the\s+)?api|operation)",
    # "Permissions required for <Service> API operations"
    r"permission[s]?\s+required\s+for\s+.+api\s+operation",
    # "Permissions Required to View Each Resource Type"
    r"permission[s]?\s+required\s+to\s+(?:view|use|call)\s+each",
    # "Operations to permissions map"
    r"operation[s]?\s+to\s+permission[s]?\s+map",
    # Generic: heading with both 'permission' and 'required/needed'
    r"permission.+(?:required|needed)|(?:required|needed).+permission",
    # Generic: heading with 'api operation'
    r"api\s+operation",
]


def _extract_api_permissions(soup: BeautifulSoup) -> list[ApiPermission]:
    """Extract API-operation → permissions-required tables.

    Handles multiple heading patterns and table formats:
    - Standard 2-col: API Operation | Permissions Required
    - 3-col with description: Operation | API Operation | Permission Required
    - 3-col search-style: Service | Resource Type | Permissions Required
    - Multi-table sections (e.g. Cloud Guard with many tables under one heading)
    """
    results: list[ApiPermission] = []
    seen_ops: set[str] = set()

    def _add_result(ap: ApiPermission) -> None:
        key = (ap.api_operation, ap.permissions_required)
        if key not in seen_ops:
            seen_ops.add(key)
            results.append(ap)

    def _process_api_table(table: Tag) -> None:
        rows = table.find_all("tr")
        if not rows:
            return
        header = [_cell_text(c).lower() for c in rows[0].find_all(["th", "td"])]
        ncols = len(header)

        # Detect column indices with flexible matching
        api_i = next(
            (i for i, h in enumerate(header)
             if "api" in h and ("operation" in h or "name" in h or "endpoint" in h)),
            -1,
        )
        if api_i < 0:
            api_i = next(
                (i for i, h in enumerate(header) if "api" in h or "operation" in h),
                -1,
            )

        perm_i = next(
            (i for i, h in enumerate(header) if "permission" in h), -1
        )

        # Description column (human-readable operation description)
        desc_i = next(
            (i for i, h in enumerate(header)
             if ("description" in h or "comment" in h)
             and i != api_i and i != perm_i),
            -1,
        )

        # 3-col pattern: "Operation" (description) | "API Operation" | "Permission"
        # The first column might be a human-readable description if api_i != 0
        if desc_i < 0 and api_i > 0 and ncols >= 3:
            candidate = next(
                (i for i in range(ncols) if i != api_i and i != perm_i), -1
            )
            if 0 <= candidate < ncols:
                h_text = header[candidate]
                if "operation" in h_text or "action" in h_text or "task" in h_text:
                    desc_i = candidate

        # Resource type column (search-style: Service | Resource Type | Permissions)
        rt_i = next(
            (i for i, h in enumerate(header) if "resource" in h and "type" in h),
            -1,
        )

        # Service column
        svc_col_i = next(
            (i for i, h in enumerate(header)
             if "service" in h and i != api_i and i != perm_i),
            -1,
        )

        # Notes / additional info column
        notes_i = next(
            (i for i, h in enumerate(header)
             if ("note" in h or "additional" in h or "condition" in h)
             and i != api_i and i != perm_i and i != desc_i),
            -1,
        )

        if api_i < 0 or perm_i < 0:
            # Fallback: search-style (Service | Resource Type | Permissions Required)
            if rt_i >= 0 and perm_i >= 0:
                for tr in rows[1:]:
                    cells = tr.find_all(["td", "th"])
                    n = len(cells)
                    rt_val = _cell_text(cells[rt_i]).strip() if rt_i < n else ""
                    perm_val = _cell_text(cells[perm_i]).strip() if perm_i < n else ""
                    svc_val = _cell_text(cells[svc_col_i]).strip() if 0 <= svc_col_i < n else ""
                    if rt_val and perm_val:
                        desc = f"View {rt_val}"
                        if svc_val:
                            desc = f"{svc_val}: {desc}"
                        _add_result(ApiPermission(
                            api_operation=f"View:{rt_val}",
                            permissions_required=perm_val,
                            description=desc,
                            resource_type=rt_val,
                        ))
                return
            return

        for tr in rows[1:]:
            cells = tr.find_all(["td", "th"])
            n = len(cells)
            api_val = _cell_text(cells[api_i]) if api_i < n else ""
            perm_val = _cell_text(cells[perm_i]) if perm_i < n else ""
            desc_val = _cell_text(cells[desc_i]) if 0 <= desc_i < n else ""
            rt_val = _cell_text(cells[rt_i]) if 0 <= rt_i < n else ""
            notes_val = _cell_text(cells[notes_i]) if 0 <= notes_i < n else ""

            # Prefer <code> for API operation name
            codes = _code_texts(cells[api_i]) if api_i < n else []
            api_clean = codes[0] if codes else api_val
            if api_clean:
                _add_result(ApiPermission(
                    api_operation=api_clean,
                    permissions_required=perm_val,
                    description=desc_val,
                    resource_type=rt_val,
                    notes=notes_val,
                ))

    # Try each heading pattern until we find a match
    headings_found: list[Tag] = []
    for pat in _API_PERM_HEADING_PATTERNS:
        for h in soup.find_all(re.compile(r"^h[1-6]$")):
            if re.search(pat, h.get_text(strip=True), re.I) and h not in headings_found:
                headings_found.append(h)

    if not headings_found:
        # Fallback: scan all tables on the page for API → Permission patterns
        _fallback_scan_api_permissions(soup, _process_api_table)
        return results

    for heading in headings_found:
        if heading.name == "h1":
            siblings = list(heading.find_next_siblings())
        else:
            siblings = _siblings_until_heading(heading)

        for elem in siblings:
            if not isinstance(elem, Tag):
                continue
            tables = [elem] if elem.name == "table" else elem.find_all("table")
            for table in tables:
                _process_api_table(table)

    return results


def _fallback_scan_api_permissions(
    soup: BeautifulSoup, process_fn: callable
) -> None:
    """Scan all tables on the page for API-operation → permission patterns.

    Used when no heading match is found but the page might still contain
    relevant tables (e.g., nested in divs or articles).
    """
    for tbl in soup.find_all("table"):
        rows = tbl.find_all("tr")
        if not rows:
            continue
        hdr = [c.get_text(strip=True).lower() for c in rows[0].find_all(["th", "td"])]
        has_api = any("api" in h or "operation" in h for h in hdr)
        has_perm = any("permission" in h for h in hdr)
        if has_api and has_perm:
            process_fn(tbl)


_SUBPAGE_PATTERNS = {
    "resource": "resource_types",
    "variable": "variables",
    "verb": "verb_resource",
    "permission": "api_permissions",
}


def _discover_subpage_links(soup: BeautifulSoup, base_url: str) -> dict[str, str]:
    """Detect sub-page links (e.g. Core Services splits content across 4 pages).
    Returns a dict mapping category → absolute URL."""
    subpages: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        text = (a.get_text(strip=True) or "").lower()
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:")):
            continue
        for kw, cat in _SUBPAGE_PATTERNS.items():
            if kw in text and cat not in subpages:
                abs_url = _normalize_url(href, base_url)
                # Only accept links to Oracle docs
                if _is_oracle_docs(abs_url) and abs_url != base_url.split("#")[0].rstrip("/"):
                    subpages[cat] = abs_url
    return subpages


def extract_service_detail(
    html: str,
    title: str,
    url: str,
    cache_dir: Path | None = None,
    use_cache: bool = True,
) -> ServiceDetail:
    """Full extraction of a service detail page, following sub-pages if needed."""
    # Derive title from HTML if we only have a URL
    real_title = title
    if not title or "/" in title or title.endswith((".htm", ".html")):
        real_title = _title_from_html(html) or title
    sid = _to_service_id(real_title, url)
    svc = ServiceDetail(id=sid, name=real_title, source_url=url)

    try:
        soup = BeautifulSoup(html, "html.parser")

        # 1. Resource types
        svc.individual_resource_types, svc.aggregate_resource_types = _extract_resource_types(soup)

        # 2. Service-specific variables
        svc_vars = _extract_service_variables(soup)
        svc.variables = [asdict(v) for v in svc_vars]

        # 3. Verb + resource-type → permissions
        vrp = _extract_verb_resource_permissions(soup)
        svc.verb_resource_permissions = [asdict(v) for v in vrp]

        # 4. API operation → permissions required
        api_perms = _extract_api_permissions(soup)
        svc.api_permissions = [asdict(a) for a in api_perms]

        # 5. If the page splits content into sub-pages, follow them
        if not svc.individual_resource_types and not svc.verb_resource_permissions and not svc.api_permissions:
            subpages = _discover_subpage_links(soup, url)
            if subpages:
                log.info("  following %d sub-pages: %s", len(subpages), list(subpages.keys()))
                for cat, sub_url in subpages.items():
                    try:
                        sub_html = fetch_page(sub_url, cache_dir=cache_dir, use_cache=use_cache)
                        sub_soup = BeautifulSoup(sub_html, "html.parser")
                        if cat == "resource_types" and not svc.individual_resource_types:
                            ind, agg = _extract_resource_types(sub_soup)
                            svc.individual_resource_types = ind
                            svc.aggregate_resource_types = agg
                        elif cat == "variables" and not svc.variables:
                            sv = _extract_service_variables(sub_soup)
                            svc.variables = [asdict(v) for v in sv]
                        elif cat == "verb_resource" and not svc.verb_resource_permissions:
                            vr = _extract_verb_resource_permissions(sub_soup)
                            svc.verb_resource_permissions = [asdict(v) for v in vr]
                        elif cat == "api_permissions" and not svc.api_permissions:
                            ap = _extract_api_permissions(sub_soup)
                            svc.api_permissions = [asdict(a) for a in ap]
                    except Exception as sub_exc:
                        log.warning("  sub-page %s failed: %s", sub_url, sub_exc)
                        svc.errors.append(f"subpage {cat}: {sub_exc}")

    except Exception as exc:
        svc.errors.append(str(exc))
        log.error("extract failed for %s: %s", url, exc)

    return svc


# ---------------------------------------------------------------------------
# Main entrypoints
# ---------------------------------------------------------------------------


def run_discovery(
    index_url: str = POLICY_REFERENCE_INDEX,
    cache_dir: Path | None = None,
    use_cache: bool = True,
) -> list[DiscoveredLink]:
    """Fetch the index and return classified links."""
    html = fetch_page(index_url, cache_dir=cache_dir, use_cache=use_cache)
    return discover_links(html, index_url)


def run_scrape(
    cache_dir: Path | None = None,
    use_cache: bool = True,
    include_variables: bool = True,
    include_services: bool = True,
    single_url: str | None = None,
    single_title: str | None = None,
) -> ScrapeResult:
    """Run discovery, variable extraction, and service-page scraping."""
    cache = cache_dir or Path("data/scrape_cache")
    if use_cache:
        cache.mkdir(parents=True, exist_ok=True)
    effective_cache = cache if use_cache else None

    result = ScrapeResult(
        source=POLICY_REFERENCE_INDEX,
        scraped_at=datetime.now(timezone.utc).isoformat(),
    )
    result.verbs = list(DEFAULT_VERBS)

    # ----- Single-URL mode --------------------------------------------------
    if single_url:
        html = fetch_page(single_url, cache_dir=effective_cache, use_cache=use_cache)
        title = single_title or _title_from_html(html) or single_url
        svc = extract_service_detail(html, title, single_url, cache_dir=effective_cache, use_cache=use_cache)
        result.services = [asdict(svc)]
        return result

    # ----- Discovery --------------------------------------------------------
    links = run_discovery(cache_dir=effective_cache, use_cache=use_cache)
    result.discovered_urls = [asdict(l) for l in links]

    # ----- General Variables ------------------------------------------------
    if include_variables:
        try:
            html = fetch_page(GENERAL_VARIABLES_URL, cache_dir=effective_cache, use_cache=use_cache)
            gv = extract_general_variables(html)
            result.general_variables = [asdict(v) for v in gv]
            log.info("extracted %d general variables", len(gv))
        except Exception as exc:
            result.general_variables = [{"_error": str(exc)}]
            log.error("failed to extract general variables: %s", exc)

    # ----- Service detail pages ---------------------------------------------
    if include_services:
        service_links = [
            l for l in links if l.link_type in (LINK_TYPE_SERVICE_DETAIL, LINK_TYPE_EXTERNAL)
        ]
        log.info("scraping %d service detail pages …", len(service_links))

        for i, link in enumerate(service_links, 1):
            log.info("[%d/%d] %s", i, len(service_links), link.title or link.url)
            try:
                html = fetch_page(link.url, cache_dir=effective_cache, use_cache=use_cache)
                svc = extract_service_detail(
                    html, link.title, link.url,
                    cache_dir=effective_cache, use_cache=use_cache,
                )
                result.services.append(asdict(svc))
                _log_service_summary(svc)
            except Exception as exc:
                log.error("  FAILED: %s", exc)
                result.services.append(
                    asdict(
                        ServiceDetail(
                            id=_to_service_id(link.title, link.url),
                            name=link.title,
                            source_url=link.url,
                            errors=[str(exc)],
                        )
                    )
                )

    return result


def _log_service_summary(svc: ServiceDetail) -> None:
    parts: list[str] = []
    if svc.individual_resource_types:
        parts.append(f"{len(svc.individual_resource_types)} resource types")
    if svc.aggregate_resource_types:
        parts.append(f"{len(svc.aggregate_resource_types)} aggregate")
    if svc.variables:
        parts.append(f"{len(svc.variables)} vars")
    if svc.verb_resource_permissions:
        parts.append(f"{len(svc.verb_resource_permissions)} verb-resource perms")
    if svc.api_permissions:
        parts.append(f"{len(svc.api_permissions)} api-perm mappings")
    if svc.errors:
        parts.append(f"{len(svc.errors)} errors")
    log.info("  → %s: %s", svc.id, ", ".join(parts) if parts else "(empty)")


# ---------------------------------------------------------------------------
# Consolidate: API operation → permissions (separate output file)
# ---------------------------------------------------------------------------


def _parse_permissions_list(raw: str) -> list[str]:
    """Parse a permissions_required string into a clean list of permission names.

    Handles formats like:
    - "PERM_A"
    - "PERM_A, PERM_B"
    - "PERM_A\\nPERM_B"
    - "PERM_A and PERM_B"
    - "PERM_A or PERM_B"
    - "PERM_A + PERM_B"
    """
    if not raw or not raw.strip():
        return []
    # Split on common delimiters
    parts = re.split(r"[\n,;]+|\s+and\s+|\s+or\s+|\s*\+\s*", raw)
    perms: list[str] = []
    for p in parts:
        p = p.strip().strip("•·-–—").strip()
        if not p:
            continue
        # Skip noise like "None", "N/A", "(none)", "no extra", etc.
        if p.lower() in ("none", "n/a", "no extra", "no extras", "(none)", ""):
            continue
        # Permission names are typically UPPER_CASE_WITH_UNDERSCORES
        # but also keep mixed-case entries for completeness
        perms.append(p)
    return perms


def build_api_operations_file(result: ScrapeResult, out_path: Path) -> dict:
    """Consolidate all API operation → permission mappings from scraped services
    into a single comprehensive file for research use.

    Returns the consolidated data dict.
    """
    entries: list[dict] = []
    services_covered = 0
    seen_global: set[tuple[str, str, str]] = set()

    for svc_dict in result.services:
        svc_id = svc_dict.get("id", "unknown")
        svc_name = svc_dict.get("name", "")
        svc_url = svc_dict.get("source_url", "")
        api_perms = svc_dict.get("api_permissions", [])

        if not api_perms:
            continue
        services_covered += 1

        for ap in api_perms:
            api_op = ap.get("api_operation", "")
            raw_perms = ap.get("permissions_required", "")
            desc = ap.get("description", "")
            rt = ap.get("resource_type", "")
            notes = ap.get("notes", "")

            if not api_op:
                continue

            # Deduplicate across services (same API op might appear in
            # subpages that overlap)
            dedup_key = (svc_id, api_op, raw_perms)
            if dedup_key in seen_global:
                continue
            seen_global.add(dedup_key)

            parsed_perms = _parse_permissions_list(raw_perms)

            entry = {
                "api_operation": api_op,
                "permissions_required": parsed_perms,
                "permissions_required_raw": raw_perms,
                "service_id": svc_id,
                "service_name": svc_name,
                "source_url": svc_url,
            }
            if desc:
                entry["description"] = desc
            if rt:
                entry["resource_type"] = rt
            if notes:
                entry["notes"] = notes

            entries.append(entry)

    # Sort for stable output: by service_id, then api_operation
    entries.sort(key=lambda e: (e["service_id"], e["api_operation"]))

    # Build summary statistics
    all_perms = set()
    all_ops = set()
    for e in entries:
        all_ops.add(e["api_operation"])
        all_perms.update(e["permissions_required"])

    data = {
        "description": (
            "Comprehensive mapping of OCI API operations to the IAM permissions "
            "required to invoke them, extracted from OCI Policy Reference documentation."
        ),
        "source": result.source,
        "scraped_at": result.scraped_at,
        "summary": {
            "total_entries": len(entries),
            "unique_api_operations": len(all_ops),
            "unique_permissions": len(all_perms),
            "services_covered": services_covered,
        },
        "entries": entries,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return data


# ---------------------------------------------------------------------------
# CLI (click)
# ---------------------------------------------------------------------------

import click


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-5s %(message)s",
        datefmt="%H:%M:%S",
    )


@click.group(invoke_without_command=True)
@click.pass_context
@click.option(
    "-o", "--out-dir",
    default="data",
    type=click.Path(file_okay=False),
    show_default=True,
    help="Directory for output JSON files and the scrape cache.",
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Bypass the on-disk HTML cache and always fetch from the network.",
)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Enable debug-level logging.")
def cli(ctx: click.Context, out_dir: str, no_cache: bool, verbose: bool) -> None:
    """Scrape OCI Policy Reference documentation.

    Discovers service pages from the Oracle policy-reference index,
    fetches them (with caching & rate limiting), and extracts resource
    types, variables, verb-permission mappings, and API-operation
    permission requirements.

    \b
    Subcommands
    -----------
    full   — Run discovery + variable extraction + (optionally) all services.
    index  — Discover & classify links only.
    url    — Scrape a single service-detail page by URL.

    When invoked without a subcommand the ``full`` scrape is run.
    """
    _setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["out_dir"] = Path(out_dir)
    ctx.obj["out_dir"].mkdir(parents=True, exist_ok=True)
    ctx.obj["use_cache"] = not no_cache
    ctx.obj["cache"] = ctx.obj["out_dir"] / "scrape_cache" if not no_cache else None

    if ctx.invoked_subcommand is None:
        ctx.invoke(full)


@cli.command()
@click.option(
    "--services",
    is_flag=True,
    default=False,
    help="Also scrape every service detail page (slow; makes many HTTP requests).",
)
@click.option(
    "--no-variables",
    is_flag=True,
    default=False,
    help="Skip extraction of the general-variables table.",
)
@click.option(
    "--full-output",
    is_flag=True,
    default=False,
    help=(
        "Write full output including api_permissions and "
        "apis_fully_covered/apis_partially_covered per VRP entry.  "
        "Default is minimal (strips API-operation fields)."
    ),
)
@click.pass_context
def full(ctx: click.Context, services: bool, no_variables: bool, full_output: bool) -> None:
    """Run a full scrape: discovery + variables + (optionally) services.

    \b
    By default only the index and general variables are scraped.
    Pass --services to also scrape every service detail page, which
    produces the complete policy_reference_scraped.json and
    api_operation_permissions.json output files.

    \b
    Output is minimal by default (no api_permissions or API-coverage
    fields in VRP entries).  Pass --full-output to include everything.

    \b
    Examples
    --------
      python -m modules.scraper full                   # index + variables
      python -m modules.scraper full --services        # full scrape
      python -m modules.scraper full --no-variables    # skip variables
      python -m modules.scraper full --full-output     # include API fields
    """
    cfg = ctx.obj
    minimal = not full_output
    result = run_scrape(
        cache_dir=cfg["cache"],
        use_cache=cfg["use_cache"],
        include_variables=not no_variables,
        include_services=services,
    )
    out_file = cfg["out_dir"] / "policy_reference_scraped.json"
    result.to_json(out_file, minimal=minimal)
    click.echo(f"Wrote {out_file} ({'minimal' if minimal else 'full'})")
    click.echo(f"  verbs: {len(result.verbs)}")
    click.echo(f"  general_variables: {len(result.general_variables)}")
    click.echo(f"  discovered_urls: {len(result.discovered_urls)}")
    click.echo(f"  services scraped: {len(result.services)}")
    if result.services:
        ok = sum(1 for s in result.services if not s.get("errors"))
        err = sum(1 for s in result.services if s.get("errors"))
        total_rt = sum(len(s.get("individual_resource_types", [])) for s in result.services)
        total_vrp = sum(len(s.get("verb_resource_permissions", [])) for s in result.services)
        total_api = sum(len(s.get("api_permissions", [])) for s in result.services)
        click.echo(f"    ok: {ok}, errors: {err}")
        click.echo(f"    total resource_types: {total_rt}, verb_resource_perms: {total_vrp}, api_perms: {total_api}")

        api_file = cfg["out_dir"] / "api_operation_permissions.json"
        api_data = build_api_operations_file(result, api_file)
        s = api_data.get("summary", {})
        click.echo(f"\nWrote {api_file}")
        click.echo(f"  total entries: {s.get('total_entries', 0)}")
        click.echo(f"  unique API operations: {s.get('unique_api_operations', 0)}")
        click.echo(f"  unique permissions: {s.get('unique_permissions', 0)}")
        click.echo(f"  services covered: {s.get('services_covered', 0)}")


@cli.command("index")
@click.pass_context
def index_only(ctx: click.Context) -> None:
    """Discover and classify links from the policy-reference index page.

    \b
    Fetches the OCI policy-reference index, classifies every link as one
    of service_detail, external, verbs, general_variables, or other, and
    writes the result to policy_reference_links.json.

    \b
    Example
    -------
      python -m modules.scraper index
    """
    cfg = ctx.obj
    links = run_discovery(cache_dir=cfg["cache"], use_cache=cfg["use_cache"])
    out_file = cfg["out_dir"] / "policy_reference_links.json"
    out_file.write_text(
        json.dumps([asdict(l) for l in links], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    click.echo(f"Discovered {len(links)} links -> {out_file}")
    for lt in (LINK_TYPE_SERVICE_DETAIL, LINK_TYPE_EXTERNAL, LINK_TYPE_OTHER):
        n = sum(1 for l in links if l.link_type == lt)
        click.echo(f"  {lt}: {n}")


@cli.command()
@click.argument("service_url")
@click.option("--title", default=None, help="Override the page title (derived from <h1> by default).")
@click.option(
    "--full-output",
    is_flag=True,
    default=False,
    help="Include api_permissions and API-coverage fields in VRP entries.",
)
@click.pass_context
def url(ctx: click.Context, service_url: str, title: str | None, full_output: bool) -> None:
    """Scrape a single service-detail page by URL.

    \b
    Fetches SERVICE_URL (an OCI policy-reference page), extracts resource
    types, variables, verb-permission mappings, and API-operation
    permissions, then writes single_service_scraped.json and
    api_operation_permissions.json.

    \b
    Example
    -------
      python -m modules.scraper url https://docs.oracle.com/.../some_service.htm
    """
    cfg = ctx.obj
    minimal = not full_output
    result = run_scrape(
        cache_dir=cfg["cache"],
        use_cache=cfg["use_cache"],
        include_variables=False,
        include_services=False,
        single_url=service_url,
        single_title=title,
    )
    out_file = cfg["out_dir"] / "single_service_scraped.json"
    result.to_json(out_file, minimal=minimal)
    svc = result.services[0] if result.services else {}
    click.echo(f"Wrote {out_file} ({'minimal' if minimal else 'full'})")
    click.echo(f"  resource_types: {len(svc.get('individual_resource_types', []))}")
    click.echo(f"  verb_resource_permissions: {len(svc.get('verb_resource_permissions', []))}")
    click.echo(f"  api_permissions: {len(svc.get('api_permissions', []))}")

    api_file = cfg["out_dir"] / "api_operation_permissions.json"
    api_data = build_api_operations_file(result, api_file)
    s = api_data.get("summary", {})
    click.echo(f"Wrote {api_file}")
    click.echo(f"  api_operation entries: {s.get('total_entries', 0)}")


def main() -> None:
    """Entry point for ``python -m modules.scraper``."""
    cli()


if __name__ == "__main__":
    main()
