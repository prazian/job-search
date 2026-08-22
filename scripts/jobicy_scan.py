#!/usr/bin/env python3
"""
Scans Jobicy's public remote-jobs API (jobicy.com/api/v2/remote-jobs, no
auth needed) for listings matching a given tech stack. Real, structured
data, confirmed directly: every job carries its own jobGeo field, a
region/country tag Jobicy assigns itself ("Europe", "UK", "Poland, Ukraine",
"EMEA, Germany, Netherlands", "Anywhere", ...), no free-text inference
needed the way company_scan.py has to for Greenhouse's bare location field.
?geo=europe narrows the pull server-side (confirmed: unfiltered, roughly
2/3 of a sample were US-only; filtered, the sample fills with Europe/UK/
Germany/Poland/etc instead), and the description comes inline, no per-job
detail fetch required. 100 results is the API's hard cap per request
(confirmed: asking for 200 still returns 100), a modest, honest limit, not
a firehose.

Region is a real filter, not a sort order, same policy as company_scan.py:
a listing only survives if at least one part of its jobGeo string is Europe
(incl. UK/Nordics minus Denmark), Armenia, Georgia, or Cyprus, and a bare
"EU" doesn't count as broad enough on its own (Armenia isn't an EU member
even though it's geographically Europe). A jobGeo naming several countries,
one of which is Denmark, isn't excluded outright, only a Denmark-only one
is, same reasoning as the GitLab multi-country bug fixed in company_scan.py:
throwing out a whole listing over Denmark being one of several options
would cost you the other options too.

Only includes listings whose title and full description are confidently
English and that don't explicitly require a language other than English or
demand physical presence somewhere specific, same three checks as every
other source here (_common.is_english_text, _common.requires_other_language,
_common.requires_specific_location).

Writes a dated, clickable markdown report to
scan-results/YYYY-MM-DD/jobicy-scan.md, one folder per day. If today's file
already exists, running this again does nothing to it, prints a note and
exits. Pass --force to rescan and merge fresh data into today's file
anyway. Same tagging convention as the other scan scripts. If the fetch
fails, the whole run aborts and no file gets written.

Usage:
    python3 jobicy_scan.py
    python3 jobicy_scan.py --stack "rust,react"
    python3 jobicy_scan.py --json
    python3 jobicy_scan.py --force
"""
import argparse
import html
import json
import os
import re
import sys
from datetime import datetime, timezone

import _common

API = "https://jobicy.com/api/v2/remote-jobs?count=100&geo=europe"
SOURCE = "jobicy"

DEFAULT_STACK = [
    "aws", "python", "typescript", "golang", r"go\b", "linux",
    "cloud", "devops", "kubernetes", "terraform", "infrastructure", "backend",
]

# Same whitelist and EU-vs-Europe/Denmark reasoning as company_scan.py's
# ACCEPTED_LOCATION_RE, kept here as its own copy rather than a cross-import
# between sibling scan scripts (house style, see djinni/remotive/himalayas,
# each carries its own tailored region check rather than importing a peer).
_ACCEPTED_LOCATIONS = (
    "europe|emea|distributed|anywhere|worldwide|global|"
    "armenia|yerevan|tbilisi|cyprus|nicosia|limassol|"
    "spain|madrid|barcelona|italy|milan|rome|roma|portugal|lisbon|greece|athens|malta|"
    "sweden|stockholm|norway|oslo|finland|helsinki|iceland|reykjavik|"
    "germany|berlin|munich|hamburg|frankfurt|netherlands|amsterdam|france|paris|"
    "ireland|dublin|united kingdom|\\buk\\b|london|edinburgh|glasgow|poland|warsaw|"
    "austria|vienna|switzerland|zurich|geneva|belgium|brussels|czech|czechia|prague|"
    "romania|bucharest|bulgaria|sofia|latvia|riga|lithuania|vilnius|estonia|tallinn|"
    "serbia|belgrade|croatia|zagreb|slovenia|ljubljana|hungary|budapest|turkiye|turkey"
)
ACCEPTED_LOCATION_RE = re.compile(rf"\b({_ACCEPTED_LOCATIONS})\b", re.I)


