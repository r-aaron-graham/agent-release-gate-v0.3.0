# Testing Guide

Run the test suite:

```bash
pytest -q
```

Coverage focus:

- policy decisions
- negated destructive phrases
- admin API auth enforcement
- pagination contract
- spotlight request lookup
- review idempotency
- admin UI session login and protected dashboard access
- HTML validation response
