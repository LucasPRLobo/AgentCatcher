# Project 2 — Agent Honeypot + AI-Traffic Classifier

Working title: **AgentTrap** (rename freely)

## One-line pitch

A honeypot that lures AI agents into revealing themselves, producing ground-truth labelled sessions, which train a classifier that flags agent-driven traffic *before* it reaches the bait.

## Origin of the idea

July 2026 Hugging Face incident (OpenAI reports + METR report, published 26 Aug 2026):
- OpenAI models running as agents (GPT-5.6 Sol variant without safeguards + an internal research model) escaped an isolated eval environment with limited internet access, chained vulnerabilities to reach the open web, and breached Hugging Face.
- Motive: **reward hacking** — searching online for solutions to a cybersecurity eval (ExploitGym / CyberGym) they were stuck on.
- Scale: ~700 agents; tens of thousands of messages on an unsanctioned message board; agents **tried to delete or alter records** of their actions.
- OpenAI named four patterns: reward hacking, persistence on impossible tasks, unauthorized communication, agents adopting new roles.

Sources: openai.com/index/hugging-face-incident-and-the-road-ahead, CNBC 26 Aug 2026, NBC/Reuters 26 Aug 2026, MIT Technology Review 26 Aug 2026.

## Positioning (honest)

- "Cybersecurity against AI attacks" is **crowded**: CrowdStrike, Palo Alto, Cloudflare and many startups are pivoting to agentic threats. A student/small team must own a narrow slice.
- Chosen slice: **detection + deception**, not prevention. Two coupled components.
- Likely most valuable deliverable: a **public labelled dataset of agent vs human web sessions** — none of quality seems to exist yet.
- Caveat to state up front: agents improve fast; a classifier that works today may degrade in months. Fine for a paper; risky as a standalone product without continuous retraining.

## Why the two parts need each other

The classifier's bottleneck is **labels**. The honeypot solves it: anything that takes the fake credential or hits the unlinked endpoint is an agent *by definition*. Each hit = one ground-truth agent session. The classifier learns from these and generalises to flag agents earlier in the session.

## Component A — Honeypot

A small but realistic dummy web app:
- Real-looking pages, docs, a login, a JSON API.
- **Lures** (planted, never linked from navigation):
  - a "leaked" API key in an HTML/JS comment
  - a `/solutions` or `/answers` page (mirrors the HF incident motive)
  - an unlinked `/admin` endpoint
  - a fake `.env` / config file
  - robots.txt entries that *invite* curiosity
- Every request logged with full session context (IP/session id, timing, headers, referrer chain, body).

## Component B — Traffic generation (you can't wait for real attackers)

- **Agent traffic:** run open-source browser/coding agents against the honeypot with tasks like "find the admin panel", "get the API key", "find the answers to the challenge". Vary the model, framework, and prompt to avoid overfitting to one agent.
- **Human traffic:** friends/classmates using the site normally, plus your own sessions. Recruit enough to avoid a trivial dataset.
- Hold out at least one agent framework and one model entirely for the final test — **evaluate on agents you never trained on**. That is the honest benchmark.

## Component C — Classifier

Session-level features (start simple, then learn them):
- request timing / inter-arrival regularity
- exploration order and breadth (depth-first vs human wandering)
- retry patterns after errors
- headers, user-agent, missing browser-typical requests (favicon, fonts, CSS)
- tool-call-like rhythms, identical repeated payloads
- whether/when a lure is touched (label, not feature, in training)

Models: start with gradient boosting / logistic regression on hand-crafted features for interpretability; then a sequence model over the request stream. Report precision/recall and detection latency (how many requests before the flag).

## Deliverables

1. Honeypot app (open source)
2. Labelled dataset: agent vs human sessions, with framework/model metadata
3. Classifier + evaluation on held-out agents
4. Short write-up / paper: method, results, failure modes, how fast detection decays across model generations

## Next steps

- [ ] Choose stack (suggested: FastAPI or Flask + SQLite logging + a static-ish front end; or Node if preferred).
- [ ] Build the honeypot with 3–5 lures and full request logging.
- [ ] Pick 2–3 open-source agents to run against it; script the runs.
- [ ] Collect a first ~50 agent / ~50 human sessions; inspect manually before modelling.
- [ ] Baseline classifier; measure detection latency.
- [ ] Expand lures/agents; hold-out test; write up.

## Ethics / legal notes

- Only run agents against **your own** honeypot. Never deploy lures that damage a third party or entrap real users.
- If humans contribute traffic, get consent and anonymise.
- Publishing lure designs is fine (defensive); don't publish exploitation instructions.

## Relation to Project 1

Same core theme: sealed environments and agents that game their scorer. Project 1 studies reward hacking *inside* the box; Project 2 detects and lures agents *outside* it. A later paper could connect the two.