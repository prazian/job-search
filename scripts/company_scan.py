#!/usr/bin/env python3
"""
Checks the public job-board APIs of a curated list of big, real European
(plus Armenia/Georgia/Cyprus) tech employers for openings matching a given
stack. Two platforms, both genuinely public, no auth, confirmed directly:

  - Greenhouse (boards-api.greenhouse.io/v1/boards/<slug>/jobs), most
    companies here. Every slug in COMPANIES was checked by hand against the
    live API and its company_name field, not guessed: a plausible-looking
    slug can silently belong to an unrelated company reusing the same word
    ("wise" on Greenhouse is a Florida sales-staffing outfit, not the
    fintech; dropped for that reason, and "remote" turned out to be a
    bootcamp, not Remote.com).
  - Sigma Software's own custom WordPress vacancy-search API
    (career.sigma.software/wp-json/api-vacancies/v1/search?q=<term>), the
    site named directly. No full-listing endpoint exists, only
    keyword search, so this queries it once per stack word and dedupes.

Companies confirmed Danish (Trustpilot) are left out entirely, and any
individual listing whose location mentions Denmark/Copenhagen is skipped,
per explicit standing preference, see _common.mentions_denmark.

Region is a real filter here, not just a sort order: a listing only
survives if its stated location is broadly Europe (including UK/Nordics
minus Denmark, Balkans, etc.), or specifically Armenia, Georgia (matched via
"Tbilisi" only, to avoid colliding with the US state), or Cyprus, see
ACCEPTED_LOCATION_RE. Companies like Stripe or Datadog post hundreds of
roles worldwide; the non-European ones are dropped silently at this stage
rather than listed as "skipped", or the report would be mostly noise, which
runs against being asked to keep this terse.

A bare city/country name in the location field is treated as an office
requirement, not remote eligibility, confirmed directly: N26's whole board
(72 jobs, every one just "Berlin"/"Barcelona"/etc, "Remote" nowhere) turned
out to be entirely hybrid-from-that-office once checked by hand, so a
listing needs an explicit remote-scope word (remote, home-based,
distributed, worldwide, ...) in the location field itself, see
REMOTE_SCOPE_RE, companies that mean it say so (Canonical: "Home based -
EMEA", GitLab: "Remote, Poland"). Sigma Software carries this as a separate
"workplace" field (Remote/Hybrid/Office) instead, checked directly rather
than inferred from the location text.

A title match alone isn't enough either, confirmed on the same N26 postings:
several matched only via the generic word "backend" in the title while the
actual requirements centered on "a JVM language and Spring Boot", no
Python/TypeScript/Go anywhere, AWS only "a plus". JVM_ONLY_RE plus a check
for the real target languages catches that and skips it, not a real stack
fit just because the title says "backend".

What survives the region and remote-eligibility filters gets one more fetch
(its own job detail page) to run the same English-language and
other-language-requirement checks used elsewhere (_common.is_english_text,
_common.requires_other_language, _common.requires_specific_location) against
the real description, not just the title, and to pull a short excerpt for
the report.

Resilient by design, per request: every fetch goes through _common.fetch
(retries on 429 and timeouts already), and if one company's board is down,
renamed, or errors out anyway, that company is skipped with a warning,
the run continues and still writes a report for everyone else, rather than
the fail-everything-on-one-error pattern the other scan scripts use (this
one talks to a dozen+ independent third-party sites, one flaky company
shouldn't cost you all the others).

Writes a dated, clickable markdown report to
scan-results/YYYY-MM-DD/companies-scan.md, one folder per day, same
don't-touch-existing-file/--force/tagging convention as the other scan
scripts. Kept deliberately terse: URL, title, location, nothing else.

Usage:
    python3 company_scan.py
    python3 company_scan.py --stack "rust,react"
    python3 company_scan.py --json
    python3 company_scan.py --force
"""
import argparse
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import _common

SOURCE = "companies"

