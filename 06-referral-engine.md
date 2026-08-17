# Referral Engine: A Weekly System, Not a One-Time Blast

One honest caveat before the design: true "autopilot" — messages that send themselves to real contacts — isn't something worth building even if it were technically easy. Referral asks work *because* they're personal; auto-sent ones read as spam and burn the relationship for the one time you actually need it. What's below is the next best thing: a system that takes 30–45 minutes a week, reuses the same 3 messages, and tracks itself so nothing falls through — plus the two scan scripts ([04](04-fresh-hiring-posts.md), [03](03-opensource-targets.md)) that genuinely do run themselves and keep feeding it raw material.

## The weekly ritual

**Once a week (pick a day, same day every week):**
1. Run `python3 scripts/hn_scan.py` — 10 seconds, fresh leads.
2. Pick **5 targets** for the week, split across three lanes:
   - **2 warm reconnects** — former colleagues, past clients, people from Denmark/Yerevan/prior jobs you haven't talked to in 6+ months. Use Template A.
   - **2 community touches** — someone active in one of the [10 communities](01-founder-communities.md) whose post or comment suggests they might know who's hiring, or a direct post into a community's jobs channel. Use Template B.
   - **1 direct referral ask** — someone well-connected (ex-manager, mentor, active networker) who probably knows 3 people you don't. Use Template C.
3. Log every send in [tracker.csv](tracker.csv) the moment you send it — not at the end of the week, you will forget.
4. **Same day, every week:** review the tracker for anything due a follow-up (day 3–4 → Template A/B follow-up; day 7–10 → final close, same shape as the [LinkedIn sequence](02-linkedin-playbook.md)).

That's the whole system. The compounding part is consistency — 5 a week is ~250 people reached over a year, from a rotating base of maybe 40–60 people you actually know plus the communities.

## 3 templates

### Template A — warm reconnect (people who already know you)
```
Hey [Name] — it's been a while! Hope [specific thing you know about their situation — new role, new city, their company] is going well.

Small update on my end: went independent, doing contract work in cloud architecture / backend (AWS, Python, TypeScript, Go) — mostly helping small teams and startups that need senior infra help without a full-time hire. Based in Armenia now, which turns out to be a pretty good remote timezone bridge for EU + US-morning teams.

No ask here really — just reconnecting. But if you ever hear of someone needing backup on the infra/backend side, keep me in mind.
```

### Template B — community touch (posted publicly or DM'd to an active member)
```
Hi [Name] — saw your [post/comment] in [community name] about [specific topic]. 

I do contract work in exactly that space (AWS/cloud architecture, Python, TypeScript, Go — 20 years combined experience) and figured I'd say hi rather than lurk. Not pitching anything specific — just glad to be a resource if you or anyone in here ever needs an extra senior hand on infra/backend work.
```

### Template C — direct referral ask (people who know a lot of people)
```
Hey [Name] — quick one. I've gone independent doing contract cloud/backend work (AWS, Python, TypeScript, Go), based in Armenia now with rates that reflect that.

You talk to a lot of founders/teams — does anyone come to mind who's been complaining about needing infra help, a cloud migration, or just extra senior backend capacity? Happy to be introduced, or feel free to just forward my info.

Thanks either way — hope things are good with you.
```

Standalone copies (plus a shorter variant of each): [templates/referral-engine-messages.md](templates/referral-engine-messages.md).

## The tracker

[tracker.csv](tracker.csv) — open in Excel/Numbers/Google Sheets. Columns:

| Column | What goes here |
|---|---|
| `date_sent` | When you sent it |
| `contact_name` | Who |
| `channel` | LinkedIn / Email / Community DM / In-person / etc |
| `source` | Where they came from — which community, "alumni", "ex-colleague", which HN post, etc |
| `template_used` | A / B / C / LinkedIn-1 / etc, so you can see what's working |
| `status` | `sent` → `replied` → `call_booked` → `hired` / `passed` / `no_response` |
| `follow_up_date` | Auto-calculate as +4 days for the first follow-up, +10 for the second — just fill it in when you log the send |
| `outcome_notes` | One line — why it worked or didn't. This is the field that makes week 12 smarter than week 1 |

Every two weeks, skim the `template_used` and `status` columns — if Template A is converting to replies 3x better than C, do more A. This is the only "optimization" step that matters; don't overthink it further than that.
