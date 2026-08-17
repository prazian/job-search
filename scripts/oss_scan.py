#!/usr/bin/env python3
"""
Checks a curated list of open-source repos (edit REPOS below) for signs of
active paid/volunteer help wanted: open "help wanted" / "good first issue"
issues, star count, open issue count. Uses GitHub's public REST API
(unauthenticated: 60 req/hr core, 10 req/min search, this script paces itself).

Usage:
    python3 oss_scan.py
    python3 oss_scan.py --repo infisical/infisical --repo zitadel/zitadel
"""
import argparse
import json
import time
import urllib.request

API = "https://api.github.com"

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
        "good_first_issue_open": good_first.get("total_count"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", action="append", help="owner/repo, repeatable; overrides default list")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

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


if __name__ == "__main__":
    main()
