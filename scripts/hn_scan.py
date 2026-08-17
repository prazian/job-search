#!/usr/bin/env python3
"""
Scans the current month's Hacker News "Who is hiring?" and "Freelancer? Seeking
freelancer?" threads for posts that mention contract/freelance work matching a
given tech stack. Uses HN's public Algolia API, no auth, no scraping, no ToS issues.

Usage:
    python3 hn_scan.py                  # scan current month, default stack
    python3 hn_scan.py --stack "rust,react"
    python3 hn_scan.py --json           # machine-readable output
"""
import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request

ALGOLIA = "https://hn.algolia.com/api/v1"

DEFAULT_STACK = [
    "aws", "python", "typescript", "golang", r"go\b", "linux",
    "cloud", "devops", "kubernetes", "terraform", "infrastructure",
]
CONTRACT_WORDS = [
    r"\bcontract\b", r"\bfreelance", r"\bcontractor", r"\bcontract.to.hire\b",
    r"\bcontract.based\b", r"\b1099\b",
]
NEED_HELP_WORDS = [
    "need help", "looking for", "hiring", "seeking", "need a",
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stack", help="comma-separated keywords, overrides default stack")
    ap.add_argument("--json", action="store_true", help="output JSON instead of text")
    args = ap.parse_args()

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

    for key, block in results.items():
        print(f"\n=== {block['thread']} ===")
        print(block["thread_url"])
        if block.get("note"):
            print(f"(note: {block['note']})")
        if not block["matches"]:
            print("No matches this run.")
        for m in block["matches"]:
            print(f"\n  [{m['author']}] {m['url']}")
            print(f"  {m['excerpt'][:280]}")


if __name__ == "__main__":
    main()
