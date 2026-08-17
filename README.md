# Job Search Playbook

A working system for landing freelance/contract work, built 2026-08-17. Read this file first, it tells you what's real, what's a template, and what to run.

## How this is organized

| File | What it is |
|---|---|
| [01-founder-communities.md](01-founder-communities.md) | 10 real founder hangouts with join links |
| [02-linkedin-playbook.md](02-linkedin-playbook.md) | Boolean search recipes + 3-message outreach sequence |
| [03-opensource-targets.md](03-opensource-targets.md) | Real, verified OSS projects that could use paid help |
| [04-fresh-hiring-posts.md](04-fresh-hiring-posts.md) | Verified live leads from HN's August 2026 threads |
| [05-wellfound-startups.md](05-wellfound-startups.md) | Recently-funded small startups + how to reach them |
| [06-referral-engine.md](06-referral-engine.md) | Weekly referral system + templates + tracker |
| [templates/](templates/) | Every reusable outreach message, standalone |
| [tracker.csv](tracker.csv) | Open in Excel/Numbers/Sheets, log every outreach here |
| [scripts/hn_scan.py](scripts/hn_scan.py) | **Working automation.** Re-run anytime for fresh leads |
| [scripts/oss_scan.py](scripts/oss_scan.py) | **Working automation.** Checks OSS repos for open help-wanted work |
| [Makefile](Makefile) | Shortcuts for the two scripts, run `make help` |

## What's real vs. what needs your hands

Being straight about this up front, because a fake lead wastes more time than an honest gap:

**Verified with live data (you can click these right now):**
- The 5 leads in [04-fresh-hiring-posts.md](04-fresh-hiring-posts.md), pulled from HN's public API today, real permalinks.
- The OSS projects in [03-opensource-targets.md](03-opensource-targets.md), star counts, open-issue counts, and help-wanted labels checked live via GitHub's API today.
- The community links in [01-founder-communities.md](01-founder-communities.md), **corrected 2026-08-18** after the first pass trusted search snippets instead of checking pages directly, which let a dead-since-2015 Slack community and a dead Discord invite through. Every row now verified against the platform's own API/page directly (Discord invite-lookup API, Telegram preview pages, direct page fetches). See that file for the method per row.
- The two scripts, both ran successfully against live APIs while building this.

**Not possible for me to do, and why:**
- **Scrape Slack/Discord/Telegram for "one recent gig posted in each community."** These platforms render via JavaScript and require a logged-in session; there's no public API for browsing a channel's history without membership. I could not fabricate a plausible-sounding fake post and hand it to you as real, that would be worse than saying nothing. Instead: real join links plus exactly which channel to check once you're in.
- **LinkedIn's "recently posted" feed, X-ray your network, or run searches as you.** LinkedIn requires an authenticated session and its ToS prohibits automated scraping; I have no login. What I *can* do, and did, is write out the actual boolean syntax and filter combinations that work, so you run them yourself in under 5 minutes.
- **Reddit.** Reddit blocks non-browser traffic outright (I hit a hard 403 testing this, both via direct fetch and API). Real subreddit names and saved-search URLs are in the docs; the live post-pulling has to happen in your own logged-in browser.
- **Wellfound founder contact info.** Wellfound intentionally gates direct contact behind its own messaging/apply system, that's the product, not an oversight, and scraping around it would cross from "research" into circumventing a platform's access controls. I found real, recently-funded companies instead; you reach founders through the normal channel (Wellfound message, or their public Twitter/LinkedIn/company email if listed).
- **15 verified fresh "need help" posts.** I got 5 solid, real, dated ones from HN (the only source with a public, scriptable API). The other 10 you'd get from Reddit/Twitter/LinkedIn/Discord live search, all blocked for the reasons above. The `hn_scan.py` script keeps this list refreshing itself, which is the actual fix for "this goes stale in a week."

## On the cloud automation attempt

Tried setting up a weekly cloud routine to run `hn_scan.py` automatically (routine `trig_01MfihDRiUAxfzmSPYauiZ6m`, currently **disabled**). It failed on the first test run: the cloud sandbox sits behind a network egress allowlist that blocks `hn.algolia.com` and `news.ycombinator.com` by default, confirmed via an explicit `EGRESS_BLOCKED` error from both `curl` and `WebFetch`, not a transient issue. Fixing it means allowlisting those two domains for the environment in claude.ai settings, which isn't something reachable from the scheduling API. Until/unless that's done, run the scan yourself, same script, already tested and working locally, just `python3 scripts/hn_scan.py`.

## Fastest path to a first message sent today

1. Open [04-fresh-hiring-posts.md](04-fresh-hiring-posts.md), pick the best-fit lead, send the opener.
2. Run `python3 scripts/hn_scan.py`, costs nothing, takes 10 seconds, HN refreshes its threads daily.
3. Join 2-3 communities from [01-founder-communities.md](01-founder-communities.md) today (approval can take a few days on some).
4. Log every send in [tracker.csv](tracker.csv) so nothing falls through.

## On positioning

Every template in here is written the same way: senior generalist (AWS/cloud architecture, Python, TypeScript, Go, Linux, 20 years combined between you and Yanovian LLC), now based in Armenia, open to competitive rates and fast starts. That's a genuine advantage (strong senior background plus cost/timezone flexibility), not a discount pitch, the copy treats it that way. Nothing here references your job-search situation, urgency, or that these materials exist; that's between you and this repo.

**Location and legal status, for accuracy when tailoring pitches:** based in Armenia, with Estonian e-Residency (a digital business ID for invoicing through an EU entity, not work authorization) and a Danish residence permit (from the years there, tied to Denmark specifically, not full EU freedom of movement). None of that grants US work authorization, so any role that explicitly requires it (like the doubling.io lead in [04](04-fresh-hiring-posts.md)) is a genuine skip, not just a caveat. It doesn't affect standard contract/B2B engagements, since those pay a foreign entity for services rather than employ a person. Timezone is fully flexible, including full US business hours, and every template above reflects that where it's relevant, not as a blanket claim shoved into every message.

The message templates are written to sound like one founder talking to another, not a marketing pitch: short, plain, contractions, no corporate polish. If you tweak them, keep that bar, a message that reads like it was typed fast and means it beats one that reads like it was drafted.
