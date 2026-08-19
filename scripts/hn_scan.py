#!/usr/bin/env python3
"""
Scans the current month's Hacker News "Who is hiring?" and "Freelancer? Seeking
freelancer?" threads for posts that mention contract/freelance work matching a
given tech stack. Uses HN's public Algolia API, no auth, no scraping, no ToS issues.

Writes a dated, clickable markdown report to scan-results/hn-scan-YYYY-MM-DD.md,
one per day. If today's file already exists, running this again does nothing
to it, prints a note and exits, your edits are never touched or re-parsed
mid-day. Pass --force to rescan and merge fresh HN data into today's file
anyway. Each lead gets a checkbox, "- [ ]"/"- [x]".

Four buckets:
  - Main list, the default, still deciding.
  - "## Might be possible": auto-flagged for stating a US work-authorization
    requirement ("must be authorized to work in the US", "no visa sponsorship").
    Soft, sometimes-negotiable signal for a contract engagement, not a hard
    wall (you've applied through this before), so it stays here, clickable and
    checkbox-able, just with a "(flag: ...)" note. Edit US_AUTH_RE below to
    change what counts.
  - "## Skipped": things ruled out for real. Three ways to get there: you tag
    it yourself, "- [x] [skipped: not a fit] **[author]...", any reason, your
    call; the scanner auto-tags a role that says "US only" / "USA only" (you
    don't reside in the US, that's not negotiable, edit US_ONLY_RE below if
    that changes); or the scanner auto-tags an onsite/hybrid-only role with no
    remote option (a physical constraint, edit the onsite check below if that
    changes). Your own tag always wins over either auto one.
  - "## Blocklisted": companies listed in 07-companies-to-avoid.md, a trust
    problem, not an eligibility one.

Once something has a tag (yours or auto) it stays tagged and out of the main
list on every future scan, read back out of the existing report before it's
rewritten. Move something out of "Might be possible" into "Skipped" the same
way you'd tag anything else, by adding your own "[skipped: ...]" reason.

Usage:
    python3 hn_scan.py                  # scan current month, default stack
    python3 hn_scan.py --stack "rust,react"
    python3 hn_scan.py --json           # machine-readable output, no file written
    python3 hn_scan.py --out path.md    # write the report somewhere else
    python3 hn_scan.py --force          # rescan and merge fresh data into today's file even if it exists
"""
import argparse
import glob
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ALGOLIA = "https://hn.algolia.com/api/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_DIR = os.path.join(ROOT, "scan-results")
BLOCKLIST_PATH = os.path.join(ROOT, "07-companies-to-avoid.md")
CHECKBOX_RE = re.compile(r"^-\s\[([ xX])\]\s(?:\[(?P<tag>[^\]]*)\]\s)?\*\*\[[^\]]+\]\((?P<url>[^)]+)\)")
SKIPPED_LINE_RE = re.compile(r"^-\s~~\[[^\]]+\]\((?P<url>[^)]+)\):.*~~\s\(skipped:\s*(?P<tag>[^)]+)\)")
TABLE_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|")

# Explicit US legal work-authorization requirements, not a timezone/overlap ask.
# Soft signal: worth flagging, not worth ruling out. You've applied through this before.
US_AUTH_RE = re.compile(
    r"authorized to work in the (?:u\.?s\.?a?\.?\b|united states)"
    r"|\bu\.?s\.?\s*citizens?\s+only\b"
    r"|\bmust be a (?:us|u\.s\.) citizen\b"
    r"|\bno (?:visa )?sponsorship\b[^.]{0,80}\b(?:u\.?s\.?a?\.?|united states)\b"
    r"|\b(?:u\.?s\.?a?\.?|united states)\b[^.]{0,80}\bno (?:visa )?sponsorship\b",
    re.I,
)
# Hard signal: says the role is US-only, and you don't reside in the US. Not
# negotiable the way "authorized to work" wording sometimes is.
US_ONLY_RE = re.compile(r"\b(?:u\.?s\.?a?\.?)\s+only\b", re.I)
# Hard signal: physically can't be onsite in a specific city without relocating.
ONSITE_RE = re.compile(r"\b(onsite|on-site|hybrid)\b", re.I)
REMOTE_RE = re.compile(r"\bremote\b", re.I)


