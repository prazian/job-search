# Fresh Hiring/Contract Posts — Verified, Not Guessed

**The honest number: 5, not 15.** Hacker News is the only one of the target platforms (Reddit, Twitter/X, LinkedIn, Discord, Telegram) that has a public, scriptable API — I tested Reddit directly and it hard-blocks non-browser requests (403 "blocked due to network policy"); Twitter/X, LinkedIn, and Discord all require an authenticated session I don't have. Rather than pad this out with 10 more that I couldn't actually verify, here are 5 that are **real, dated, and independently checkable right now** — click any link below.

Source: [Ask HN: Who is hiring? (August 2026)](https://news.ycombinator.com/item?id=49156683), scanned via HN's public Algolia API on 2026-08-17. `scripts/hn_scan.py` re-runs this scan against whichever month's thread is current — run it weekly, it auto-discovers the new thread each month.

## The 5 leads

### 1. Reef Technologies — Senior Python Backend Engineer — 🟢 best geographic fit
**[Post](https://news.ycombinator.com/item?id=49166151)** · Fully remote, worldwide, B2B contract · $45–70 USD/hr (or 180–280 PLN/hr) · 30h/week minimum, flexible schedule
> "Contribute from wherever you like; we are fully remote... Set your own time commitment, as long as it's at least 30h per week."

No location restriction stated — explicitly "from wherever you like." Apply via [careers.reef.pl](https://careers.reef.pl/?utm_source=hackernews) (they say skip the CV, just follow their apply flow).

**DM/apply opener:**
```
Applying via the careers.reef.pl flow, but wanted to say hello directly too — the Sociocracy 3.0 / self-directed structure is a great fit for how I like to work. 5+ years hands-on Python plus a deep AWS/Linux infrastructure background (I've spent most of my career on exactly this kind of distributed-systems/cloud-infra work) — happy to talk specifics on the supercluster/container-runner problem.
```

### 2. Viteus (Alteus) — Contract Engineer, DevOps/Full-Stack — 🟢 good fit
**[Post](https://news.ycombinator.com/item?id=49165622)** · Remote · Contract, matched per-engagement (1-week audits to multi-week refactors)
> "We are inviting independent contractors with experience across Full-Stack, AI/ML, QA, DevOps Engineering to register interest for matching against upcoming client engagements."

**DM opener:**
```
Saw the Viteus contractor call for DevOps/Full-Stack support. I do exactly this kind of production audit-and-refactor work — AWS, Kubernetes, Terraform, cloud cost/architecture cleanup — for scale-ups. Happy to register for the network; where should I send background and rate?
```

### 3. Flywheel Motion — Sr Agentic Engineer — 🟡 good fit, adjacent to core infra
**[Post](https://news.ycombinator.com/item?id=49156702)** · Remote, worldwide · Contract, scoped engagements (not hourly staffing)
> "Sr Agentic Engineer — Claude Code / Cursor / Aider across the FM stack: member site infrastructure, content automation pipelines. TypeScript, system architecture, comfortable scoping a problem before writing code."

**DM opener:**
```
The "scope before writing code" framing in your Sr Agentic Engineer listing matches how I already work with Claude Code and Cursor on production TypeScript systems — not just prototyping. 20 years combined backend/cloud architecture background behind it. Worth a quick conversation about the FM stack?
```

### 4. Arcforma AI — AI Engineer (contract track) — 🟡 confirm geography before pitching
**[Post](https://news.ycombinator.com/item?id=49248055)** · Contract, project-based, $50–150/hr, 3–6 week scoped engagements · Listing says "REMOTE (US only) or ONSITE NYC" — unclear if that restriction applies to the contract track specifically or just the full-time track. **Worth a direct one-line email to confirm before investing a full pitch.**

**Opener (framed as the clarifying question, not a full pitch):**
```
Quick question before I put together a proposal: is the contract track (project-based, $50–150/hr) open to remote-from-anywhere, or is the US-only restriction on the listing specific to the full-time role? If it's open, I'd like to talk about the infra/backend side of your AI production work — AWS, Python, cloud architecture background.
```

### 5. Early-stage health & wellness startup (doubling.io) — 🔴 skip unless you hold US work authorization
**[Post](https://news.ycombinator.com/item?id=49191343)** · Contract (1099), 40 hrs/week, Chicago-preferred or remote US · Explicitly states: **"Must be authorized to work in the US as an independent contractor; no visa sponsorship."** Including this for completeness, but the stated requirement disqualifies a non-US-authorized applicant — don't spend a pitch here unless that's changed or you have a path around it (e.g., a US-based EOR/agency relationship).

## Keeping this list alive

This goes stale within days — HN's hiring thread fills up over the first two weeks of each month. Run:
```
python3 scripts/hn_scan.py
```
weekly. It re-discovers the current month's thread automatically (no hardcoded IDs) and re-filters for contract/freelance + your stack. Takes about 10 seconds.
