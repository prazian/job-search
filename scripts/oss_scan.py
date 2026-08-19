#!/usr/bin/env python3
"""
Checks a curated list of open-source repos (edit REPOS below) for signs of
active paid/volunteer help wanted: open "help wanted" / "good first issue"
issues, star count, open issue count. Uses GitHub's public REST API
(unauthenticated: 60 req/hr core, 10 req/min search, this script paces itself).

Writes a dated, clickable markdown report to scan-results/oss-scan-YYYY-MM-DD.md,
one per day. If today's file already exists, running this again does nothing
to it (skips the ~2 minute rate-limited scan entirely), prints a note and
exits, your edits are never touched or re-parsed mid-day. Pass --force to
rescan and merge fresh GitHub data into today's file anyway. Each repo's
"Applied" column shows a checkbox, just open the file in an editor and tick
it, "- [ ]" to "- [x]", once you've reached out. When a genuinely new day's
file gets created, that column is read back out of the most recent prior
day's file, so applied status carries forward automatically.

Usage:
    python3 oss_scan.py
    python3 oss_scan.py --repo infisical/infisical --repo zitadel/zitadel
    python3 oss_scan.py --json           # machine-readable output, no file written
    python3 oss_scan.py --force          # rescan and merge fresh data into today's file even if it exists
"""
import argparse
import glob
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://api.github.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_DIR = os.path.join(ROOT, "scan-results")
TABLE_ROW_RE = re.compile(r"^\|\s*\[([^\]]+)\]\([^)]+\)\s*\|\s*(\[x\]|\[ \])\s*\|")

# Repos worth checking periodically: fast-growing or sponsor/VC-backed infra &
# devtool projects in the AWS/Python/TypeScript/Go/cloud space. Edit freely.
REPOS = [
    "infisical/infisical",
    "windmill-labs/windmill",
    "triggerdotdev/trigger.dev",
    "opentofu/opentofu",
    "crossplane/crossplane",
    "coder/coder",
    "dagger/dagger",
    "coollabsio/coolify",
    "zitadel/zitadel",
    "kubernetes-sigs/karpenter",
]


def default_out() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(SCAN_DIR, f"oss-scan-{today}.md")


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "User-Agent": "job-search-scan/1.0",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def issue_search_url(repo: str, label: str) -> str:
    q = f'is:issue is:open label:"{label}"'
    return f"https://github.com/{repo}/issues?q={urllib.parse.quote(q)}"


def check_repo(repo: str) -> dict:
    meta = get(f"{API}/repos/{repo}")
    time.sleep(6.5)  # stay under the 10/min unauthenticated search rate limit
    help_wanted = get(
        f"{API}/search/issues?q=repo:{repo}+is:issue+is:open+label:%22help+wanted%22"
    )
    time.sleep(6.5)
    good_first = get(
        f"{API}/search/issues?q=repo:{repo}+is:issue+is:open+label:%22good+first+issue%22"
    )
    time.sleep(6.5)
    return {
        "repo": repo,
        "url": meta.get("html_url"),
        "homepage": meta.get("homepage"),
        "stars": meta.get("stargazers_count"),
        "open_issues": meta.get("open_issues_count"),
        "help_wanted_open": help_wanted.get("total_count"),
        "help_wanted_url": issue_search_url(repo, "help wanted"),
        "good_first_issue_open": good_first.get("total_count"),
        "good_first_issue_url": issue_search_url(repo, "good first issue"),
    }


def applied_repos_from_file(path: str) -> set[str]:
    if not path or not os.path.exists(path):
        return set()
    applied = set()
    with open(path) as f:
        for line in f:
            m = TABLE_ROW_RE.match(line)
            if m and m.group(2) == "[x]":
                applied.add(m.group(1))
    return applied


def find_prior_report(out_path: str) -> str | None:
    """Today's own file if a same-day rerun, else the most recent earlier report."""
    if os.path.exists(out_path):
        return out_path
    others = sorted(glob.glob(os.path.join(SCAN_DIR, "oss-scan-*.md")))
    return others[-1] if others else None


def write_markdown(results: list[dict], path: str, applied: set[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# OSS help-wanted scan",
        "",
        f"Generated {now}.",
        "New file each day (`scan-results/oss-scan-YYYY-MM-DD.md`). Once this file exists, running the scan again today does nothing to it, edit freely.",
        "Applied somewhere? Tick its box in the Applied column, `[ ]` to `[x]`, and save. It carries into the next new day's scan automatically.",
        "",
        "| Repo | Applied | Stars | Open issues | Help wanted | Good first issue |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        if "error" in r:
            lines.append(f"| {r['repo']} | [ ] | error | {r['error']} | | |")
            continue
        box = "[x]" if r["repo"] in applied else "[ ]"
        hw = f"[{r['help_wanted_open']} open]({r['help_wanted_url']})" if r["help_wanted_open"] else "0"
        gfi = f"[{r['good_first_issue_open']} open]({r['good_first_issue_url']})" if r["good_first_issue_open"] else "0"
        lines.append(
            f"| [{r['repo']}]({r['url']}) | {box} | {r['stars']} | {r['open_issues']} | {hw} | {gfi} |"
        )
    lines.append("")
    with open(path, "w") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", action="append", help="owner/repo, repeatable; overrides default list")
    ap.add_argument("--json", action="store_true", help="output JSON instead of text, skips writing the markdown file")
    ap.add_argument("--out", default=None, help="markdown report path (default scan-results/oss-scan-<today>.md)")
    ap.add_argument("--force", action="store_true", help="rescan and merge fresh data into today's file even if it already exists")
    args = ap.parse_args()
    out_path = args.out or default_out()

    if not args.json and not args.force and os.path.exists(out_path):
        print(f"{out_path} already exists, leaving it alone.")
        print("Your edits (Applied checkboxes, anything else) are untouched. Pass --force to rescan and merge in fresh data anyway.")
        return

    repos = args.repo if args.repo else REPOS
    results = []
    for i, repo in enumerate(repos):
        if i > 0:
            time.sleep(2)
        try:
            results.append(check_repo(repo))
        except Exception as e:
            results.append({"repo": repo, "error": str(e)})

    if args.json:
        print(json.dumps(results, indent=2))
        return

    for r in results:
        if "error" in r:
            print(f"{r['repo']}: ERROR {r['error']}")
            continue
        print(f"\n{r['repo']}  ({r['url']})")
        print(f"  stars={r['stars']}  open_issues={r['open_issues']}  "
              f"help_wanted={r['help_wanted_open']}  good_first_issue={r['good_first_issue_open']}")

    prior = find_prior_report(out_path)
    applied = applied_repos_from_file(prior)
    write_markdown(results, out_path, applied)
    print(f"\nReport written to {out_path}")


if __name__ == "__main__":
    main()
