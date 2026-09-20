---
title: "Reachability triage for the prod box — timeout vs refusal, and why third-party probers prove nothing"
date: 2026-09-20
category: developer-experience
module: folio_api
problem_type: workflow_issue
component: development_workflow
severity: medium
root_cause: missing_workflow_step
resolution_type: workflow_improvement
applies_when:
  - "Probing folio.openlegalstandard.org or its EC2 host and getting a connection timeout, a curl 000, or no HTTP response at all"
  - "About to state that production is down, or to escalate an apparent outage to whoever runs the infrastructure"
  - "Deciding whether an unreachable TCP port means a firewall or security-group rule versus a stopped daemon"
  - "Tempted to cite a third-party is-it-down service or CORS proxy as corroboration that an origin is unreachable"
tags: [reachability-triage, false-outage, connection-timeout, security-group, ssh-access, rate-limiting, verification, evidence]
related_components: [infrastructure, "folio_api/rate_limit.py"]
---

# Reachability triage: what a failed probe actually proves

## Context

Deploying PR #23 to `folio.openlegalstandard.org` required SSH to the production
EC2 box, and SSH would not connect. Diagnosing that took two passes with opposite
outcomes.

The first pass was sound and was later confirmed by an independent party. The
second pass declared production **down** and drafted an urgent outage message for
the user to forward to the person who administers the AWS account. Production was
never down. The user corrected it, and a re-test returned HTTP 200 in under 0.2s.

Both passes ran in the same session, minutes apart, against the same host. The
difference was not effort or care. It was whether each probe's failure mode was
matched to the claim it could support. This page records that mapping.

### The same failure had already happened once (session history)

The preceding session (2026-09-19, same branch) hit the same wall and left two
absence claims in its handoff: that no PEM for the box existed anywhere under the
home directory, and that "no Tailscale peer or `~/.ssh/config` entry exists for
it." Reviewing that session's transcript shows the whole diagnosis was a single
batched shell step, and that **it never checked `~/.ssh/config` or Tailscale at
all** — neither string appears anywhere in the session. The config file did in
fact exist. The claim was not a wrong measurement; it was a measurement that never
happened, written as a finding.

That session also produced a smaller instance of the same shape on an unrelated
subject: a research pass reported the property-tree child lists were unsorted, a
reviewer contradicted it, and inspection showed the sort was already there. Its own
diagnosis was "my grep pattern did not match `sorted(`." A negative result was
reported without stating the scope that produced it. Three instances across two
sessions — the false outage described above, plus these two — make this the repo's
most repeated verification failure, which is why it is worth a page.

## Guidance

### Read the failure signature before reading the failure

A connection attempt fails in distinguishable ways, and the way it fails localizes
the fault:

| Signature | What it proves | What it does NOT prove |
|---|---|---|
| **Connection refused** (immediate RST) | Host reachable, nothing listening on that port | Nothing about firewalls |
| **Connection timed out** (silent drop) | Packets discarded in flight — firewall, security group, or routing | Nothing about whether the daemon runs |
| **TLS completes, HTTP never answers** | The TLS terminator is alive | Nothing conclusive about the app behind it |
| **`curl` writes `000`** | *This client* got no response | Nothing about other clients, or about the origin |

The refused/timeout distinction is the highest-value one and costs nothing:

```bash
# refused → dead listener;  timed out → firewall
timeout 8 bash -c 'exec 3<>/dev/tcp/HOST/22' && echo OPEN || echo "exit=$?"
ssh -vv -o ConnectTimeout=10 user@HOST true 2>&1 | grep -iE 'refused|timed out'
```

### Pair every probe with a control that isolates one variable

A single failing probe has several candidate explanations, and each control below
removes one of them. Together these four narrow the fault to the network path; none
of them clears the service itself, which is why the conclusion stops at "`sshd` is
very likely fine" rather than asserting it.

