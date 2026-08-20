#!/usr/bin/env python3
"""
Scans Remotive's public API (remotive.com/api/remote-jobs, no auth, free tier)
for contract/freelance remote listings matching a given tech stack. Honest
limitation: the free API only exposes a small rolling window, currently ~17
total jobs across all categories, not a huge feed, but real and it refreshes.
Remotive asks for max ~4 requests/day; the daily-file design below naturally
respects that (see --force).

Region handling, per explicit preference: US-only listings ("USA" and nothing
else in candidate_required_location) are a hard skip, same policy as
hn_scan.py, Armenia doesn't clear US-only bars. Everything else is shown with
its location string attached, and EMEA/APAC/Worldwide-flagged listings sort
first, since those are the preferred region.

Only includes listings whose title and full description are confidently
English and that don't explicitly require a language other than English (see
_common.is_english_text / _common.requires_other_language) and doesn't demand
physical presence in a specific place (_common.requires_specific_location,
e.g. "Location: Ukraine" or "office-based role"), since you only
speak English.

Writes a dated, clickable markdown report to
scan-results/YYYY-MM-DD/remotive-scan.md, one folder per day. If today's file
already exists, running this again does nothing to it, prints a note and
exits. Pass --force to rescan and merge fresh data into today's file anyway.
Same tagging convention as hn_scan.py: "- [x] [skipped: reason] **[company]...",
your tag always wins and survives future scans. If the fetch fails, the whole
run aborts and no file gets written, nothing partial/broken persisted.

Usage:
    python3 remotive_scan.py
    python3 remotive_scan.py --stack "rust,react"
    python3 remotive_scan.py --json
    python3 remotive_scan.py --force
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

import _common

API = "https://remotive.com/api/remote-jobs"
SOURCE = "remotive"

DEFAULT_STACK = [
    "aws", "python", "typescript", "golang", r"go\b", "linux",
    "cloud", "devops", "kubernetes", "terraform", "infrastructure", "backend",
]
CONTRACT_TYPES = {"contract", "freelance"}


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "job-search-scan/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def strip_html(t: str) -> str:
    if not t:
        return ""
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def scan_jobs(stack_pattern: re.Pattern, blocklist: list[str]) -> list[dict]:
    data = fetch_json(f"{API}?limit=500")
    matches = []
    for j in data.get("jobs", []):
        if j.get("job_type") not in CONTRACT_TYPES:
            continue
        text = f"{j.get('title', '')} {j.get('category', '')} {' '.join(j.get('tags', []))}"
        if not stack_pattern.search(text):
            continue
        full_desc = strip_html(j.get("description", ""))
        if not _common.is_english_text(f"{j.get('title', '')} {full_desc}"):
            continue
        if _common.requires_other_language(f"{j.get('title', '')} {full_desc}"):
            continue
        if _common.requires_specific_location(f"{j.get('title', '')} {full_desc}"):
            continue
        location = j.get("candidate_required_location", "")
        blocked = next((name for name in blocklist if name.lower() in j.get("company_name", "").lower()), None)
        matches.append({
            "id": str(j.get("id")),
            "author": j.get("company_name", "?"),
            "url": j.get("url", ""),
            "excerpt": f"{j.get('title', '')} | {location or 'location not specified'} | "
                       f"{j.get('job_type')} | {j.get('salary') or 'salary not listed'}",
            "location": location,
            "hard_skip": "US-only, and you don't reside in the US" if _common.is_us_only(location) else None,
            "preferred_region": _common.is_preferred_region(location),
            "blocked": blocked,
        })
    # EMEA/APAC/Worldwide-flagged listings first, per stated preference
    matches.sort(key=lambda m: not m["preferred_region"])
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
        "# Remotive contract/freelance scan",
        "",
        f"Generated {now}. Stack filter: {', '.join(display_stack)}. Contract/freelance job_type only.",
        "New file each day (`scan-results/YYYY-MM-DD/remotive-scan.md`). Once this file exists, running the scan again today does nothing to it, edit freely.",
        "EMEA/APAC/Worldwide-flagged listings sort first. US-only listings are auto-skipped, not eligible.",
        "Applied? Tick its box, `- [ ]` to `- [x]`. Skipping one? Same, plus a reason: `- [x] [skipped: not a fit] **[company]...`.",
        "",
        "## Open contract/freelance leads",
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
    ap.add_argument("--json", action="store_true", help="output JSON instead of text, skips writing the markdown file")
    ap.add_argument("--out", default=None, help="markdown report path (default scan-results/<today>/remotive-scan.md)")
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

    print(f"\n=== Remotive contract/freelance matches ({len(matches)} total) ===")
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

    write_markdown(matches, out_path, stack_words, prior)
    print(f"\nReport written to {out_path}")


if __name__ == "__main__":
    main()
