# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

AgentCatcher (working title "AgentTrap") is in early development: the repo is scaffolded, but the honeypot, traffic tooling and classifier are still mostly empty. `docs/project_idea.md` is the source of truth for scope and intent, and `docs/stack_plan.md` records the stack; read both before making design decisions.

## Commands

Python comes from the `agent-catcher` conda env. Poetry manages dependencies inside it (Poetry detects the active conda env, so it does not create its own virtualenv).

```bash
conda activate agent-catcher
poetry install --with dev        # add --with notebooks for Jupyter
poetry add <pkg>                 # runtime dependency; poetry add --group dev <pkg> for tooling

poetry run pytest                # all tests
poetry run pytest tests/test_app.py::test_fastapi_default_docs_are_not_exposed   # a single test
poetry run ruff format . && poetry run ruff check --fix .
poetry run uvicorn agentcatcher.honeypot.app:app --reload
```

CI (`.github/workflows/ci.yml`) runs `ruff format --check`, `ruff check` and `pytest` on every push and pull request.

## Layout

`src/agentcatcher/` has one subpackage per component: `honeypot/` (A), `traffic/` (B) and `classifier/` (C). `schemas.py` holds the pydantic models for the session log that all three share.

## Stack

From `docs/stack_plan.md`:

- **Honeypot:** FastAPI. Requests are logged to SQLite through SQLAlchemy 2.0, with Alembic migrations. Headers and other unstructured data go in JSON columns rather than a separate NoSQL store.
- **Decoy site:** starts as a minimal static page served by FastAPI's `StaticFiles`, and grows between experiments.
- **Classifier:** Python with scikit-learn, built as a ladder of increasing complexity: baseline (majority class + user-agent rule) → KNN → logistic regression → random forest → gradient boosting.

Implementation rules that follow from this:

- Log in a pure ASGI middleware wrapping the whole app (not `BaseHTTPMiddleware` or per-route logging), so 404s, unrouted probes and static-asset requests are all captured and bodies are read without being consumed. Stamp arrival with `time.time_ns()` at middleware entry.
- Never serve static assets from a separate web server: favicon, CSS and font requests must reach the log, because their absence is a classifier signal.
- The decoy app keeps FastAPI's `/docs`, `/redoc` and `/openapi.json` disabled; they would reveal the stack and list every route.
- `.gitignore` ignores only the repo-root `/.env`, so the fake `.env` lure files the honeypot serves stay tracked.
- Every session records the decoy site's version (git commit), because the site changes between experiments.
- With SQLite, run a single uvicorn worker or enable WAL mode.
- KNN and logistic regression go behind a `StandardScaler` in a `Pipeline`. Every model is scored by the same evaluation harness, including detection latency.

## What is being built

A honeypot that lures AI agents into revealing themselves, producing ground-truth labelled sessions that train a classifier to flag agent-driven web traffic *before* it reaches the bait. The main research deliverable is a public labelled dataset of agent vs human web sessions.

Three coupled components:

- **A — Honeypot:** a small, realistic dummy web app, starting as a static page, with docs, a login and a JSON API added in later iterations. It has lures that are planted but never linked from navigation — a "leaked" API key in an HTML/JS comment, a `/solutions` or `/answers` page, an unlinked `/admin` endpoint, a fake `.env`/config file, curiosity-inviting `robots.txt` entries. Every request is logged with full session context (IP/session id, timing, headers, referrer chain, body).
- **B — Traffic generation:** scripted runs of open-source browser/coding agents against the honeypot (varying model, framework, prompt), plus consented human sessions.
- **C — Classifier:** session-level features (inter-arrival timing regularity, exploration order/breadth, retry patterns after errors, headers/user-agent, missing browser-typical requests like favicon/fonts/CSS, repeated identical payloads). Start with the classifier ladder (see Stack) on hand-crafted features, then a sequence model over the request stream. Report precision/recall and **detection latency** (requests before the flag).

## Invariants that must hold across components

- **Lure contact is the label, not a feature.** A session that touches a lure is an agent by definition. Never feed lure-hit signals into classifier features — that leaks the label and makes the classifier useless for flagging agents *before* they reach the bait.
- **Honest evaluation:** hold out at least one agent framework and one model entirely from training; the final benchmark is on agents never seen in training. Keep framework/model metadata on every agent session so this split is possible.
- Session logging must be complete enough to reconstruct the full request stream per session, since both hand-crafted features and the sequence model are derived from it.

## Ethics / legal constraints

- Only run agents against our own honeypot. Never deploy lures that damage third parties or entrap real users.
- Human-contributed traffic requires consent and must be anonymised before it enters the dataset.
- Publishing lure designs is fine (defensive); do not publish exploitation instructions.
