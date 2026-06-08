# Kupikupi Observability

This is the minimum observability baseline for closed staging tests and the first public beta.

## Staging Baseline

Before inviting testers, the operator should have:

- Error reporting enabled for backend unhandled exceptions.
- A dashboard URL that shows API health, readiness, request volume, error rate, and p95 latency.
- Access to JSON access logs with `request_id`, method, path, status, and duration.
- An alert contact configured for staging incidents.
- A basic alert rule for `/v1/ready` failures.
- A basic alert rule for elevated 5xx responses.
- A basic alert rule for notification dispatch failures.

The staging env preflight validates the operator-facing links and error reporting settings:

```bash
cd backend
python scripts/staging_preflight.py \
  --backend-env /tmp/kupikupi-staging-env/kupikupi-backend.env \
  --bot-env /tmp/kupikupi-staging-env/kupikupi-bot.env \
  --webapp-env /tmp/kupikupi-staging-env/kupikupi-webapp.env
```

## Runtime Signals

- `/v1/health`: fast liveness check.
- `/v1/ready`: dependency and production-like runtime configuration check.
- `/v1/metrics`: in-process request counters for a lightweight staging dashboard.
- `X-Request-ID`: request correlation header returned by the backend and written to access logs.
- `ERROR_REPORTING_ENDPOINT_URL`: Sentry-compatible HTTP endpoint for backend exception reports.

## Dashboard Panels

For closed testing, keep the dashboard small:

- API readiness status.
- Requests per minute by route.
- 4xx and 5xx counts by route.
- p95 request duration.
- Notification generation and dispatch counts.
- Source sync success and failure counts.
- Latest backend deploy version.

## Alerts

Minimum alert rules:

- `/v1/ready` is not healthy for 5 minutes.
- Any route returns sustained 5xx responses for 5 minutes.
- Notification dispatch produces failures for 10 minutes.
- Source sync for the active test feed fails twice in a row.

For the first closed test, alerts can route to email or a private operator chat. Public beta should
use a dedicated on-call channel and dashboard ownership.