def default_out() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(SCAN_DIR, f"hn-scan-{today}.md")


DEFAULT_STACK = [
    "aws", "python", "typescript", "golang", r"go\b", "linux",
    "cloud", "devops", "kubernetes", "terraform", "infrastructure",
]
CONTRACT_WORDS = [
    r"\bcontract\b", r"\bfreelance", r"\bcontractor", r"\bcontract.to.hire\b",
    r"\bcontract.based\b", r"\b1099\b",
]


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "job-search-scan/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def strip_html(t: str) -> str:
    if not t:
        return ""
    t = re.sub(r"<p>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t)
    return html.unescape(t).strip()


def detect_flag(text: str) -> str | None:
    """Soft signal, worth a heads-up but not a reason to rule it out."""
    if US_AUTH_RE.search(text):
        return "requires US work authorization, stated"
    return None


def detect_hard_skip(text: str) -> str | None:
    """Hard signal, a real constraint, not a negotiable one."""
    if US_ONLY_RE.search(text):
        return "US-only, and you don't reside in the US"
    head = text[:200]
    if ONSITE_RE.search(head) and not REMOTE_RE.search(head):
        return "onsite/hybrid only, no remote option"
    return None


def find_latest_thread(query: str, author: str | None = None) -> dict | None:
    tags = "story"
    if author:
        tags += f",author_{author}"
    url = f"{ALGOLIA}/search_by_date?query={urllib.parse.quote(query)}&tags={tags}&hitsPerPage=1"
    data = fetch_json(url)
    hits = data.get("hits", [])
    return hits[0] if hits else None


def scan_thread(story_id: str, contract_required: bool, stack_pattern: re.Pattern) -> list[dict]:
    data = fetch_json(f"{ALGOLIA}/items/{story_id}")
    contract_re = re.compile("|".join(CONTRACT_WORDS), re.I)
    matches = []
    for c in data.get("children", []):
        text = strip_html(c.get("text", ""))
        if not text:
            continue
        if contract_required and not contract_re.search(text):
            continue
        if not stack_pattern.search(text):
            continue
        matches.append({
            "id": c.get("id"),
            "author": c.get("author"),
            "url": f"https://news.ycombinator.com/item?id={c.get('id')}",
            "excerpt": text[:400],
            "full_text": text,
            "flag": detect_flag(text),
            "hard_skip": detect_hard_skip(text),
        })
    return matches


def load_blocklist(path: str = BLOCKLIST_PATH) -> list[str]:
    """Reads company names out of the Blocked table in 07-companies-to-avoid.md."""
    if not os.path.exists(path):
        return []
    names = []
    with open(path) as f:
        for line in f:
            m = TABLE_ROW_RE.match(line)
            if not m:
                continue
            first = m.group(1).strip()
            if not first or first.lower() == "company" or set(first) <= {"-", " "}:
                continue
            names.append(first)
    return names


def tag_blocklist(results: dict, blocklist: list[str]) -> None:
    for block in results.values():
        for m in block["matches"]:
            for name in blocklist:
                if name.lower() in m["full_text"].lower():
                    m["blocked"] = name
                    break


def read_prior_state(path: str) -> dict[str, dict]:
    """URL -> {checked, tag} read back from an existing report, so manual edits
    (ticked boxes, "[skipped: ...]" reasons) survive the next scan. Covers both
    line shapes: a normal checkbox line (main list, tag optional) and a
    struck-through line already moved to the Skipped section (tag required)."""
    if not path or not os.path.exists(path):
        return {}
    state = {}
    with open(path) as f:
        for line in f:
            m = CHECKBOX_RE.match(line)
            if m:
                state[m.group("url")] = {
                    "checked": m.group(1).lower() == "x",
                    "tag": m.group("tag"),
                }
                continue
            m = SKIPPED_LINE_RE.match(line)
            if m:
                state[m.group("url")] = {"checked": True, "tag": m.group("tag")}
    return state


def find_prior_report(out_path: str) -> str | None:
    """Today's own file if a same-day rerun, else the most recent earlier report."""
    if os.path.exists(out_path):
        return out_path
    others = sorted(glob.glob(os.path.join(SCAN_DIR, "hn-scan-*.md")))
    return others[-1] if others else None


SKIPPED_PREFIX_RE = re.compile(r"^\s*skipped\s*:\s*", re.I)


def bucket_matches(
    matches: list[dict], prior: dict[str, dict]
) -> tuple[list[dict], list[tuple[dict, str]], list[tuple[dict, str]], list[dict]]:
    """Splits into (main, flagged [reason], skipped [reason], blocked).
    Priority: blocked company > your own tag (always wins, it's your call) >
    scanner's hard skip (a physical constraint) > scanner's soft flag (worth
    trying anyway) > main list."""
    main, flagged, skipped, blocked = [], [], [], []
    for m in matches:
        if m.get("blocked"):
            blocked.append(m)
            continue
        prev_tag = prior.get(m["url"], {}).get("tag")
        if prev_tag:
            skipped.append((m, SKIPPED_PREFIX_RE.sub("", prev_tag).strip()))
        elif m.get("hard_skip"):
            skipped.append((m, m["hard_skip"]))
        elif m.get("flag"):
            flagged.append((m, m["flag"]))
        else:
            main.append(m)
    return main, flagged, skipped, blocked


def write_markdown(results: dict, path: str, stack_words: list[str], prior: dict[str, dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    display_stack = [w.replace(r"\b", "").replace("\\", "") for w in stack_words]
    lines = [
        "# HN contract/freelance scan",
        "",
        f"Generated {now}. Stack filter: {', '.join(display_stack)}.",
        "New file each day (`scan-results/hn-scan-YYYY-MM-DD.md`). Once this file exists, running the scan again today does nothing to it, edit freely.",
        "Applied a lead? Tick its box, `- [ ]` to `- [x]`. Skipping one? Same, plus a reason: "
        "`- [x] [skipped: not a fit] **[author]...`. Either tag moves it to its own section below the next time a new day's file is created.",
        "",
    ]
    all_flagged, all_skipped, all_blocked = [], [], []
    for block in results.values():
        lines.append(f"## [{block['thread']}]({block['thread_url']})")
        lines.append("")
        if block.get("note"):
            lines.append(f"*{block['note']}*")
            lines.append("")
        main, flagged, skipped, blocked = bucket_matches(block["matches"], prior)
        all_flagged.extend(flagged)
        all_skipped.extend(skipped)
        all_blocked.extend(blocked)
        if not main:
            lines.append("No matches this run.")
            lines.append("")
            continue
        for m in main:
            checked = prior.get(m["url"], {}).get("checked", False)
            box = "x" if checked else " "
            lines.append(f"- [{box}] **[{m['author']}]({m['url']})**: {m['excerpt'][:300]}")
        lines.append("")

    if all_flagged:
        lines.append("## Might be possible")
        lines.append("")
        lines.append("Still in play, just flagged, worth trying anyway (see the script's docstring for why these aren't hard skips). "
                      "Tick the box the same way if you apply, or tag it `[skipped: ...]` yourself to move it to Skipped instead.")
        lines.append("")
        for m, reason in all_flagged:
            checked = prior.get(m["url"], {}).get("checked", False)
            box = "x" if checked else " "
            lines.append(f"- [{box}] **[{m['author']}]({m['url']})**: {m['excerpt'][:300]} (flag: {reason})")
        lines.append("")

    if all_skipped:
        lines.append("## Skipped")
        lines.append("")
        lines.append("Ruled out for real, either you tagged it or the scanner's onsite/hybrid-only check did (see the script's docstring).")
        lines.append("")
        for m, reason in all_skipped:
            lines.append(f"- ~~[{m['author']}]({m['url']}): {m['excerpt'][:200]}~~ (skipped: {reason})")
        lines.append("")

    if all_blocked:
        lines.append("## Blocklisted")
        lines.append("")
        lines.append("Pulled out of the lists above. See [07-companies-to-avoid.md](07-companies-to-avoid.md) for why.")
        lines.append("")
        for m in all_blocked:
            lines.append(f"- ~~[{m['author']}]({m['url']}): {m['excerpt'][:200]}~~ (matched: {m['blocked']})")
        lines.append("")
    with open(path, "w") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stack", help="comma-separated keywords, overrides default stack")
    ap.add_argument("--json", action="store_true", help="output JSON instead of text, skips writing the markdown file")
    ap.add_argument("--out", default=None, help="markdown report path (default scan-results/hn-scan-<today>.md)")
    ap.add_argument("--force", action="store_true", help="rescan and merge fresh HN data into today's file even if it already exists")
    args = ap.parse_args()
    out_path = args.out or default_out()

    if not args.json and not args.force and os.path.exists(out_path):
        print(f"{out_path} already exists, leaving it alone.")
        print("Your edits (checkboxes, [skipped: ...] tags, anything else) are untouched. Pass --force to rescan and merge in fresh HN data anyway.")
        return

    stack_words = [w.strip() for w in args.stack.split(",")] if args.stack else DEFAULT_STACK
    stack_pattern = re.compile("|".join(rf"\b{w}\b" for w in stack_words), re.I)

    results = {}

    hiring = find_latest_thread("Ask HN Who is hiring", author="whoishiring")
    if hiring:
        results["who_is_hiring"] = {
            "thread": hiring["title"],
            "thread_url": f"https://news.ycombinator.com/item?id={hiring['objectID']}",
            "matches": scan_thread(hiring["objectID"], contract_required=True, stack_pattern=stack_pattern),
        }

    freelancer = find_latest_thread("Freelancer Seeking freelancer")
    if freelancer:
        # In this thread, filter for people SEEKING a freelancer (hiring), not offering work.
        data = fetch_json(f"{ALGOLIA}/items/{freelancer['objectID']}")
        seeking_re = re.compile(r"SEEKING (A )?FREELANCER|LOOKING FOR|HIRING", re.I)
        matches = []
        for c in data.get("children", []):
            text = strip_html(c.get("text", ""))
            if seeking_re.search(text[:80]) and stack_pattern.search(text):
                matches.append({
                    "id": c.get("id"),
                    "author": c.get("author"),
                    "url": f"https://news.ycombinator.com/item?id={c.get('id')}",
                    "excerpt": text[:400],
                    "full_text": text,
                    "flag": detect_flag(text),
                    "hard_skip": detect_hard_skip(text),
                })
        results["freelancer_thread"] = {
            "thread": freelancer["title"],
            "thread_url": f"https://news.ycombinator.com/item?id={freelancer['objectID']}",
            "matches": matches,
            "note": "This thread is usually dominated by people OFFERING freelance work, not seeking it. Check manually too.",
        }

    blocklist = load_blocklist()
    tag_blocklist(results, blocklist)

    if args.json:
        print(json.dumps(results, indent=2))
        return

    prior_path = find_prior_report(out_path)
    prior = read_prior_state(prior_path)

    all_flagged, all_skipped, all_blocked = [], [], []
    for block in results.values():
        print(f"\n=== {block['thread']} ===")
        print(block["thread_url"])
        if block.get("note"):
            print(f"(note: {block['note']})")
        main, flagged, skipped, blocked = bucket_matches(block["matches"], prior)
        all_flagged.extend(flagged)
        all_skipped.extend(skipped)
        all_blocked.extend(blocked)
        if not main:
            print("No matches this run.")
        for m in main:
            print(f"\n  [{m['author']}] {m['url']}")
            print(f"  {m['excerpt'][:280]}")

    if all_flagged:
        print("\n=== Might be possible ===")
        for m, reason in all_flagged:
            print(f"  [{reason}] {m['author']} {m['url']}")

    if all_skipped:
        print("\n=== Skipped ===")
        for m, reason in all_skipped:
            print(f"  [{reason}] {m['author']} {m['url']}")

    if all_blocked:
        print("\n=== Blocklisted (see 07-companies-to-avoid.md) ===")
        for m in all_blocked:
            print(f"  [{m['blocked']}] {m['author']} {m['url']}")

    write_markdown(results, out_path, stack_words, prior)
    print(f"\nReport written to {out_path}")


if __name__ == "__main__":
    main()