```bash
# Is outbound :22 blocked from THIS machine?  (isolates local egress)
timeout 8 bash -c 'exec 3<>/dev/tcp/github.com/22' && echo "egress 22 OK"

# Is the host up at all?                      (isolates host liveness)
timeout 8 bash -c 'exec 3<>/dev/tcp/HOST/443' && echo "host up"

# Is the recorded address still current?      (isolates stale DNS/rebuilt instance)
dig +short folio.openlegalstandard.org A

# Has this machine ever connected before?     (isolates "never had access")
ssh-keygen -F HOST -f ~/.ssh/known_hosts
```

Those four controls are what made the SSH diagnosis correct. Outbound 22 worked,
the host answered on 443, DNS still pointed at the recorded address, and
`known_hosts` already held the host keys — so the only remaining explanation for a
*timeout* on 22 was a packet-dropping allowlist. That held up: the security group
was opened, `sshd` was never touched, and SSH worked immediately afterward.

**The security group is a fourth mutable variable in prod access**, alongside host,
user, and key. A home IP that rotates silently revokes access, and the symptom is a
timeout that reads like a dead box. Any "access is resolved" note that lists only
host and key is incomplete.

### State the scope of every absence claim

An absence claim is a claim about where you looked, so the scope is the claim. Name
the depth, the filters, and the exclusions, or do not assert the negative.

```bash
# Weak:  "no PEM anywhere under home"  (from a depth-limited, filtered search)
# Strong: name the scope in the claim itself
find "$HOME" -name '*.pem' -type f -not -path '*/node_modules/*' 2>&1 | head -60
echo "(end; empty = none found at any depth under \$HOME)"
```

Never send stderr to `/dev/null` on a command whose empty output you intend to read
as a negative result. Silence from a command that never ran is indistinguishable
from a real clean result.

### A third-party prober's status code describes the prober

This is the specific error that produced the false outage. Three "independent"
services were queried and all three failed, which looked like corroboration:

- `allorigins` returned **522** — Cloudflare's *own* upstream-timeout code for that
  service's fetch infrastructure.
- `downforeveryoneorjustme` returned **403** — that site refusing an automated
  request.
- `r.jina.ai` returned **000** — the local `curl` getting no response from the
  *prober*.

Not one of those observed the origin. Three unrelated failures of three unrelated
services were read as three votes for the same conclusion. **Correlated failure of
your instruments is not evidence about the subject.**

If an external vantage point is genuinely needed, use one that reports the origin's
response explicitly, and treat any non-2xx from the prober itself as "no data",
never as "target down".

### Vary the client before concluding the server is broken

`000` says this client got nothing. The cheapest next step is to change one client
property and retry:

```bash
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0 Safari/537.36'
curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' --max-time 25 -A "$UA" https://HOST/
```

In this session that single command returned `200 0.185s` and ended the
investigation.

### Do not load-test production to confirm a feature shipped

The burst that triggered all of this — roughly twelve rapid requests to
`/taxonomy/tree/search?query=a` — was fired to check whether PR #21's rate limiting
was live. That question was not worth asking, and the deploy question it was
nominally serving was already answered by a **single** request:

```bash
curl -s 'https://HOST/taxonomy/tree/search?query=deontic' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('hidden_root_count' in d['tree'])"
```

One request against the JSON payload proves a field's presence. Volume proves
nothing extra.

## Why This Matters

The false outage cost more than the real problem. It produced an urgent message
addressed to a third party, on a premise that was wrong, about a system that was
serving traffic normally. Had it been sent, it would have consumed someone else's
time and damaged the credibility of the next genuine alert.

It also nearly obscured a correct finding. The *same* session had already diagnosed
the SSH block correctly, and the user's pushback ("SSH should be running on the
box") was right and was confirmed. A session that over-claims on one probe makes its
sound conclusions harder to trust.

The cost asymmetry is what drives the rule. Running a control test costs one command
and a few seconds. Retracting a false production-outage claim costs a user's
attention, a correction, and trust.

## When to Apply

- Any time a probe against a remote host fails and you are about to characterize
  *why*, especially before telling a human that something is down.