GREENHOUSE_COMPANIES = [
    ("N26", "n26"),
    ("trivago", "trivago"),
    ("Canonical", "canonical"),
    ("Elastic", "elastic"),
    ("GitLab", "gitlab"),
    ("Datadog", "datadog"),
    ("Cloudflare", "cloudflare"),
    ("Stripe", "stripe"),
    ("Adyen", "adyen"),
    ("Bitpanda", "bitpanda"),
    ("GetYourGuide", "getyourguide"),
    ("GoCardless", "gocardless"),
    ("Monzo", "monzo"),
    ("Tide", "tide"),
    ("HelloFresh", "hellofresh"),
    ("FxPro", "fxpro"),
    ("Freenow", "freenow"),
    ("Contentful", "contentful"),
    ("Typeform", "typeform"),
    ("Skyscanner", "skyscanner"),
    ("Bitwarden", "bitwarden"),
    ("Honeycomb", "honeycomb"),
    ("Chainguard", "chainguard"),
    ("Fastly", "fastly"),
    ("Algolia", "algolia"),
    ("Postman", "postman"),
    ("Vonage", "vonage"),
    ("Twilio", "twilio"),
    ("Tanium", "tanium"),
    ("PlanetScale", "planetscale"),
    ("Cockroach Labs", "cockroachlabs"),
    ("CircleCI", "circleci"),
]
SIGMA_SEARCH_TERMS = ["python", "golang", "devops", "aws", "kubernetes", "terraform", "backend", "cloud"]

DEFAULT_STACK = [
    "aws", "python", "typescript", "golang", r"go\b", "linux",
    "cloud", "devops", "kubernetes", "terraform", "infrastructure", "backend",
]

# Deliberately explicit whitelist rather than a US-only-style blacklist: this
# source's whole point is "companies with a European/Armenia/Georgia/Cyprus
# presence", so a listing needs a positive match, not just the absence of a
# red flag. "Georgia" is matched via "Tbilisi" only, to avoid colliding with
# the US state (a real risk, e.g. "Atlanta, Georgia, USA" postings show up
# on these boards). "Remote"/"Hybrid" alone are deliberately NOT on this
# list: they describe a work arrangement, not a place, and a bare "Hybrid"
# location field can hide a US-only role (confirmed directly, a Cloudflare
# posting whose list-level location just said "Hybrid" turned out, on its
# own page, to be Austin/New York/San Francisco only). Only words that are
# themselves a genuine scope claim (worldwide, distributed, EMEA, Europe,
# anywhere, global) count as broad on their own. "EU" is deliberately absent
# too, and on purpose, same reasoning as djinni_scan.py's EU-vs-Europe fix:
# Armenia is geographically Europe but not an EU member, so a listing whose
# only scope word is the bare "EU" (Schengen/EU-work-authorization territory)
# doesn't qualify just because it superficially reads as European. It only
# passes if a real named country (see below) or "Europe"/"EMEA" itself is
# also present, e.g. Bitwarden's "Remote, EU / UK" passes on "UK", not "EU".
_ACCEPTED_LOCATIONS = (
    "europe|emea|distributed|anywhere|worldwide|global|"
    "armenia|yerevan|tbilisi|cyprus|nicosia|limassol|"
    "spain|madrid|barcelona|italy|milan|rome|roma|portugal|lisbon|greece|athens|malta|"
    "sweden|stockholm|norway|oslo|finland|helsinki|iceland|reykjavik|"
    "germany|berlin|munich|hamburg|frankfurt|netherlands|amsterdam|france|paris|"
    "ireland|dublin|united kingdom|\\buk\\b|london|edinburgh|glasgow|poland|warsaw|"
    "austria|vienna|switzerland|zurich|geneva|belgium|brussels|czech|prague|"
    "romania|bucharest|bulgaria|sofia|latvia|riga|lithuania|vilnius|estonia|tallinn|"
    "serbia|belgrade|croatia|zagreb|slovenia|ljubljana|hungary|budapest"
)
ACCEPTED_LOCATION_RE = re.compile(rf"\b({_ACCEPTED_LOCATIONS})\b", re.I)

# A location field naming a real city/country with no remote-scope word at
# all almost always means "you work from this office", confirmed directly:
# N26's whole board (72 jobs, every one just "Berlin"/"Barcelona"/"Vienna"/
# etc, never "Remote" anywhere) turned out to be entirely hybrid-from-that-
# office once checked by hand ("This is a hybrid role from Barcelona or
# Berlin"), same for individual Adyen/Bitpanda/HelloFresh listings spot-
# checked. Companies that actually mean "remote, team happens to sit in
# Berlin" say so explicitly (Canonical: "Home based - EMEA", GitLab:
# "Remote, Poland", Monzo: "...or Remote (UK)"), so require that explicit
# word rather than trusting a bare city/country name.
_REMOTE_SCOPE_WORDS = "remote|home[- ]based|distributed|anywhere|worldwide|global"
REMOTE_SCOPE_RE = re.compile(rf"\b({_REMOTE_SCOPE_WORDS})\b", re.I)

