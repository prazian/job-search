# Fresh Hiring/Contract Posts, Verified Not Guessed

**The honest number: 5, not 15.** Hacker News is the only one of the target platforms (Reddit, Twitter/X, LinkedIn, Discord, Telegram) that has a public, scriptable API. I tested Reddit directly and it hard-blocks non-browser requests (403 "blocked due to network policy"); Twitter/X, LinkedIn, and Discord all require an authenticated session I don't have. Rather than pad this out with 10 more that I couldn't actually verify, here are 5 that are **real, dated, and independently checkable right now**. Click any link below.

Source: [Ask HN: Who is hiring? (August 2026)](https://news.ycombinator.com/item?id=49156683), scanned via HN's public Algolia API on 2026-08-17. `scripts/hn_scan.py` re-runs this scan against whichever month's thread is current, run it weekly, it auto-discovers the new thread each month.

**On location and hours:** based in Armenia, but genuinely flexible on timezone, including full US business hours if a role needs it. What isn't flexible: legal work authorization. The documents on hand (Estonian e-Residency, Danish residence permit) are useful for running things as an EU-facing B2B entity, but neither one, nor Armenian residency, grants authorization to work in the US. That distinction only bites on roles that explicitly require it, most contract/B2B engagements don't, since they're paying a foreign entity for services rather than employing a person. Flagged below wherever it matters.

## The 5 leads

### 1. Reef Technologies, Senior Python Backend Engineer, 🟢 best geographic fit
**[Post](https://news.ycombinator.com/item?id=49166151)** · Fully remote, worldwide, B2B contract · $45-70 USD/hr (or 180-280 PLN/hr) · 30h/week minimum, flexible schedule
> "Contribute from wherever you like; we are fully remote... Set your own time commitment, as long as it's at least 30h per week."

No location restriction stated, explicitly "from wherever you like." Apply via [careers.reef.pl](https://careers.reef.pl/?utm_source=hackernews) (they say skip the CV, just follow their apply flow).

**DM/apply opener:**
```
Applying through the careers.reef.pl flow, but wanted to say hi directly too. The Sociocracy 3.0 / self-directed structure is a great fit for how I like to work. 5+ years hands-on Python plus a deep AWS/Linux background, most of my career's been exactly this kind of distributed-systems/cloud-infra work. Happy to talk specifics on the supercluster/container-runner problem.
```

### 2. Viteus (Alteus), Contract Engineer, DevOps/Full-Stack, 🟢 good fit
**[Post](https://news.ycombinator.com/item?id=49165622)** · Remote · Contract, matched per-engagement (1-week audits to multi-week refactors)
> "We are inviting independent contractors with experience across Full-Stack, AI/ML, QA, DevOps Engineering to register interest for matching against upcoming client engagements."

**DM opener:**
```
Saw the Viteus contractor call for DevOps/Full-Stack support. I do exactly this kind of production audit-and-refactor work (AWS, Kubernetes, Terraform, cloud cost/architecture cleanup) for scale-ups. Happy to register for the network, where should I send background and rate?
```

### 3. Flywheel Motion, Sr Agentic Engineer, 🟡 good fit, adjacent to core infra
**[Post](https://news.ycombinator.com/item?id=49156702)** · Remote, worldwide · Contract, scoped engagements (not hourly staffing)
> "Sr Agentic Engineer, Claude Code / Cursor / Aider across the FM stack: member site infrastructure, content automation pipelines. TypeScript, system architecture, comfortable scoping a problem before writing code."

**DM opener:**
```
The "scope before writing code" line in your Sr Agentic Engineer listing matches how I already work with Claude Code and Cursor on production TypeScript systems, not just prototyping. Got 20 years of backend/cloud architecture behind it too. Worth a quick chat about the FM stack?
```

### 4. Arcforma AI, AI Engineer (contract track), 🟡 confirm which kind of "US only" before pitching
**[Post](https://news.ycombinator.com/item?id=49248055)** · Contract, project-based, $50-150/hr, 3-6 week scoped engagements · Listing says "REMOTE (US only) or ONSITE NYC." The open question is what "US only" means here: if it's about timezone/overlap, that's a non-issue (happy to work US hours); if it's about requiring US work authorization for tax/compliance reasons, that's a real blocker, since Armenian residency, Estonian e-Residency, and a Danish residence permit don't add up to US work authorization. **Worth a direct one-line email to find out which one it is before investing a full pitch.**

**Opener (framed as the clarifying question, not a full pitch):**
```
Quick question before I put together a proposal: is the "US only" on the contract track about needing US work authorization, or just wanting someone on US hours? I can work any timezone including full US business hours, just flagging that I'm not US-authorized if that's what it's about. If it's the former, I'd still love to talk, infra/backend side of your AI production work is right in my lane (AWS, Python, cloud architecture).
```

### 5. Early-stage health & wellness startup (doubling.io), 🔴 skip, this one's a real blocker
**[Post](https://news.ycombinator.com/item?id=49191343)** · Contract (1099), 40 hrs/week, Chicago-preferred or remote US · Explicitly states: **"Must be authorized to work in the US as an independent contractor; no visa sponsorship."** That's unambiguous, and Armenian, Estonian, or Danish documents don't satisfy it. Including this for completeness, but don't spend a pitch here unless a US-based EOR/agency relationship changes the picture.

## Keeping this list alive

This goes stale within days, HN's hiring thread fills up over the first two weeks of each month. Run:
```
python3 scripts/hn_scan.py
```
weekly. It re-discovers the current month's thread automatically (no hardcoded IDs) and re-filters for contract/freelance plus your stack. Takes about 10 seconds.
