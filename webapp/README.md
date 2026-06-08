# Kupikupi WebApp

Telegram WebApp frontend for Kupikupi.

The first iteration lets a user submit a shopping request, inspect deterministic parser output,
and explicitly confirm watchlist creation.

## Development

```bash
cd webapp
npm install
npm run dev
```

The app expects the backend API at `NEXT_PUBLIC_API_BASE_URL`.
In Telegram, it authenticates with WebApp `initData` through `/auth/telegram`.
For local MVP testing outside Telegram, set `NEXT_PUBLIC_DEMO_ACCESS_TOKEN` to a backend access token.

Set `NEXT_PUBLIC_SUPPORT_CONTACT_URL`, `NEXT_PUBLIC_PRIVACY_POLICY_URL`, and
`NEXT_PUBLIC_TERMS_URL` to show support, privacy, and terms links in the WebApp entry point.

## Tests

```bash
npm test
```
