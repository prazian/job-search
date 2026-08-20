#!/usr/bin/env python3
"""
Crawls Himalayas' public job API (himalayas.app/jobs/api, no auth needed) for
listings matching a given tech stack. Honest limitation, tested directly: the
free API ignores every filter param tried (search=, q=, keywords=, category=,
categories=, employmentType=), it just returns pages of the same raw,
unfiltered firehose (currently ~99k+ total jobs, capped at 20 per page
regardless of the requested limit), so this crawls pages and filters
client-side instead. Includes full-time roles, not just contract/freelance,
a full-time EMEA/APAC-friendly role is still worth reaching out about.

Defaults to a bounded 500-page crawl (~10,000 jobs sampled, roughly 10% of the
current total) to stay a reasonable citizen of someone else's free API and
finish in a few minutes. Prints progress every 10 pages ("page N/500 crawled,
X matches so far"). Pass --pages N to crawl further, or --all to attempt the
entire firehose (thousands of requests, genuinely slow, only do this if you
mean it).

Only includes listings whose title and full description are confidently
English (script + common-word heuristics, no external library, see
_common.is_english_text) and that don't explicitly require a language other
than English (e.g. "native Armenian speaker", "fluent Russian required", see
_common.requires_other_language) or demand physical presence in a specific
place (e.g. "Location: Ukraine", "office-based role", see
_common.requires_specific_location). All three checks run against the full
job description, not just the short excerpt.

Writes a dated, clickable markdown report to
scan-results/YYYY-MM-DD/himalayas-scan.md, one folder per day. If today's file
already exists, running this again does nothing to it, prints a note and
exits. Pass --force to rescan and merge fresh data into today's file anyway.
Same tagging convention as the other scan scripts: "- [x] [skipped: reason]
**[company]...", your tag always wins and survives future scans. US-only
listings auto-skip (see 07-companies-to-avoid.md's sibling scripts for why),
EMEA/APAC/Worldwide-flagged listings sort first. If the fetch fails partway,
the whole run aborts and no file gets written.

Usage:
    python3 himalayas_scan.py                    # default 500-page sample
    python3 himalayas_scan.py --pages 1500        # deeper sample
    python3 himalayas_scan.py --all               # attempt the full firehose, slow
    python3 himalayas_scan.py --stack "rust,react"
    python3 himalayas_scan.py --json
    python3 himalayas_scan.py --force
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone

import _common

API = "https://himalayas.app/jobs/api"
SOURCE = "himalayas"
PAGE_SIZE = 20  # server caps it here regardless of the requested limit
DEFAULT_PAGES = 500

DEFAULT_STACK = [
    "aws", "python", "typescript", "golang", r"go\b", "linux",
    "cloud", "devops", "kubernetes", "terraform", "infrastructure", "backend",
]


def strip_html(t: str) -> str:
    if not t:
        return ""
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def fetch_json(url: str, retries: int = 4) -> dict:
    """429s happen during a long crawl even at a polite pace, no documented
    rate limit or Retry-After header from this API, so back off progressively
    and retry rather than treating a transient 429 as a hard failure."""
    import urllib.error
    req = urllib.request.Request(url, headers={"User-Agent": "job-search-scan/1.0"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = 10 * (attempt + 1)
                print(f"  429, backing off {wait}s (attempt {attempt + 1}/{retries})", file=sys.stderr)
                time.sleep(wait)
                continue
            raise


def display_company(j: dict) -> str:
    """A handful of listings leak a literal "name" placeholder instead of the
    real company name, fall back to the slug (which is always real) when that
    happens."""
    name = j.get("companyName") or ""
    if name.strip().lower() == "name" and j.get("companySlug"):
        return j["companySlug"].replace("-", " ").title()
    return name or j.get("companySlug", "?")


def format_locations(countries: list[str]) -> str:
    """Some listings restrict to "everywhere except a handful of countries",
    which Himalayas represents as a 100+ country allowlist, dumping all of
    them inline made every such line an unreadable wall of text."""
    if not countries:
        return "no restriction stated"
    if len(countries) <= 6:
        return ", ".join(countries)
    return f"{', '.join(countries[:4])}, and {len(countries) - 4} more countries"


def crawl(stack_pattern: re.Pattern, blocklist: list[str], max_pages: int) -> tuple[list[dict], int, int]:
    """Returns (matches, pages_crawled, total_pages_available)."""
    first = fetch_json(f"{API}?limit={PAGE_SIZE}&offset=0")
    total_count = first.get("totalCount", 0)
    total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE if total_count else 0
    pages_to_crawl = min(max_pages, total_pages) if total_pages else max_pages

    matches = []
    seen_guids = set()

    def process_page(data: dict):
        for j in data.get("jobs", []):
            guid = j.get("guid") or j.get("applicationLink")
            if not guid or guid in seen_guids:
                continue
            seen_guids.add(guid)
            title = j.get("title", "")
            categories = " ".join(j.get("categories", []))
            excerpt_text = j.get("excerpt", "")
            text = f"{title} {categories} {excerpt_text}"
            if not stack_pattern.search(text):
                continue
            full_desc = strip_html(j.get("description", "")) or excerpt_text
            if not _common.is_english_text(f"{title} {full_desc}"):
                continue
            other_lang = _common.requires_other_language(f"{title} {full_desc}")
            if other_lang:
                continue
            if _common.requires_specific_location(f"{title} {full_desc}"):
                continue
            company = display_company(j)
            countries = j.get("locationRestrictions", []) or []
            location_display = format_locations(countries)
            # Region checks look at title + raw country list together: a
            # 150-country "rest of world minus US" restriction never spells
            # out "EMEA" itself, but the job title usually does, and a lone
            # country name like "South Africa" would false-positive-match
            # "africa" on its own without the title's context to lean on.
            region_text = f"{title} {', '.join(countries)}"
            employment = j.get("employmentType", "?")
            blocked = next((name for name in blocklist if name.lower() in company.lower()), None)
            pub = j.get("pubDate")
            posted = datetime.fromtimestamp(pub, tz=timezone.utc).strftime("%Y-%m-%d") if pub else "?"
            matches.append({
                "id": guid,
                "author": company,
                "url": j.get("applicationLink") or guid,
                "excerpt": f"{title} | {location_display} | {employment} | posted {posted}",
                "location": location_display,
                "hard_skip": "US-only, and you don't reside in the US" if _common.is_us_only(region_text) and len(countries) <= 3 else None,
                "preferred_region": _common.is_preferred_region(region_text),
                "blocked": blocked,
            })

    process_page(first)
    pages_done = 1
    print(f"  {_common.progress_bar(pages_done, pages_to_crawl)}  page {pages_done}/{pages_to_crawl}  {len(matches)} matches so far", file=sys.stderr)

    for page in range(1, pages_to_crawl):
        offset = page * PAGE_SIZE
        data = fetch_json(f"{API}?limit={PAGE_SIZE}&offset={offset}")
        process_page(data)
        pages_done += 1
        if pages_done % 10 == 0 or pages_done == pages_to_crawl:
            print(f"  {_common.progress_bar(pages_done, pages_to_crawl)}  page {pages_done}/{pages_to_crawl}  {len(matches)} matches so far", file=sys.stderr)
        time.sleep(0.6)  # 0.2s got a 429 after ~110 pages, this held up in testing

    matches.sort(key=lambda m: not m["preferred_region"])
    return matches, pages_done, total_pages


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


def write_markdown(matches: list[dict], path: str, stack_words: list[str], prior: dict[str, dict],
                    pages_done: int, total_pages: int) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    display_stack = [w.replace(r"\b", "").replace("\\", "") for w in stack_words]
    coverage = f"{pages_done}/{total_pages} pages" if total_pages else f"{pages_done} pages"
    lines = [
        "# Himalayas scan (full-time + contract, EMEA/APAC preferred)",
        "",
        f"Generated {now}. Stack filter: {', '.join(display_stack)}. "
        f"Crawled {coverage} of the unfiltered firehose ({pages_done * 20} jobs sampled), no server-side filter exists.",
        "New file each day (`scan-results/YYYY-MM-DD/himalayas-scan.md`). Once this file exists, running the scan again today does nothing to it, edit freely.",
        "Includes full-time roles, not just contract, employment type is shown per listing. EMEA/APAC/Worldwide-flagged listings sort first. US-only listings are auto-skipped, not eligible.",
        "Applied? Tick its box, `- [ ]` to `- [x]`. Skipping one? Same, plus a reason: `- [x] [skipped: not a fit] **[company]...`.",
        "",
        "## Matches",
        "",
    ]
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
        lines.append("Ruled out for real, either you tagged it or the scanner's US-only check did.")
        lines.append("")
        for m, reason in skipped:
            lines.append(f"- ~~[{m['author']}]({m['url']}): {m['excerpt']}~~ (skipped: {reason})")
        lines.append("")

    if blocked:
        lines.append("## Blocklisted")
        lines.append("")
        lines.append("Pulled out of the list above. See [07-companies-to-avoid.md](07-companies-to-avoid.md) for why.")
        lines.append("")
        for m in blocked:
            lines.append(f"- ~~[{m['author']}]({m['url']}): {m['excerpt']}~~ (matched: {m['blocked']})")
        lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stack", help="comma-separated keywords, overrides default stack")
    ap.add_argument("--pages", type=int, default=DEFAULT_PAGES, help=f"how many 20-job pages to crawl (default {DEFAULT_PAGES})")
    ap.add_argument("--all", action="store_true", help="attempt to crawl the entire firehose, thousands of requests, slow")
    ap.add_argument("--json", action="store_true", help="output JSON instead of text, skips writing the markdown file")
    ap.add_argument("--out", default=None, help="markdown report path (default scan-results/<today>/himalayas-scan.md)")
    ap.add_argument("--force", action="store_true", help="rescan and merge fresh data into today's file even if it already exists")
    args = ap.parse_args()
    out_path = args.out or _common.dated_out(SOURCE)

    if not args.json and not args.force and os.path.exists(out_path):
        print(f"{out_path} already exists, leaving it alone.")
        print("Your edits are untouched. Pass --force to rescan and merge in fresh data anyway.")
        return

    stack_words = [w.strip() for w in args.stack.split(",")] if args.stack else DEFAULT_STACK
    stack_pattern = re.compile("|".join(rf"\b{w}\b" for w in stack_words), re.I)
    max_pages = 10**9 if args.all else args.pages

    try:
        blocklist = _common.load_blocklist()
        matches, pages_done, total_pages = crawl(stack_pattern, blocklist, max_pages)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print("Not writing a report, fetch failed partway or entirely.", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(matches, indent=2))
        return

    prior_path = _common.find_prior_report(out_path, SOURCE)
    prior = _common.read_prior_state(prior_path)
    main_list, skipped, blocked = bucket_matches(matches, prior)

    print(f"\n=== Himalayas matches ({len(matches)} total, {pages_done}/{total_pages} pages crawled) ===")
    for m in main_list:
        print(f"\n  [{m['author']}] {m['url']}")
        print(f"  {m['excerpt']}")
    if skipped:
        print("\n=== Skipped ===")
        for m, reason in skipped:
            print(f"  [{reason}] {m['author']} {m['url']}")
    if blocked:
        print("\n=== Blocklisted ===")
        for m in blocked:
            print(f"  [{m['blocked']}] {m['author']} {m['url']}")

    write_markdown(matches, out_path, stack_words, prior, pages_done, total_pages)
    print(f"\nReport written to {out_path}")


if __name__ == "__main__":
    main()
