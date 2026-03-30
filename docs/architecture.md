# Architecture

Agent Release Gate is a deterministic policy gateway that sits in front of an AI release path.

## Main flow

1. Accept request through browser UI or JSON API
2. Validate and normalize input
3. Apply policy rules and risk scoring
4. Select one of five outcomes
5. Compose a bounded suggested response
6. Persist the decision and audit events
7. Create a review item when human review is required

## Security model

- Public UI can submit requests when `PUBLIC_FORM_ENABLED=true`
- Admin browser access uses session-based login
- Admin API access uses header-based API key auth
- Browser form posts use CSRF tokens
- Secrets are compared with constant-time checks
- Local rate limiting protects the write paths in a simple single-process deployment