# Confirmed directly on N26 postings that matched only via the generic title
# word "backend": full requirements centered on "a JVM language and Spring
# Boot", AWS/cloud only "a plus", no Python/TypeScript/Go anywhere. A title
# match alone isn't enough, the actual required language matters.
JVM_ONLY_RE = re.compile(r"\b(jvm language|kotlin|spring boot|\bjava\b)\b", re.I)
_ACTUAL_STACK_RE = re.compile(r"\b(python|typescript|golang|\bgo\b)\b", re.I)


def location_region_ok(location_text: str) -> bool:
    """Region/Denmark check only, shared by both platforms."""
    if not location_text or _common.mentions_denmark(location_text):
        return False
    return bool(ACCEPTED_LOCATION_RE.search(location_text))


def location_ok(location_text: str) -> bool:
    """Greenhouse's location.name field conflates office city with remote
    scope (see REMOTE_SCOPE_RE comment above), so a bare city/country needs
    that extra explicit word. Sigma Software has its own separate workplace
    field for that distinction instead, see scan_sigma."""
    return location_region_ok(location_text) and bool(REMOTE_SCOPE_RE.search(location_text or ""))


def strip_html(t: str) -> str:
    if not t:
        return ""
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t)
    return html.unescape(t).strip()


def scan_greenhouse(company: str, slug: str, stack_pattern: re.Pattern) -> list[dict]:
    data = _common.fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
    candidates = []
    for j in data.get("jobs", []):
        title = j.get("title", "")
        if not stack_pattern.search(title):
            continue
        if j.get("language") not in (None, "en"):
            continue
        location = (j.get("location") or {}).get("name", "") or ""
        if not location_ok(location):
            continue
        candidates.append((j, location))

    matches = []
    for j, location in candidates:
        detail = _common.fetch_json(
            f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{j['id']}"
        )
        full_text = f"{j['title']} {strip_html(detail.get('content', ''))}"
        hard_skip = None
        if not _common.is_english_text(full_text):
            hard_skip = "not confidently English"
        elif JVM_ONLY_RE.search(full_text) and not _ACTUAL_STACK_RE.search(full_text):
            hard_skip = "requires Java/Kotlin/Spring Boot (JVM), not your stack"
        else:
            hard_skip = _common.requires_other_language(full_text)
            if not hard_skip:
                loc_req = _common.requires_specific_location(full_text)
                if loc_req and loc_req.lower() not in location.lower():
                    hard_skip = f"page text requires {loc_req}"
        posted = (j.get("first_published") or "")[:10]
        matches.append({
            "id": j["absolute_url"],
            "author": company,
            "url": j["absolute_url"],
            "excerpt": f"{j['title']} | {location} | posted {posted or '?'}",
            "hard_skip": hard_skip,
            "blocked": None,
        })
        time.sleep(0.3)
    return matches


def scan_sigma(stack_pattern: re.Pattern) -> list[dict]:
    seen = {}
    for term in SIGMA_SEARCH_TERMS:
        results = _common.fetch_json(
            f"https://career.sigma.software/wp-json/api-vacancies/v1/search?q={term}"
        )
        for r in results:
            seen.setdefault(r["id"], r)
        time.sleep(0.3)

    matches = []
    for r in seen.values():
        if not stack_pattern.search(r.get("title", "")):
            continue
        html_text = _common.fetch_text(r["url"])
        workplace_m = re.search(r'class="vacancy-card__workplace">([^<]*)<', html_text)
        if not workplace_m or workplace_m.group(1).strip().lower() != "remote":
            continue
        loc_m = re.search(
            r'class="vacancy-card-new__locations">.*?<span>([^<]*)</span>', html_text, re.S
        )
        location = loc_m.group(1).strip() if loc_m else ""
        if not location_region_ok(location):
            continue
        desc_m = re.search(r'id="tabContent_A".*?</ul>', html_text, re.S)
        full_text = f"{r['title']} {strip_html(desc_m.group(0)) if desc_m else ''}"
        hard_skip = None
        if not _common.is_english_text(full_text):
            hard_skip = "not confidently English"
        elif JVM_ONLY_RE.search(full_text) and not _ACTUAL_STACK_RE.search(full_text):
            hard_skip = "requires Java/Kotlin/Spring Boot (JVM), not your stack"
        else:
            hard_skip = _common.requires_other_language(full_text)
        matches.append({
            "id": r["url"],
            "author": "Sigma Software",
            "url": r["url"],
            "excerpt": f"{r['title']} | {location or 'location not specified'}",
            "hard_skip": hard_skip,
            "blocked": None,
        })
        time.sleep(0.3)
    return matches