- Before escalating to anyone who is not already in the conversation.
- When reaching for a third-party checker, uptime service, or proxy as
  "independent" confirmation.
- When a diagnosis rests on the *absence* of a response, or the absence of a file.
  Absence has many causes, and the observer is one of them.
- Before sending more than one request to a production endpoint to test a
  hypothesis about that endpoint.

## Examples

### The correct pass

> Port 22 times out while 443 is open, `github.com:22` is open from the same
> machine, DNS still resolves to the recorded address, and `known_hosts` already
> holds the host's keys. Therefore: packets to 22 are being dropped by an
> allowlist, and `sshd` is very likely fine.

Confirmed. The security group was opened and SSH worked, with no change to the
daemon.

### The incorrect pass

> Twelve rapid requests all return `000`. Three external probers also fail.
> Therefore: production is down and the app container behind Caddy is hung.

Wrong on the conclusion and on the corroboration. The probers reported their own
failures. The site was serving normally the whole time.

### What the tree says about the leading hypothesis

The session's initial explanation was that the burst tripped the app-level rate
limiter from PR #21. Checking the source refutes it on two independent grounds:

1. **Wrong response shape.** The limiter returns an HTTP response, not a dropped
   connection — `folio_api/rate_limit.py:328-338` builds a `JSONResponse` with
   `status_code=429` and a `Retry-After` header. A rate-limited client sees `429`,
   never `000`.
2. **Wrong tier, by a wide margin.** Tiers match by longest path prefix: prefixes are
   sorted longest-first at `folio_api/rate_limit.py:143-149` and matched first-wins by
   `path.startswith(pref)` at `:161-164`. The burst hit
   `/taxonomy/tree/search`, which matches neither `/search/llm/` nor `/search/`, so
   it fell to the `default` tier of **240/minute** (`config.json`, `api.rate_limit.tiers`).
   Twelve requests cannot trip a 240/minute limit.

**The `000` burst therefore remains unexplained.** That is the honest state. Note
how much better this reads than the original guess: two source reads turned a
confident wrong answer into a bounded open question. When the cause is unknown, the
useful artifact is the list of hypotheses you *eliminated*, not a plausible story.

### A related trap in the same family

While establishing which commit production ran, the `?v=` cache-bust token was read
as a build timestamp, putting production two releases further behind than it was.
It is not a build stamp: `_compute_asset_version` at `folio_api/api.py:61-75`
returns the newest **mtime** among static files, so it tracks file timestamps rather
than the release. It neither advances for a release that touches no static asset, nor
stays put across a deploy method that rewrites every file — a fresh clone or an image
rebuild bumps mtimes even when content is identical. It cannot date the deployed
commit in either direction. The reliable answer is `git rev-parse HEAD` on the
box. Same root error as the prober mistake — reading a signal as evidence for a
claim it was never measuring.

## Related

- `docs/plans/evidence/2026-09-20-pr23-prod-deploy-receipt.md` — the deploy this
  triage was performed around: rollback point, the sudo-docker correction, and the
  verification table. Its `## Note` records the same `000`-burst refutation and points
  back here.
- `docs/solutions/security-issues/2026-07-07-app-level-rate-limiting-restoration.md`
  — the limiter's design and its build-side verification trick (1-char queries prove
  the `/search/llm/` threshold at zero spend). This page adds the read-side: what a
  trip looks like to a client that did not intend one, and why `000` is not it.
- `docs/solutions/developer-experience/2026-09-19-codex-worker-sandbox-cannot-run-pytest-or-app.md`
  — closest sibling in method. A sandbox's read-only-filesystem error and a security
  group's packet drop are both the environment declining, and both are resolved by
  re-running the check from a vantage point where it can succeed.
- `docs/plans/2026-07-02-001-chore-deploy-entity-graph-to-prod-plan.md` — its "PROD
  access — RESOLVED" note lists host and key only, and is the kind of incomplete
  access record this page argues against.
- Issue #17 — prod config drift on the same box; background for why a deploy has to
  restore host-local `config.json`.
