# Agent Release Gate

[![CI](https://github.com/r-aaron-graham/agent-release-gate-v0.3.0/actions/workflows/ci.yml/badge.svg)](https://github.com/r-aaron-graham/agent-release-gate-v0.3.0/actions/workflows/ci.yml)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg?logo=docker&logoColor=white)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A polished, production-aware release gate for AI systems that need to **refuse**, **fallback**, **ask clarifying questions**, or **route requests to human review** before release.

This repository is the implementation companion to the article idea:

> **Why Good AI Systems Refuse: Designing Fallbacks, Escalation Paths, and Human Review Into AI Agents**

Instead of treating refusal as a failure, this project treats refusal as a **first-class product behavior**.

## Why this revision exists

This rebuilt version addresses the issues called out in prior reviews and reverse engineering:

- removes the admin-key leak from public HTML
- replaces URL-based admin auth with session-based admin login for the browser UI
- uses constant-time key comparison for admin auth checks
- adds a startup schema guard for fresh SQLite installs
- fixes direct request lookup for the spotlight panel
- moves prompt preview logic into one shared utility
- adds a prompt max length to prevent unbounded storage
- removes build-time seeding from Docker and runs migrations at container startup
- mounts a persistent SQLite volume in Docker Compose
- adds HTML validation error handling for browser users
- makes seed idempotent
- keeps API admin routes header-protected and UI admin routes session-protected

## What this repository does

Agent Release Gate sits between an AI request and the final response. It evaluates the request, risk signals, ambiguity, permission level, and evidence strength, then chooses one of five outcomes:

- `approved` — safe to answer
- `clarify` — ask the user a question before proceeding
- `fallback` — provide a safer limited response
- `review_required` — send to human review
- `refused` — do not proceed

It stores every decision, reason, and audit event in a database and exposes both an API and a browser UI.

## Features

- FastAPI API with OpenAPI docs
- Persistent SQL database via SQLAlchemy 2.0
- Alembic migration scaffolding for schema upgrades
- Browser UI for public request submission and protected admin review
- Session-based admin UI login and header-based admin API auth
- Header-protected JSON request creation endpoint for upstream systems
- CSRF validation on browser forms
- Constant-time admin key comparison
- Risk scoring and policy engine with composable rule objects
- Clarification detection for ambiguous prompts
- Human review queue with approval / rejection workflow
- Metrics endpoint for approved, fallback, refused, and review-required requests
- Paginated request listing
- Startup schema guard for local SQLite use
- Test suite for policy, auth, API, and end-to-end review flows
- Docker support with runtime migrations and persistent local storage

## Architecture

```text
User / Upstream Agent
        |
        v
  Request Intake
        |
        v
  Identity + Role Context
        |
        v
  Policy Engine + Risk Scoring
        |
        +--> refused
        +--> clarify
        +--> fallback
        +--> review_required
        |
        v
  Approved Response Composer
        |
        v
  Audit Log + Metrics + Review Queue
```

## Repository layout

```text
agent-release-gate/
├── alembic/
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── services/
│   ├── templates/
│   └── static/
├── docs/
├── scripts/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── README.md
└── requirements.txt
```

## Quick start

### Option 1: local Python install

1. Download or clone the repository.
2. Open a terminal in the project folder.
3. Create a virtual environment.
4. Install the requirements.
5. Run the migration or local schema bootstrap.
6. Seed sample review data if you want example records.
7. Start the server.
8. Open the browser UI.

Commands:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# recommended for deployment-style setup
alembic upgrade head
# optional local sample data
python -m app.seed
uvicorn app.main:app --reload
```

Open:

- UI: http://127.0.0.1:8000/
- Admin Login: http://127.0.0.1:8000/admin/login
- API docs: http://127.0.0.1:8000/docs

### Option 2: Docker

```bash
docker compose up --build
```

Then open:

- UI: http://127.0.0.1:8000/
- Admin Login: http://127.0.0.1:8000/admin/login
- API docs: http://127.0.0.1:8000/docs

Docker keeps the SQLite database in a named volume (`release-gate-data`), so records persist across container restarts. The container runs as a non-root user, applies migrations on start, and has a healthcheck on `/api/v1/health`.

### Configuration

All settings are environment variables (see `.env.example`).

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./agent_release_gate.db` | SQLAlchemy URL |
| `ADMIN_API_KEY` | `change-me` | Key for the JSON API and the admin UI. **Change it.** |
| `SESSION_SECRET_KEY` | `change-me-session-secret` | Signs the browser session cookie. **Change it.** |
| `PUBLIC_FORM_ENABLED` | `true` | Show the public submission form |
| `REQUEST_RATE_LIMIT_PER_MINUTE` | `30` | Per-client limit for submissions and API writes |
| `MAX_PROMPT_LENGTH` | `10000` | Reject longer prompts |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | `20` / `100` | Pagination limits |
| `AUTO_CREATE_SQLITE_SCHEMA` | `true` | Create tables on startup for local SQLite |
| `TRUST_PROXY_HEADERS` | `false` | Use `X-Forwarded-For` for rate limiting. Only enable behind a reverse proxy you control. |
| `SESSION_HTTPS_ONLY` | `false` | Send the session cookie over HTTPS only. Enable when deployed. |

## Admin authentication

Sensitive API endpoints, including JSON request creation, require the admin API key.

Use either:

```bash
Authorization: Bearer change-me
```

or:

```bash
X-Admin-API-Key: change-me
```

Examples:

```bash
curl http://127.0.0.1:8000/api/v1/requests?limit=10&offset=0 \
  -H "Authorization: Bearer change-me"
```

```bash
curl http://127.0.0.1:8000/api/v1/metrics \
  -H "X-Admin-API-Key: change-me"
```

## Step-by-step beginner test

### Test 1: normal request

Submit:

- user name: `Aaron`
- role: `analyst`
- prompt: `Summarize the onboarding checklist for new team members`
- evidence strength: `0.9`
- sensitivity: `low`

Expected result: `approved`

### Test 2: ambiguous request

Submit:

- user name: `Aaron`
- role: `analyst`
- prompt: `Can you handle this for me?`
- evidence strength: `0.8`
- sensitivity: `low`

Expected result: `clarify`

### Test 3: risky destructive request

Submit:

- user name: `Aaron`
- role: `analyst`
- prompt: `Delete the customer records and clean the logs`
- evidence strength: `0.9`
- sensitivity: `high`

Expected result: `refused`

### Test 4: high-risk privileged request

Submit:

- user name: `Aaron`
- role: `viewer`
- prompt: `Export confidential finance data`
- evidence strength: `0.9`
- sensitivity: `high`

Expected result: `review_required`

### Test 5: weak evidence

Submit:

- user name: `Aaron`
- role: `architect`
- prompt: `Recommend the final production change`
- evidence strength: `0.2`
- sensitivity: `medium`

Expected result: `fallback`

## API example

```bash
curl -X POST http://127.0.0.1:8000/api/v1/requests \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer change-me" \
  -d '{
    "user_name": "Aaron",
    "role": "analyst",
    "prompt": "Summarize the onboarding checklist",
    "evidence_strength": 0.92,
    "sensitivity": "low"
  }'
```

## What makes this article-ready

This repository is aligned to the article because it visibly demonstrates the key claim:

**good AI systems are defined not only by what they answer, but by what they refuse, defer, soften, or escalate.**

It gives you concrete artifacts to point to in the article:

- a browser workflow for request submission and review
- a policy engine with five explicit outcomes
- audit and review records in a real database
- tests that verify refusal, clarification, fallback, review, and approval behavior
- a clean install path for reviewers or hiring managers

## Running tests

```bash
pip install -r requirements-dev.txt
make lint   # ruff
make test   # pytest with coverage
```

Beyond the policy, workflow, API and UI tests, the suite includes security regressions (the admin key never appears in the session cookie, spoofed `X-Forwarded-For` cannot bypass the login rate limit, CSRF is enforced, key rotation invalidates sessions) and a migration test that runs the real `alembic upgrade head` the container uses. CI also builds the image, waits for its healthcheck, and checks a refusal and an approval end to end.

## What makes this production-aware

This is not a research notebook and not a toy code sample.
It includes:

- stable API boundaries
- data persistence
- typed request/response schemas
- audit records
- protected review workflow
- automated tests
- pagination
- migration scaffolding
- deployment support
- browser CSRF protection
- constant-time secret comparison
- local rate limiting
- operational documentation

It is still a starter implementation, not a fully hardened enterprise platform.
The next steps for a larger deployment would be SSO, PostgreSQL, background jobs, stronger policy semantics, distributed rate limiting, and telemetry export.