def location_region_ok(location_text: str) -> bool:
    """True if at least one comma-separated part of jobGeo is an accepted
    region/country, ignoring Denmark specifically rather than rejecting a
    whole multi-country listing over it being one of several options."""
    if not location_text:
        return False
    parts = re.split(r"[;,]|\bor\b", location_text)
    return any(
        ACCEPTED_LOCATION_RE.search(part) and not _common.mentions_denmark(part)
        for part in parts
    )


def strip_html(t: str) -> str:
    if not t:
        return ""
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t)
    return html.unescape(t).strip()


def scan_jobs(stack_pattern: re.Pattern, blocklist: list[str]) -> list[dict]:
    data = _common.fetch_json(API)
    matches = []
    for j in data.get("jobs", []):
        title = j.get("jobTitle", "")
        excerpt = strip_html(j.get("jobExcerpt", ""))
        if not stack_pattern.search(f"{title} {excerpt}"):
            continue
        geo = j.get("jobGeo", "")
        if not location_region_ok(geo):
            continue
        full_desc = strip_html(j.get("jobDescription", "")) or excerpt
        full_text = f"{title} {full_desc}"
        hard_skip = None
        if not _common.is_english_text(full_text):
            hard_skip = "not confidently English"
        else:
            hard_skip = _common.requires_other_language(full_text)
            if not hard_skip:
                loc_req = _common.requires_specific_location(full_text)
                if loc_req and loc_req.lower() not in geo.lower():
                    hard_skip = f"page text requires {loc_req}"
        company = j.get("companyName", "?")
        blocked = next((name for name in blocklist if name.lower() in company.lower()), None)
        pub = (j.get("pubDate") or "")[:10]
        matches.append({
            "id": j.get("url", str(j.get("id"))),
            "author": company,
            "url": j.get("url", ""),
            "excerpt": f"{title} | {geo} | posted {pub or '?'}",
            "hard_skip": hard_skip,
            "blocked": blocked,
        })
    return matches


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


def write_markdown(matches: list[dict], path: str, stack_words: list[str], prior: dict[str, dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    display_stack = [w.replace(r"\b", "").replace("\\", "") for w in stack_words]
    lines = [
        "# Jobicy scan (Europe/Armenia/Georgia/Cyprus, no Denmark)",
        "",
        f"Generated {now}. Stack filter: {', '.join(display_stack)}. 100 results max per the API, region-filtered.",
        "New file each day (`scan-results/YYYY-MM-DD/jobicy-scan.md`). Once this file exists, running the scan again today does nothing to it, edit freely.",
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
    ap.add_argument("--json", action="store_true", help="output JSON instead of text, skips writing the markdown file")
    ap.add_argument("--out", default=None, help="markdown report path (default scan-results/<today>/jobicy-scan.md)")
    ap.add_argument("--force", action="store_true", help="rescan and merge fresh data into today's file even if it already exists")
    args = ap.parse_args()
    out_path = args.out or _common.dated_out(SOURCE)

    if not args.json and not args.force and os.path.exists(out_path):
        print(f"{out_path} already exists, leaving it alone.")
        print("Your edits are untouched. Pass --force to rescan and merge in fresh data anyway.")
        return

    stack_words = [w.strip() for w in args.stack.split(",")] if args.stack else DEFAULT_STACK
    stack_pattern = re.compile("|".join(rf"\b{w}\b" for w in stack_words), re.I)

    try:
        blocklist = _common.load_blocklist()
        matches = scan_jobs(stack_pattern, blocklist)
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

    print(f"\n=== Jobicy matches ({len(matches)} total) ===")
    for m in main_list:
        print(f"  [{m['author']}] {m['url']}")
    if skipped:
        print("\n=== Skipped ===")
        for m, reason in skipped:
            print(f"  [{reason}] {m['author']} {m['url']}")
    if blocked:
        print("\n=== Blocklisted ===")
        for m in blocked:
            print(f"  [{m['blocked']}] {m['author']} {m['url']}")

    write_markdown(matches, out_path, stack_words, prior)
    print(f"\nReport written to {out_path}")


if __name__ == "__main__":
    main()
