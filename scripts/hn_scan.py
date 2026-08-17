#!/usr/bin/env python3
"""
Scans the current month's Hacker News "Who is hiring?" and "Freelancer? Seeking
freelancer?" threads for posts that mention contract/freelance work matching a
given tech stack. Uses HN's public Algolia API, no auth, no scraping, no ToS issues.

Writes a dated, clickable markdown report to scan-results/hn-scan-YYYY-MM-DD.md
(one per day, kept for history, re-running the same day overwrites that day's
file). Each lead gets a checkbox, "- [ ]"/"- [x]", just open the file in an
editor and tick it once you've applied. Before writing, the script reads
checkbox state back out of today's existing file if there is one (so a same-day
re-run doesn't lose your edits), otherwise out of the most recent prior day's
file (so applied status carries forward day to day without you re-checking
anything).

Usage:
    python3 hn_scan.py                  # scan current month, default stack
    python3 hn_scan.py --stack "rust,react"
    python3 hn_scan.py --json           # machine-readable output, no file written
    python3 hn_scan.py --out path.md    # write the report somewhere else
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
CHECKBOX_RE = re.compile(r"^-\s\[([ xX])\]\s\*\*\[[^\]]+\]\((?P<url>[^)]+)\)")


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
        })
    return matches


def applied_urls_from_file(path: str) -> set[str]:
    if not path or not os.path.exists(path):
        return set()
    applied = set()
    with open(path) as f:
        for line in f:
            m = CHECKBOX_RE.match(line)
            if m and m.group(1).lower() == "x":
                applied.add(m.group("url"))
    return applied


def find_prior_report(out_path: str) -> str | None:
    """Today's own file if a same-day rerun, else the most recent earlier report."""
    if os.path.exists(out_path):
        return out_path
    others = sorted(glob.glob(os.path.join(SCAN_DIR, "hn-scan-*.md")))
    return others[-1] if others else None


def write_markdown(results: dict, path: str, stack_words: list[str], applied: set[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    display_stack = [w.replace(r"\b", "").replace("\\", "") for w in stack_words]
    lines = [
        "# HN contract/freelance scan",
        "",
        f"Generated {now}. Stack filter: {', '.join(display_stack)}.",
        "New file each day (`scan-results/hn-scan-YYYY-MM-DD.md`), history kept.",
        "Applied a lead? Just tick its box below, `- [ ]` to `- [x]`, and save. It carries into tomorrow's scan automatically.",
        "",
    ]
    for block in results.values():
        lines.append(f"## [{block['thread']}]({block['thread_url']})")
        lines.append("")
        if block.get("note"):
            lines.append(f"*{block['note']}*")
            lines.append("")
        if not block["matches"]:
            lines.append("No matches this run.")
            lines.append("")
            continue
        for m in block["matches"]:
            checked = m["url"] in applied
            box = "x" if checked else " "
            tag = " (applied)" if checked else ""
            lines.append(f"- [{box}] **[{m['author']}]({m['url']})**{tag}: {m['excerpt'][:300]}")
        lines.append("")
    with open(path, "w") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stack", help="comma-separated keywords, overrides default stack")
    ap.add_argument("--json", action="store_true", help="output JSON instead of text, skips writing the markdown file")
    ap.add_argument("--out", default=None, help="markdown report path (default scan-results/hn-scan-<today>.md)")
    args = ap.parse_args()
    out_path = args.out or default_out()

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
                })
        results["freelancer_thread"] = {
            "thread": freelancer["title"],
            "thread_url": f"https://news.ycombinator.com/item?id={freelancer['objectID']}",
            "matches": matches,
            "note": "This thread is usually dominated by people OFFERING freelance work, not seeking it. Check manually too.",
        }

    if args.json:
        print(json.dumps(results, indent=2))
        return

    for block in results.values():
        print(f"\n=== {block['thread']} ===")
        print(block["thread_url"])
        if block.get("note"):
            print(f"(note: {block['note']})")
        if not block["matches"]:
            print("No matches this run.")
        for m in block["matches"]:
            print(f"\n  [{m['author']}] {m['url']}")
            print(f"  {m['excerpt'][:280]}")

    prior = find_prior_report(out_path)
    applied = applied_urls_from_file(prior)
    write_markdown(results, out_path, stack_words, applied)
    print(f"\nReport written to {out_path}")


if __name__ == "__main__":
    main()
