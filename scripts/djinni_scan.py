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
through for that.

Only fetches category-filtered feeds (?primary_keyword=) for categories that
actually map to the stack (Python, Golang, DevOps, Sysadmin, Data Engineer,
Node.js), not the general/unfiltered firehose: that firehose spans every
category Djinni has (Marketing, Sales, QA, Business Analyst, ...) and the
stack-keyword regex alone let plenty of those through on a single loose word
match ("go" inside a sentence, "cloud" mentioned in passing), confirmed
directly against real listings a human had to hand-tag "unrelated".

Language and location requirements on Djinni are structured page data, not
free text, confirmed directly: a job requiring "Ukrainian, Native" or an
office in a specific country never says so in the RSS description, it's a
"Required languages" section (language + CEFR level) and Schema.org
JobPosting JSON-LD (jobLocationType/jobLocation/applicantLocationRequirements)
on the job's own page, both invisible to the feed. A confirmed, real pattern
on this source: English-written postings that require living in Ukraine or
speaking Ukrainian, common since Djinni's core base is Ukrainian, and neither
has anything to do with the text itself. So candidates that clear the cheap
RSS-level checks (_common.is_english_text, _common.requires_other_language,
_common.requires_specific_location, all still run first since they're free)
get one more fetch of their own job page to read that structured data before
being called a real match. If that one extra fetch fails for a given job
(deleted listing, hiccup), the job is kept rather than dropped silently, a
warning is printed and you can catch it by eye instead of losing a lead to a
network blip.

Writes a dated, clickable markdown report to
scan-results/YYYY-MM-DD/djinni-scan.md, one folder per day. If today's file
already exists, running this again does nothing to it, prints a note and
exits. Pass --force to rescan and merge fresh data into today's file anyway.
Same tagging convention as the other scan scripts. If the RSS feed fetch
fails, the whole run aborts and no file gets written.

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
# Confirmed against Djinni's own category tree (djinni.co/jobs/ search page,
# "categories_tree" data), the subset that actually maps to the stack. No
# general/unfiltered feed, see docstring, that's what let Marketing/QA/
# Business-Analyst postings through on a loose keyword match.
CATEGORIES = ["Python", "DevOps", "Golang", "Data Engineer", "Sysadmin", "Node.js"]

DEFAULT_STACK = [
    "aws", "python", "typescript", "golang", r"go\b", "linux",
    "cloud", "devops", "kubernetes", "terraform", "infrastructure", "backend",
]

ITEM_RE = re.compile(r"<item>(.*?)</item>", re.S)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
LINK_RE = re.compile(r"<link>(.*?)</link>", re.S)
DESC_RE = re.compile(r"<description>(.*?)</description>", re.S)
PUBDATE_RE = re.compile(r"<pubDate>(.*?)</pubDate>", re.S)

# Structured data on the job's own page, confirmed directly against real
# listings, none of this is present in the RSS description.
REQUIRED_LANG_SECTION_RE = re.compile(r'<h2[^>]*>Required languages</h2>(.*?)(?=<h2|\Z)', re.S)
LANG_BLOCK_RE = re.compile(r'csc--language.*?</span>\s*</span>', re.S)
LANG_PRIMARY_RE = re.compile(r'csc__primary">([^<]+)<')
LANG_SECONDARY_RE = re.compile(r'csc__secondary">([^<]+)<')
LD_JSON_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
# The sidebar "quick facts" panel's own eligible-candidates line, scoped by
# requiring its exact trailing caption so it can't match the panel's
# "Office: X" line below it, which reuses the same span class for a
# different, unrelated fact (a job's office can be in Poland while it's
# still fully remote-eligible worldwide, confirmed on a real listing).
CANDIDATE_COUNTRIES_RE = re.compile(
    r'<span class="location-text">([^<]*)</span>\s*</strong>\s*'
    r'<div class="font-size-extra-small">Countries where we consider candidates</div>',
    re.S,
)


def _as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _is_broad_location(token: str) -> bool:
    """Worldwide/EMEA/Armenia are broad enough. "Europe" is not: the
    2026-09-04 review tagged dozens of Djinni listings "only Europe" after
    clicking through, companies that say Europe keep treating Armenia as
    outside the region. "EU" was already a skip (Armenia isn't a member)."""
    t = token.strip().lower()
    if t in ("eu", "european union", "eu only", "europe", "only europe", "european"):
        return False
    if t == "armenia":
        return True
    return bool(re.search(r"\b(worldwide|anywhere|global|emea)\b", t))


def required_languages(html: str) -> list[tuple[str, str]]:
    """[(language, CEFR level or "Native", ...)], read off the job page's own
    "Required languages" section, empty if that section isn't present."""
    m = REQUIRED_LANG_SECTION_RE.search(html)
    if not m:
        return []
    out = []
    for block in LANG_BLOCK_RE.findall(m.group(1)):
        pm = LANG_PRIMARY_RE.search(block)
        if not pm:
            continue
        sm = LANG_SECONDARY_RE.search(block)
        out.append((pm.group(1).strip(), sm.group(1).strip() if sm else ""))
    return out


def location_requirement(html: str) -> str | None:
    """Two independent checks, in order:

    1. The Schema.org JobPosting JSON-LD block Djinni embeds on every job
       page. jobLocationType == "TELECOMMUTE" means remote; if it's missing
       and jobLocation names a country, that's an office-based (or hybrid)
       role, physical presence trumps whatever the eligibility line below
       says, confirmed on a real "Hybrid Remote, Office: Poland, countries
       considered: Worldwide" listing where the hybrid office requirement is
       the real constraint despite the broad-sounding eligibility line.
    2. If it's genuinely remote, the sidebar's own "Countries where we
       consider candidates" line (see CANDIDATE_COUNTRIES_RE), the
       human-readable eligibility whitelist. Anything not broad enough to
       include Armenia (a single country, "Europe" alone, or "EU"
       specifically, see _is_broad_location) is a hard skip. "Europe" is
       not enough: the 2026-09-04 review tagged those only-Europe after
       clicking through."""
    m = LD_JSON_RE.search(html)
    if m:
        try:
            data = json.loads(m.group(1))
        except (json.JSONDecodeError, TypeError):
            data = None
        if isinstance(data, dict) and data.get("jobLocationType") != "TELECOMMUTE":
            for job_loc in _as_list(data.get("jobLocation")):
                if not isinstance(job_loc, dict):
                    continue
                country = (job_loc.get("address") or {}).get("addressCountry")
                if country:
                    return f"office-based in {country}, not remote"

    cm = CANDIDATE_COUNTRIES_RE.search(html)
    if not cm:
        return None
    tokens = [t.strip() for t in re.split(r",|\bor\b", cm.group(1)) if t.strip()]
    if not tokens or any(_is_broad_location(t) for t in tokens):
        return None
    if any(t.lower() in ("eu", "european union", "eu only") for t in tokens):
        return "EU-only, and Armenia isn't in the EU (though it is in Europe)"
    if all(re.search(r"\beurope\b", t, re.I) for t in tokens):
        return "only Europe"
    return f"remote, but restricted to applicants based in {' or '.join(tokens)}"


def fetch_job_flags(url: str) -> str | None:
    """One fetch of the job's own page, checked for both a non-English
    required language and a location restriction. Returns a skip reason or
    None. Raises on a fetch failure, caller decides how to handle that."""
    html = _common.fetch_text(url)
    for lang, level in required_languages(html):
        if lang.lower() != "english":
            return f"requires {lang}" + (f" ({level})" if level else "")
    return location_requirement(html)


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
    urls = [f"{BASE}?primary_keyword={cat.replace(' ', '+')}" for cat in CATEGORIES]
    for i, url in enumerate(urls):
        if i > 0:
            time.sleep(0.5)
        for item in parse_items(_common.fetch_text(url)):
            seen_links.setdefault(item["link"], item)

    candidates = []
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
        candidates.append(item)

    matches = []
    fetch_errors = 0
    for i, item in enumerate(candidates):
        if i % 20 == 0 or i == len(candidates) - 1:
            print(f"  {_common.progress_bar(i + 1, len(candidates))}  checking listing {i + 1}/{len(candidates)}", file=sys.stderr)
        try:
            hard_skip = fetch_job_flags(item["link"])
        except Exception as e:
            fetch_errors += 1
            print(f"  couldn't check {item['link']}: {e} (kept, not dropped over a fetch hiccup)", file=sys.stderr)
            hard_skip = None
        hard_skip = _common.first_skip(hard_skip, _common.role_skip(item["title"]))
        blocked = next((name for name in blocklist if name.lower() in item["title"].lower()), None)
        matches.append({
            "id": item["link"],
            "author": "(see listing, company not named in feed)",
            "url": item["link"],
            "excerpt": f"{item['title']} | posted {item['pub_date']}",
            "hard_skip": hard_skip,
            "blocked": blocked,
        })
        time.sleep(0.3)

    if fetch_errors:
        print(f"\n{fetch_errors}/{len(candidates)} listing detail fetches failed, "
              f"those are kept unverified rather than dropped, check them by eye.", file=sys.stderr)
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
        f"Generated {now}. Stack filter: {', '.join(display_stack)}. English-only, no other-language-required, "
        f"no specific-country-residency-required listings (that last check reads the listing's own page, not just the feed).",
        "New file each day (`scan-results/YYYY-MM-DD/djinni-scan.md`). Once this file exists, running the scan again today does nothing to it, edit freely.",
        "No company-name field in Djinni's feed, click through for that.",
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
        lines.append("Ruled out for real, either you tagged it or the scanner's language/location check "
                      "(read off the listing's own page, not the feed) did.")
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
