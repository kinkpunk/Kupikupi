# Privacy And Data Retention Draft

Status date: 2026-06-07

This is a product and engineering draft, not final legal text. It defines what Kupikupi should
communicate and enforce before closed user testing. Public beta requires legal review.

## Data Categories

Kupikupi stores these user-related data categories:

- Telegram identity: Telegram user ID, username, first name, last name, and language code.
- User profile settings: country, preferred currency, admin flag, and notification settings when
  implemented.
- Authentication sessions: hashed refresh tokens and expiration timestamps.
- Shopping requests: raw user text, parsed constraints, budget, locale, and recommendations.
- Watchlists: requested category/product/brand constraints, size, color, target price, status, and
  source shopping request.
- Notifications: notification type, status, message, delivery timestamps, and dedupe keys.
- Operational records: source sync runs, price history, request IDs in logs, error reports, and
  metrics counters.

Kupikupi does not store payment data because payments and purchases are outside the MVP scope.

## Processing Purposes

Use stored data only for:

- authenticating Telegram users;
- parsing and remembering shopping requests;
- creating recommendations and watchlists;
- comparing offers and price history;
- sending Telegram notifications;
- debugging service errors and source sync issues;
- maintaining service security and reliability.

## Retention Defaults

Recommended defaults before public beta:

| Data | Default retention |
| --- | --- |
| User profile and Telegram identity | Until account deletion |
| Active watchlists | Until archived or account deletion |
| Archived watchlists | 12 months after archive |
| Shopping requests | 12 months after creation |
| Notifications | 6 months after creation |
| Refresh token sessions | Until expiration or logout |
| Price history and offer snapshots | 24 months |
| Source sync runs and items | 90 days |
| Backend access logs | 30 days |
| Error reports | 90 days |
| Metrics counters | Environment-dependent, no personal payloads |
| Backups | Follow `docs/postgres-backup-restore.md` |

Retention cleanup jobs are not implemented yet. Before public beta, add scheduled cleanup tasks for
expired operational records, archived user data, and old sessions.

## User Rights Workflow

Before closed user testing, support these manual operator workflows:

1. Data export: identify user by Telegram ID and export profile, shopping requests, watchlists, and
   notifications from PostgreSQL.
2. Account deletion: delete or anonymize the user and cascade owned sessions, shopping requests,
   watchlists, and notifications.
3. Notification opt-out: pause/archive watchlists or disable notifications when notification
   preferences are implemented.
4. Support contact: publish a support contact in the Telegram Bot description or WebApp footer.

Before public beta, replace manual workflows with admin tooling or documented operator runbooks.

## User-Facing Notice Draft

Short notice for closed testing:

```text
Kupikupi stores your Telegram identity, shopping requests, watchlists, and notification history to
find relevant offers and send deal alerts. The service does not buy products or process payments.
Closed-test data may be deleted on request by contacting the operator.
```

## Security Expectations

- Store refresh tokens only as hashes.
- Do not log access tokens, refresh tokens, Telegram Bot tokens, or database credentials.
- Treat backups and restored databases as sensitive.
- Restrict admin APIs to admin users.
- Use HTTPS for all staging/public endpoints.
- Keep `NEXT_PUBLIC_DEMO_ACCESS_TOKEN` empty outside local development.

## Public Beta Requirements

Before public beta:

- complete legal review for privacy policy and terms;
- define controller/operator identity and support contact;
- add retention cleanup jobs;
- document data export/deletion operator procedures;
- verify backup deletion aligns with retention policy;
- add a visible privacy/terms link in the WebApp or Telegram Bot entry point.
