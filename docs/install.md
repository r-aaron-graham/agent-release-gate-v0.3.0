# Install Guide

## Fast local setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

## Docker setup

```bash
docker compose up --build
```

## Notes

- The browser admin UI uses a session cookie after login at `/admin/login`.
- Sensitive API routes, including JSON request creation, use the admin API key via `Authorization: Bearer ...` or `X-Admin-API-Key`.
- Browser forms include CSRF tokens.
- Local SQLite installs auto-create the schema on first start when `AUTO_CREATE_SQLITE_SCHEMA=true`.
