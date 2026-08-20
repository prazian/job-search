#!/usr/bin/env python3
"""
Scans Djinni's public RSS feed (djinni.co/jobs/rss/, no auth needed) for
listings matching a given tech stack. Djinni is the main Ukraine/Eastern
Europe/CIS tech job board, timezone-friendly to Armenia and culturally close
to the region, worth including per that preference even though it's not
EMEA/APAC in the geographic sense.

Real limitation, tested directly: individual RSS items have no company-name
field, just title/link/description/pubDate (a lot of Djinni postings are
recruiting-agency-posted without naming the end client in the feed), so
listings show as "(see listing)" rather than a real company name, click
through for that. There's also no structured location/remote field, Djinni is
inherently a remote-friendly regional board, but you'll want to confirm
remote status on the listing page itself.

Fetches the general feed plus a few category-filtered feeds
(?primary_keyword=Python/DevOps/Golang, confirmed these actually narrow
results, unlike Himalayas) and dedupes by link. Only includes listings whose
title and full description are confidently English and that don't explicitly
require a language other than English (Djinni's own feed mixes English and
Ukrainian/Russian listings even within a single category, confirmed directly,
so this matters here more than on the other sources) or demand physical
presence in a specific place. That last check matters more here than
anywhere else too: a real, confirmed pattern on this source is postings
written in English that require living in Ukraine specifically ("Location:
Ukraine", "(Ukraine only)"), which have nothing to do with language but are
just as much a hard no for someone based in Armenia. See
_common.is_english_text, _common.requires_other_language, and
_common.requires_specific_location.

Writes a dated, clickable markdown report to
scan-results/YYYY-MM-DD/djinni-scan.md, one folder per day. If today's file
already exists, running this again does nothing to it, prints a note and
exits. Pass --force to rescan and merge fresh data into today's file anyway.
Same tagging convention as the other scan scripts. If the fetch fails, the
whole run aborts and no file gets written.

Usage:
    python3 djinni_scan.py
    python3 djinni_scan.py --stack "rust,react"
    python3 djinni_scan.py --json
    python3 djinni_scan.py --force
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import _common

BASE = "https://djinni.co/jobs/rss/"
SOURCE = "djinni"
# Categories confirmed to exist in Djinni's own taxonomy and to actually
# narrow the RSS feed when passed as ?primary_keyword=. General feed is
# fetched too and dedupe by link means no double-counting.
CATEGORIES = ["Python", "DevOps", "Golang", "Data Engineer"]

DEFAULT_STACK = [
    "aws", "python", "typescript", "golang", r"go\b", "linux",
    "cloud", "devops", "kubernetes", "terraform", "infrastructure", "backend",
]

ITEM_RE = re.compile(r"<item>(.*?)</item>", re.S)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
LINK_RE = re.compile(r"<link>(.*?)</link>", re.S)
DESC_RE = re.compile(r"<description>(.*?)</description>", re.S)
PUBDATE_RE = re.compile(r"<pubDate>(.*?)</pubDate>", re.S)


def strip_html(t: str) -> str:
    if not t:
        return ""
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def unescape(t: str) -> str:
    import html
    return html.unescape(t or "")


def parse_items(rss_text: str) -> list[dict]:
    items = []
    for raw in ITEM_RE.findall(rss_text):
        title_m = TITLE_RE.search(raw)
        link_m = LINK_RE.search(raw)
        desc_m = DESC_RE.search(raw)
        pub_m = PUBDATE_RE.search(raw)
        if not title_m or not link_m:
            continue
        items.append({
            "title": unescape(title_m.group(1)),
            "link": link_m.group(1).strip(),
            "description": strip_html(unescape(desc_m.group(1))) if desc_m else "",
            "pub_date": pub_m.group(1).strip() if pub_m else "?",
        })
    return items


def scan_jobs(stack_pattern: re.Pattern, blocklist: list[str]) -> list[dict]:
    seen_links = {}
    urls = [BASE] + [f"{BASE}?primary_keyword={cat.replace(' ', '+')}" for cat in CATEGORIES]
    for i, url in enumerate(urls):
        if i > 0:
            time.sleep(0.5)
        for item in parse_items(_common.fetch_text(url)):
            seen_links.setdefault(item["link"], item)

    matches = []
    for item in seen_links.values():
        text = f"{item['title']} {item['description']}"
        if not stack_pattern.search(text):
            continue
        if not _common.is_english_text(text):
            continue
        if _common.requires_other_language(text):
            continue
        if _common.requires_specific_location(text):
            continue
        blocked = next((name for name in blocklist if name.lower() in item["title"].lower()), None)
        matches.append({
            "id": item["link"],
            "author": "(see listing, company not named in feed)",
            "url": item["link"],
            "excerpt": f"{item['title']} | posted {item['pub_date']}",
            "hard_skip": None,
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
        "# Djinni scan (Ukraine/CIS/Eastern Europe tech board)",
        "",
        f"Generated {now}. Stack filter: {', '.join(display_stack)}. English-only, no other-language-required listings.",
        "New file each day (`scan-results/YYYY-MM-DD/djinni-scan.md`). Once this file exists, running the scan again today does nothing to it, edit freely.",
        "No company-name or location field in Djinni's feed, click through for both. Djinni is inherently remote/CIS-region-friendly but confirm on the listing.",
        "Applied? Tick its box, `- [ ]` to `- [x]`. Skipping one? Same, plus a reason: `- [x] [skipped: not a fit] **[listing]...`.",
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
        lines.append("Ruled out for real, you tagged it yourself.")
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
    ap.add_argument("--out", default=None, help="markdown report path (default scan-results/<today>/djinni-scan.md)")
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

    print(f"\n=== Djinni matches ({len(matches)} total) ===")
    for m in main_list:
        print(f"\n  {m['url']}")
        print(f"  {m['excerpt']}")
    if skipped:
        print("\n=== Skipped ===")
        for m, reason in skipped:
            print(f"  [{reason}] {m['url']}")
    if blocked:
        print("\n=== Blocklisted ===")
        for m in blocked:
            print(f"  [{m['blocked']}] {m['url']}")

    write_markdown(matches, out_path, stack_words, prior)
    print(f"\nReport written to {out_path}")


if __name__ == "__main__":
    main()
