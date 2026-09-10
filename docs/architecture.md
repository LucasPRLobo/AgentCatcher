# AgentCatcher — architecture & threat model

Status: design. This document is the north star; `docs/project_idea.md` is the original
brief and `docs/stack_plan.md` the tech stack. Where they disagree with this file on
scope, this file wins and they should be updated.

## What we are actually building

Not (only) a standalone honeypot that produces a dataset. The **product is a stealth
detection-and-deception overlay, shipped as middleware** that a real platform — a bank is
the guiding example — drops into its own application to catch an AI agent interfering with
its systems, respond silently, and leave a trail back to whoever is behind it.

The standalone decoy site we scope in the board is the **research testbed**: it generates
the labelled agent-vs-human data and lets us build and validate the layers safely, because
we cannot experiment on a real bank. The FastAPI logging middleware (AC-08) is the natural
delivery vehicle — a drop-in middleware is exactly how a platform would install this.

### The reframe that drives everything

The axis is **not** human-vs-agent. It is **authorised-vs-unauthorised**. A friendly agent
doing normal work for its consenting owner is fine; a hostile agent — or a hostile human —
enumerating decoy records is not. So "is this an agent?" is a **weighted signal into an
authorise-and-risk decision, not the verdict**. The detection target is *unauthorised
autonomous abuse*.

Three classes of visitor, not two:
1. **Legitimate humans** — admitted silently, as today.
2. **Authorised agents** — a customer's own assistant, an accessibility agent, a partner
   integration, our own internal agents. Admitted, but *known and scoped*.
3. **Hostile / unauthorised agents** — caught silently, then attributed.

And authorisation is **not** trust: an authorised agent can be hijacked (stolen delegation
token, confused deputy) or turn adversarial (the fired insider's assistant). So behavioural
monitoring runs on **everyone**, regardless of how they entered.

## The four layers (defense in depth)

Governing principle: **assume every layer can be broken.** Each layer exists because the
one before it can be bypassed. No layer trusts the layer before it.

> L0 decides *who you are* · L1 watches *what you do* · L2 decides *what to do about it* ·
> L3 tells you *who to send the bill to*.

### Layer 0 — Front Door · identity & delegation (the "naive handshake")
- **Does:** challenges cooperative agents to identify themselves — a per-request signature
  (Web Bot Auth / RFC 9421), a delegation token, or mTLS — and resolves most legitimate
  agent traffic up front as *known, scoped* principals. Delegation carries the on-behalf-of
  facts: which human, did they consent, what scope.
- **Catches:** unsophisticated hostile agents that do not expect a handshake; cleanly
  *labels* the honest ones.
- **Honest limits:** breakable and spoofable; most benign agents do not speak it yet.
  Therefore it is an **opt-in front door, not a wall** — humans bypass it entirely, and a
  friendly-but-unauthenticated agent gets a graceful lane (reduced scope + monitoring,
  never a lockout). Credentials must be **per-request signatures, not static secrets**
  (a static token can be stolen and replayed). Its value depends on a **trust root**; for
  research we run our own small registry, which does not generalise to the open web.
- **Principle:** grants *entry and scope*, not trust. Hands off to L1, which watches it anyway.

### Layer 1 — Laser Grid · behavioural detection & tripwires (silent, on everyone inside)
Runs on every visitor already inside, whatever door they used. Two halves:
- **Passive classifier** — request-stream + JS-beacon features (timing, inter-arrival
  regularity, exploration order, header stack, mouse/keystroke/scroll absence, superhuman
  sequences). Scores *unauthorised autonomous abuse*, with agent-ness as one weighted input.
- **Active tripwires** — honeytoken endpoints, canary records, hidden fields, prompt-
  injection canaries woven into the real app: surfaces **no legitimate principal touches**.
  A hit is high-signal.
- **Catches:** the hostile agent that spoofed or skipped L0, **and the authorised agent that
  turns** — hijacked token, confused deputy, insider. This is the layer that abstracts away
  "allowed = friendly".
- **Honest limits:** a perfect human-mimic beats the *passive* half; the *active* tripwires
  still catch it because they guard fake treasure it has no legitimate reason to reach.
  Passive detection decays as models improve (AC-41); tripwires decay far slower. In
  production, a **false positive on a real customer is catastrophic** — tune for near-zero
  false positives even at the cost of missed agents.

### Layer 2 — Silent Alarm · graduated response & containment
- **Does:** responds *silently* — flag → elevate monitoring → shadow / tarpit (feed
  plausible fake data, let them keep reaching) → contain / revoke / eject on a human's call.
  Never blocks or errors in a way that tells the intruder they tripped a wire.
- **Response is keyed by L0 identity:** authorised + tripped → notify the owner, revoke the
  token; unknown + tripped → silent watch + SOC.
- **Reconciliation of dwell-vs-risk:** because the lasers guard *decoy* surfaces woven into
  the real app, we can safely dwell and gather evidence — the intruder is reaching for
  something that is not real.

### Layer 3 — The Trail · attribution & forensics ("find out who hired them")
- **Does:** canary tokens that fire at *use* time — linking the stealthy recon session to
  the noisy exploitation session and revealing the next hop of infrastructure. Plus
  model/framework fingerprint (which tool), planted identifiers that re-link sessions across
  IP rotation, and network/OPSEC correlation.
- **Honest limits:** realistically delivers "autonomous agent, this model/framework, this
  infra trail, loot went *here*" — rarely the named human principal. It hands a strong
  thread to threat-intel or law enforcement. Works regardless of how good the mimicry was,
  and decays far slower than detection.

## Threats, and where each is stopped

| Threat | Stopped at |
|---|---|
| Naive hostile agent, does not expect a handshake | L0 |
| Agent that spoofs or skips the handshake | L1 (behaviour + tripwire) |
| Perfect human-mimic stealth agent | L1 active tripwires + L3 canary |
| Authorised agent hijacked, or insider-turned-adversary | L1 (behaviour change); response keyed by L0 identity |
| Anything that successfully exfiltrates | L3 canary fires at use-time |

## Cross-cutting principles (hold at every layer)

- **Stealth.** Silent to the intruder; detection changes *watching*, never the visitor's
  experience. The only loud, opt-in surface is the L0 front door.
- **Assume breach.** Each layer is defeatable; the next is why that is survivable.
- **Precision.** In a real platform a false alarm on a customer is catastrophic; optimise
  for near-zero false positives.
- **Separation (leakage firewall).** Lure hits, canary hits and handshake outcomes are
  *labels and forensics*, never classifier features — the same firewall as `lure_hits`
  (see `docs/stack_plan.md`, AC-05, AC-35). A feature that can see the label makes the
  classifier useless for flagging before the bait is touched.

## What is novel here

Human-vs-agent detection is relatively easy and crowded. The differentiated, paper-worthy
question this architecture exposes is **authorised-agent vs hostile-agent when both are
agents** — telling a customer's real assistant from an attacker's assistant by behaviour and
intent, not by whether it is automated. The dataset therefore has three classes (human /
authorised-agent / hostile-agent), and the honest hard evaluation is against a stealth agent
built to mimic a human, held out from training.
