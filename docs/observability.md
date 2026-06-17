# Kupikupi Observability

Status date: 2026-06-17

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
  --webapp-env /tmp/kupikupi-staging-env/kupikupi-webapp.env \
  --operator-env /tmp/kupikupi-staging-env/kupikupi-operator.env
python scripts/field_test_checklist.py --env-dir /tmp/kupikupi-staging-env
```

The field-test checklist repeats the key observability checks as separate `error-reporting`,
`observability-dashboard`, and `alert-contact` items so the operator can see them without parsing the
full preflight issue list.

## Runtime Signals

- `/v1/health`: fast liveness check.
- `/v1/ready`: dependency and production-like runtime configuration check.
- `/v1/metrics`: in-process request counters for a lightweight staging dashboard.
- `X-Request-ID`: request correlation header returned by the backend and written to access logs.
- `traceparent`: W3C trace context header accepted by the backend, returned in responses, and
  included in error reports.
- `ERROR_REPORTING_ENDPOINT_URL`: Sentry-compatible HTTP endpoint for backend exception reports.

## Smoke Checklist

Run this checklist before the closed test starts:

1. Validate env values:

   ```bash
   cd backend
   python scripts/staging_preflight.py \
     --backend-env /tmp/kupikupi-staging-env/kupikupi-backend.env \
     --bot-env /tmp/kupikupi-staging-env/kupikupi-bot.env \
     --webapp-env /tmp/kupikupi-staging-env/kupikupi-webapp.env \
     --operator-env /tmp/kupikupi-staging-env/kupikupi-operator.env
   python scripts/field_test_checklist.py --env-dir /tmp/kupikupi-staging-env
   ```

2. Run remote smoke for health, readiness, metrics, WebApp, support, privacy, and terms:

   ```bash
   cd backend
   python scripts/staging_smoke.py \
     --api-base-url "$KUPIKUPI_API_BASE_URL" \
     --webapp-url "$KUPIKUPI_WEBAPP_URL" \
     --support-url "$KUPIKUPI_SUPPORT_URL" \
     --privacy-url "$KUPIKUPI_PRIVACY_URL" \
     --terms-url "$KUPIKUPI_TERMS_URL"
   ```

3. Open the dashboard and confirm these panels are populated or explicitly empty with a clear zero:
   `/v1/ready`, request volume, 4xx/5xx rate, p95 latency, source sync results, notification
   generation/dispatch, and latest deploy version.
4. Trigger a harmless endpoint such as `/v1/health` and confirm the request appears in logs with
   `request_id`, status, route, and duration.
5. Confirm `ALERT_CONTACT_URL` reaches the operator channel for the test window.
6. Confirm the error reporting project/collector receives backend exception events in staging.

Application-level error-reporting behavior is covered locally by:

```bash
cd backend
python -m pytest tests/test_error_reporting.py
```

If staging exposes a protected test route for deliberate errors in the future, use it to verify the
external collector end to end. Until then, treat `tests/test_error_reporting.py`, preflight env
validation, and dashboard inspection as the minimum closed-test baseline.

## Dashboard Panels

For closed testing, keep the dashboard small:

- API readiness status.
- Requests per minute by route.
- 4xx and 5xx counts by route.
- p95 request duration.
- Notification generation and dispatch counts.
- Source sync success and failure counts.
- Latest backend deploy version.
- Trace ID search for reported user sessions.

## Alerts

Minimum alert rules:

- `/v1/ready` is not healthy for 5 minutes.
- Any route returns sustained 5xx responses for 5 minutes.
- Notification dispatch produces failures for 10 minutes.
- Source sync for the active test feed fails twice in a row.

For the first closed test, alerts can route to email or a private operator chat. Public beta should
use a dedicated on-call channel and dashboard ownership.

## No-Go Conditions

- `ERROR_REPORTING_ENABLED` is off in staging.
- `ERROR_REPORTING_ENDPOINT_URL` is missing or not absolute HTTP(S).
- `OBSERVABILITY_DASHBOARD_URL` is missing or inaccessible to the operator.
- `ALERT_CONTACT_URL` is missing or unmonitored during the test window.
- The dashboard cannot show readiness, 5xx rate, source sync status, or notification failures.
