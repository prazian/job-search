#!/usr/bin/env python3
"""
Checks a curated list of open-source repos (edit REPOS below) for signs of
active paid/volunteer help wanted: open, unassigned "help wanted" / "good
first issue" issues, star count, open issue count. Query is state:open plus
no:assignee, so already-claimed issues don't show up as opportunities, and
adds label:accepted too on repos that actually use that triage label (checked
live per repo, not assumed). Uses GitHub's public REST API (unauthenticated:
60 req/hr core, 10 req/min search, this script paces itself).

Writes a dated, clickable markdown report to
scan-results/YYYY-MM-DD/oss-scan.md, one folder per day. If today's file
already exists, running this again does nothing to it (skips the ~2 minute
rate-limited scan entirely), prints a note and exits, your edits are never
touched or re-parsed mid-day. Pass --force to rescan and merge fresh GitHub
data into today's file anyway. Each repo's "Applied" column shows a checkbox,
just open the file in an editor and tick it, "- [ ]" to "- [x]", once you've
reached out. When a genuinely new day's file gets created, that column is read
back out of the most recent prior day's file, so applied status carries
forward automatically.

If any repo's fetch fails partway through (rate limit, network, whatever),
the whole run aborts and no file gets written, exit code 1, nothing
partial/broken persisted as today's report. Re-run once the problem's gone.

Usage:
    python3 oss_scan.py
    python3 oss_scan.py --repo infisical/infisical --repo zitadel/zitadel
    python3 oss_scan.py --json           # machine-readable output, no file written
    python3 oss_scan.py --force          # rescan and merge fresh data into today's file even if it exists
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import _common

API = "https://api.github.com"
SOURCE = "oss"
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


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "User-Agent": "job-search-scan/1.0",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def repo_has_label(repo: str, label_name: str) -> bool:
    """"accepted" is a project-specific triage label, not a GitHub standard,
    only add it to the query for repos that actually use it (checked live,
    not hardcoded, since REPOS is meant to be edited freely)."""
    try:
        labels = get(f"{API}/repos/{repo}/labels?per_page=100")
    except Exception:
        return False
    return any(l.get("name", "").lower() == label_name.lower() for l in labels)


def build_filter_query(label: str, require_accepted: bool) -> str:
    parts = ["is:issue", "state:open", f'label:"{label}"']
    if require_accepted:
        parts.append("label:accepted")
    parts.append("no:assignee")
    return " ".join(parts)


def issue_search_url(repo: str, filter_query: str) -> str:
    return f"https://github.com/{repo}/issues?q={urllib.parse.quote(filter_query)}"


def check_repo(repo: str) -> dict:
    meta = get(f"{API}/repos/{repo}")
    has_accepted = repo_has_label(repo, "accepted")
    time.sleep(6.5)  # stay under the 10/min unauthenticated search rate limit

    hw_query = build_filter_query("help wanted", has_accepted)
    help_wanted = get(f"{API}/search/issues?q={urllib.parse.quote(f'repo:{repo} {hw_query}')}")
    time.sleep(6.5)

    gfi_query = build_filter_query("good first issue", has_accepted)
    good_first = get(f"{API}/search/issues?q={urllib.parse.quote(f'repo:{repo} {gfi_query}')}")
    time.sleep(6.5)

    return {
        "repo": repo,
        "url": meta.get("html_url"),
        "homepage": meta.get("homepage"),
        "stars": meta.get("stargazers_count"),
        "open_issues": meta.get("open_issues_count"),
        "help_wanted_open": help_wanted.get("total_count"),
        "help_wanted_url": issue_search_url(repo, hw_query),
        "good_first_issue_open": good_first.get("total_count"),
        "good_first_issue_url": issue_search_url(repo, gfi_query),
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


def write_markdown(results: list[dict], path: str, applied: set[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# OSS help-wanted scan",
        "",
        f"Generated {now}.",
        "New file each day (`scan-results/YYYY-MM-DD/oss-scan.md`). Once this file exists, running the scan again today does nothing to it, edit freely.",
        "Applied somewhere? Tick its box in the Applied column, `[ ]` to `[x]`, and save. It carries into the next new day's scan automatically.",
        "",
        "| Repo | Applied | Stars | Open issues | Help wanted | Good first issue |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
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
    ap.add_argument("--out", default=None, help="markdown report path (default scan-results/<today>/oss-scan.md)")
    ap.add_argument("--force", action="store_true", help="rescan and merge fresh data into today's file even if it already exists")
    args = ap.parse_args()
    out_path = args.out or _common.dated_out(SOURCE)

    if not args.json and not args.force and os.path.exists(out_path):
        print(f"{out_path} already exists, leaving it alone.")
        print("Your edits (Applied checkboxes, anything else) are untouched. Pass --force to rescan and merge in fresh data anyway.")
        return

    repos = args.repo if args.repo else REPOS
    results = []
    for i, repo in enumerate(repos):
        if i > 0:
            time.sleep(2)
        print(f"  {_common.progress_bar(i, len(repos))}  checking {i + 1}/{len(repos)}: {repo}", file=sys.stderr)
        try:
            results.append(check_repo(repo))
        except Exception as e:
            results.append({"repo": repo, "error": str(e)})
            print(f"{repo}: ERROR {e}", file=sys.stderr)
            break  # no point burning more quota once one call has failed

    errors = [r for r in results if "error" in r]
    if errors:
        print(f"\n{len(errors)} repo(s) failed, most likely a rate limit. Not writing a report, "
              f"partial/broken data isn't worth persisting as today's file. Try again once "
              f"the rate limit resets (check: curl -s https://api.github.com/rate_limit).", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(results, indent=2))
        return

    for r in results:
        print(f"\n{r['repo']}  ({r['url']})")
        print(f"  stars={r['stars']}  open_issues={r['open_issues']}  "
              f"help_wanted={r['help_wanted_open']}  good_first_issue={r['good_first_issue_open']}")

    prior = _common.find_prior_report(out_path, SOURCE)
    applied = applied_repos_from_file(prior)
    write_markdown(results, out_path, applied)
    print(f"\nReport written to {out_path}")


if __name__ == "__main__":
    main()
