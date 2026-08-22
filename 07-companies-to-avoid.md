# Companies to Avoid

Two kinds of entries here: **reported directly** (you ran into it yourself, that's real signal but not something I independently fact-checked) and **pattern-matched** (it fits a well-known scam shape, worth caution even without a direct report). Each entry says which.

## Blocked

| Company | Why | Source | First seen |
|---|---|---|---|
| Flywheel Motion | Frames real production work as a disposable "40 minute task" and asks candidates to complete it unpaid, a classic unpaid-labor extraction pattern dressed up as a skills test | Reported directly, 2026-08-19 | [HN, Who is hiring (August 2026)](https://news.ycombinator.com/item?id=49156702), posted by HN user norejisace |

I searched for independent corroboration (Glassdoor, Reddit) before writing this and found none, not because the report looks weak, but because this looks like a very small/new operation with no public review footprint yet either way. So this entry rests entirely on what you ran into, treat it as solid (you're the one who dealt with them), just noting for the record that it isn't cross-checked against a second source the way the rest of this repo's data is.

## Note on Danish companies (not a block)

**Correction, 2026-08-22**: an earlier version of this file blocked Trustpilot and Pleo entirely as "Danish companies." That was wrong. The actual preference, clarified directly: Danish companies are fine, remote work for one is fine, the only thing off the table is a role that requires actually living in Denmark again. So this is handled at the listing level instead, not the company level: `djinni_scan.py`, `company_scan.py`, and `jobicy_scan.py` all skip a listing whose location is Denmark-only, but don't exclude a listing (or a company) just because Denmark is one of several remote-eligible options alongside others, or because the company happens to be Danish-founded. Nothing blocked here for this reason anymore.

## What "unpaid test task" scams usually look like

- A task framed as short and casual ("just a 40 minute task") that turns out, on a closer look, to be real production work: a piece of content, a landing page, a working script, an actual bug fix.
- No compensation offered for the task itself. "Just to see how you work" is the usual line.
- Vague or dodged answers about what happens to the output afterward.
- The company collects free deliverables from a batch of applicants and either nobody gets hired, or the "role" quietly disappears once enough free work has come in.

Legitimate paid test tasks are normal for senior contract work, the difference is they're **explicitly paid**, tightly scoped, and usually capped at an hour or two. If a "test" isn't paid and isn't obviously throwaway in scope, don't do it.

## How this feeds back into the automation

`scripts/hn_scan.py` reads the Blocked table above and checks every match's text against it. If a blocked company's name shows up in a future scan (say, Flywheel Motion posts again next month), the report flags it instead of quietly listing it as a fresh lead. See the flagged entries in your scan reports for a working example.

## Adding to this list

Add a row to the Blocked table: company, why, source, where you saw it. Keep the Company cell to just the plain name (e.g. "Flywheel Motion", not "Flywheel Motion (flywheelmotion.com)"), that's the exact string the scanner matches against.
