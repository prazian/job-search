# LinkedIn: Boolean Search + Recency Filters + Outreach Sequence

LinkedIn's ToS blocks automated access and there's no API for this, so everything below you run yourself, in your own logged-in browser. It's genuinely fast once you have the strings saved.

## 1. Boolean search syntax that actually works

LinkedIn's search bar (top of the page, not the Jobs search) supports:
- `AND` / `OR` / `NOT`, must be capitalized
- `"exact phrase"`, quotes force an exact match
- `(grouping)`, parentheses to combine

**Base string for your stack:**
```
("looking for" OR "need help" OR "hiring" OR "anyone know") AND ("contract" OR "freelance" OR "contractor" OR "part-time") AND (AWS OR Python OR TypeScript OR Golang OR "cloud architecture" OR DevOps OR Kubernetes OR Terraform)
```

Paste that into the main search bar, hit enter, then filter results to **Content type → Posts** (not People/Jobs/Companies, that's the whole trick, most people only ever search Jobs).

**Narrower variants worth saving:**
```
("need a contractor" OR "hiring a freelancer" OR "looking for a contract") AND (backend OR infrastructure OR DevOps OR "cloud migration")
```
```
("MVP" OR "early stage" OR "small team") AND ("need help" OR "looking for") AND (AWS OR backend OR infrastructure)
```

## 2. The "recently posted" view

This isn't a single named button, it's a combination:

1. Run the boolean search above.
2. Filter **Content type → Posts**.
3. Sort by **Latest** (top-right of results, default is usually "Top match", switch it). This is what actually gets you recency; "Top match" mixes in old high-engagement posts.
4. If a **Date posted** filter appears (Past 24 hours / Past week / Past month), use it. LinkedIn rolls this in and out, so if it's not there, Latest-sort plus eyeballing timestamps is the reliable fallback.
5. Click into any promising author, then their profile, to see if they've posted similarly before. That tells you if they hire contractors regularly, worth a bookmark for repeat outreach.

**Save the search.** On the results page there's a "Create search alert" bell icon, LinkedIn will notify you of new matching posts without you re-running it manually. This is the closest thing to automation LinkedIn allows.

## 3. Google X-ray (when LinkedIn's own recency filter is being unhelpful)

Google indexes public LinkedIn posts and gives you a recency filter LinkedIn sometimes doesn't:
```
site:linkedin.com/posts "hiring" "contract" AWS OR Python OR "cloud architecture"
```
Run it, then in Google click **Tools → Any time → Past week**. This catches posts even when you're not sure of the exact phrasing, and Google's date filter is more reliable than LinkedIn's own.

## 4. If you get access to Sales Navigator (even a trial)

Worth a free 30-day trial just for this: boolean search extends to profile fields (headline, About section), you can filter by company headcount and founded date (a great proxy for "small, recently-funded team"), and saved searches auto-refresh with alerts. Not required, the free-tier method above works fine, but it compounds if you're doing this daily.

---

## 5. Three-part outreach sequence

Rules that matter more than the wording: **reply within hours, not days** (hiring posts get buried fast), reference their actual words, ask one small yes/no question instead of proposing a call, and never lead with a rate.

### Message 1, same day as their post

```
Hey [Name], saw your post about [specific thing they said, e.g. "needing a hand with your AWS migration"].

I'm a solutions architect / full-stack dev (AWS, Python, TypeScript, Go, [X] years, ex-[relevant angle if useful]), currently taking on contract work. [One line tying your background to their specific problem, e.g. "Spent the last few years doing exactly this kind of ECS/Terraform migration for startups moving off Heroku."]

Can send a couple examples if that's useful, no pressure either way. Still looking for someone?
```

### Message 2, day 3-4, only if no reply

```
Hey, following up in case this got buried. No worries if the timing's off or it's already filled.

One more thing that might help: [a genuinely specific, useful observation about their stack/problem, a link to a relevant OSS contribution, a one-line technical suggestion, or a short case study link].

Either way, if you ever need backup down the line, happy to stay in touch.
```

### Message 3, day 7-10, final

```
Last one from me on this, didn't want to keep nudging.

If it's still open I can usually start within a few days. If not, all good, keep me in mind if something similar comes up. Good luck with [specific thing they're building]!
```

Why this shape works: message 1 is fast and low-friction, message 2 gives without asking (people respond to being helped more than being chased), message 3 removes the pressure entirely. Counter-intuitively that's often the one that gets a reply, because it signals you're not desperate and closes the loop cleanly.

Standalone copies of all three (with more placeholder variants) are in [templates/linkedin-sequence.md](templates/linkedin-sequence.md).
