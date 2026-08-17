# Open Source Projects Worth Pitching

All stats below pulled live from GitHub's public API today (2026-08-17), real numbers, not estimates. Selected for fit with your actual stack (AWS, Go, TypeScript, Python, cloud infra) and for being scaled/funded enough that "pay a contractor" is plausible, not wishful.

Reality check on "backed by active sponsors": GitHub's API doesn't expose sponsorship dollar amounts, so funding status below is general knowledge about each company (all are known VC-backed or foundation-backed), not something I verified line-by-line today. Cross-check on Crunchbase or the project's own site before you lean on a specific funding claim in conversation.

| Project | Stack fit | Stars | Open issues | help-wanted / good-first-issue (open, today) | Backing |
|---|---|---|---|---|---|
| [Infisical](https://github.com/Infisical/infisical) | TS, Go, AWS integrations | 28,810 | 738 | 8 / 15 | YC-backed (secrets management SaaS) |
| [Zitadel](https://github.com/zitadel/zitadel) | Go, cloud-native IAM | 14,751 | 1,124 | 7 / 43 | VC-backed (Germany) |
| [OpenTofu](https://github.com/opentofu/opentofu) | Go, IaC (Terraform fork) | 29,820 | 336 | not currently labeled, check Issues board directly | Linux Foundation |
| [Crossplane](https://github.com/crossplane/crossplane) | Go, cloud infra control plane | 11,944 | 184 | not currently labeled, check Issues board directly | CNCF graduated project |
| [Coder](https://github.com/coder/coder) | Go, remote dev environments | 14,176 | 976 | not currently labeled, check Issues board directly | VC-backed |
| [Dagger](https://github.com/dagger/dagger) | Go, CI/CD engine | 16,168 | 137 | not currently labeled, check Issues board directly | VC-backed |
| [Coolify](https://github.com/coollabsio/coolify) | PHP/Go, self-hosted PaaS | 60,686 | 762 | not currently labeled, check Issues board directly | Bootstrapped via Coolify Cloud, huge community |
| [Windmill](https://github.com/windmill-labs/windmill) | TS/Python/Rust, workflow engine | 17,566 | 820 | not currently labeled, check Issues board directly | YC-backed |
| [Trigger.dev](https://github.com/triggerdotdev/trigger.dev) | TS, background jobs platform | 16,047 | 426 | not currently labeled, check Issues board directly | VC-backed |

`scripts/oss_scan.py` re-checks all of these (and any repos you add to the list) live. The help-wanted/good-first-issue counts change week to week, so re-run it before you reach out rather than trusting this table after a few weeks.

## How to actually reach a maintainer

There's no "email the maintainer" shortcut that isn't public, and shouldn't be (personal emails aren't yours to scrape). The real paths, in order of response rate:
1. **Comment on a specific open issue.** By far the highest response rate. Maintainers watch their own issue queue; a cold DM doesn't compete with that.
2. **GitHub Discussions tab** (if the repo has one). Good for "would the team consider paid contract help with X" type asks that don't fit a single issue.
3. **Project Discord/Slack.** Most of the above link one from their README or homepage; ask in the `#contributing` or `#help` channel.
4. **Maintainer's public Twitter/X or Bluesky.** Listed on their GitHub profile, fine for a light, specific, non-spammy mention.

## Two tailored pitches (ready to adapt)

**Infisical, commenting on [issue #678](https://github.com/Infisical/infisical/issues/678), "Remove @aws-sdk/client-secrets-manager dependency from backend":**
```
Happy to pick this up. I've done a fair amount of AWS SDK v2 to v3 migration work and secrets-manager cleanup on production systems (AWS Solutions Architect background). If it's still open I can have a PR up in a few days. Also, if the team's ever open to ongoing contract help on the AWS integration side beyond this one issue, happy to talk. Background's cloud infra/DevOps (AWS, Terraform, Go, TS), available for contract work now.
```

**Zitadel, commenting on [issue #6912](https://github.com/zitadel/zitadel/issues/6912), "Add support for reverse proxy standard ForwardAuth (traefik, caddy, nginx)":**
```
This overlaps with infra work I've shipped before, reverse-proxy/auth integration on Traefik and Nginx in production Kubernetes setups. Happy to take a pass at this if it's still unclaimed. Also open to contract work if the team ever needs extra hands on the infra/DevOps side beyond individual issues, background's Go, Kubernetes, and cloud architecture (AWS/GCP/Azure).
```

Generic, swap-in version (any project, any issue) is in [templates/oss-maintainer-pitch.md](templates/oss-maintainer-pitch.md).

## Why this beats a generic "I'd love to contribute" DM

Every pitch above does real work first (claims a specific, real, currently-open issue) and only *then* mentions availability for paid work. That ordering is what makes it a low-friction yes instead of a cold ask. It costs you one real merged PR, but that PR is also portfolio evidence for the next pitch.