def scan_all(stack_pattern: re.Pattern, blocklist: list[str]) -> tuple[list[dict], list[str]]:
    all_matches = []
    failed = []

    for i, (company, slug) in enumerate(GREENHOUSE_COMPANIES):
        print(f"  {_common.progress_bar(i, len(GREENHOUSE_COMPANIES) + 1)}  {company}", file=sys.stderr)
        try:
            all_matches.extend(scan_greenhouse(company, slug, stack_pattern))
        except Exception as e:
            failed.append(company)
            print(f"    skipped {company}, fetch failed: {e}", file=sys.stderr)
        time.sleep(0.3)

    print(f"  {_common.progress_bar(len(GREENHOUSE_COMPANIES), len(GREENHOUSE_COMPANIES) + 1)}  Sigma Software", file=sys.stderr)
    try:
        all_matches.extend(scan_sigma(stack_pattern))
    except Exception as e:
        failed.append("Sigma Software")
        print(f"    skipped Sigma Software, fetch failed: {e}", file=sys.stderr)

    for m in all_matches:
        blocked = next((name for name in blocklist if name.lower() in m["author"].lower()), None)
        if blocked:
            m["blocked"] = blocked
    return all_matches, failed


def bucket_matches(matches: list[dict], prior: dict[str, dict]):
    main, skipped, blocked = [], [], []
    for m in matches:
        if m.get("blocked"):
            blocked.append(m)
            continue
        prev_tag = prior.get(m["url"], {}).get("tag")
        reason = _common.resolve_reason(prev_tag, m.get("hard_skip"))
        if reason:
            skipped.append((m, reason))
        else:
            main.append(m)
    return main, skipped, blocked


def write_markdown(matches: list[dict], path: str, prior: dict[str, dict], failed: list[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Company career-page scan (Europe/Armenia/Georgia/Cyprus, no Denmark)",
        "",
        f"Generated {now}. New file each day, edit freely, `--force` to rescan.",
    ]
    if failed:
        lines.append(f"Skipped this run (fetch failed): {', '.join(failed)}.")
    lines.append("")
    main, skipped, blocked = bucket_matches(matches, prior)
    if not main:
        lines.append("No matches this run.")
        lines.append("")
    for m in main:
        checked = prior.get(m["url"], {}).get("checked", False)
        box = "x" if checked else " "
        lines.append(f"- [{box}] **[{m['author']}]({m['url']})**: {m['excerpt']}")
    lines.append("")

    if skipped:
        lines.append("## Skipped")
        lines.append("")
        for m, reason in skipped:
            lines.append(f"- ~~[{m['author']}]({m['url']}): {m['excerpt']}~~ (skipped: {reason})")
        lines.append("")

    if blocked:
        lines.append("## Blocklisted")
        lines.append("")
        for m in blocked:
            lines.append(f"- ~~[{m['author']}]({m['url']}): {m['excerpt']}~~ (matched: {m['blocked']})")
        lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stack", help="comma-separated keywords, overrides default stack")
    ap.add_argument("--json", action="store_true", help="output JSON instead of text, skips writing the markdown file")
    ap.add_argument("--out", default=None, help="markdown report path (default scan-results/<today>/companies-scan.md)")
    ap.add_argument("--force", action="store_true", help="rescan and merge fresh data into today's file even if it already exists")
    args = ap.parse_args()
    out_path = args.out or _common.dated_out(SOURCE)

    if not args.json and not args.force and os.path.exists(out_path):
        print(f"{out_path} already exists, leaving it alone.")
        print("Your edits are untouched. Pass --force to rescan and merge in fresh data anyway.")
        return

    stack_words = [w.strip() for w in args.stack.split(",")] if args.stack else DEFAULT_STACK
    stack_pattern = re.compile("|".join(rf"\b{w}\b" for w in stack_words), re.I)

    blocklist = _common.load_blocklist()
    matches, failed = scan_all(stack_pattern, blocklist)

    if args.json:
        print(json.dumps(matches, indent=2))
        return

    prior_path = _common.find_prior_report(out_path, SOURCE)
    prior = _common.read_prior_state(prior_path)
    main_list, skipped, blocked = bucket_matches(matches, prior)

    print(f"\n=== Company matches ({len(matches)} total) ===")
    for m in main_list:
        print(f"  [{m['author']}] {m['url']}")

    write_markdown(matches, out_path, prior, failed)
    print(f"\nReport written to {out_path}")


if __name__ == "__main__":
    main()
